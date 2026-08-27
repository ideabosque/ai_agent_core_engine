# -*- coding: utf-8 -*-
"""DynamoDB repositories — thin wrappers over existing PynamoDB model functions.

Each entity has its own repo file. The register_all function instantiates
all 17 repositories and registers them with the dispatch registry.
"""
from __future__ import print_function

__author__ = "bibow"

from typing import Dict

from ..base import EntityRepository


def register_all(registry: Dict[str, EntityRepository]) -> None:
    """Register all DynamoDB repositories into the given registry dict."""
    from .agent_repo import AgentRepository
    from .llm_repo import LlmRepository
    from .thread_repo import ThreadRepository
    from .run_repo import RunRepository
    from .message_repo import MessageRepository
    from .tool_call_repo import ToolCallRepository
    from .async_task_repo import AsyncTaskRepository
    from .fine_tuning_message_repo import FineTuningMessageRepository
    from .element_repo import ElementRepository
    from .wizard_repo import WizardRepository
    from .wizard_schema_repo import WizardSchemaRepository
    from .wizard_group_repo import WizardGroupRepository
    from .wizard_group_filter_repo import WizardGroupFilterRepository
    from .mcp_server_repo import McpServerRepository
    from .ui_component_repo import UiComponentRepository
    from .flow_snippet_repo import FlowSnippetRepository
    from .prompt_template_repo import PromptTemplateRepository

    repos = [
        AgentRepository(),
        LlmRepository(),
        ThreadRepository(),
        RunRepository(),
        MessageRepository(),
        ToolCallRepository(),
        AsyncTaskRepository(),
        FineTuningMessageRepository(),
        ElementRepository(),
        WizardRepository(),
        WizardSchemaRepository(),
        WizardGroupRepository(),
        WizardGroupFilterRepository(),
        McpServerRepository(),
        UiComponentRepository(),
        FlowSnippetRepository(),
        PromptTemplateRepository(),
    ]
    for repo in repos:
        registry[repo.entity_type] = repo


__all__ = ["register_all"]