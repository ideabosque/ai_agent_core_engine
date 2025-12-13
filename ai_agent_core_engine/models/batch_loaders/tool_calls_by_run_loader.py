#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict, List

from promise import Promise
from silvaengine_utility.cache import HybridCacheEngine

from ...handlers.config import Config
from .base import SafeDataLoader, normalize_model


class ToolCallsByRunLoader(SafeDataLoader):
    """Batch loader for fetching tool calls by run_uuid."""

    def __init__(self, logger=None, cache_enabled=True, **kwargs):
        super(ToolCallsByRunLoader, self).__init__(
            logger=logger, cache_enabled=cache_enabled, **kwargs
        )
        if self.cache_enabled:
            self.cache = HybridCacheEngine(
                Config.get_cache_name("models", "tool_calls_by_run")
            )

    def batch_load_fn(self, keys: List[str]) -> Promise:
        """
        Load tool calls for multiple run_uuids.
        Keys are run_uuids (string).
        """
        unique_keys = list(dict.fromkeys(keys))
        key_map: Dict[str, List[Dict[str, Any]]] = {}
        uncached_keys = []

        # Check cache first if enabled
        if self.cache_enabled:
            for key in unique_keys:
                cache_key = key  # run_uuid
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
                from ..tool_call import ToolCallModel

                for run_uuid in uncached_keys:
                    tool_calls = list(
                        ToolCallModel.run_uuid_index.query(
                            ToolCallModel.run_uuid == run_uuid
                        )
                    )

                    normalized_tool_calls = [normalize_model(tc) for tc in tool_calls]

                    key_map[run_uuid] = normalized_tool_calls

                    # Cache the result if enabled
                    if self.cache_enabled:
                        self.cache.set(
                            run_uuid, normalized_tool_calls, ttl=Config.get_cache_ttl()
                        )

            except Exception as exc:  # pragma: no cover - defensive
                if self.logger:
                    self.logger.exception(exc)

        return Promise.resolve([key_map.get(key, []) for key in keys])
