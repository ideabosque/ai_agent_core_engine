#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import functools
import threading
import traceback
import uuid
import xml.dom.minidom
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Dict, List

import pendulum
from graphene import ResolveInfo

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

from ..models.repositories import get_repo

# message list resolved via get_repo
# tool_call list resolved via get_repo
from ..types.agent import AgentType


import copy as _copy
import time as _time

# Handler instance cache — reuse httpx.Client connection pool across requests.
# Cached entries are templates only: never hand one out directly, because
# callers stash per-request state on the instance (context/run/task_queue) and
# the cache key is per-agent, not per-request. See _per_request_handler().
_handler_cache: Dict[tuple, tuple] = {}
_HANDLER_CACHE_TTL = 300  # 5 minutes


def clear_cached_agent_handler(
    agent_uuid: str | None = None,
    endpoint_id: str | None = None,
    part_id: str | None = None,
    partition_key: str | None = None,
) -> None:
    """Clear cached handler templates for an agent after its config changes."""
    if partition_key and (not endpoint_id or not part_id) and "#" in partition_key:
        endpoint_id, part_id = partition_key.split("#", 1)

    if not agent_uuid:
        _handler_cache.clear()
        return

    keys_to_delete = []
    for key in list(_handler_cache.keys()):
        key_endpoint_id, key_part_id, key_agent_uuid = key
        if key_agent_uuid != agent_uuid:
            continue
        if endpoint_id and key_endpoint_id != endpoint_id:
            continue
        if part_id and key_part_id != part_id:
            continue
        keys_to_delete.append(key)

    for key in keys_to_delete:
        _handler_cache.pop(key, None)


def _per_request_handler(handler: Any, info: ResolveInfo) -> Any:
    """Return an isolated per-request view of a cached handler.

    The cache is keyed by (endpoint, part_id, agent_uuid), so concurrent
    requests to the same agent resolve to the same object, and callers stash
    per-request state on the instance. ``handler.context`` carries the
    WebSocket ``connection_id`` that ``send_data_to_stream`` routes chunks by,
    and ``ask_model`` streams from a background thread reading ``self.context``.
    Handing out the shared instance let a second request overwrite the first's
    context mid-stream, so its tokens went to the other client's socket and its
    own response came back empty.

    A shallow copy gives each request its own attribute namespace while still
    sharing what the cache exists for: the imported module and the handler's
    httpx.Client connection pool.

    The handler's own per-run state (``final_output``, ``_short_term_memory``,
    ...) is not reset here — each ``ask_model`` establishes it via
    ``AIAgentEventHandler._reset_run_state()``. Keeping that inside the handlers
    means this function needs no knowledge of their internals, and a new
    provider handler cannot silently reintroduce the bug by adding a container
    this list didn't know about.
    """
    request_handler = _copy.copy(handler)
    request_handler.context = info.context
    return request_handler


def get_ai_agent_handler(info: ResolveInfo, agent: AgentType):
    llm_config = getattr(agent, "llm", None)

    if not llm_config or not isinstance(llm_config, dict):
        raise RuntimeError("LLM is required and must be a dictionary")

    required_fields = ["module_name", "class_name"]

    if not all(llm_config.get(field) for field in required_fields):
        raise RuntimeError("LLM requires both module_name and class_name")

    # Cache handler instance per (endpoint, part_id, agent_uuid) to reuse
    # the httpx.Client connection pool and avoid re-importing the module
    # on every request (~50-100ms savings + TLS reuse).
    _agent_uuid = getattr(agent, "agent_uuid", None)
    cache_key = (
        info.context.get("endpoint_id", ""),
        info.context.get("part_id", ""),
        _agent_uuid,
    )
    cached = _handler_cache.get(cache_key)
    if cached and (_time.time() - cached[1] < _HANDLER_CACHE_TTL):
        # Never return the cached instance itself — concurrent requests would
        # overwrite each other's per-request context. See _per_request_handler.
        return _per_request_handler(cached[0], info)

    # Dynamically load and initialize AI agent handler
    ai_agent_handler = Invoker.resolve_proxied_callable(
        module_name=agent.llm.get("module_name"),
        class_name=agent.llm.get("class_name"),
        constructor_parameters={
            "logger": info.context.get("logger"),
            "agent": agent.__dict__,
            **info.context.get("setting", {}),
        },
    )

    if not ai_agent_handler:
        raise RuntimeError(
            f"Can't import module `{agent.llm.get('module_name')}` or not class `{agent.llm.get('class_name')}`"
        )

    # Cache the freshly built instance as a template and hand back a
    # per-request copy, so the very first request is isolated too.
    _handler_cache[cache_key] = (ai_agent_handler, _time.time())
    return _per_request_handler(ai_agent_handler, info)


def _load_runs_by_keys(
    info: ResolveInfo, run_keys: set[tuple[str, str]]
) -> Dict[tuple[str, str], Dict[str, Any]]:
    """Fetch runs in one batch keyed by (thread_uuid, run_uuid) using DataLoader."""
    if not run_keys:
        return {}
    try:
        from ..models.repositories import get_loaders

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


# ---------------------------------------------------------------------------
# Unified in-process async dispatch (SilvaEngine Gateway / FastAPI).
#
# Engine "Event" functions (async_execute_ask_model, async_insert_update_tool_call)
# are dispatched fire-and-forget. This deployment runs entirely on the gateway
# (a long-lived process), so they always execute in-process here — AWS Lambda
# is not used. (Lambda would require a separate invocation instead, since a
# background thread is frozen once a Lambda handler returns.)
#
# ``local_async_invoker`` is a drop-in for ``context['aws_lambda_invoker']`` (the
# LLM handler calls it as ``invoker(payload=...)``) and is also used by
# ``dispatch_async_funct``. Heavy functions (a full model run) get their own
# thread; lightweight ordered recordings (tool_call start->in_progress->
# completed must stay in order) share a single serialized worker.
# ---------------------------------------------------------------------------

# Engine functions whose local execution is heavy and must not share the
# serialized recording worker.
_HEAVY_LOCAL_FUNCTIONS = {"async_execute_ask_model"}

_local_dispatch_executor: ThreadPoolExecutor | None = None
_local_dispatch_lock = threading.Lock()


def _get_local_dispatch_executor() -> ThreadPoolExecutor:
    """Lazily create the single-worker executor for ordered local dispatch."""
    global _local_dispatch_executor
    if _local_dispatch_executor is None:
        with _local_dispatch_lock:
            if _local_dispatch_executor is None:
                _local_dispatch_executor = ThreadPoolExecutor(
                    max_workers=1, thread_name_prefix="aace-local-invoker"
                )
    return _local_dispatch_executor


def local_async_invoker(payload: Dict[str, Any], **_ignored: Any) -> None:
    """In-process replacement for ``aws_lambda_invoker`` (SilvaEngine Gateway).

    Drop-in for ``context['aws_lambda_invoker']``: the LLM handler calls it as
    ``invoker(payload=...)``. Resolves the target engine method from the payload
    (built by ``Invoker.build_invoker_payload``) and runs it on the cached
    engine — heavy functions on their own thread, ordered recordings on the
    shared single worker. Fire-and-forget: errors are logged, never raised.
    """
    function_name = payload.get("function_name")
    if not function_name:
        return
    params = dict(payload.get("parameters") or {})
    params["context"] = payload.get("context") or {}
    logger = params["context"].get("logger")

    def _run() -> None:
        try:
            from ..main import _build_engine_from_config

            getattr(_build_engine_from_config(), function_name)(**params)
        except Exception:
            if logger:
                logger.exception(
                    "Local async dispatch of %s failed", function_name
                )

    if function_name in _HEAVY_LOCAL_FUNCTIONS:
        threading.Thread(
            target=_run, name=f"aace-{function_name}", daemon=True
        ).start()
    else:
        _get_local_dispatch_executor().submit(_run)


def dispatch_async_funct(
    info: ResolveInfo, function_name: str, params: Dict[str, Any]
) -> None:
    """Dispatch an async engine "Event" function in-process.

    All async dispatch runs locally (SilvaEngine Gateway / FastAPI); AWS Lambda
    is not used. ``local_async_invoker`` runs heavy functions on their own
    thread and lightweight ordered recordings on a shared single worker.
    """
    local_async_invoker(
        payload=Invoker.build_invoker_payload(
            context=info.context,
            module_name="ai_agent_core_engine",
            class_name="AIAgentCoreEngine",
            function_name=function_name,
            parameters=params,
        )
    )


def generate_async_task_uuid() -> str:
    """Pre-generate an async_task_uuid for a new AsyncTask row.

    Single source of truth for every call site that writes an AsyncTask
    directly via ``get_repo("async_task").insert_update(...)`` instead of
    going through the DynamoDB ``insert_update_decorator`` (which can
    auto-generate a range key on its own). PostgreSQL's composite primary
    key (``function_name`` + ``async_task_uuid``) has no equivalent
    auto-generation, so it always needs the value supplied explicitly; we
    generate it unconditionally on both backends so every direct-insert call
    site behaves the same way regardless of ``Config.DB_BACKEND``.
    """
    return str(uuid.uuid4())


def start_async_task(
    info: ResolveInfo, function_name: str, **arguments: Dict[str, Any]
) -> str | None:
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
        _async_task_kwargs = {
            "function_name": function_name,
            "async_task_uuid": generate_async_task_uuid(),
            "arguments": {k: v for k, v in arguments.items() if k != "updated_by"},
            "updated_by": arguments["updated_by"],
        }
        async_task = get_repo("async_task").insert_update(info, **_async_task_kwargs)

        # Support both dict (PG) and ObjectType (DynamoDB) return types;
        # guard against a None return so we never AttributeError on __dict__.
        if isinstance(async_task, dict):
            _async_task_dict = async_task
        elif async_task is not None:
            _async_task_dict = async_task.__dict__
        else:
            _async_task_dict = {}

        # Prepare parameters for Lambda invocation
        params = {
            "async_task_uuid": _async_task_dict.get("async_task_uuid"),
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
            value = info.context.get(index)

            if value:
                params[index] = value

        try:
            # AWS Lambda: dispatch via the injected invoker. SilvaEngine Gateway
            # (no Lambda): run in-process (async_execute_ask_model is "heavy", so
            # local_async_invoker gives it its own thread). Non-streaming when
            # there is no connection_id; the client polls the async_task.
            dispatch_async_funct(info, function_name, params)
        except Exception as e:
            Debugger.info(
                variable=e,
                stage=f"{__file__}",
                logger=info.context.get("logger"),
                setting=info.context.get("setting"),
            )
            pass

        return _async_task_dict.get("async_task_uuid")
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

    # Parallelize message_list and tool_call_list queries (independent)
    from concurrent.futures import ThreadPoolExecutor

    with ThreadPoolExecutor(max_workers=2) as pool:
        msg_future = pool.submit(
            get_repo("message").list,
            info,
            **{
                "thread_uuid": thread_uuid,
                "pageNumber": 1,
                "limit": 100,
                "updated_at_gt": updated_at_gt,
            },
        )
        tc_future = pool.submit(
            get_repo("tool_call").list,
            info,
            **{
                "thread_uuid": thread_uuid,
                "pageNumber": 1,
                "limit": 100,
                "updated_at_gt": updated_at_gt,
            },
        )
        message_list = msg_future.result()
        tool_call_list = tc_future.result()

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


def calculate_num_tokens(
    agent: AgentType, text: str, include_instructions: bool = False
) -> int:
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
        if include_instructions and agent.instructions:
            text = f"{agent.instructions}\n\n{text}"
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


def async_task_handler(function_name: str) -> Callable:
    """
    Decorator to handle async task lifecycle (in_progress -> completed/failed).

    The decorated function should return a tuple of (result, output_files).

    Args:
        function_name: The name of the async function for tracking purposes.

    Returns:
        Decorator function that wraps the target function with async task handling.

    Usage:
        @async_task_handler("async_execute_ask_model")
        def execute_ask_model(info: ResolveInfo, **kwargs) -> Tuple[str, list]:
            # ... implementation ...
            return result, output_files
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(info: ResolveInfo, **kwargs: Dict[str, Any]) -> bool:
            async_task_uuid = kwargs.get("async_task_uuid")
            arguments = kwargs.get("arguments", {})
            # When the gateway pre-created the async_task, skip the redundant
            # "in_progress" write to save a DB round-trip (~100-200ms).
            _skip_init_write = kwargs.pop("_skip_init_write", False)

            if not async_task_uuid or not arguments:
                raise Exception(
                    "Missing required parameter(s): async_task_uuid or arguments"
                )

            try:
                # Initialize async task as in_progress (skip if pre-created)
                if not _skip_init_write:
                    get_repo("async_task").insert_update(
                        info,
                        **{
                            "function_name": function_name,
                            "async_task_uuid": async_task_uuid,
                            "status": "in_progress",
                            "updated_by": arguments["updated_by"],
                        },
                    )

                # Execute the wrapped function
                result, output_files = func(info, **kwargs)

                # Mark async task as completed with results
                get_repo("async_task").insert_update(
                    info,
                    **{
                        "function_name": function_name,
                        "async_task_uuid": async_task_uuid,
                        "result": result,
                        "output_files": output_files,
                        "status": "completed",
                        "updated_by": arguments["updated_by"],
                    },
                )

                return True

            except Exception as e:
                # Log and record any errors
                log = traceback.format_exc()
                info.context["logger"].error(log)
                get_repo("async_task").insert_update(
                    info,
                    **{
                        "function_name": function_name,
                        "async_task_uuid": async_task_uuid,
                        "status": "failed",
                        "updated_by": arguments["updated_by"],
                        "notes": log,
                    },
                )
                raise e

        return wrapper

    return decorator
