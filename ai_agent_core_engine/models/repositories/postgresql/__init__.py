# -*- coding: utf-8 -*-
"""PostgreSQL repositories — register_all with importlib lazy loading.

Each repo is imported lazily so partially-ported entity sets don't crash
on startup. ImportError is logged but swallowed for non-critical entities
when the active backend is dynamodb; when DB_BACKEND=postgresql, import
failures are raised loudly.
"""
from __future__ import print_function

__author__ = "bibow"

import importlib
import logging
from typing import Dict

from ..base import EntityRepository

_REPOS = [
    ("agent_repo", "AgentRepository"),
    ("llm_repo", "LlmRepository"),
    ("thread_repo", "ThreadRepository"),
    ("run_repo", "RunRepository"),
    ("message_repo", "MessageRepository"),
    ("tool_call_repo", "ToolCallRepository"),
    ("async_task_repo", "AsyncTaskRepository"),
    ("fine_tuning_message_repo", "FineTuningMessageRepository"),
    ("element_repo", "ElementRepository"),
    ("wizard_repo", "WizardRepository"),
    ("wizard_schema_repo", "WizardSchemaRepository"),
    ("wizard_group_repo", "WizardGroupRepository"),
    ("wizard_group_filter_repo", "WizardGroupFilterRepository"),
    ("mcp_server_repo", "MCPServerRepository"),
    ("ui_component_repo", "UIComponentRepository"),
    ("flow_snippet_repo", "FlowSnippetRepository"),
    ("prompt_template_repo", "PromptTemplateRepository"),
    ("usage_repo", "UsageRepository"),
]


def register_all(registry: Dict[str, EntityRepository]) -> None:
    """Register all PostgreSQL repositories into the given registry dict."""
    _logger = logging.getLogger(__name__)
    from ....handlers.config import Config

    _raise_on_fail = getattr(Config, "DB_BACKEND", "dynamodb") == "postgresql"

    for module_name, class_name in _REPOS:
        try:
            mod = importlib.import_module(f".{module_name}", package=__name__)
            repo_cls = getattr(mod, class_name)
            repo = repo_cls()
            registry[repo.entity_type] = repo
        except ImportError as exc:
            if _raise_on_fail:
                raise
            _logger.debug("PostgreSQL repo not yet available: %s (%s)", module_name, exc)
        except Exception as exc:
            if _raise_on_fail:
                raise
            _logger.debug("PostgreSQL repo init failed: %s (%s)", module_name, exc)


__all__ = ["register_all"]