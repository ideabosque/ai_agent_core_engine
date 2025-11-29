#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict, List

from promise import Promise
from silvaengine_utility.cache import HybridCacheEngine

from ...handlers.config import Config
from ..run import RunModel
from .base import SafeDataLoader, normalize_model


class RunsByThreadLoader(SafeDataLoader):
    """Batch loader for fetching runs by thread_uuid."""

    def __init__(self, logger=None, cache_enabled=True, **kwargs):
        super(RunsByThreadLoader, self).__init__(
            logger=logger, cache_enabled=cache_enabled, **kwargs
        )
        if self.cache_enabled:
            self.cache = HybridCacheEngine(
                Config.get_cache_name("models", "runs_by_thread")
            )

    def batch_load_fn(self, keys: List[str]) -> Promise:
        """
        Load runs for multiple thread_uuids.
        Keys are thread_uuids (string).
        """
        unique_keys = list(dict.fromkeys(keys))
        key_map: Dict[str, List[Dict[str, Any]]] = {}
        uncached_keys = []

        # Check cache first if enabled
        if self.cache_enabled:
            for key in unique_keys:
                cache_key = key  # thread_uuid
                cached_item = self.cache.get(cache_key)
                if cached_item:
                    key_map[key] = cached_item
                else:
                    uncached_keys.append(key)
        else:
            uncached_keys = unique_keys

        # Batch fetch uncached items
        if uncached_keys:
            try:
                for thread_uuid in uncached_keys:
                    runs = list(RunModel.query(thread_uuid))

                    normalized_runs = [normalize_model(run) for run in runs]

                    key_map[thread_uuid] = normalized_runs

                    # Cache the result if enabled
                    if self.cache_enabled:
                        self.cache.set(
                            thread_uuid, normalized_runs, ttl=Config.get_cache_ttl()
                        )

            except Exception as exc:  # pragma: no cover - defensive
                if self.logger:
                    self.logger.exception(exc)

        return Promise.resolve([key_map.get(key, []) for key in keys])
