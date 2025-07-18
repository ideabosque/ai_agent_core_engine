# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import logging
from typing import Any, Dict, List


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
        "function_configuration": agent.function_configuration,
        "functions": agent.functions,
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
    }


def _get_wizard(endpoint_id: str, wizard_uuid: str) -> Dict[str, Any]:
    from .wizard import get_wizard

    wizard = get_wizard(endpoint_id, wizard_uuid)
    elements = [
        _get_element(endpoint_id, element_uuid) for element_uuid in wizard.element_uuids
    ]

    return {
        "wizard_uuid": wizard.wizard_uuid,
        "wizard_title": wizard.wizard_title,
        "wizard_description": wizard.wizard_description,
        "wizard_type": wizard.wizard_type,
        "form_schema": wizard.form_schema,
        "priority": wizard.priority,
        "elements": elements,
    }
