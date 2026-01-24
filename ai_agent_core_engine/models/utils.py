# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import logging
from typing import Any, Dict, List

from graphene import ResolveInfo

from ..utils.normalization import normalize_to_json

def initialize_tables(logger: logging.Logger) -> None:
    from .agent import AgentModel
    from .async_task import AsyncTaskModel
    from .element import ElementModel
    from .fine_tuning_message import FineTuningMessageModel
    from .flow_snippet import FlowSnippetModel
    from .llm import LlmModel
    from .mcp_server import MCPServerModel
    from .message import MessageModel
    from .prompt_template import PromptTemplateModel
    from .run import RunModel
    from .thread import ThreadModel
    from .tool_call import ToolCallModel
    from .ui_component import UIComponentModel
    from .wizard import WizardModel
    from .wizard_group import WizardGroupModel
    from .wizard_group_filter import WizardGroupFilterModel
    from .wizard_schema import WizardSchemaModel

    models: List = [
        AgentModel,
        AsyncTaskModel,
        ElementModel,
        FineTuningMessageModel,
        FlowSnippetModel,
        LlmModel,
        MCPServerModel,
        MessageModel,
        PromptTemplateModel,
        RunModel,
        ThreadModel,
        ToolCallModel,
        UIComponentModel,
        WizardModel,
        WizardGroupModel,
        WizardGroupFilterModel,
        WizardSchemaModel,
    ]

    for model in models:
        if model.exists():
            continue

        table_name = model.Meta.table_name
        # Create with on-demand billing (PAY_PER_REQUEST)
        model.create_table(billing_mode="PAY_PER_REQUEST", wait=True)
        logger.info(f"The {table_name} table has been created.")


def get_element(endpoint_id: str, element_uuid: str) -> Dict[str, Any]:
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


def get_wizard(endpoint_id: str, wizard_uuid: str) -> Dict[str, Any]:
    from .wizard import get_wizard

    wizard = get_wizard(endpoint_id, wizard_uuid)

    wizard_schema = get_wizard_schema(
        wizard.wizard_schema_type, wizard.wizard_schema_name
    )

    wizard_elements = []
    for wizard_element in wizard.wizard_elements:
        wizard_element = normalize_to_json(wizard_element)
        element = get_element(endpoint_id, wizard_element.pop("element_uuid"))
        wizard_element["element"] = element
        wizard_elements.append(wizard_element)

    return {
        "wizard_uuid": wizard.wizard_uuid,
        "wizard_title": wizard.wizard_title,
        "wizard_description": wizard.wizard_description,
        "wizard_type": wizard.wizard_type,
        "wizard_schema": wizard_schema,
        "wizard_attributes": [
            normalize_to_json(attr) for attr in wizard.wizard_attributes
        ],
        "wizard_elements": wizard_elements,
        "priority": wizard.priority,
    }


def get_flow_snippet(endpoint_id: str, flow_snippet_uuid: str) -> Dict[str, Any]:
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


def get_mcp_servers(
    info: ResolveInfo, mcp_servers: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    from ..handlers.config import Config
    from .mcp_server import get_mcp_server_type, resolve_mcp_server

    resolved_servers = [
        resolve_mcp_server(info, **{"mcp_server_uuid": server["mcp_server_uuid"]})
        for server in mcp_servers
        if "mcp_server_uuid" in server
    ]
    resolved_servers = [
        {
            k: v
            for k, v in server.__dict__.items()
            if k
            not in [
                "partition_key",
                "endpoint_id",
                "part_id",
                "updated_by",
                "created_at",
                "updated_at",
            ]
        }
        for server in resolved_servers
        if server is not None
    ]

    internal_mcp = Config.get_internal_mcp(
        info.context["endpoint_id"], part_id=info.context.get("part_id")
    )
    if internal_mcp:
        internal_server = get_mcp_server_type(
            info,
            {
                "headers": internal_mcp["headers"],
                "mcp_label": internal_mcp["name"],
                "mcp_server_url": internal_mcp["base_url"],
            },
        )
        resolved_servers.append(internal_server.__dict__)

    return resolved_servers


def get_ui_components(
    info: ResolveInfo, ui_components: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    from .ui_component import resolve_ui_component

    resolved_components = [
        resolve_ui_component(
            info,
            **{
                "ui_component_type": component["ui_component_type"],
                "ui_component_uuid": component["ui_component_uuid"],
            },
        )
        for component in ui_components
        if "ui_component_type" in component and "ui_component_uuid" in component
    ]
    resolved_components = [
        {
            k: v
            for k, v in component.__dict__.items()
            if k not in ["endpoint_id", "updated_by", "created_at", "updated_at"]
        }
        for component in resolved_components
    ]
    return resolved_components


def get_wizard_schema(
    wizard_schema_type: str, wizard_schema_name: str
) -> Dict[str, Any]:
    from .wizard_schema import get_wizard_schema

    # Check if wizard schema type and name are provided.
    # This is important to ensure that the schema is valid and can be used for further processing.
    # If either is missing, return an empty dictionary to support legacy systems.
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


def get_prompt_template(info: ResolveInfo, prompt_uuid: str) -> Dict[str, Any]:
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
        "mcp_servers": get_mcp_servers(info, prompt_template.mcp_servers),
        "ui_components": get_ui_components(info, prompt_template.ui_components),
        "status": prompt_template.status,
    }


def update_agents_by_flow_snippet(
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
