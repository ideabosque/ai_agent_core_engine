#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict, List

from promise import Promise
from silvaengine_utility.cache import HybridCacheEngine

from ...handlers.config import Config
from .base import SafeDataLoader, normalize_model, Key


class McpServerToolLoader(SafeDataLoader):
    """Batch loader for McpServerModel keyed by (partition_key, mcp_server_uuid)."""

    def __init__(self, logger=None, cache_enabled=True, **kwargs):
        super(McpServerToolLoader, self).__init__(
            logger=logger, cache_enabled=cache_enabled, **kwargs
        )
        if self.cache_enabled:
            self.cache = HybridCacheEngine(
                Config.get_cache_name("models", "mcp_server_tools")
            )
            cache_meta = Config.get_cache_entity_config().get("mcp_server")
            self.cache_func_prefix = ""
            if cache_meta:
                self.cache_func_prefix = ".".join([cache_meta.get("module"), "_run_list_tools"])

    def generate_cache_key(self, key: Key) -> str:
        if not isinstance(key, tuple):
            key = (key,)
        key_data = ":".join([str(key), str({})])
        return self.cache._generate_key(
            self.cache_func_prefix,
            key_data
        )
    
    def get_cache_data(self, key: Key) -> Dict[str, Any] | None | List[Dict[str, Any]]:
        cache_key = self.generate_cache_key(key)
        cached_item = self.cache.get(cache_key)
        if cached_item is None:  # pragma: no cover - defensive
            return None
        if isinstance(cached_item, dict):  # pragma: no cover - defensive
            return cached_item
        if isinstance(cached_item, list):  # pragma: no cover - defensive
            return [normalize_model(item) if not isinstance(item, dict) else item for item in cached_item]
        return normalize_model(cached_item)

    def set_cache_data(self, key: Key, data: Any) -> None:
        cache_key = self.generate_cache_key(key)
        self.cache.set(cache_key, data, ttl=Config.get_cache_ttl())

    def batch_load_fn(self, keys: List[Key]) -> Promise:
        from ..mcp_server import _load_list_tools
        unique_keys = list(dict.fromkeys(keys))
        key_map: Dict[Key, Dict[str, Any]] = {}
        uncached_keys = []
        # Check cache first if enabled
        if self.cache_enabled:
            for key in unique_keys:
                cached_item = self.get_cache_data(key)
                if cached_item:
                    key_map[key] = cached_item
                else:
                    uncached_keys.append(key)
        else:
            uncached_keys = unique_keys
            
        # Batch fetch uncached items
        if uncached_keys:
            try:
                for mcp_server_url, headers_tuple in uncached_keys:
                    key = (mcp_server_url, headers_tuple)
                    mcp_server_tools = _load_list_tools(self.logger, {"mcp_server_url":mcp_server_url, "headers": dict(headers_tuple)})

                    if self.cache_enabled:
                            self.set_cache_data(key, mcp_server_tools)
                    key_map[key] = mcp_server_tools

            except Exception as exc:  # pragma: no cover - defensive
                if self.logger:
                    self.logger.exception(exc)

        return Promise.resolve([key_map.get(key) for key in keys])
