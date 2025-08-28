#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import logging
import traceback
import xml.dom.minidom
import xml.etree.ElementTree as ET
from typing import Any, Dict, List

import anthropic
import tiktoken
from google import genai
from graphene import ResolveInfo

from silvaengine_utility import Utility

from ..models.async_task import insert_update_async_task
from ..models.message import resolve_message_list
from ..models.tool_call import resolve_tool_call_list
from .config import Config


def create_listener_info(
    logger: logging.Logger,
    field_name: str,
    setting: Dict[str, Any],
    **kwargs: Dict[str, Any],
) -> ResolveInfo:
    # Minimal example: some parameters can be None if you're only testing
    info = ResolveInfo(
        field_name=field_name,
        field_asts=[],  # or [some_field_node]
        return_type=None,  # e.g., GraphQLString
        parent_type=None,  # e.g., schema.get_type("Query")
        schema=None,  # your GraphQLSchema
        fragments={},
        root_value=None,
        operation=None,
        variable_values={},
        context={
            "setting": setting,
            "endpoint_id": kwargs.get("endpoint_id"),
            "logger": logger,
            "connectionId": kwargs.get("connection_id"),
        },
        path=None,
    )
    return info


def start_async_task(
    info: ResolveInfo, function_name: str, **arguments: Dict[str, Any]
) -> str:
    """
    Initialize and trigger an asynchronous task for processing the model request.
    Creates a task record in the database and invokes an AWS Lambda function asynchronously.

    Args:
        info: GraphQL resolver context containing logger, endpoint_id, connectionId and settings
        function_name: Name of the Lambda function to invoke
        **arguments: Task parameters including thread_uuid, run_uuid, agent_uuid, user_query etc.

    Returns:
        async_task_uuid: Unique identifier for tracking the async task

    Note:
        The function creates an async task record, prepares Lambda invocation parameters,
        and triggers the Lambda function asynchronously using the Utility helper.
    """

    # Create task record in database
    async_task = insert_update_async_task(
        info,
        **{
            "function_name": function_name,
            "arguments": {k: v for k, v in arguments.items() if k != "updated_by"},
            "updated_by": arguments["updated_by"],
        },
    )

    # Prepare parameters for Lambda invocation
    params = {
        "async_task_uuid": async_task.async_task_uuid,
        "arguments": arguments,
    }
    if info.context.get("connectionId"):
        params["connection_id"] = info.context.get("connectionId")

    # Invoke Lambda function asynchronously
    Utility.invoke_funct_on_aws_lambda(
        info.context["logger"],
        info.context["endpoint_id"],
        function_name,
        params=params,
        setting=info.context["setting"],
        test_mode=info.context["setting"].get("test_mode"),
        aws_lambda=Config.aws_lambda,
        invocation_type="Event",
    )

    return async_task.async_task_uuid


# Retrieves and formats message history for a thread
def get_input_messages(
    info: ResolveInfo,
    thread_uuid: str,
    num_of_messages: int,
    tool_call_role: str,
) -> List[Dict[str, any]]:
    """
    Retrieves message history for a thread.

    Args:
        info: GraphQL resolver info
        thread_uuid: UUID of the thread to get messages for
        num_of_messages: Number of messages to retrieve
        tool_call_role: Role to assign to tool call messages

    Returns:
        List of message dictionaries in chronological order, combining both regular messages
        and tool call messages. Each message contains role and content fields.

    Raises:
        Exception: If there is an error retrieving messages from either message_list or tool_call_list
    """
    try:
        messages = combine_thread_messages(info, thread_uuid, tool_call_role)

        # TODO: Implement message processing pipeline (long term memory) to:
        # 1. Update conversation context in the graph database
        # 2. Retrieve relevant long-term memory based on message content
        # 3. Integrate memory retrieval with vector embeddings for semantic search
        # 4. Handle memory pruning/summarization for efficient storage
        # Notes:
        # Asynchronously update long-term memory with new conversation context
        # Synchronously fetch relevant historical context from long-term memory store
        # Combine historical context with current conversation thread
        # Use semantic similarity to prioritize most relevant memories
        # Prune and summarize older memories to maintain storage efficiency

        # Return last n messages sorted by creation time (most recent first)
        # Remove timestamps and reverse to get chronological order
        return [
            {"role": msg["message"]["role"], "content": msg["message"]["content"]}
            for msg in sorted(messages, key=lambda x: x["created_at"], reverse=True)
        ][:num_of_messages][::-1]
    except Exception as e:
        # Log error and re-raise with full traceback
        info.context["logger"].error(traceback.format_exc())
        raise e


def combine_thread_messages(
    info: ResolveInfo,
    thread_uuid: str,
    tool_call_role: str,
) -> List[Dict[str, any]]:
    """Helper function to get and combine messages from message list and tool call list"""
    # Get message list for thread
    message_list = resolve_message_list(
        info,
        **{
            "thread_uuid": thread_uuid,
            "pageNumber": 1,
            "limit": 100,
        },
    )
    # Get tool call list for thread
    tool_call_list = resolve_tool_call_list(
        info,
        **{
            "thread_uuid": thread_uuid,
            "pageNumber": 1,
            "limit": 100,
        },
    )

    # Return empty list if no messages or no tool_call found
    if message_list.total == 0 and tool_call_list.total == 0:
        return []

    # Combine messages from both message_list and tool_call_list
    seen_contents = set()
    messages = []

    # Add regular messages
    for message in message_list.message_list:
        if message.message in seen_contents:
            continue

        seen_contents.add(message.message)
        messages.append(
            {
                "message": {
                    "run": {
                        "run_uuid": message.run["run_uuid"],
                        "prompt_tokens": message.run["prompt_tokens"],
                        "completion_tokens": message.run["completion_tokens"],
                        "total_tokens": message.run["total_tokens"],
                    },
                    "role": message.role,
                    "content": message.message,
                },
                "created_at": message.created_at,
            }
        )

    # Add tool call messages
    for tool_call in tool_call_list.tool_call_list:
        if tool_call.content in seen_contents:
            continue

        seen_contents.add(tool_call.content)
        messages.append(
            {
                "message": {
                    "role": tool_call_role,
                    "content": Utility.json_dumps(
                        {
                            "tool": {
                                "tool_call_id": tool_call.tool_call_id,
                                "tool_type": tool_call.tool_type,
                                "name": tool_call.name,
                                "arguments": tool_call.arguments,
                            },
                            "output": tool_call.content,
                        }
                    ),
                },
                "created_at": tool_call.created_at,
            }
        )

    return messages


def calculate_num_tokens(agent: dict[str, Any], text: str) -> int:
    """
    Calculates the number of tokens for a given model.

    Args:
        agent: Dictionary containing LLM configuration including model name and API key
        text: The input text to tokenize

    Returns:
        Number of tokens in the text for the specified model

    Raises:
        Exception: If there is an error getting the encoding or calculating tokens
    """
    try:
        if agent.llm["llm_name"] == "openai":
            try:
                encoding = tiktoken.encoding_for_model(agent.configuration["model"])
                num_tokens = len(encoding.encode(text))
            except Exception as e:
                encoding = tiktoken.encoding_for_model("gpt-4o")
                num_tokens = len(encoding.encode(text))

            return num_tokens

        elif agent.llm["llm_name"] == "gemini":
            client = genai.Client(api_key=agent.configuration["api_key"])
            num_tokens = client.models.count_tokens(
                model=agent.configuration["model"], contents=text
            ).total_tokens
            return num_tokens
        elif agent.llm["llm_name"] == "claude":
            client = anthropic.Anthropic(api_key=agent.configuration["api_key"])
            num_tokens = client.messages.count_tokens(
                model=agent.configuration["model"],
                messages=[{"role": "user", "content": text}],
            ).input_tokens
            return num_tokens
        else:
            raise Exception(f"Unsupported LLM: {agent.llm['llm_name']}")
    except Exception as e:
        # Log error and re-raise
        raise e


def _build_text_element(text: str) -> ET.Element:
    """
    Creates an XML Text element with the given text content

    Args:
        text: The text content to include in the element

    Returns:
        ET.Element: The created Text element
    """
    text_element = ET.Element("Text")
    text_element.text = text
    return text_element

def _build_prompt_element(text: str) -> ET.Element:
    prompt_element = ET.Element("Prompt")
    prompt_element.text = text
    return prompt_element
def _build_action_element(action_data: Dict[str, Any], has_children: bool) -> ET.Element:
    """
    Creates an XML Action element from the provided action data

    Args:
        action_data: Dictionary containing action configuration including type, text and transforms

    Returns:
        ET.Element: The created Action element with all child elements
    """
    action_type = action_data.get("type")
    transform_type = action_data.get("transform", {}).get("type")
    attrs = action_data.get("attrs", [])
    action = ET.Element("Action", attrib={"type": "call_function"})
    if has_children:
        action.set("value", action_type)
        return action

    if len(attrs) > 0:
        action.set("value", action_type)
        transform_el = ET.Element("Transform", attrib={"type": transform_type})
        if transform_type == "structure_input":
            transform_el.set("value", "data_collect_dataset")

        if transform_type in ["summarize", "full_content"]:
            transform_el.text = attrs[0].get("attr")
        else:
            for attr in attrs:
                attr_el = ET.Element("Attribute")
                attr_el.text = attr.get("attr")
                transform_el.append(attr_el)
        action.append(transform_el)
    else:
        if action_type:
            action.text = action_type

    return action


def _build_ui_element(ui_data: Dict[str, Any]) -> ET.Element:
    """
    Creates an XML UIComponent element from the provided UI data

    Args:
        ui_data: Dictionary containing UI component configuration

    Returns:
        ET.Element: The created UIComponent element with all child elements
    """
    ui_element = ET.Element("UIComponent")

    component_name = ui_data.get("name")
    if not component_name:
        return ui_element  # fallback

    component_el = ET.Element(component_name)

    for key, value in ui_data.items():
        if key not in ["name", "text", "waitFor"] and value is not None:
            component_el.set(key, str(value))

    ui_element.append(component_el)

    if "waitFor" in ui_data:
        wait_el = ET.Element("WaitFor")
        wait_el.text = ui_data["waitFor"]
        ui_element.append(wait_el)

    return ui_element

def _build_step_with_conditions(step_el: ET.Element, step_data: Dict[str, Any]):
    hierarchy_nodes = get_details_hierarchy(step_data)
    def build_element_with_children(node):
        
        current_element =  __build_detail_element(node)
        for child in node.get("children", []):
            current_element.append(build_element_with_children(child))
        return current_element
    
    for hierarchy_node in hierarchy_nodes:
        if len(hierarchy_node.get("children", [])) == 0:
            element = __build_detail_element(hierarchy_node)
            if element is not None:
                step_el.append(element)
            continue
        step_el.append(build_element_with_children(hierarchy_node))

    if step_data.get("nextStep"):
        next_step = ET.Element("NextStep")
        next_step.text = step_data["nextStep"]
        step_el.append(next_step)

    return step_el

def get_details_hierarchy(data):
    details = data.get('details', [])
    if not details:
        return None
    conditions_map = {
        condition.get("id"): condition
        for condition in data.get("conditions", [])
    }

    node_map = {node['id']: node for node in details}

    referenced_ids = set()
    for node in details:
        if node.get('nextStep'):
            referenced_ids.add(node['nextStep'])
        if 'conditions' in node:
            for cond in node['conditions']:
                if cond.get('nextStep'):
                    referenced_ids.add(cond['nextStep'])
    
    start_nodes = [node for node in details if node['id'] not in referenced_ids]
    start_node_id = start_nodes[0]['id'] if start_nodes else details[0]['id']
    details_nodes = []
    taken_node_ids = []
    
    def build_condition_hierarchy(condition):
        condition_hierarchy = dict(condition, **{"children": []})
        if len(conditions_map) == 0 or condition_hierarchy.get("id") not in conditions_map:
            condition_hierarchy.pop("nextStep", None)
        if condition.get("nextStep"):
            child_node = node_map.get(condition.get("nextStep"))
            if child_node:
                taken_node_ids.append(condition.get("nextStep"))
                if child_node.get("type") not in ["branch"]:
                    condition_hierarchy["children"].append(child_node)
                    message_node_next = node_map.get(child_node.get("nextStep"))
                    if message_node_next:
                        taken_node_ids.append(child_node.get("nextStep"))
                        if "conditions" in message_node_next:
                            for condition_node in message_node_next.get("conditions"):
                                formated_condition_node = dict(condition_node, **{"type": message_node_next.get("type")})
                                condition_hierarchy["children"].append(build_condition_hierarchy(formated_condition_node))
                        else:
                            condition_hierarchy["children"].append(message_node_next)
                        
                else:
                    condition_hierarchy["children"].append(build_condition_hierarchy(child_node))

        return condition_hierarchy
    
    for detail in details:
        if detail.get("id") in taken_node_ids:
            continue
        taken_node_ids.append(detail.get("id"))
        if detail.get("id") == start_node_id:
            details_nodes.append(detail)
            continue
        if "conditions" in detail:
            for condition in detail.get("conditions"):
                formated_condition = dict(condition, **{"type": detail.get("type")})
                condition_hierarchy = build_condition_hierarchy(formated_condition)
                details_nodes.append(condition_hierarchy)
        else:
            details_nodes.append(detail)
    return details_nodes

def _build_branch_element(branch_data: Dict[str, Any]) -> ET.Element:
    branch_element = ET.Element("Branch")
    condition_name = branch_data.get("condition")
    if condition_name:
        branch_element.set("condition", condition_name)
    if branch_data.get("nextStep"):
        branch_element.set("next_step", branch_data.get("nextStep"))
    
    return branch_element

def _build_step_element(step_index: int, step_data: Dict[str, Any]) -> ET.Element:
    """
    Creates an XML Step element for a flow step

    Args:
        step_index: Index number of the step
        step_data: Dictionary containing step configuration including name, description and details

    Returns:
        ET.Element: The created Step element with all child elements
    """
    step_el = ET.Element(
        "Step", attrib={"id": str(step_data["id"]), "name": step_data["formData"]["name"]}
    )

    has_conditions = False
    for detail in step_data.get("details", []):
        if "conditions" in detail:
            has_conditions = True
    if "conditions" in step_data or has_conditions:
        return _build_step_with_conditions(step_el, step_data)

    for detail in step_data.get("details", []):
        detail_el = __build_detail_element(detail)
        if detail_el is not None:
            step_el.append(detail_el)
    if step_data.get("nextStep"):
        next_step = ET.Element("NextStep")
        next_step.text = step_data["nextStep"]
        step_el.append(next_step)

    return step_el

def __build_detail_element(detail_data: Dict[str, Any]) -> ET.Element:
    element = None
    if "type" not in detail_data:
        return element
    has_children = True if len(detail_data.get("children", [])) > 0 else False
    if detail_data["type"] == "ui":
        element = _build_ui_element(detail_data["formData"])
    elif detail_data["type"] == "action":
        element = _build_action_element(detail_data["formData"], has_children)
    elif detail_data["type"] in ["message", "prompt"]:
        if detail_data["formData"]["type"] == "text":
            element = _build_text_element(detail_data["formData"]["text"])
        elif detail_data["formData"]["type"] == "prompt":
            element = _build_prompt_element(detail_data["formData"]["text"])
    elif detail_data["type"] == "branch":
        element = _build_branch_element(detail_data)
    return element


def _json_to_xml(json_data: List[Dict[str, Any]]) -> str:
    """
    Converts JSON flow data to XML string format

    Args:
        json_data: List of flow step dictionaries to convert

    Returns:
        str: XML string representation of the flow
    """
    flow_snippet = ET.Element("FlowSnippet")

    for i, step in enumerate(json_data):
        step_el = _build_step_element(i, step)
        flow_snippet.append(step_el)

    return ET.tostring(flow_snippet, encoding="unicode")


def convert_flow_snippet_xml(flow_snippet: List[Dict[str, Any]]) -> str:
    """
    Converts a flow snippet into an XML string.

    Args:
        flow_snippet: The flow snippet to convert

    Returns:
        str: Pretty-printed XML string representation of the flow snippet
    """
    flow_snippet_xml = _json_to_xml(Utility.json_loads(flow_snippet))

    dom = xml.dom.minidom.parseString(flow_snippet_xml)
    return dom.toprettyxml(indent="  ")
