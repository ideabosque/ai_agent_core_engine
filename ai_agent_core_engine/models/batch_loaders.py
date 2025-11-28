#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict, List, Tuple

from promise import Promise
from promise.dataloader import DataLoader
from silvaengine_utility import Utility
from silvaengine_utility.cache import HybridCacheEngine

from ..handlers.config import Config
from .agent import AgentModel
from .element import ElementModel
from .flow_snippet import FlowSnippetModel
from .llm import LlmModel
from .mcp_server import MCPServerModel
from .message import MessageModel
from .prompt_template import PromptTemplateModel
from .run import RunModel
from .thread import ThreadModel
from .ui_component import UIComponentModel
from .wizard import WizardModel
from .wizard_group import WizardGroupModel

# Type aliases for readability
Key = Tuple[str, str]


def _normalize_model(model: Any) -> Dict[str, Any]:
    """Safely convert a Pynamo model into a plain dict."""
    return Utility.json_normalize(model.__dict__["attribute_values"])


class _SafeDataLoader(DataLoader):
    """
    Base DataLoader that swallows and logs errors rather than breaking the entire
    request. This keeps individual load failures isolated.
    """

    def __init__(self, logger=None, cache_enabled=True, **kwargs):
        super(_SafeDataLoader, self).__init__(**kwargs)
        self.logger = logger
        self.cache_enabled = cache_enabled and Config.is_cache_enabled()

    def dispatch(self):
        try:
            return super(_SafeDataLoader, self).dispatch()
        except Exception as exc:  # pragma: no cover - defensive
            if self.logger:
                self.logger.exception(exc)
            raise


class LlmLoader(_SafeDataLoader):
    """Batch loader for LlmModel records keyed by (llm_provider, llm_name)."""

    def __init__(self, logger=None, cache_enabled=True, **kwargs):
        super(LlmLoader, self).__init__(
            logger=logger, cache_enabled=cache_enabled, **kwargs
        )
        if self.cache_enabled:
            self.cache = HybridCacheEngine(Config.get_cache_name("models", "llm"))

    def batch_load_fn(self, keys: List[Key]) -> Promise:
        unique_keys = list(dict.fromkeys(keys))
        key_map: Dict[Key, Dict[str, Any]] = {}
        uncached_keys = []

        # Check cache first if enabled
        if self.cache_enabled:
            for key in unique_keys:
                cache_key = f"{key[0]}:{key[1]}"  # llm_provider:llm_name
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
                for llm in LlmModel.batch_get(uncached_keys):
                    normalized = _normalize_model(llm)
                    key = (llm.llm_provider, llm.llm_name)
                    key_map[key] = normalized

                    # Cache the result if enabled
                    if self.cache_enabled:
                        cache_key = f"{key[0]}:{key[1]}"
                        self.cache.set(
                            cache_key, normalized, ttl=Config.get_cache_ttl()
                        )

            except Exception as exc:  # pragma: no cover - defensive
                if self.logger:
                    self.logger.exception(exc)

        return Promise.resolve([key_map.get(key) for key in keys])


class McpServerLoader(_SafeDataLoader):
    """Batch loader for McpServerModel keyed by (endpoint_id, mcp_server_uuid)."""

    def __init__(self, logger=None, cache_enabled=True, **kwargs):
        super(McpServerLoader, self).__init__(
            logger=logger, cache_enabled=cache_enabled, **kwargs
        )
        if self.cache_enabled:
            self.cache = HybridCacheEngine(
                Config.get_cache_name("models", "mcp_server")
            )

    def batch_load_fn(self, keys: List[Key]) -> Promise:
        unique_keys = list(dict.fromkeys(keys))
        key_map: Dict[Key, Dict[str, Any]] = {}
        uncached_keys = []

        # Check cache first if enabled
        if self.cache_enabled:
            for key in unique_keys:
                cache_key = f"{key[0]}:{key[1]}"  # endpoint_id:mcp_server_uuid
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
                for mcp in MCPServerModel.batch_get(uncached_keys):
                    normalized = _normalize_model(mcp)
                    key = (mcp.endpoint_id, mcp.mcp_server_uuid)
                    key_map[key] = normalized

                    # Cache the result if enabled
                    if self.cache_enabled:
                        cache_key = f"{key[0]}:{key[1]}"
                        self.cache.set(
                            cache_key, normalized, ttl=Config.get_cache_ttl()
                        )

            except Exception as exc:  # pragma: no cover - defensive
                if self.logger:
                    self.logger.exception(exc)

        return Promise.resolve([key_map.get(key) for key in keys])


class AgentLoader(_SafeDataLoader):
    """Batch loader for AgentModel keyed by (endpoint_id, agent_version_uuid)."""

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
                cache_key = f"{key[0]}:{key[1]}"  # endpoint_id:agent_version_uuid
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
                for agent in AgentModel.batch_get(uncached_keys):
                    normalized = _normalize_model(agent)
                    key = (agent.endpoint_id, agent.agent_version_uuid)
                    key_map[key] = normalized

                    # Cache the result if enabled
                    if self.cache_enabled:
                        cache_key = f"{key[0]}:{key[1]}"
                        self.cache.set(
                            cache_key, normalized, ttl=Config.get_cache_ttl()
                        )

            except Exception as exc:  # pragma: no cover - defensive
                if self.logger:
                    self.logger.exception(exc)

        return Promise.resolve([key_map.get(key) for key in keys])


class ThreadLoader(_SafeDataLoader):
    """Batch loader for ThreadModel keyed by (endpoint_id, thread_uuid)."""

    def __init__(self, logger=None, cache_enabled=True, **kwargs):
        super(ThreadLoader, self).__init__(
            logger=logger, cache_enabled=cache_enabled, **kwargs
        )
        if self.cache_enabled:
            self.cache = HybridCacheEngine(Config.get_cache_name("models", "thread"))

    def batch_load_fn(self, keys: List[Key]) -> Promise:
        unique_keys = list(dict.fromkeys(keys))
        key_map: Dict[Key, Dict[str, Any]] = {}
        uncached_keys = []

        # Check cache first if enabled
        if self.cache_enabled:
            for key in unique_keys:
                cache_key = f"{key[0]}:{key[1]}"  # endpoint_id:thread_uuid
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
                for thread in ThreadModel.batch_get(uncached_keys):
                    normalized = _normalize_model(thread)
                    key = (thread.endpoint_id, thread.thread_uuid)
                    key_map[key] = normalized

                    # Cache the result if enabled
                    if self.cache_enabled:
                        cache_key = f"{key[0]}:{key[1]}"
                        self.cache.set(
                            cache_key, normalized, ttl=Config.get_cache_ttl()
                        )

            except Exception as exc:  # pragma: no cover - defensive
                if self.logger:
                    self.logger.exception(exc)

        return Promise.resolve([key_map.get(key) for key in keys])


class RunLoader(_SafeDataLoader):
    """Batch loader for RunModel keyed by (thread_uuid, run_uuid)."""

    def __init__(self, logger=None, cache_enabled=True, **kwargs):
        super(RunLoader, self).__init__(
            logger=logger, cache_enabled=cache_enabled, **kwargs
        )
        if self.cache_enabled:
            self.cache = HybridCacheEngine(Config.get_cache_name("models", "run"))

    def batch_load_fn(self, keys: List[Key]) -> Promise:
        unique_keys = list(dict.fromkeys(keys))
        key_map: Dict[Key, Dict[str, Any]] = {}
        uncached_keys = []

        # Check cache first if enabled
        if self.cache_enabled:
            for key in unique_keys:
                cache_key = f"{key[0]}:{key[1]}"  # thread_uuid:run_uuid
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
                for run in RunModel.batch_get(uncached_keys):
                    normalized = _normalize_model(run)
                    key = (run.thread_uuid, run.run_uuid)
                    key_map[key] = normalized

                    # Cache the result if enabled
                    if self.cache_enabled:
                        cache_key = f"{key[0]}:{key[1]}"
                        self.cache.set(
                            cache_key, normalized, ttl=Config.get_cache_ttl()
                        )

            except Exception as exc:  # pragma: no cover - defensive
                if self.logger:
                    self.logger.exception(exc)

        return Promise.resolve([key_map.get(key) for key in keys])


class MessageLoader(_SafeDataLoader):
    """Batch loader for MessageModel keyed by (thread_uuid, message_uuid)."""

    def __init__(self, logger=None, cache_enabled=True, **kwargs):
        super(MessageLoader, self).__init__(
            logger=logger, cache_enabled=cache_enabled, **kwargs
        )
        if self.cache_enabled:
            self.cache = HybridCacheEngine(Config.get_cache_name("models", "message"))

    def batch_load_fn(self, keys: List[Key]) -> Promise:
        unique_keys = list(dict.fromkeys(keys))
        key_map: Dict[Key, Dict[str, Any]] = {}
        uncached_keys = []

        # Check cache first if enabled
        if self.cache_enabled:
            for key in unique_keys:
                cache_key = f"{key[0]}:{key[1]}"  # thread_uuid:message_uuid
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
                for message in MessageModel.batch_get(uncached_keys):
                    normalized = _normalize_model(message)
                    key = (message.thread_uuid, message.message_uuid)
                    key_map[key] = normalized

                    # Cache the result if enabled
                    if self.cache_enabled:
                        cache_key = f"{key[0]}:{key[1]}"
                        self.cache.set(
                            cache_key, normalized, ttl=Config.get_cache_ttl()
                        )

            except Exception as exc:  # pragma: no cover - defensive
                if self.logger:
                    self.logger.exception(exc)

        return Promise.resolve([key_map.get(key) for key in keys])


class PromptTemplateLoader(_SafeDataLoader):
    """Batch loader for PromptTemplateModel keyed by (endpoint_id, prompt_version_uuid)."""

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
                cache_key = f"{key[0]}:{key[1]}"  # endpoint_id:prompt_version_uuid
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
                for prompt in PromptTemplateModel.batch_get(uncached_keys):
                    normalized = _normalize_model(prompt)
                    key = (prompt.endpoint_id, prompt.prompt_version_uuid)
                    key_map[key] = normalized

                    # Cache the result if enabled
                    if self.cache_enabled:
                        cache_key = f"{key[0]}:{key[1]}"
                        self.cache.set(
                            cache_key, normalized, ttl=Config.get_cache_ttl()
                        )

            except Exception as exc:  # pragma: no cover - defensive
                if self.logger:
                    self.logger.exception(exc)

        return Promise.resolve([key_map.get(key) for key in keys])


class FlowSnippetLoader(_SafeDataLoader):
    """Batch loader for FlowSnippetModel keyed by (endpoint_id, flow_snippet_version_uuid)."""

    def __init__(self, logger=None, cache_enabled=True, **kwargs):
        super(FlowSnippetLoader, self).__init__(
            logger=logger, cache_enabled=cache_enabled, **kwargs
        )
        if self.cache_enabled:
            self.cache = HybridCacheEngine(
                Config.get_cache_name("models", "flow_snippet")
            )

    def batch_load_fn(self, keys: List[Key]) -> Promise:
        unique_keys = list(dict.fromkeys(keys))
        key_map: Dict[Key, Dict[str, Any]] = {}
        uncached_keys = []

        # Check cache first if enabled
        if self.cache_enabled:
            for key in unique_keys:
                cache_key = (
                    f"{key[0]}:{key[1]}"  # endpoint_id:flow_snippet_version_uuid
                )
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
                for flow_snippet in FlowSnippetModel.batch_get(uncached_keys):
                    normalized = _normalize_model(flow_snippet)
                    key = (
                        flow_snippet.endpoint_id,
                        flow_snippet.flow_snippet_version_uuid,
                    )
                    key_map[key] = normalized

                    # Cache the result if enabled
                    if self.cache_enabled:
                        cache_key = f"{key[0]}:{key[1]}"
                        self.cache.set(
                            cache_key, normalized, ttl=Config.get_cache_ttl()
                        )

            except Exception as exc:  # pragma: no cover - defensive
                if self.logger:
                    self.logger.exception(exc)

        return Promise.resolve([key_map.get(key) for key in keys])


class WizardLoader(_SafeDataLoader):
    """Batch loader for WizardModel keyed by (endpoint_id, wizard_uuid)."""

    def __init__(self, logger=None, cache_enabled=True, **kwargs):
        super(WizardLoader, self).__init__(
            logger=logger, cache_enabled=cache_enabled, **kwargs
        )
        if self.cache_enabled:
            self.cache = HybridCacheEngine(Config.get_cache_name("models", "wizard"))

    def batch_load_fn(self, keys: List[Key]) -> Promise:
        unique_keys = list(dict.fromkeys(keys))
        key_map: Dict[Key, Dict[str, Any]] = {}
        uncached_keys = []

        # Check cache first if enabled
        if self.cache_enabled:
            for key in unique_keys:
                cache_key = f"{key[0]}:{key[1]}"  # endpoint_id:wizard_uuid
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
                for wizard in WizardModel.batch_get(uncached_keys):
                    normalized = _normalize_model(wizard)
                    key = (wizard.endpoint_id, wizard.wizard_uuid)
                    key_map[key] = normalized

                    # Cache the result if enabled
                    if self.cache_enabled:
                        cache_key = f"{key[0]}:{key[1]}"
                        self.cache.set(
                            cache_key, normalized, ttl=Config.get_cache_ttl()
                        )

            except Exception as exc:  # pragma: no cover - defensive
                if self.logger:
                    self.logger.exception(exc)

        return Promise.resolve([key_map.get(key) for key in keys])


class ElementLoader(_SafeDataLoader):
    """Batch loader for ElementModel keyed by (endpoint_id, element_uuid)."""

    def __init__(self, logger=None, cache_enabled=True, **kwargs):
        super(ElementLoader, self).__init__(
            logger=logger, cache_enabled=cache_enabled, **kwargs
        )
        if self.cache_enabled:
            self.cache = HybridCacheEngine(Config.get_cache_name("models", "element"))

    def batch_load_fn(self, keys: List[Key]) -> Promise:
        unique_keys = list(dict.fromkeys(keys))
        key_map: Dict[Key, Dict[str, Any]] = {}
        uncached_keys = []

        # Check cache first if enabled
        if self.cache_enabled:
            for key in unique_keys:
                cache_key = f"{key[0]}:{key[1]}"  # endpoint_id:element_uuid
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
                for element in ElementModel.batch_get(uncached_keys):
                    normalized = _normalize_model(element)
                    key = (element.endpoint_id, element.element_uuid)
                    key_map[key] = normalized

                    # Cache the result if enabled
                    if self.cache_enabled:
                        cache_key = f"{key[0]}:{key[1]}"
                        self.cache.set(
                            cache_key, normalized, ttl=Config.get_cache_ttl()
                        )

            except Exception as exc:  # pragma: no cover - defensive
                if self.logger:
                    self.logger.exception(exc)

        return Promise.resolve([key_map.get(key) for key in keys])


class WizardGroupLoader(_SafeDataLoader):
    """Batch loader for WizardGroupModel keyed by (endpoint_id, wizard_group_uuid)."""

    def __init__(self, logger=None, cache_enabled=True, **kwargs):
        super(WizardGroupLoader, self).__init__(
            logger=logger, cache_enabled=cache_enabled, **kwargs
        )
        if self.cache_enabled:
            self.cache = HybridCacheEngine(
                Config.get_cache_name("models", "wizard_group")
            )

    def batch_load_fn(self, keys: List[Key]) -> Promise:
        unique_keys = list(dict.fromkeys(keys))
        key_map: Dict[Key, Dict[str, Any]] = {}
        uncached_keys = []

        # Check cache first if enabled
        if self.cache_enabled:
            for key in unique_keys:
                cache_key = f"{key[0]}:{key[1]}"  # endpoint_id:wizard_group_uuid
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
                for wizard_group in WizardGroupModel.batch_get(uncached_keys):
                    normalized = _normalize_model(wizard_group)
                    key = (wizard_group.endpoint_id, wizard_group.wizard_group_uuid)
                    key_map[key] = normalized

                    # Cache the result if enabled
                    if self.cache_enabled:
                        cache_key = f"{key[0]}:{key[1]}"
                        self.cache.set(
                            cache_key, normalized, ttl=Config.get_cache_ttl()
                        )

            except Exception as exc:  # pragma: no cover - defensive
                if self.logger:
                    self.logger.exception(exc)

        return Promise.resolve([key_map.get(key) for key in keys])


class ThreadsByAgentLoader(_SafeDataLoader):
    """Batch loader for fetching threads by agent_uuid."""

    def __init__(self, logger=None, cache_enabled=True, **kwargs):
        super(ThreadsByAgentLoader, self).__init__(
            logger=logger, cache_enabled=cache_enabled, **kwargs
        )
        if self.cache_enabled:
            self.cache = HybridCacheEngine(
                Config.get_cache_name("models", "threads_by_agent")
            )

    def batch_load_fn(self, keys: List[Key]) -> Promise:
        """
        Load threads for multiple agent_uuids.
        Keys are tuples of (endpoint_id, agent_uuid).
        """
        unique_keys = list(dict.fromkeys(keys))
        key_map: Dict[Key, List[Dict[str, Any]]] = {}
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

        # Batch fetch uncached items
        if uncached_keys:
            try:
                # Group by endpoint_id for efficient querying
                from collections import defaultdict

                endpoint_groups = defaultdict(list)
                for endpoint_id, agent_uuid in uncached_keys:
                    endpoint_groups[endpoint_id].append(agent_uuid)

                # Query for each endpoint
                for endpoint_id, agent_uuids in endpoint_groups.items():
                    for agent_uuid in agent_uuids:
                        # Query threads for this agent using the index
                        threads = list(
                            ThreadModel.agent_uuid_index.query(
                                endpoint_id, ThreadModel.agent_uuid == agent_uuid
                            )
                        )

                        # Normalize threads
                        normalized_threads = [
                            _normalize_model(thread) for thread in threads
                        ]

                        key = (endpoint_id, agent_uuid)
                        key_map[key] = normalized_threads

                        # Cache the result if enabled
                        if self.cache_enabled:
                            cache_key = f"{endpoint_id}:{agent_uuid}"
                            self.cache.set(
                                cache_key,
                                normalized_threads,
                                ttl=Config.get_cache_ttl(),
                            )

            except Exception as exc:  # pragma: no cover - defensive
                if self.logger:
                    self.logger.exception(exc)

        return Promise.resolve([key_map.get(key, []) for key in keys])


class RunsByThreadLoader(_SafeDataLoader):
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
                    # Query runs for this thread using the primary key
                    runs = list(RunModel.query(thread_uuid))

                    # Normalize runs
                    normalized_runs = [_normalize_model(run) for run in runs]

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


class MessagesByRunLoader(_SafeDataLoader):
    """Batch loader for fetching messages by run_uuid."""

    def __init__(self, logger=None, cache_enabled=True, **kwargs):
        super(MessagesByRunLoader, self).__init__(
            logger=logger, cache_enabled=cache_enabled, **kwargs
        )
        if self.cache_enabled:
            self.cache = HybridCacheEngine(
                Config.get_cache_name("models", "messages_by_run")
            )

    def batch_load_fn(self, keys: List[str]) -> Promise:
        """
        Load messages for multiple run_uuids.
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
                for run_uuid in uncached_keys:
                    # Query messages for this run
                    messages = list(
                        MessageModel.run_uuid_index.query(
                            MessageModel.run_uuid == run_uuid
                        )
                    )

                    # Normalize messages
                    normalized_messages = [_normalize_model(msg) for msg in messages]

                    key_map[run_uuid] = normalized_messages

                    # Cache the result if enabled
                    if self.cache_enabled:
                        self.cache.set(
                            run_uuid, normalized_messages, ttl=Config.get_cache_ttl()
                        )

            except Exception as exc:  # pragma: no cover - defensive
                if self.logger:
                    self.logger.exception(exc)

        return Promise.resolve([key_map.get(key, []) for key in keys])


class MessagesByThreadLoader(_SafeDataLoader):
    """Batch loader for fetching messages by thread_uuid."""

    def __init__(self, logger=None, cache_enabled=True, **kwargs):
        super(MessagesByThreadLoader, self).__init__(
            logger=logger, cache_enabled=cache_enabled, **kwargs
        )
        if self.cache_enabled:
            self.cache = HybridCacheEngine(
                Config.get_cache_name("models", "messages_by_thread")
            )

    def batch_load_fn(self, keys: List[str]) -> Promise:
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
                import pendulum

                # Only retrieve messages from the past 24 hours
                updated_at_gt = pendulum.now("UTC").subtract(hours=24)

                for thread_uuid in uncached_keys:
                    # Query messages for this thread using updated_at_index
                    messages = list(
                        MessageModel.updated_at_index.query(
                            thread_uuid,
                            MessageModel.updated_at > updated_at_gt,
                        )
                    )

                    # Normalize messages
                    normalized_messages = [_normalize_model(msg) for msg in messages]

                    key_map[thread_uuid] = normalized_messages

                    # Cache the result if enabled
                    if self.cache_enabled:
                        self.cache.set(
                            thread_uuid, normalized_messages, ttl=Config.get_cache_ttl()
                        )

            except Exception as exc:  # pragma: no cover - defensive
                if self.logger:
                    self.logger.exception(exc)

        return Promise.resolve([key_map.get(key, []) for key in keys])


class ToolCallsByRunLoader(_SafeDataLoader):
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
                from .tool_call import ToolCallModel

                for run_uuid in uncached_keys:
                    # Query tool calls for this run
                    tool_calls = list(
                        ToolCallModel.run_uuid_index.query(
                            ToolCallModel.run_uuid == run_uuid
                        )
                    )

                    # Normalize tool calls
                    normalized_tool_calls = [_normalize_model(tc) for tc in tool_calls]

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


class ToolCallsByThreadLoader(_SafeDataLoader):
    """Batch loader for fetching tool calls by thread_uuid."""

    def __init__(self, logger=None, cache_enabled=True, **kwargs):
        super(ToolCallsByThreadLoader, self).__init__(
            logger=logger, cache_enabled=cache_enabled, **kwargs
        )
        if self.cache_enabled:
            self.cache = HybridCacheEngine(
                Config.get_cache_name("models", "tool_calls_by_thread")
            )

    def batch_load_fn(self, keys: List[str]) -> Promise:
        """
        Load tool calls for multiple thread_uuids.
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
                import pendulum

                from .tool_call import ToolCallModel

                # Only retrieve tool calls from the past 24 hours
                updated_at_gt = pendulum.now("UTC").subtract(hours=24)

                for thread_uuid in uncached_keys:
                    # Query tool calls for this thread
                    tool_calls = list(
                        ToolCallModel.updated_at_index.query(
                            thread_uuid,
                            ToolCallModel.updated_at > updated_at_gt,
                        )
                    )

                    # Normalize tool calls
                    normalized_tool_calls = [_normalize_model(tc) for tc in tool_calls]

                    key_map[thread_uuid] = normalized_tool_calls

                    # Cache the result if enabled
                    if self.cache_enabled:
                        self.cache.set(
                            thread_uuid,
                            normalized_tool_calls,
                            ttl=Config.get_cache_ttl(),
                        )

            except Exception as exc:  # pragma: no cover - defensive
                if self.logger:
                    self.logger.exception(exc)

        return Promise.resolve([key_map.get(key, []) for key in keys])


class AgentsByFlowSnippetLoader(_SafeDataLoader):
    """Batch loader for fetching agents by flow_snippet_version_uuid."""

    def __init__(self, logger=None, cache_enabled=True, **kwargs):
        super(AgentsByFlowSnippetLoader, self).__init__(
            logger=logger, cache_enabled=cache_enabled, **kwargs
        )
        if self.cache_enabled:
            self.cache = HybridCacheEngine(
                Config.get_cache_name("models", "agents_by_flow_snippet")
            )

    def batch_load_fn(self, keys: List[Key]) -> Promise:
        """
        Load agents for multiple flow_snippet_version_uuids.
        Keys are tuples of (endpoint_id, flow_snippet_version_uuid).
        """
        unique_keys = list(dict.fromkeys(keys))
        key_map: Dict[Key, List[Dict[str, Any]]] = {}
        uncached_keys = []

        # Check cache first if enabled
        if self.cache_enabled:
            for key in unique_keys:
                cache_key = (
                    f"{key[0]}:{key[1]}"  # endpoint_id:flow_snippet_version_uuid
                )
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
                for endpoint_id, flow_snippet_version_uuid in uncached_keys:
                    # Query agents for this endpoint with filter condition
                    agents = list(
                        AgentModel.query(
                            endpoint_id,
                            filter_condition=(
                                AgentModel.flow_snippet_version_uuid
                                == flow_snippet_version_uuid
                            ),
                        )
                    )

                    # Normalize agents
                    normalized_agents = [_normalize_model(agent) for agent in agents]

                    key = (endpoint_id, flow_snippet_version_uuid)
                    key_map[key] = normalized_agents

                    # Cache the result if enabled
                    if self.cache_enabled:
                        cache_key = f"{endpoint_id}:{flow_snippet_version_uuid}"
                        self.cache.set(
                            cache_key, normalized_agents, ttl=Config.get_cache_ttl()
                        )

            except Exception as exc:  # pragma: no cover - defensive
                if self.logger:
                    self.logger.exception(exc)

        return Promise.resolve([key_map.get(key, []) for key in keys])


class AgentsByLlmLoader(_SafeDataLoader):
    """Batch loader for fetching agents by LLM (llm_provider, llm_name)."""

    def __init__(self, logger=None, cache_enabled=True, **kwargs):
        super(AgentsByLlmLoader, self).__init__(
            logger=logger, cache_enabled=cache_enabled, **kwargs
        )
        if self.cache_enabled:
            self.cache = HybridCacheEngine(
                Config.get_cache_name("models", "agents_by_llm")
            )

    def batch_load_fn(self, keys: List[Tuple[str, str, str]]) -> Promise:
        """
        Load agents for multiple LLMs.
        Keys are tuples of (endpoint_id, llm_provider, llm_name).
        """
        unique_keys = list(dict.fromkeys(keys))
        key_map: Dict[Tuple[str, str, str], List[Dict[str, Any]]] = {}
        uncached_keys = []

        # Check cache first if enabled
        if self.cache_enabled:
            for key in unique_keys:
                cache_key = (
                    f"{key[0]}:{key[1]}:{key[2]}"  # endpoint_id:llm_provider:llm_name
                )
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
                for endpoint_id, llm_provider, llm_name in uncached_keys:
                    # Query agents for this endpoint with filter condition
                    agents = list(
                        AgentModel.query(
                            endpoint_id,
                            filter_condition=(
                                (AgentModel.llm_provider == llm_provider)
                                & (AgentModel.llm_name == llm_name)
                            ),
                        )
                    )

                    # Normalize agents
                    normalized_agents = [_normalize_model(agent) for agent in agents]

                    key = (endpoint_id, llm_provider, llm_name)
                    key_map[key] = normalized_agents

                    # Cache the result if enabled
                    if self.cache_enabled:
                        cache_key = f"{endpoint_id}:{llm_provider}:{llm_name}"
                        self.cache.set(
                            cache_key, normalized_agents, ttl=Config.get_cache_ttl()
                        )

            except Exception as exc:  # pragma: no cover - defensive
                if self.logger:
                    self.logger.exception(exc)

        return Promise.resolve([key_map.get(key, []) for key in keys])


class UIComponentLoader(_SafeDataLoader):
    """Batch loader for UIComponentModel keyed by (ui_component_type, ui_component_uuid)."""

    def __init__(self, logger=None, cache_enabled=True, **kwargs):
        super(UIComponentLoader, self).__init__(
            logger=logger, cache_enabled=cache_enabled, **kwargs
        )
        if self.cache_enabled:
            self.cache = HybridCacheEngine(
                Config.get_cache_name("models", "ui_component")
            )

    def batch_load_fn(self, keys: List[Key]) -> Promise:
        unique_keys = list(dict.fromkeys(keys))
        key_map: Dict[Key, Dict[str, Any]] = {}
        uncached_keys = []

        # Check cache first if enabled
        if self.cache_enabled:
            for key in unique_keys:
                cache_key = f"{key[0]}:{key[1]}"  # ui_component_type:ui_component_uuid
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
                for ui_component in UIComponentModel.batch_get(uncached_keys):
                    normalized = _normalize_model(ui_component)
                    key = (
                        ui_component.ui_component_type,
                        ui_component.ui_component_uuid,
                    )
                    key_map[key] = normalized

                    # Cache the result if enabled
                    if self.cache_enabled:
                        cache_key = f"{key[0]}:{key[1]}"
                        self.cache.set(
                            cache_key, normalized, ttl=Config.get_cache_ttl()
                        )

            except Exception as exc:  # pragma: no cover - defensive
                if self.logger:
                    self.logger.exception(exc)

        return Promise.resolve([key_map.get(key) for key in keys])


class RequestLoaders:
    """Container for all DataLoaders scoped to a single GraphQL request."""

    def __init__(self, context: Dict[str, Any], cache_enabled: bool = True):
        logger = context.get("logger")
        self.cache_enabled = cache_enabled

        self.llm_loader = LlmLoader(logger=logger, cache_enabled=cache_enabled)
        self.mcp_server_loader = McpServerLoader(
            logger=logger, cache_enabled=cache_enabled
        )
        self.agent_loader = AgentLoader(logger=logger, cache_enabled=cache_enabled)
        self.thread_loader = ThreadLoader(logger=logger, cache_enabled=cache_enabled)
        self.run_loader = RunLoader(logger=logger, cache_enabled=cache_enabled)
        self.message_loader = MessageLoader(logger=logger, cache_enabled=cache_enabled)
        self.prompt_template_loader = PromptTemplateLoader(
            logger=logger, cache_enabled=cache_enabled
        )
        self.flow_snippet_loader = FlowSnippetLoader(
            logger=logger, cache_enabled=cache_enabled
        )
        self.wizard_loader = WizardLoader(logger=logger, cache_enabled=cache_enabled)
        self.element_loader = ElementLoader(logger=logger, cache_enabled=cache_enabled)
        self.wizard_group_loader = WizardGroupLoader(
            logger=logger, cache_enabled=cache_enabled
        )
        self.ui_component_loader = UIComponentLoader(
            logger=logger, cache_enabled=cache_enabled
        )

        # One-to-many relationship loaders
        self.threads_by_agent_loader = ThreadsByAgentLoader(
            logger=logger, cache_enabled=cache_enabled
        )
        self.runs_by_thread_loader = RunsByThreadLoader(
            logger=logger, cache_enabled=cache_enabled
        )
        self.messages_by_run_loader = MessagesByRunLoader(
            logger=logger, cache_enabled=cache_enabled
        )
        self.messages_by_thread_loader = MessagesByThreadLoader(
            logger=logger, cache_enabled=cache_enabled
        )
        self.tool_calls_by_run_loader = ToolCallsByRunLoader(
            logger=logger, cache_enabled=cache_enabled
        )
        self.tool_calls_by_thread_loader = ToolCallsByThreadLoader(
            logger=logger, cache_enabled=cache_enabled
        )
        self.agents_by_flow_snippet_loader = AgentsByFlowSnippetLoader(
            logger=logger, cache_enabled=cache_enabled
        )
        self.agents_by_llm_loader = AgentsByLlmLoader(
            logger=logger, cache_enabled=cache_enabled
        )

    def invalidate_cache(self, entity_type: str, entity_keys: Dict[str, str]):
        """Invalidate specific cache entries when entities are modified."""
        if not self.cache_enabled:
            return

        if entity_type == "llm" and "llm_name" in entity_keys:
            cache_key = f"{entity_keys.get('llm_provider')}:{entity_keys['llm_name']}"
            if hasattr(self.llm_loader, "cache"):
                self.llm_loader.cache.delete(cache_key)
        elif entity_type == "mcp_server" and "mcp_server_uuid" in entity_keys:
            cache_key = (
                f"{entity_keys.get('endpoint_id')}:{entity_keys['mcp_server_uuid']}"
            )
            if hasattr(self.mcp_server_loader, "cache"):
                self.mcp_server_loader.cache.delete(cache_key)
        elif entity_type == "agent" and "agent_version_uuid" in entity_keys:
            cache_key = (
                f"{entity_keys.get('endpoint_id')}:{entity_keys['agent_version_uuid']}"
            )
            if hasattr(self.agent_loader, "cache"):
                self.agent_loader.cache.delete(cache_key)
        elif entity_type == "thread" and "thread_uuid" in entity_keys:
            cache_key = f"{entity_keys.get('endpoint_id')}:{entity_keys['thread_uuid']}"
            if hasattr(self.thread_loader, "cache"):
                self.thread_loader.cache.delete(cache_key)
        elif entity_type == "run" and "run_uuid" in entity_keys:
            cache_key = f"{entity_keys.get('thread_uuid')}:{entity_keys['run_uuid']}"
            if hasattr(self.run_loader, "cache"):
                self.run_loader.cache.delete(cache_key)
        elif entity_type == "message" and "message_uuid" in entity_keys:
            cache_key = (
                f"{entity_keys.get('thread_uuid')}:{entity_keys['message_uuid']}"
            )
            if hasattr(self.message_loader, "cache"):
                self.message_loader.cache.delete(cache_key)
        elif entity_type == "prompt_template" and "prompt_version_uuid" in entity_keys:
            cache_key = (
                f"{entity_keys.get('endpoint_id')}:{entity_keys['prompt_version_uuid']}"
            )
            if hasattr(self.prompt_template_loader, "cache"):
                self.prompt_template_loader.cache.delete(cache_key)
        elif (
            entity_type == "flow_snippet" and "flow_snippet_version_uuid" in entity_keys
        ):
            cache_key = f"{entity_keys.get('endpoint_id')}:{entity_keys['flow_snippet_version_uuid']}"
            if hasattr(self.flow_snippet_loader, "cache"):
                self.flow_snippet_loader.cache.delete(cache_key)


def get_loaders(context: Dict[str, Any]) -> RequestLoaders:
    """Fetch or initialize request-scoped loaders from the GraphQL context."""
    if context is None:
        context = {}

    loaders = context.get("batch_loaders")
    if not loaders:
        # Check if caching is enabled
        cache_enabled = Config.is_cache_enabled()
        loaders = RequestLoaders(context, cache_enabled=cache_enabled)
        context["batch_loaders"] = loaders
    return loaders


def clear_loaders(context: Dict[str, Any]) -> None:
    """Clear loaders from context (useful for tests)."""
    if context is None:
        return
    context.pop("batch_loaders", None)
