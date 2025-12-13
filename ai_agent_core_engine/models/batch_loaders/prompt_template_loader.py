#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict, List, Tuple

from promise import Promise
from silvaengine_utility.cache import HybridCacheEngine

from ...handlers.config import Config
from ..prompt_template import PromptTemplateModel
from .base import SafeDataLoader, normalize_model

Key = Tuple[str, str]


class PromptTemplateLoader(SafeDataLoader):
    """Batch loader for PromptTemplateModel keyed by (partition_key, prompt_uuid) returning the active version."""

    def __init__(self, logger=None, cache_enabled=True, **kwargs):
        super(PromptTemplateLoader, self).__init__(
            logger=logger, cache_enabled=cache_enabled, **kwargs
        )
        if self.cache_enabled:
            self.cache = HybridCacheEngine(
                Config.get_cache_name("models", "prompt_template")
            )

    def batch_load_fn(self, keys: List[Key]) -> Promise:
        unique_keys = list(dict.fromkeys(keys))
        key_map: Dict[Key, Dict[str, Any]] = {}
        uncached_keys = []

        # Check cache first if enabled
        if self.cache_enabled:
            for key in unique_keys:
                cache_key = f"{key[0]}:{key[1]}"  # partition_key:prompt_uuid
                cached_item = self.cache.get(cache_key)
                if cached_item:
                    key_map[key] = cached_item
                else:
                    uncached_keys.append(key)
        else:
            uncached_keys = unique_keys

        # Fetch uncached items via prompt_uuid_index for the active version
        if uncached_keys:
            try:
                for partition_key, prompt_uuid in uncached_keys:
                    results = PromptTemplateModel.prompt_uuid_index.query(
                        partition_key,
                        PromptTemplateModel.prompt_uuid == prompt_uuid,
                        filter_condition=(PromptTemplateModel.status == "active"),
                        scan_index_forward=False,
                        limit=1,
                    )
                    try:
                        prompt_template = next(results)
                    except StopIteration:
                        prompt_template = None

                    if prompt_template:
                        normalized = normalize_model(prompt_template)
                        key_map[(partition_key, prompt_uuid)] = normalized

                        if self.cache_enabled:
                            cache_key = f"{partition_key}:{prompt_uuid}"
                            self.cache.set(
                                cache_key, normalized, ttl=Config.get_cache_ttl()
                            )

            except Exception as exc:  # pragma: no cover - defensive
                if self.logger:
                    self.logger.exception(exc)

        return Promise.resolve([key_map.get(key) for key in keys])
