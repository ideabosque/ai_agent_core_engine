#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict

from .agent_loader import AgentLoader
from .element_loader import ElementLoader
from .flow_snippet_loader import FlowSnippetLoader
from .llm_loader import LlmLoader
from .mcp_server_loader import McpServerLoader
from .messages_by_thread_loader import MessagesByThreadLoader
from .prompt_template_loader import PromptTemplateLoader
from .run_loader import RunLoader
from .runs_by_thread_loader import RunsByThreadLoader
from .thread_loader import ThreadLoader
from .tool_calls_by_run_loader import ToolCallsByRunLoader
from .tool_calls_by_thread_loader import ToolCallsByThreadLoader
from .ui_component_loader import UIComponentLoader
from .wizard_group_loader import WizardGroupLoader
from .wizard_loader import WizardLoader



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
        self.runs_by_thread_loader = RunsByThreadLoader(
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

    def invalidate_cache(self, entity_type: str, entity_keys: Dict[str, str]):
        """Invalidate specific cache entries when entities are modified."""
        if not self.cache_enabled:
            return

        if entity_type == "llm" and "llm_name" in entity_keys:
            if hasattr(self.llm_loader, "cache"):
                cache_key = self.llm_loader.generate_cache_key((entity_keys.get('llm_provider'),entity_keys['llm_name']))
                self.llm_loader.cache.delete(cache_key)
        elif entity_type == "mcp_server" and "mcp_server_uuid" in entity_keys:
            if hasattr(self.mcp_server_loader, "cache"):
                cache_key = self.mcp_server_loader.generate_cache_key((entity_keys.get('partition_key'),entity_keys['mcp_server_uuid']))
                self.mcp_server_loader.cache.delete(cache_key)
        elif entity_type == "agent" and "agent_version_uuid" in entity_keys:
            if hasattr(self.agent_loader, "cache"):
                cache_key = self.agent_loader.generate_cache_key((entity_keys.get('partition_key'),entity_keys['agent_version_uuid']))
                self.agent_loader.cache.delete(cache_key)
        elif entity_type == "thread" and "thread_uuid" in entity_keys:
            if hasattr(self.thread_loader, "cache"):
                cache_key = self.thread_loader.generate_cache_key((entity_keys.get('partition_key'),entity_keys['thread_uuid']))
                self.thread_loader.cache.delete(cache_key)
        elif entity_type == "run" and "run_uuid" in entity_keys:
            if hasattr(self.run_loader, "cache"):
                cache_key = self.run_loader.generate_cache_key((entity_keys.get('thread_uuid'),entity_keys['run_uuid']))
                self.run_loader.cache.delete(cache_key)
        elif entity_type == "prompt_template":
            # prompt_uuid = entity_keys.get("prompt_uuid")
            # prompt_version_uuid = entity_keys.get("prompt_version_uuid")
            # partition_key = entity_keys.get("partition_key")
            if hasattr(self.prompt_template_loader, "cache"):
                cache_key = self.run_loader.generate_cache_key((entity_keys.get('partition_key'),entity_keys['prompt_uuid']))
                self.prompt_template_loader.cache.delete(cache_key)
            # # Prefer clearing by prompt_uuid (active lookup path)
            # if prompt_uuid and partition_key and hasattr(self.prompt_template_loader, "cache"):
                
            # elif prompt_version_uuid and partition_key and hasattr(self.prompt_template_loader, "cache"):
            #     self.prompt_template_loader.cache.delete(
            #         f"{partition_key}:{prompt_version_uuid}"
            #     )
        elif (
            entity_type == "flow_snippet" and "flow_snippet_version_uuid" in entity_keys
        ):
            if hasattr(self.flow_snippet_loader, "cache"):
                cache_key = self.flow_snippet_loader.generate_cache_key((entity_keys.get('partition_key'),entity_keys['flow_snippet_version_uuid']))
                self.flow_snippet_loader.cache.delete(cache_key)
        elif entity_type == "element" and "element_uuid" in entity_keys:
            if hasattr(self.element_loader, "cache"):
                cache_key = self.element_loader.generate_cache_key((entity_keys.get('partition_key'),entity_keys['element_uuid']))
                self.element_loader.cache.delete(cache_key)
        elif entity_type == "wizard" and "wizard_uuid" in entity_keys:
            if hasattr(self.wizard_loader, "cache"):
                cache_key = self.wizard_loader.generate_cache_key((entity_keys.get('partition_key'),entity_keys['wizard_uuid']))
                self.wizard_loader.cache.delete(cache_key)
        elif entity_type == "wizard_group" and "wizard_group_uuid" in entity_keys:
            if hasattr(self.wizard_group_loader, "cache"):
                cache_key = self.wizard_group_loader.generate_cache_key((entity_keys.get('partition_key'),entity_keys['wizard_group_uuid']))
                self.wizard_group_loader.cache.delete(cache_key)


def get_loaders(context: Dict[str, Any]) -> RequestLoaders:
    """Fetch or initialize request-scoped loaders from the GraphQL context."""
    if context is None:
        context = {}

    loaders = context.get("batch_loaders")
    if not loaders:
        from ...handlers.config import Config
        cache_enabled = Config.is_cache_enabled()
        loaders = RequestLoaders(context, cache_enabled=cache_enabled)
        context["batch_loaders"] = loaders
    return loaders


def clear_loaders(context: Dict[str, Any]) -> None:
    """Clear loaders from context (useful for tests)."""
    if context is None:
        return
    context.pop("batch_loaders", None)


__all__ = [
    "RequestLoaders",
    "get_loaders",
    "clear_loaders",
    "AgentLoader",
    "ElementLoader",
    "FlowSnippetLoader",
    "LlmLoader",
    "McpServerLoader",
    "MessagesByThreadLoader",
    "PromptTemplateLoader",
    "RunLoader",
    "RunsByThreadLoader",
    "ThreadLoader",
    "ToolCallsByRunLoader",
    "ToolCallsByThreadLoader",
    "UIComponentLoader",
    "WizardGroupLoader",
    "WizardLoader",
]
