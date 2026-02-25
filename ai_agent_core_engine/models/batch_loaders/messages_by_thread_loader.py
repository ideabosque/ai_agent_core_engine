#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict, List

from promise import Promise
from silvaengine_utility.cache import HybridCacheEngine

from ...handlers.config import Config
from .base import Key, SafeDataLoader, normalize_model


class MessagesByThreadLoader(SafeDataLoader):
    """Batch loader for fetching messages by thread_uuid."""

    def __init__(self, logger=None, cache_enabled=True, **kwargs):
        super(MessagesByThreadLoader, self).__init__(
            logger=logger, cache_enabled=cache_enabled, **kwargs
        )
        if self.cache_enabled:
            self.cache = HybridCacheEngine(Config.get_cache_name("models", "message"))
            cache_meta = Config.get_cache_entity_config().get("message")
            self.cache_func_prefix = ""
            if cache_meta:
                self.cache_func_prefix = ".".join(
                    [cache_meta.get("module"), "get_messages_by_thread"]
                )

    def generate_cache_key(self, key: Key) -> str:
        if not isinstance(key, tuple):
            key = (key,)
        key_data = ":".join([str(key), str({})])
        return self.cache._generate_key(self.cache_func_prefix, key_data)

    def get_cache_data(self, key: Key) -> Dict[str, Any] | None | List[Dict[str, Any]]:
        cache_key = self.generate_cache_key(key)
        cached_item = self.cache.get(cache_key)
        if cached_item is None:  # pragma: no cover - defensive
            return None
        if isinstance(cached_item, dict):  # pragma: no cover - defensive
            return cached_item
        if isinstance(cached_item, list):  # pragma: no cover - defensive
            return [normalize_model(item) for item in cached_item]
        return normalize_model(cached_item)

    def set_cache_data(self, key: Key, data: Any) -> None:
        cache_key = self.generate_cache_key(key)
        self.cache.set(cache_key, data, ttl=Config.get_cache_ttl())

    def batch_load_fn(self, keys: List[str]) -> Promise:
        from ..message import get_messages_by_thread

        """
        Load messages for multiple thread_uuids.
        Keys are thread_uuids (string).
        """
        unique_keys = list(dict.fromkeys(keys))
        key_map: Dict[str, List[Dict[str, Any]]] = {}
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
                for thread_uuid in uncached_keys:
                    messages = get_messages_by_thread(thread_uuid)

                    normalized_messages = [normalize_model(msg) for msg in messages]
                    key_map[thread_uuid] = normalized_messages

            except Exception as exc:  # pragma: no cover - defensive
                if self.logger:
                    self.logger.exception(exc)

        return Promise.resolve([key_map.get(key, []) for key in keys])
