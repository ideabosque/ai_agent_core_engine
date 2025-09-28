# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import logging
from functools import lru_cache
from typing import Any, Dict, Optional

from silvaengine_dynamodb_base.cache_utils import (
    CacheConfigResolvers,
    CascadingCachePurger,
)


@lru_cache(maxsize=1)
def _get_cascading_cache_purger() -> CascadingCachePurger:
    from ..handlers.config import Config

    return CascadingCachePurger(
        CacheConfigResolvers(
            get_cache_entity_config=Config.get_cache_entity_config,
            get_cache_relationships=Config.get_cache_relationships,
            queries_module_base="ai_agent_core_engine.queries",
        )
    )


def purge_entity_cascading_cache(
    logger: logging.Logger,
    entity_type: str,
    context_keys: Optional[Dict[str, Any]] = None,
    entity_keys: Optional[Dict[str, Any]] = None,
    cascade_depth: int = 3,
) -> Dict[str, Any]:
    """Universal function to purge entity cache with cascading child cache support."""
    purger = _get_cascading_cache_purger()
    return purger.purge_entity_cascading_cache(
        logger,
        entity_type,
        context_keys=context_keys,
        entity_keys=entity_keys,
        cascade_depth=cascade_depth,
    )


# ===============================
# UNIVERSAL CASCADING CACHE PURGING WRAPPERS
# ===============================


def purge_agent_cascading_cache(
    logger: logging.Logger,
    endpoint_id: str,
    agent_uuid: str = None,
    agent_version_uuid: str = None,
    cascade_depth: int = 3,
) -> Dict[str, Any]:
    """
    Agent-specific wrapper for the universal cache purging function.

    Args:
        endpoint_id: The endpoint ID
        agent_uuid: Agent UUID (for child cache clearing)
        agent_version_uuid: Specific agent version UUID (for individual cache clearing)
        cascade_depth: How many levels deep to cascade (default: 3)
        logger: logging.Logger instance

    Returns:
        Dict with comprehensive purge operation results
    """
    entity_keys = {}
    if agent_uuid:
        entity_keys["agent_uuid"] = agent_uuid
    if agent_version_uuid:
        entity_keys["agent_version_uuid"] = agent_version_uuid

    result = purge_entity_cascading_cache(
        logger,
        entity_type="agent",
        context_keys={"endpoint_id": endpoint_id} if endpoint_id else None,
        entity_keys=entity_keys if entity_keys else None,
        cascade_depth=cascade_depth,
    )

    agent_result = {
        "agent_uuid": agent_uuid,
        "agent_version_uuid": agent_version_uuid,
        "individual_agent_cache_cleared": result["individual_cache_cleared"],
        "agent_list_cache_cleared": result["list_cache_cleared"],
        "cascaded_levels": result["cascaded_levels"],
        "total_child_caches_cleared": result["total_child_caches_cleared"],
        "total_individual_children_cleared": result.get(
            "total_individual_children_cleared", 0
        ),
        "errors": result["errors"],
    }

    return agent_result


def purge_thread_cascading_cache(
    logger: logging.Logger,
    endpoint_id: str,
    thread_uuid: str = None,
    cascade_depth: int = 3,
) -> Dict[str, Any]:
    """
    Thread-specific wrapper for the universal cache purging function.

    Args:
        endpoint_id: The endpoint ID
        thread_uuid: Thread UUID (for both individual and child cache clearing)
        cascade_depth: How many levels deep to cascade (default: 3)
        logger: logging.Logger instance

    Returns:
        Dict with comprehensive purge operation results
    """
    entity_keys = {}
    if thread_uuid:
        entity_keys["thread_uuid"] = thread_uuid

    result = purge_entity_cascading_cache(
        logger,
        entity_type="thread",
        context_keys={"endpoint_id": endpoint_id} if endpoint_id else None,
        entity_keys=entity_keys if entity_keys else None,
        cascade_depth=cascade_depth,
    )

    # Transform result for backward compatibility
    thread_result = {
        "thread_uuid": thread_uuid,
        "individual_thread_cache_cleared": result["individual_cache_cleared"],
        "thread_list_cache_cleared": result["list_cache_cleared"],
        "cascaded_levels": result["cascaded_levels"],
        "total_child_caches_cleared": result["total_child_caches_cleared"],
        "total_individual_children_cleared": result.get(
            "total_individual_children_cleared", 0
        ),
        "errors": result["errors"],
    }

    return thread_result


def purge_run_cascading_cache(
    logger: logging.Logger,
    thread_uuid: str,
    run_uuid: str = None,
    cascade_depth: int = 3,
) -> Dict[str, Any]:
    """
    Run-specific wrapper for the universal cache purging function.

    Args:
        thread_uuid: Thread UUID that the run belongs to
        run_uuid: Run UUID (for both individual and child cache clearing)
        cascade_depth: How many levels deep to cascade (default: 3)
        logger: logging.Logger instance

    Returns:
        Dict with comprehensive purge operation results
    """
    entity_keys = {}
    if thread_uuid:
        entity_keys["thread_uuid"] = thread_uuid
    if run_uuid:
        entity_keys["run_uuid"] = run_uuid

    result = purge_entity_cascading_cache(
        logger,
        entity_type="run",
        context_keys=None,  # Runs don't use endpoint_id directly
        entity_keys=entity_keys if entity_keys else None,
        cascade_depth=cascade_depth,
    )

    # Transform result for backward compatibility
    run_result = {
        "thread_uuid": thread_uuid,
        "run_uuid": run_uuid,
        "individual_run_cache_cleared": result["individual_cache_cleared"],
        "run_list_cache_cleared": result["list_cache_cleared"],
        "cascaded_levels": result["cascaded_levels"],
        "total_child_caches_cleared": result["total_child_caches_cleared"],
        "total_individual_children_cleared": result.get(
            "total_individual_children_cleared", 0
        ),
        "errors": result["errors"],
    }

    return run_result


def purge_llm_cascading_cache(
    logger: logging.Logger,
    llm_provider: str,
    llm_name: str = None,
    cascade_depth: int = 3,
) -> Dict[str, Any]:
    """
    LLM-specific wrapper for the universal cache purging function.

    Args:
        llm_provider: LLM provider name
        llm_name: LLM name (for individual cache clearing)
        cascade_depth: How many levels deep to cascade (default: 3)
        logger: logging.Logger instance

    Returns:
        Dict with comprehensive purge operation results
    """
    entity_keys = {}
    if llm_provider:
        entity_keys["llm_provider"] = llm_provider
    if llm_name:
        entity_keys["llm_name"] = llm_name

    result = purge_entity_cascading_cache(
        logger,
        entity_type="llm",
        context_keys=None,  # LLMs don't use endpoint_id directly
        entity_keys=entity_keys if entity_keys else None,
        cascade_depth=cascade_depth,
    )

    # Transform result for backward compatibility
    llm_result = {
        "llm_provider": llm_provider,
        "llm_name": llm_name,
        "individual_llm_cache_cleared": result["individual_cache_cleared"],
        "llm_list_cache_cleared": result["list_cache_cleared"],
        "cascaded_levels": result["cascaded_levels"],
        "total_child_caches_cleared": result["total_child_caches_cleared"],
        "total_individual_children_cleared": result.get(
            "total_individual_children_cleared", 0
        ),
        "errors": result["errors"],
    }

    return llm_result


def purge_flow_snippet_cascading_cache(
    logger: logging.Logger,
    endpoint_id: str,
    flow_snippet_version_uuid: str = None,
    flow_snippet_uuid: str = None,
    cascade_depth: int = 3,
) -> Dict[str, Any]:
    """
    Flow snippet-specific wrapper for the universal cache purging function.

    Args:
        endpoint_id: The endpoint ID
        flow_snippet_version_uuid: Flow snippet version UUID (for individual cache clearing)
        flow_snippet_uuid: Flow snippet UUID (for child cache clearing)
        cascade_depth: How many levels deep to cascade (default: 3)
        logger: logging.Logger instance

    Returns:
        Dict with comprehensive purge operation results
    """
    entity_keys = {}
    if flow_snippet_version_uuid:
        entity_keys["flow_snippet_version_uuid"] = flow_snippet_version_uuid
    if flow_snippet_uuid:
        entity_keys["flow_snippet_uuid"] = flow_snippet_uuid

    result = purge_entity_cascading_cache(
        logger,
        entity_type="flow_snippet",
        context_keys={"endpoint_id": endpoint_id} if endpoint_id else None,
        entity_keys=entity_keys if entity_keys else None,
        cascade_depth=cascade_depth,
    )

    # Transform result for backward compatibility
    flow_snippet_result = {
        "flow_snippet_version_uuid": flow_snippet_version_uuid,
        "flow_snippet_uuid": flow_snippet_uuid,
        "individual_flow_snippet_cache_cleared": result["individual_cache_cleared"],
        "flow_snippet_list_cache_cleared": result["list_cache_cleared"],
        "cascaded_levels": result["cascaded_levels"],
        "total_child_caches_cleared": result["total_child_caches_cleared"],
        "total_individual_children_cleared": result.get(
            "total_individual_children_cleared", 0
        ),
        "errors": result["errors"],
    }

    return flow_snippet_result


def purge_mcp_server_cascading_cache(
    logger: logging.Logger,
    endpoint_id: str,
    mcp_server_uuid: str = None,
    cascade_depth: int = 3,
) -> Dict[str, Any]:
    """
    MCP server-specific wrapper for the universal cache purging function.

    Args:
        endpoint_id: The endpoint ID
        mcp_server_uuid: MCP server UUID (for both individual and child cache clearing)
        cascade_depth: How many levels deep to cascade (default: 3)
        logger: logging.Logger instance

    Returns:
        Dict with comprehensive purge operation results
    """
    entity_keys = {}
    if mcp_server_uuid:
        entity_keys["mcp_server_uuid"] = mcp_server_uuid

    result = purge_entity_cascading_cache(
        logger,
        entity_type="mcp_server",
        context_keys={"endpoint_id": endpoint_id} if endpoint_id else None,
        entity_keys=entity_keys if entity_keys else None,
        cascade_depth=cascade_depth,
    )

    # Transform result for backward compatibility
    mcp_server_result = {
        "mcp_server_uuid": mcp_server_uuid,
        "individual_mcp_server_cache_cleared": result["individual_cache_cleared"],
        "mcp_server_list_cache_cleared": result["list_cache_cleared"],
        "cascaded_levels": result["cascaded_levels"],
        "total_child_caches_cleared": result["total_child_caches_cleared"],
        "total_individual_children_cleared": result.get(
            "total_individual_children_cleared", 0
        ),
        "errors": result["errors"],
    }

    return mcp_server_result


def purge_wizard_group_cascading_cache(
    logger: logging.Logger,
    endpoint_id: str,
    wizard_group_uuid: str = None,
    wizard_uuids: list = None,
    cascade_depth: int = 3,
) -> Dict[str, Any]:
    """
    Wizard group-specific wrapper for the universal cache purging function.

    Args:
        endpoint_id: The endpoint ID
        wizard_group_uuid: Wizard group UUID (for both individual and child cache clearing)
        wizard_uuids: List of wizard UUIDs belonging to the group
        cascade_depth: How many levels deep to cascade (default: 3)
        logger: logging.Logger instance

    Returns:
        Dict with comprehensive purge operation results
    """
    entity_keys = {}
    if wizard_group_uuid:
        entity_keys["wizard_group_uuid"] = wizard_group_uuid
    if wizard_uuids:
        entity_keys["wizard_uuids"] = wizard_uuids

    result = purge_entity_cascading_cache(
        logger,
        entity_type="wizard_group",
        context_keys={"endpoint_id": endpoint_id} if endpoint_id else None,
        entity_keys=entity_keys if entity_keys else None,
        cascade_depth=cascade_depth,
    )

    # Transform result for backward compatibility
    wizard_group_result = {
        "wizard_group_uuid": wizard_group_uuid,
        "wizard_uuids": wizard_uuids,
        "individual_wizard_group_cache_cleared": result["individual_cache_cleared"],
        "wizard_group_list_cache_cleared": result["list_cache_cleared"],
        "cascaded_levels": result["cascaded_levels"],
        "total_child_caches_cleared": result["total_child_caches_cleared"],
        "total_individual_children_cleared": result.get(
            "total_individual_children_cleared", 0
        ),
        "errors": result["errors"],
    }

    return wizard_group_result


def purge_wizard_cascading_cache(
    logger: logging.Logger,
    endpoint_id: str,
    wizard_uuid: str = None,
    element_uuids: list = None,
    cascade_depth: int = 3,
) -> Dict[str, Any]:
    """
    Wizard-specific wrapper for the universal cache purging function.

    Args:
        endpoint_id: The endpoint ID
        wizard_uuid: Wizard UUID (for individual cache clearing)
        element_uuids: List of element UUIDs (for child cache clearing)
        cascade_depth: How many levels deep to cascade (default: 3)
        logger: logging.Logger instance

    Returns:
        Dict with comprehensive purge operation results
    """
    entity_keys = {}
    if wizard_uuid:
        entity_keys["wizard_uuid"] = wizard_uuid
    if element_uuids:
        entity_keys["element_uuids"] = element_uuids

    result = purge_entity_cascading_cache(
        logger,
        entity_type="wizard",
        context_keys={"endpoint_id": endpoint_id} if endpoint_id else None,
        entity_keys=entity_keys if entity_keys else None,
        cascade_depth=cascade_depth,
    )

    # Transform result for backward compatibility
    wizard_result = {
        "wizard_uuid": wizard_uuid,
        "element_uuids": element_uuids,
        "individual_wizard_cache_cleared": result["individual_cache_cleared"],
        "wizard_list_cache_cleared": result["list_cache_cleared"],
        "cascaded_levels": result["cascaded_levels"],
        "total_child_caches_cleared": result["total_child_caches_cleared"],
        "total_individual_children_cleared": result.get(
            "total_individual_children_cleared", 0
        ),
        "errors": result["errors"],
    }

    return wizard_result


def purge_prompt_template_cascading_cache(
    logger: logging.Logger,
    endpoint_id: str,
    prompt_version_uuid: str = None,
    prompt_uuid: str = None,
    cascade_depth: int = 3,
) -> Dict[str, Any]:
    """
    Prompt template-specific wrapper for the universal cache purging function.

    Args:
        endpoint_id: The endpoint ID
        prompt_version_uuid: Prompt version UUID (for individual cache clearing)
        prompt_uuid: Prompt UUID (for child cache clearing)
        cascade_depth: How many levels deep to cascade (default: 3)
        logger: logging.Logger instance

    Returns:
        Dict with comprehensive purge operation results
    """
    entity_keys = {}
    if prompt_version_uuid:
        entity_keys["prompt_version_uuid"] = prompt_version_uuid
    if prompt_uuid:
        entity_keys["prompt_uuid"] = prompt_uuid

    result = purge_entity_cascading_cache(
        logger,
        entity_type="prompt_template",
        context_keys={"endpoint_id": endpoint_id} if endpoint_id else None,
        entity_keys=entity_keys if entity_keys else None,
        cascade_depth=cascade_depth,
    )

    # Transform result for backward compatibility
    prompt_template_result = {
        "prompt_version_uuid": prompt_version_uuid,
        "prompt_uuid": prompt_uuid,
        "individual_prompt_template_cache_cleared": result["individual_cache_cleared"],
        "prompt_template_list_cache_cleared": result["list_cache_cleared"],
        "cascaded_levels": result["cascaded_levels"],
        "total_child_caches_cleared": result["total_child_caches_cleared"],
        "total_individual_children_cleared": result.get(
            "total_individual_children_cleared", 0
        ),
        "errors": result["errors"],
    }

    return prompt_template_result


def purge_message_cascading_cache(
    logger: logging.Logger,
    thread_uuid: str = None,
    message_uuid: str = None,
    run_uuid: str = None,
    cascade_depth: int = 3,
) -> Dict[str, Any]:
    """
    Message-specific wrapper for the universal cache purging function.

    Args:
        thread_uuid: Thread UUID (for identifying message context)
        message_uuid: Message UUID (for individual cache clearing)
        run_uuid: Run UUID (for additional context)
        cascade_depth: How many levels deep to cascade (default: 3)
        logger: logging.Logger instance

    Returns:
        Dict with comprehensive purge operation results
    """
    entity_keys = {}
    if thread_uuid:
        entity_keys["thread_uuid"] = thread_uuid
    if message_uuid:
        entity_keys["message_uuid"] = message_uuid
    if run_uuid:
        entity_keys["run_uuid"] = run_uuid

    result = purge_entity_cascading_cache(
        logger,
        entity_type="message",
        context_keys=None,  # Messages don't use endpoint_id directly
        entity_keys=entity_keys if entity_keys else None,
        cascade_depth=cascade_depth,
    )

    # Transform result for backward compatibility
    message_result = {
        "thread_uuid": thread_uuid,
        "message_uuid": message_uuid,
        "run_uuid": run_uuid,
        "individual_message_cache_cleared": result["individual_cache_cleared"],
        "message_list_cache_cleared": result["list_cache_cleared"],
        "cascaded_levels": result["cascaded_levels"],
        "total_child_caches_cleared": result["total_child_caches_cleared"],
        "total_individual_children_cleared": result.get(
            "total_individual_children_cleared", 0
        ),
        "errors": result["errors"],
    }

    return message_result


def purge_tool_call_cascading_cache(
    logger: logging.Logger,
    thread_uuid: str = None,
    tool_call_uuid: str = None,
    cascade_depth: int = 3,
) -> Dict[str, Any]:
    """
    Tool call-specific wrapper for the universal cache purging function.

    Args:
        thread_uuid: Thread UUID (for identifying tool call context)
        tool_call_uuid: Tool call UUID (for individual cache clearing)
        cascade_depth: How many levels deep to cascade (default: 3)
        logger: logging.Logger instance

    Returns:
        Dict with comprehensive purge operation results
    """
    entity_keys = {}
    if thread_uuid:
        entity_keys["thread_uuid"] = thread_uuid
    if tool_call_uuid:
        entity_keys["tool_call_uuid"] = tool_call_uuid

    result = purge_entity_cascading_cache(
        logger,
        entity_type="tool_call",
        context_keys=None,  # Tool calls don't use endpoint_id directly
        entity_keys=entity_keys if entity_keys else None,
        cascade_depth=cascade_depth,
    )

    # Transform result for backward compatibility
    tool_call_result = {
        "thread_uuid": thread_uuid,
        "tool_call_uuid": tool_call_uuid,
        "individual_tool_call_cache_cleared": result["individual_cache_cleared"],
        "tool_call_list_cache_cleared": result["list_cache_cleared"],
        "cascaded_levels": result["cascaded_levels"],
        "total_child_caches_cleared": result["total_child_caches_cleared"],
        "total_individual_children_cleared": result.get(
            "total_individual_children_cleared", 0
        ),
        "errors": result["errors"],
    }

    return tool_call_result


def purge_fine_tuning_message_cascading_cache(
    logger: logging.Logger,
    agent_uuid: str = None,
    thread_uuid: str = None,
    message_uuid: str = None,
    cascade_depth: int = 3,
) -> Dict[str, Any]:
    """
    Fine tuning message-specific wrapper for the universal cache purging function.

    Args:
        agent_uuid: Agent UUID (for identifying fine tuning message context)
        thread_uuid: Thread UUID (for identifying fine tuning message context)
        message_uuid: Message UUID (for individual cache clearing)
        cascade_depth: How many levels deep to cascade (default: 3)
        logger: logging.Logger instance

    Returns:
        Dict with comprehensive purge operation results
    """
    entity_keys = {}
    if agent_uuid:
        entity_keys["agent_uuid"] = agent_uuid
    if thread_uuid:
        entity_keys["thread_uuid"] = thread_uuid
    if message_uuid:
        entity_keys["message_uuid"] = message_uuid

    result = purge_entity_cascading_cache(
        logger,
        entity_type="fine_tuning_message",
        context_keys=None,  # Fine tuning messages don't use endpoint_id directly
        entity_keys=entity_keys if entity_keys else None,
        cascade_depth=cascade_depth,
    )

    # Transform result for backward compatibility
    fine_tuning_message_result = {
        "agent_uuid": agent_uuid,
        "thread_uuid": thread_uuid,
        "message_uuid": message_uuid,
        "individual_fine_tuning_message_cache_cleared": result[
            "individual_cache_cleared"
        ],
        "fine_tuning_message_list_cache_cleared": result["list_cache_cleared"],
        "cascaded_levels": result["cascaded_levels"],
        "total_child_caches_cleared": result["total_child_caches_cleared"],
        "total_individual_children_cleared": result.get(
            "total_individual_children_cleared", 0
        ),
        "errors": result["errors"],
    }

    return fine_tuning_message_result


def purge_element_cascading_cache(
    logger: logging.Logger,
    endpoint_id: str,
    element_uuid: str = None,
    cascade_depth: int = 3,
) -> Dict[str, Any]:
    """
    Element-specific wrapper for the universal cache purging function.

    Args:
        endpoint_id: The endpoint ID
        element_uuid: Element UUID (for individual cache clearing)
        cascade_depth: How many levels deep to cascade (default: 3)
        logger: logging.Logger instance

    Returns:
        Dict with comprehensive purge operation results
    """
    entity_keys = {}
    if element_uuid:
        entity_keys["element_uuid"] = element_uuid

    result = purge_entity_cascading_cache(
        logger,
        entity_type="element",
        context_keys={"endpoint_id": endpoint_id} if endpoint_id else None,
        entity_keys=entity_keys if entity_keys else None,
        cascade_depth=cascade_depth,
    )

    # Transform result for backward compatibility
    element_result = {
        "element_uuid": element_uuid,
        "individual_element_cache_cleared": result["individual_cache_cleared"],
        "element_list_cache_cleared": result["list_cache_cleared"],
        "cascaded_levels": result["cascaded_levels"],
        "total_child_caches_cleared": result["total_child_caches_cleared"],
        "total_individual_children_cleared": result.get(
            "total_individual_children_cleared", 0
        ),
        "errors": result["errors"],
    }

    return element_result


def purge_ui_component_cascading_cache(
    logger: logging.Logger,
    ui_component_type: str = None,
    ui_component_uuid: str = None,
    cascade_depth: int = 3,
) -> Dict[str, Any]:
    """
    UI component-specific wrapper for the universal cache purging function.

    Args:
        ui_component_type: UI component type
        ui_component_uuid: UI component UUID (for individual cache clearing)
        cascade_depth: How many levels deep to cascade (default: 3)
        logger: logging.Logger instance

    Returns:
        Dict with comprehensive purge operation results
    """
    entity_keys = {}
    if ui_component_type:
        entity_keys["ui_component_type"] = ui_component_type
    if ui_component_uuid:
        entity_keys["ui_component_uuid"] = ui_component_uuid

    result = purge_entity_cascading_cache(
        logger,
        entity_type="ui_component",
        context_keys=None,  # UI components don't use endpoint_id directly
        entity_keys=entity_keys if entity_keys else None,
        cascade_depth=cascade_depth,
    )

    # Transform result for backward compatibility
    ui_component_result = {
        "ui_component_type": ui_component_type,
        "ui_component_uuid": ui_component_uuid,
        "individual_ui_component_cache_cleared": result["individual_cache_cleared"],
        "ui_component_list_cache_cleared": result["list_cache_cleared"],
        "cascaded_levels": result["cascaded_levels"],
        "total_child_caches_cleared": result["total_child_caches_cleared"],
        "total_individual_children_cleared": result.get(
            "total_individual_children_cleared", 0
        ),
        "errors": result["errors"],
    }

    return ui_component_result


def purge_async_task_cascading_cache(
    logger: logging.Logger,
    function_name: str = None,
    async_task_uuid: str = None,
    cascade_depth: int = 3,
) -> Dict[str, Any]:
    """
    Async task-specific wrapper for the universal cache purging function.

    Args:
        function_name: Function name (for identifying async task context)
        async_task_uuid: Async task UUID (for individual cache clearing)
        cascade_depth: How many levels deep to cascade (default: 3)
        logger: logging.Logger instance

    Returns:
        Dict with comprehensive purge operation results
    """
    entity_keys = {}
    if function_name:
        entity_keys["function_name"] = function_name
    if async_task_uuid:
        entity_keys["async_task_uuid"] = async_task_uuid

    result = purge_entity_cascading_cache(
        logger,
        entity_type="async_task",
        context_keys=None,  # Async tasks don't use endpoint_id directly
        entity_keys=entity_keys if entity_keys else None,
        cascade_depth=cascade_depth,
    )

    # Transform result for backward compatibility
    async_task_result = {
        "function_name": function_name,
        "async_task_uuid": async_task_uuid,
        "individual_async_task_cache_cleared": result["individual_cache_cleared"],
        "async_task_list_cache_cleared": result["list_cache_cleared"],
        "cascaded_levels": result["cascaded_levels"],
        "total_child_caches_cleared": result["total_child_caches_cleared"],
        "total_individual_children_cleared": result.get(
            "total_individual_children_cleared", 0
        ),
        "errors": result["errors"],
    }

    return async_task_result
