#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import traceback
import xml.dom.minidom
import xml.etree.ElementTree as ET
from typing import Any, Dict, List

import pendulum

try:
    import tiktoken
except ModuleNotFoundError:  # Optional dependency; only needed for GPT token counting
    tiktoken = None

try:
    from google import genai
except (
    ModuleNotFoundError
):  # Optional dependency; only needed for Gemini token counting
    genai = None

try:
    import anthropic
except (
    ModuleNotFoundError
):  # Optional dependency; only needed for Claude token counting
    anthropic = None
from graphene import ResolveInfo
from silvaengine_utility import Debugger, Invoker, Serializer

from ..models.async_task import insert_update_async_task
from ..models.message import resolve_message_list
from ..models.tool_call import resolve_tool_call_list
from ..types.agent import AgentType
from .config import Config


def _load_runs_by_keys(
    info: ResolveInfo, run_keys: set[tuple[str, str]]
) -> Dict[tuple[str, str], Dict[str, Any]]:
    """Fetch runs in one batch keyed by (thread_uuid, run_uuid) using DataLoader."""
    if not run_keys:
        return {}
    try:
        from ..models.batch_loaders import get_loaders

        loaders = get_loaders(info.context)
        run_loader = loaders.run_loader

        # Load all runs using the DataLoader (handles batching and caching)
        runs = run_loader.load_many(list(run_keys)).get()

        # Build the result map
        result = {}
        for key, run in zip(run_keys, runs):
            if run is not None:
                result[key] = {
                    "run_uuid": run.get("run_uuid"),
                    "prompt_tokens": int(run.get("prompt_tokens", 0) or 0),
                    "completion_tokens": int(run.get("completion_tokens", 0) or 0),
                    "total_tokens": int(run.get("total_tokens", 0) or 0),
                }
        return result
    except Exception:
        info.context["logger"].error(traceback.format_exc())
        return {}


def start_async_task(
    info: ResolveInfo, function_name: str, **arguments: Dict[str, Any]
) -> str:
    """
    Initialize and trigger an asynchronous task for processing the model request.
    Creates a task record in the database and invokes an AWS Lambda function asynchronously.

    Args:
        info: GraphQL resolver context containing logger, endpoint_id, connection_id and settings
        function_name: Name of the Lambda function to invoke
        **arguments: Task parameters including thread_uuid, run_uuid, agent_uuid, user_query etc.

    Returns:
        async_task_uuid: Unique identifier for tracking the async task

    Note:
        The function creates an async task record, prepares Lambda invocation parameters,
        and triggers the Lambda function asynchronously using the Utility helper.
    """
    try:
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
        required = [
            "endpoint_id",
            "part_id",
            "connection_id",
            "context",
            "partition_key",
        ]

        for index in required:
            if info.context.get(index):
                params[index] = info.context.get(index)

        setting = (
            info.context.get("setting")
            if isinstance(info.context.get("setting"), dict)
            else {}
        )

        try:
            Invoker.resolve_proxied_callable(
                module_name="ai_agent_core_engine",
                function_name=function_name,
                class_name="AIAgentCoreEngine",
                constructor_parameters={
                    "logger": info.context.get("logger"),
                    **setting,
                },
            )(**params)
            # Invoker.execute_async_task(
            #     task=Invoker.resolve_proxied_callable(
            #         module_name="ai_agent_core_engine",
            #         function_name=function_name,
            #         class_name="AIAgentCoreEngine",
            #         constructor_parameters={
            #             "logger": info.context.get("logger"),
            #             **setting,
            #         },
            #     ),
            #     parameters=params,
            # )

        except Exception as e:
            Debugger.info(
                variable=e,
                stage="AI Agent Core Engine(resolve_proxied_callable)",
                logger=info.context.get("logger"),
            )
            pass

        # # Invoke Lambda function asynchronously
        # Invoker.invoke_funct_on_aws_lambda(
        #     info.context,
        #     function_name,
        #     params=params,
        #     aws_lambda=Config.aws_lambda,
        #     invocation_type="Event",
        # )

        return async_task.async_task_uuid
    except Exception as e:
        raise e


# Retrieves and formats message history for a thread
def get_input_messages(
    info: ResolveInfo,
    thread_uuid: str,
    num_of_messages: int,
    tool_call_role: str,
) -> List[Dict[str, Any]]:
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
) -> List[Dict[str, Any]]:
    """Helper function to get and combine messages from message list and tool call list"""
    # Only retrieve messages and tool calls from the past 24 hours
    updated_at_gt = pendulum.now("UTC").subtract(hours=24)

    # Get message list for thread
    message_list = resolve_message_list(
        info,
        **{
            "thread_uuid": thread_uuid,
            "pageNumber": 1,
            "limit": 100,
            "updated_at_gt": updated_at_gt,
        },
    )
    # Get tool call list for thread
    tool_call_list = resolve_tool_call_list(
        info,
        **{
            "thread_uuid": thread_uuid,
            "pageNumber": 1,
            "limit": 100,
            "updated_at_gt": updated_at_gt,
        },
    )

    # Return empty list if no messages or no tool_call found
    if message_list.total == 0 and tool_call_list.total == 0:
        return []

    run_keys = {
        (message.thread_uuid, message.run_uuid)
        for message in message_list.message_list
        if getattr(message, "run_uuid", None)
    }
    run_map = _load_runs_by_keys(info, run_keys)

    # Combine messages from both message_list and tool_call_list
    seen_contents = set()
    messages = []

    # Add regular messages
    for message in message_list.message_list:
        if message.message in seen_contents:
            continue

        seen_contents.add(message.message)
        run_key = (message.thread_uuid, message.run_uuid)
        run = run_map.get(run_key) if run_key[1] else None
        if run is None:
            run = {
                "run_uuid": run_key[1],
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
            }

        messages.append(
            {
                "message": {
                    "run": run,
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
                    "content": Serializer.json_dumps(
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


def calculate_num_tokens(agent: AgentType, text: str) -> int:
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
        if agent.llm_name == "gpt":
            if tiktoken is None:
                raise ImportError(
                    "tiktoken is required for GPT token calculation but is not installed."
                )
            try:
                encoding = tiktoken.encoding_for_model(agent.configuration["model"])
                num_tokens = len(encoding.encode(text))
            except Exception as e:
                encoding = tiktoken.encoding_for_model("gpt-4o")
                num_tokens = len(encoding.encode(text))

            return num_tokens

        elif agent.llm_name == "gemini":
            if genai is None:
                raise ImportError(
                    "google-genai is required for Gemini token calculation but is not installed."
                )
            client = genai.Client(api_key=agent.configuration["api_key"])
            num_tokens = client.models.count_tokens(
                model=agent.configuration["model"], contents=text
            ).total_tokens
            return int(num_tokens)
        elif agent.llm_name == "claude":
            if anthropic is None:
                raise ImportError(
                    "anthropic is required for Claude token calculation but is not installed."
                )
            client = anthropic.Anthropic(api_key=agent.configuration["api_key"])
            num_tokens = client.messages.count_tokens(
                model=agent.configuration["model"],
                messages=[{"role": "user", "content": text}],
            ).input_tokens
            return num_tokens
        else:
            return max(1, len(text) // 4)
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


def _build_action_element(
    action_data: Dict[str, Any], has_children: bool
) -> ET.Element:
    """
    Creates an XML Action element from the provided action data

    Args:
        action_data: Dictionary containing action configuration including type, text and transforms

    Returns:
        ET.Element: The created Action element with all child elements
    """
    action_type = action_data.get("type")
    transform = action_data.get("transform")

    action = ET.Element("Action", attrib={"type": "call_function"})
    if has_children:
        action.set("value", action_type)
        return action

    has_children_element = False
    if isinstance(transform, dict):
        transform_type = transform.get("type")
        attrs = action_data.get("attrs", [])
        if len(attrs) > 0:
            has_children_element = True
            transform_el = _build_transform_element(transform_type, attrs)
            action.append(transform_el)
    elif isinstance(transform, list):
        if len(transform) > 0:
            has_children_element = True
        for tf in transform:
            transform_el = _build_transform_element(tf.get("type"), tf.get("attrs", []))
            action.append(transform_el)

    if has_children_element:
        action.set("value", action_type)
    else:
        if action_type:
            action.text = action_type

    return action


def _build_transform_element(type: str, attrs: List[Dict[str, Any]]) -> ET.Element:
    transform_el = ET.Element("Transform", attrib={"type": type})
    if type == "structure_input":
        transform_el.set("value", "data_collect_dataset")

    if type in ["summarize", "full_content"]:
        transform_el.text = attrs[0].get("attr")
    else:
        for attr in attrs:
            attr_el = ET.Element("Attribute")
            attr_el.text = attr.get("attr")
            transform_el.append(attr_el)
    return transform_el


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
        current_element = __build_detail_element(node)
        for child in node.get("children", []):
            child_element = build_element_with_children(child)
            if child_element is not None:
                current_element.append(child_element)
                after_el = __process_after_build_detail_element(child)
                if after_el is not None and current_element is not None:
                    current_element.append(after_el)
        return current_element

    for hierarchy_node in hierarchy_nodes:
        if len(hierarchy_node.get("children", [])) == 0:
            element = __build_detail_element(hierarchy_node)
            if element is not None:
                step_el.append(element)
                after_el = __process_after_build_detail_element(hierarchy_node)
                if after_el is not None:
                    step_el.append(after_el)
            continue
        step_el.append(build_element_with_children(hierarchy_node))

    if step_data.get("nextStep"):
        next_step = ET.Element("NextStep")
        next_step.text = step_data["nextStep"]
        step_el.append(next_step)

    return step_el


def get_details_hierarchy(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    details = data.get("details", [])
    if not details:
        return []
    conditions_map = {
        condition.get("id"): condition for condition in data.get("conditions", [])
    }

    node_map = {node["id"]: node for node in details}

    referenced_ids = set()
    for node in details:
        if node.get("nextStep"):
            referenced_ids.add(node["nextStep"])
        if "conditions" in node:
            for cond in node["conditions"]:
                if cond.get("nextStep"):
                    referenced_ids.add(cond["nextStep"])

    start_nodes = [node for node in details if node["id"] not in referenced_ids]
    start_node_id = start_nodes[0]["id"] if start_nodes else details[0]["id"]
    details_nodes = []
    taken_node_ids = []

    def build_condition_hierarchy(condition):
        condition_hierarchy = dict(condition, **{"children": []})
        if (
            len(conditions_map) == 0
            or condition_hierarchy.get("id") not in conditions_map
        ):
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
                                formated_condition_node = dict(
                                    condition_node,
                                    **{"type": message_node_next.get("type")},
                                )
                                condition_hierarchy["children"].append(
                                    build_condition_hierarchy(formated_condition_node)
                                )
                        else:
                            condition_hierarchy["children"].append(message_node_next)

                else:
                    condition_hierarchy["children"].append(
                        build_condition_hierarchy(child_node)
                    )

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
        "Step",
        attrib={"id": str(step_data["id"]), "name": step_data["formData"]["name"]},
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
            after_el = __process_after_build_detail_element(detail)
            if after_el is not None:
                step_el.append(after_el)

    if step_data.get("nextStep"):
        next_step = ET.Element("NextStep")
        next_step.text = step_data["nextStep"]
        step_el.append(next_step)

    return step_el


def __build_detail_element(detail_data: Dict[str, Any]) -> ET.Element | None:
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


def __process_after_build_detail_element(
    detail_data: Dict[str, Any],
) -> ET.Element | None:
    element = None
    if (
        detail_data.get("type") == "action"
        and detail_data.get("formData", {}).get("type") == "get_contact_profile"
    ):
        element = ET.Element("WaitFor")
        element.text = "contact_uuid"

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
    flow_snippet_xml = _json_to_xml(Serializer.json_loads(flow_snippet))

    dom = xml.dom.minidom.parseString(flow_snippet_xml)
    return dom.toprettyxml(indent="  ")
