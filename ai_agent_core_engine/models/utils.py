# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import logging
from typing import Any, Dict, List

from graphene import ResolveInfo


def _initialize_tables(logger: logging.Logger) -> None:
    from .agent import create_agent_table
    from .async_task import create_async_task_table
    from .element import create_element_table
    from .fine_tuning_message import create_fine_tuning_message_table
    from .flow_snippet import create_flow_snippet_table
    from .llm import create_llm_table
    from .mcp_server import create_mcp_server_table
    from .message import create_message_table
    from .prompt_template import create_prompt_template_table
    from .run import create_run_table
    from .thread import create_thread_table
    from .tool_call import create_tool_call_table
    from .ui_component import create_ui_component_table
    from .wizard import create_wizard_table
    from .wizard_group import create_wizard_group_table
    from .wizard_schema import create_wizard_schema_table

    create_llm_table(logger)
    create_agent_table(logger)
    create_thread_table(logger)
    create_run_table(logger)
    create_tool_call_table(logger)
    create_message_table(logger)
    create_async_task_table(logger)
    create_fine_tuning_message_table(logger)
    create_element_table(logger)
    create_wizard_table(logger)
    create_wizard_schema_table(logger)
    create_wizard_group_table(logger)
    create_mcp_server_table(logger)
    create_ui_component_table(logger)
    create_flow_snippet_table(logger)
    create_prompt_template_table(logger)


def _get_llm(llm_provider: str, llm_name: str) -> Dict[str, Any]:
    from .llm import get_llm

    llm = get_llm(llm_provider, llm_name)

    return {
        "llm_provider": llm.llm_provider,
        "llm_name": llm.llm_name,
        "module_name": llm.module_name,
        "class_name": llm.class_name,
        "configuration_schema": llm.configuration_schema,
        "updated_by": llm.updated_by,
        "created_at": llm.created_at,
        "updated_at": llm.updated_at,
    }


def _get_agent(endpoint_id: str, agent_uuid: str) -> Dict[str, Any]:
    from .agent import _get_active_agent

    agent = _get_active_agent(endpoint_id, agent_uuid)

    return {
        "endpoint_id": agent.endpoint_id,
        "agent_uuid": agent.agent_uuid,
        "agent_version_uuid": agent.agent_version_uuid,
        "agent_name": agent.agent_name,
        "agent_description": agent.agent_description,
        "llm_provider": agent.llm_provider,
        "llm_name": agent.llm_name,
        "llm": _get_llm(agent.llm_provider, agent.llm_name),
        "instructions": agent.instructions,
        "configuration": agent.configuration,
        "num_of_messages": agent.num_of_messages,
        "tool_call_role": agent.tool_call_role,
        "flow_snippet_version_uuid": agent.flow_snippet_version_uuid,
        "status": agent.status,
    }


def _get_thread(endpoint_id: str, thread_id: str) -> Dict[str, Any]:
    from .thread import get_thread

    thread = get_thread(endpoint_id, thread_id)

    return {
        "endpoint_id": thread.endpoint_id,
        "thread_uuid": thread.thread_uuid,
        "agent_uuid": thread.agent_uuid,
        "user_id": thread.user_id,
    }


def _get_run(thread_uuid: str, run_uuid: str) -> Dict[str, Any]:
    from .run import get_run

    run = get_run(thread_uuid, run_uuid)

    return {
        "thread": _get_thread(run.endpoint_id, run.thread_uuid),
        "run_uuid": run.run_uuid,
        "completion_tokens": run.completion_tokens,
        "prompt_tokens": run.prompt_tokens,
        "total_tokens": run.total_tokens,
    }


def _get_element(endpoint_id: str, element_uuid: str) -> Dict[str, Any]:
    from .element import get_element

    element = get_element(endpoint_id, element_uuid)

    return {
        "element_uuid": element.element_uuid,
        "data_type": element.data_type,
        "element_title": element.element_title,
        "priority": element.priority,
        "attribute_name": element.attribute_name,
        "attribute_type": element.attribute_type,
        "option_values": element.option_values,
        "conditions": element.conditions,
        "pattern": element.pattern,
    }


def _get_wizard(endpoint_id: str, wizard_uuid: str) -> Dict[str, Any]:
    from silvaengine_utility import Utility

    from .wizard import get_wizard

    wizard = get_wizard(endpoint_id, wizard_uuid)

    wizard_schema = _get_wizard_schema(
        wizard.wizard_schema_type, wizard.wizard_schema_name
    )

    wizard_elements = []
    for wizard_element in wizard.wizard_elements:
        wizard_element = Utility.json_normalize(wizard_element)
        element = _get_element(endpoint_id, wizard_element.pop("element_uuid"))
        wizard_element["element"] = element
        wizard_elements.append(wizard_element)

    return {
        "wizard_uuid": wizard.wizard_uuid,
        "wizard_title": wizard.wizard_title,
        "wizard_description": wizard.wizard_description,
        "wizard_type": wizard.wizard_type,
        "wizard_schema": wizard_schema,
        "wizard_attributes": [
            Utility.json_normalize(attr) for attr in wizard.wizard_attributes
        ],
        "wizard_elements": wizard_elements,
        "priority": wizard.priority,
    }


def _get_flow_snippet(endpoint_id: str, flow_snippet_uuid: str) -> Dict[str, Any]:
    from .flow_snippet import get_flow_snippet

    flow_snippet = get_flow_snippet(endpoint_id, flow_snippet_uuid)

    return {
        "flow_snippet_version_uuid": flow_snippet.flow_snippet_version_uuid,
        "flow_snippet_uuid": flow_snippet.flow_snippet_uuid,
        "prompt_uuid": flow_snippet.prompt_uuid,
        "flow_name": flow_snippet.flow_name,
        "flow_relationship": flow_snippet.flow_relationship,
        "flow_context": flow_snippet.flow_context,
        "status": flow_snippet.status,
    }


def _get_mcp_servers(
    info: ResolveInfo, mcp_servers: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    from ..handlers.config import Config
    from .mcp_server import get_mcp_server_type, resolve_mcp_server

    mcp_servers = [
        resolve_mcp_server(info, **{"mcp_server_uuid": mcp_server["mcp_server_uuid"]})
        for mcp_server in mcp_servers
        if "mcp_server_uuid" in mcp_server
    ]
    mcp_servers = [
        {
            k: v
            for k, v in mcp_server.__dict__.items()
            if k not in ["endpoint_id", "updated_by", "created_at", "updated_at"]
        }
        for mcp_server in mcp_servers
        if mcp_server is not None
    ]

    internal_mcp = Config.get_internal_mcp(info.context["endpoint_id"])
    if internal_mcp:
        mcp_server = get_mcp_server_type(
            info,
            {
                "headers": internal_mcp["headers"],
                "mcp_label": internal_mcp["name"],
                "mcp_server_url": internal_mcp["base_url"],
            },
        )
        mcp_servers.append(mcp_server.__dict__)

    return mcp_servers


def _get_ui_components(
    info: ResolveInfo, ui_components: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    from .ui_component import resolve_ui_component

    ui_components = [
        resolve_ui_component(
            info,
            **{
                "ui_component_type": ui_component["ui_component_type"],
                "ui_component_uuid": ui_component["ui_component_uuid"],
            },
        )
        for ui_component in ui_components
        if "ui_component_type" in ui_component and "ui_component_uuid" in ui_component
    ]
    ui_components = [
        {
            k: v
            for k, v in component.__dict__.items()
            if k not in ["endpoint_id", "updated_by", "created_at", "updated_at"]
        }
        for component in ui_components
    ]
    return ui_components


def _get_wizard_schema(
    wizard_schema_type: str, wizard_schema_name: str
) -> Dict[str, Any]:
    from .wizard_schema import get_wizard_schema

    if wizard_schema_type is None or wizard_schema_name is None:
        return {}

    wizard_schema = get_wizard_schema(wizard_schema_type, wizard_schema_name)

    return {
        "wizard_schema_type": wizard_schema.wizard_schema_type,
        "wizard_schema_name": wizard_schema.wizard_schema_name,
        "wizard_schema_description": wizard_schema.wizard_schema_description,
        "attributes": wizard_schema.attributes,
        "attribute_groups": wizard_schema.attribute_groups,
    }


def _get_prompt_template(info: ResolveInfo, prompt_uuid: str) -> Dict[str, Any]:
    from .prompt_template import _get_active_prompt_template

    prompt_template = _get_active_prompt_template(
        info.context["endpoint_id"], prompt_uuid
    )

    return {
        "prompt_version_uuid": prompt_template.prompt_version_uuid,
        "prompt_uuid": prompt_template.prompt_uuid,
        "prompt_type": prompt_template.prompt_type,
        "prompt_name": prompt_template.prompt_name,
        "prompt_description": prompt_template.prompt_description,
        "template_context": prompt_template.template_context,
        "variables": prompt_template.variables,
        "mcp_servers": _get_mcp_servers(info, prompt_template.mcp_servers),
        "ui_components": _get_ui_components(info, prompt_template.ui_components),
        "status": prompt_template.status,
    }


def _update_agents_by_flow_snippet(
    info: ResolveInfo,
    flow_snippet_version_uuid: str,
    updated_flow_snippet_version_uuid: str,
) -> None:
    from .agent import insert_update_agent, resolve_agent_list

    agent_list = resolve_agent_list(
        info,
        **{
            "flow_snippet_version_uuid": flow_snippet_version_uuid,
        },
    )

    for agent in agent_list.agent_list:
        agent = insert_update_agent(
            info,
            **{
                "agent_uuid": agent.agent_uuid,
                "flow_snippet_version_uuid": updated_flow_snippet_version_uuid,
                "updated_by": agent.updated_by,
            },
        )

    return
