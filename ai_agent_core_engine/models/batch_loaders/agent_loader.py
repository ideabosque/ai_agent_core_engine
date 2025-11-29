#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict, List, Tuple

from promise import Promise
from silvaengine_utility.cache import HybridCacheEngine

from ...handlers.config import Config
from ..agent import AgentModel
from .base import SafeDataLoader, normalize_model

Key = Tuple[str, str]


class AgentLoader(SafeDataLoader):
    """Batch loader for AgentModel keyed by (endpoint_id, agent_uuid) returning the active version."""

    def __init__(self, logger=None, cache_enabled=True, **kwargs):
        super(AgentLoader, self).__init__(
            logger=logger, cache_enabled=cache_enabled, **kwargs
        )
        if self.cache_enabled:
            self.cache = HybridCacheEngine(Config.get_cache_name("models", "agent"))

    def batch_load_fn(self, keys: List[Key]) -> Promise:
        unique_keys = list(dict.fromkeys(keys))
        key_map: Dict[Key, Dict[str, Any]] = {}
        uncached_keys = []

        # Check cache first if enabled
        if self.cache_enabled:
            for key in unique_keys:
                cache_key = f"{key[0]}:{key[1]}"  # endpoint_id:agent_uuid
                cached_item = self.cache.get(cache_key)
                if cached_item:
                    key_map[key] = cached_item
                else:
                    uncached_keys.append(key)
        else:
            uncached_keys = unique_keys

        # Fetch uncached items via agent_uuid_index, returning the latest active version
        if uncached_keys:
            try:
                for endpoint_id, agent_uuid in uncached_keys:
                    results = AgentModel.agent_uuid_index.query(
                        endpoint_id,
                        AgentModel.agent_uuid == agent_uuid,
                        filter_condition=(AgentModel.status == "active"),
                        scan_index_forward=False,
                        limit=1,
                    )
                    try:
                        agent = next(results)
                    except StopIteration:
                        agent = None

                    if agent:
                        normalized = normalize_model(agent)
                        key_map[(endpoint_id, agent_uuid)] = normalized
                        if self.cache_enabled:
                            cache_key = f"{endpoint_id}:{agent_uuid}"
                            self.cache.set(
                                cache_key, normalized, ttl=Config.get_cache_ttl()
                            )

            except Exception as exc:  # pragma: no cover - defensive
                if self.logger:
                    self.logger.exception(exc)

        return Promise.resolve([key_map.get(key) for key in keys])
