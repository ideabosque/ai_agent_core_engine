# -*- coding: utf-8 -*-
"""PGRequestLoaders — PostgreSQL DataLoader container with 16 lazy loader properties.

Property names match the DynamoDB RequestLoaders exactly so that
cross-entity helpers and nested type resolvers work unchanged.
"""
from __future__ import print_function

__author__ = "bibow"

import importlib
from typing import Any, Dict, Optional


class PGRequestLoaders:
    """Request-scoped PostgreSQL DataLoader container.

    Each property lazily imports and creates the corresponding PG loader.
    Loaders are memoized on the instance for request-scoped batching.
    """

    def __init__(self, context: Dict[str, Any], cache_enabled: bool = True) -> None:
        self._context = context
        self._cache_enabled = cache_enabled
        self._loaders: Dict[str, Any] = {}

    def _get_loader(self, loader_name: str, module_name: str) -> Any:
        if loader_name in self._loaders:
            return self._loaders[loader_name]
        try:
            mod = importlib.import_module(
                f"ai_agent_core_engine.models.postgresql.batch_loaders.{module_name}"
            )
            # Construct from the capitalized class name (e.g. llm_loader -> LlmLoader)
            # Strip trailing "_loader" so we don't double up to "LlmLoaderLoader".
            base = module_name.removesuffix("_loader")
            cls_name = "".join(
                p.capitalize() for p in base.split("_")
            ) + "Loader"
            loader_cls = getattr(mod, cls_name, None)
            if loader_cls is None:
                raise RuntimeError(
                    f"PostgreSQL loader '{module_name}' is not yet implemented"
                )
            loader = loader_cls(self._context, cache_enabled=self._cache_enabled)
        except ImportError:
            raise RuntimeError(
                f"PostgreSQL loader '{module_name}' is not yet implemented"
            )
        self._loaders[loader_name] = loader
        return loader

    @property
    def llm_loader(self) -> Any:
        return self._get_loader("llm_loader", "llm_loader")

    @property
    def agent_loader(self) -> Any:
        return self._get_loader("agent_loader", "agent_loader")

    @property
    def thread_loader(self) -> Any:
        return self._get_loader("thread_loader", "thread_loader")

    @property
    def run_loader(self) -> Any:
        return self._get_loader("run_loader", "run_loader")

    @property
    def element_loader(self) -> Any:
        return self._get_loader("element_loader", "element_loader")

    @property
    def flow_snippet_loader(self) -> Any:
        return self._get_loader("flow_snippet_loader", "flow_snippet_loader")

    @property
    def prompt_template_loader(self) -> Any:
        return self._get_loader("prompt_template_loader", "prompt_template_loader")

    @property
    def mcp_server_loader(self) -> Any:
        return self._get_loader("mcp_server_loader", "mcp_server_loader")

    @property
    def mcp_server_tool_loader(self) -> Any:
        return self._get_loader("mcp_server_tool_loader", "mcp_server_tool_loader")

    @property
    def ui_component_loader(self) -> Any:
        return self._get_loader("ui_component_loader", "ui_component_loader")

    @property
    def wizard_group_loader(self) -> Any:
        return self._get_loader("wizard_group_loader", "wizard_group_loader")

    @property
    def wizard_loader(self) -> Any:
        return self._get_loader("wizard_loader", "wizard_loader")

    @property
    def messages_by_thread_loader(self) -> Any:
        return self._get_loader("messages_by_thread_loader", "messages_by_thread_loader")

    @property
    def runs_by_thread_loader(self) -> Any:
        return self._get_loader("runs_by_thread_loader", "runs_by_thread_loader")

    @property
    def tool_calls_by_run_loader(self) -> Any:
        return self._get_loader("tool_calls_by_run_loader", "tool_calls_by_run_loader")

    @property
    def tool_calls_by_thread_loader(self) -> Any:
        return self._get_loader("tool_calls_by_thread_loader", "tool_calls_by_thread_loader")


__all__ = ["PGRequestLoaders"]