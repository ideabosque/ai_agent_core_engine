# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import threading
import time
import traceback
import uuid
from collections.abc import Iterable
from queue import Queue
from typing import Any, Dict, List

import pendulum
from graphene import ResolveInfo

from silvaengine_utility import Debugger, Serializer

from ..models.repositories import get_repo
# message insert via get_repo
# run insert via get_repo
# thread operations via get_repo
from ..types.ai_agent import AskModelType, FileType, PresignedAWSS3UrlType
from ..types.message import MessageType
from ..types.thread import ThreadListType, ThreadType
from ..utils.decorators import extract_token_usage, log_usage_record, usage_recorder
from .ai_agent_utility import (
    async_task_handler,
    calculate_num_tokens,
    get_ai_agent_handler,
    get_input_messages,
    start_async_task,
)
from .config import Config


def ask_model(info: ResolveInfo, **kwargs: Dict[str, Any]) -> AskModelType:
    """
    Process a user query through an AI model and return the response asynchronously.

    Args:
        info: GraphQL resolver context containing logger, endpoint and connection info
        **kwargs: Parameters including:
            - agent_uuid: ID of AI agent to use (required)
            - thread_uuid: Optional ID of existing conversation thread
            - user_id: Optional ID of the user
            - user_query: The actual query text (required)
            - input_files: Optional list of input files in JSON format
            - stream: Whether to stream responses (default False)
            - thread_life_minutes: Optional thread lifetime in minutes (default 30)
            - updated_by: User making the request (required)

    Returns:
        AskModelType containing thread, task and run identifiers
    """
    try:
        required_keys = {"updated_by", "agent_uuid", "user_query"}

        if not required_keys.issubset(kwargs.keys()):
            raise ValueError("Missing required parameter(s)")

        # Log request details
        thread = _get_thread(info=info, **kwargs)

        if not thread:
            raise ValueError("Not found any thread")

        # Create new run instance for this request
        # PG repos require an explicit run_uuid (composite PK); DynamoDB's
        # insert_update_decorator auto-generates one when not provided.
        _run_uuid = str(uuid.uuid4()) if Config.DB_BACKEND == "postgresql" else None
        _run_kwargs = {
            "thread_uuid": thread.get("thread_uuid") if isinstance(thread, dict) else thread.thread_uuid,
            "updated_by": kwargs.get("updated_by"),
        }
        if _run_uuid:
            _run_kwargs["run_uuid"] = _run_uuid
        run = get_repo("run").insert_update(info, **_run_kwargs)

        if not run:
            raise ValueError("Invalid run entity")

        _run_dict = run if isinstance(run, dict) else run.__dict__
        # Prepare arguments for async processing
        arguments = {
            "thread_uuid": thread.get("thread_uuid") if isinstance(thread, dict) else thread.thread_uuid,
            "run_uuid": _run_dict.get("run_uuid"),
            "agent_uuid": kwargs["agent_uuid"],
            "user_query": kwargs["user_query"],
            "stream": kwargs.get("stream", False),
            "updated_by": kwargs["updated_by"],
        }

        if "input_files" in kwargs:
            arguments["input_files"] = kwargs["input_files"]

        # Start async task and get identifiers
        function_name = "async_execute_ask_model"
        async_task_uuid = start_async_task(
            info,
            function_name,
            **arguments,
        )

        # Return response with all relevant IDs
        _thread_uuid = thread.get("thread_uuid") if isinstance(thread, dict) else thread.thread_uuid
        return AskModelType(
            agent_uuid=kwargs["agent_uuid"],
            thread_uuid=_thread_uuid,
            user_query=kwargs["user_query"],
            function_name=function_name,
            async_task_uuid=async_task_uuid,
            current_run_uuid=_run_dict.get("run_uuid"),
        )
    except Exception as e:
        log = traceback.format_exc()
        info.context.get("logger").error(log)
        raise e


def _get_thread(info: ResolveInfo, **kwargs: Dict[str, Any]) -> ThreadType | None:
    """
    Retrieve a conversation thread by its UUID.

    Args:
        info: GraphQL resolver context
        **kwargs: Contains thread_uuid

    Returns:
        Dict[str, Any]: Thread data
    """
    try:
        # Only query for thread if thread_uuid is a valid non-empty string
        if "thread_uuid" in kwargs and kwargs["thread_uuid"]:
            return resolve_thread(
                info,
                **{"thread_uuid": kwargs["thread_uuid"]},
            )

        if "user_id" in kwargs:
            # Only retrieve threads from the past 'thread_life_minutes' minutes
            thread_life_minutes = kwargs.get("thread_life_minutes", 30)
            created_at_gt = pendulum.now("UTC").subtract(minutes=thread_life_minutes)
            thread_list: ThreadListType = get_repo("thread").list(
                info,
                **{
                    "agent_uuid": kwargs["agent_uuid"],
                    "user_id": kwargs["user_id"],
                    "created_at_gt": created_at_gt,
                },
            )

            if thread_list.total > 0:
                # Return the latest thread based on updated_time or created_time
                latest_thread = max(thread_list.thread_list, key=lambda t: t.created_at)
                return latest_thread

        # PG repos require an explicit thread_uuid (composite PK); DynamoDB's
        # insert_update_decorator auto-generates one when not provided.
        _thread_uuid = str(uuid.uuid4()) if Config.DB_BACKEND == "postgresql" else None
        _thread_kwargs = {
            "agent_uuid": kwargs["agent_uuid"],
            "user_id": kwargs.get("user_id"),
            "updated_by": kwargs["updated_by"],
        }
        if _thread_uuid:
            _thread_kwargs["thread_uuid"] = _thread_uuid
        thread = get_repo("thread").insert_update(info, **_thread_kwargs)
        return thread
    except Exception as e:
        log = traceback.format_exc()
        info.context.get("logger").error(log)
        raise e


def _get_agent(info: ResolveInfo, agent_uuid: str):
    from ..models.repositories import get_loaders

    # Phase 2.1: Cache resolved agents (with MCP tools) to avoid
    # re-fetching 80 tools from the MCP daemon on every request.
    # The cache is keyed by (endpoint_id, part_id, agent_uuid) and
    # has a TTL of 5 minutes.  The MCP tool resolution is the single
    # biggest bottleneck (~3s per request), so caching it gives the
    # largest performance win.
    import time as _time

    cache_key = (
        info.context.get("endpoint_id", ""),
        info.context.get("part_id", ""),
        agent_uuid,
    )
    _cache = getattr(_get_agent, "_cache", None)
    if _cache is None:
        _cache = {}
        _get_agent._cache = _cache
        _get_agent._ttl = 300  # 5 minutes

    cached = _cache.get(cache_key)
    if cached and (_time.time() - cached[1] < _get_agent._ttl):
        # Return a shallow copy so the caller can mutate agent.__dict__
        # without polluting the cached entry.
        import copy
        return copy.copy(cached[0])

    agent = get_repo("agent").resolve_single(info, **{"agent_uuid": agent_uuid})

    if not agent:
        return None

    # Use the DataLoader to fetch LLM data (triggers nested resolver)
    agent.llm = (
        get_loaders(info.context)
        .llm_loader.load((agent.llm_provider, agent.llm_name))
        .get()
    )

    if isinstance(agent.mcp_server_uuids, Iterable):
        from ..handlers.config import Config

        if Config.DB_BACKEND == "postgresql":
            from ..models.postgresql.utils import get_mcp_servers
        else:
            from ..models.dynamodb.utils import get_mcp_servers

        mcp_servers = [
            {"mcp_server_uuid": mcp_server_uuid}
            for mcp_server_uuid in agent.mcp_server_uuids
        ]

        agent.mcp_servers = []
        # TODO: "mcp_server_uuid" does not exist in the internal mcp
        required_keys = ["headers", "mcp_label", "mcp_server_url"]

        for mcp_server in get_mcp_servers(info, mcp_servers):
            if mcp_server is None or not all(mcp_server.get(k) for k in required_keys):
                raise ValueError(
                    f"MCP Server ({mcp_server}) is not configured correctly."
                )

            agent.mcp_servers.append(
                {
                    "name": mcp_server.get("mcp_label"),
                    "mcp_server_uuid": mcp_server.get("mcp_server_uuid"),
                    "setting": {
                        "base_url": mcp_server.get("mcp_server_url"),
                        "headers": mcp_server.get("headers"),
                    },
                }
            )

    # Phase 2.1: Store resolved agent in cache for subsequent requests
    _cache[cache_key] = (agent, _time.time())

    return agent


@usage_recorder("ai_agent_core_engine", extract_token_usage, log_usage_record)
@async_task_handler("async_execute_ask_model")
def execute_ask_model(info: ResolveInfo, **kwargs: Dict[str, Any]) -> tuple:
    """
    Execute an AI model query and handle the response asynchronously.

    Args:
        info: GraphQL resolve info containing context and connection details
        kwargs: Dictionary containing async_task_uuid and arguments

    Returns:
        tuple: A tuple of (result, output_files)

    Raises:
        Exception: If any error occurs during execution
    """
    arguments = kwargs["arguments"]

    # Retrieve AI agent configuration with LLM details
    agent = _get_agent(info, arguments["agent_uuid"])

    if not agent:
        raise ValueError("Not found any agent")

    # Build conversation history and add new user query
    input_messages = get_input_messages(
        info,
        arguments["thread_uuid"],
        int(agent.num_of_messages) if agent.num_of_messages is not None else 0,
        agent.tool_call_role,
    )
    input_messages.append({"role": "user", "content": arguments["user_query"]})
    # TODO: Implement long term memory processing pipeline.
    # TODO: Implement long term memory context retrival.

    # TODO: Implement message evaluation system to:
    #  1. Evaluate all system messages and instructions with last assistant message
    #  2. Analyze if current user query relates to previous context
    #  3. Add metadata flags for conversation flow and context tracking
    #  4. Enable smarter handling of follow-up questions vs new topics

    # Phase 3.1: Parallelize user message insert and run record insert.
    # Previously these were sequential (~0.4s each = 0.8s total).  Running
    # them in parallel saves ~0.4s on the critical path.
    from concurrent.futures import ThreadPoolExecutor

    # Defer token counting — it's only needed for the run record which is
    # updated AFTER streaming completes.  For Gemini/Claude this avoids a
    # synchronous network API call (~200-500ms) on the critical path.
    # Use 0 as placeholder; the actual value comes from the LLM usage response.
    prompt_tokens = 0

    # PG repos require an explicit message_uuid (composite PK); DynamoDB's
    # insert_update_decorator auto-generates one when not provided and raises
    # "Cannot find" if a caller-specified uuid doesn't exist yet.
    from ..handlers.config import Config

    _msg_uuid_user = str(uuid.uuid4()) if Config.DB_BACKEND == "postgresql" else None

    msg_kwargs = {
        "thread_uuid": arguments["thread_uuid"],
        "run_uuid": arguments["run_uuid"],
        "role": "user",
        "message": arguments["user_query"],
        "updated_by": arguments["updated_by"],
    }
    if _msg_uuid_user:
        msg_kwargs["message_uuid"] = _msg_uuid_user
    run_kwargs = {
        "thread_uuid": arguments["thread_uuid"],
        "run_uuid": arguments["run_uuid"],
        "prompt_tokens": prompt_tokens,
        "updated_by": arguments["updated_by"],
    }

    with ThreadPoolExecutor(max_workers=2) as pool:
        msg_future = pool.submit(get_repo("message").insert_update, info, **msg_kwargs)
        run_future = pool.submit(get_repo("run").insert_update, info, **run_kwargs)
        user_message = msg_future.result()
        run = run_future.result()

    ai_agent_handler = get_ai_agent_handler(info=info, agent=agent)
    ai_agent_handler.context = info.context
    # Gateway (non-Lambda) contexts carry no ``aws_lambda_invoker``, so the
    # handler's fire-and-forget recordings (e.g. tool_call rows) would be
    # silently dropped. Provide an in-process invoker when one is absent; the
    # AWS Lambda path already injects its own and is left untouched.
    if not callable(ai_agent_handler.context.get("aws_lambda_invoker")):
        from ..main import _local_async_invoker

        ai_agent_handler.context["aws_lambda_invoker"] = _local_async_invoker
    ai_agent_handler.run = run if isinstance(run, dict) else run.__dict__
    ai_agent_handler.task_queue = Config.task_queue

    if info.context.get("connection_id") or arguments.get("stream", False):
        stream_queue = Queue()
        stream_event = threading.Event()
        args = [input_messages, stream_queue, stream_event]

        if "input_files" in arguments:
            args.append(arguments["input_files"])

        # Trigger a streaming ask_model in a separate thread if desired:
        stream_thread = threading.Thread(
            target=ai_agent_handler.ask_model,
            args=args,
            daemon=True,
        )

        stream_thread.start()

        # Wait until we get the run_id from the queue
        current_run = stream_queue.get()

        if current_run["name"] == "run_id":
            run_id = current_run["value"]

        # Wait until streaming is done, timeout after 120 second
        stream_event.wait(timeout=120)
    else:
        # Process query through AI model
        if "input_files" in arguments:
            run_id = ai_agent_handler.ask_model(
                input_messages,
                input_files=arguments["input_files"],
            )
        else:
            run_id = ai_agent_handler.ask_model(input_messages)

    # Verify final_output is a dict and contains required fields message_id, role, content with non-empty values
    if not isinstance(ai_agent_handler.final_output, dict) or not all(
        key in ai_agent_handler.final_output and ai_agent_handler.final_output[key]
        for key in ["message_id", "role", "content"]
    ):
        Debugger.info(
            variable=f"final_output must be a dict containing non-empty values for message_id, role and content fields: {ai_agent_handler.final_output}",
            stage=f"{__name__}.final_output",
            setting=info.context.get("setting", {"debug_mode": True}),
        )
        raise ValueError("Invalid final_output from AI agent handler")

    if ai_agent_handler.uploaded_files:
        _update_user_message_with_files(
            info,
            agent,
            user_message,
            ai_agent_handler.uploaded_files,
            arguments["updated_by"],
        )

    # Record AI assistant response
    _msg_uuid_assistant = str(uuid.uuid4()) if Config.DB_BACKEND == "postgresql" else None
    _assistant_kwargs = {
        "thread_uuid": arguments["thread_uuid"],
        "run_uuid": arguments["run_uuid"],
        "message_id": ai_agent_handler.final_output["message_id"],
        "role": ai_agent_handler.final_output["role"],
        "message": ai_agent_handler.final_output["content"],
        "updated_by": arguments["updated_by"],
    }
    if _msg_uuid_assistant:
        _assistant_kwargs["message_uuid"] = _msg_uuid_assistant
    assistant_message = get_repo("message").insert_update(
        info,
        **_assistant_kwargs,
    )
    _assistant_msg = assistant_message if isinstance(assistant_message, dict) else assistant_message.__dict__
    info.context["logger"].info(
        f"Assistant message recorded - thread: {arguments['thread_uuid']}, "
        f"run: {arguments['run_uuid']}, message: {_assistant_msg.get('message_uuid')}, "
        f"role: {_assistant_msg.get('role')}"
    )

    # Update run with completion details
    # Use LLM usage response if available (avoids another network call for token counting)
    _completion_tokens = 0
    _prompt_tokens = 0
    _last_usage = getattr(ai_agent_handler, "_last_usage", None)
    if _last_usage:
        _completion_tokens = getattr(_last_usage, "completion_tokens", 0) or 0
        _prompt_tokens = getattr(_last_usage, "prompt_tokens", 0) or 0
    if _completion_tokens == 0:
        _completion_tokens = calculate_num_tokens(
            agent, ai_agent_handler.final_output["content"]
        )
    if _prompt_tokens == 0:
        _prompt_tokens = prompt_tokens

    run = get_repo("run").insert_update(
        info,
        **{
            "thread_uuid": arguments["thread_uuid"],
            "run_uuid": arguments["run_uuid"],
            "run_id": run_id,
            "prompt_tokens": _prompt_tokens,
            "completion_tokens": _completion_tokens,
            "updated_by": arguments["updated_by"],
        },
    )
    _run = run if isinstance(run, dict) else run.__dict__
    info.context["logger"].info(
        f"Run completed - thread: {arguments['thread_uuid']}, "
        f"run: {_run.get('run_uuid')}, run_id: {run_id}, "
        f"prompt_tokens: {_run.get('prompt_tokens')}, completion_tokens: {_run.get('completion_tokens')}"
    )
    # TODO: Implement MCP Prompt and update system prmompt by analyzing user query and assistant response.
    # TODO: Implement feedack loop to evaluate assistant response and ingest feedback for model fine-tuning and response improvement.
    # TODO: Invoke execute_ask_model with the updated system prompt by dispatching thread.

    return (
        ai_agent_handler.final_output["content"],
        ai_agent_handler.final_output.get("output_files", []),
    )


def _update_user_message_with_files(
    info: ResolveInfo,
    agent: Dict[str, Any],
    user_message,
    uploaded_files: List[Dict[str, Any]],
    updated_by: str,
) -> None:
    """Helper function to update message content with file references"""
    # Support both ObjectType (DynamoDB) and dict (PostgreSQL) return types
    _msg = user_message if isinstance(user_message, dict) else user_message.__dict__
    _msg_text = _msg.get("message", "")

    if agent.llm["llm_name"] == "gpt":
        message_content = [{"type": "input_text", "text": _msg_text}]

        # Add each file reference to content array
        message_content.extend(
            {"type": "input_file", "file_id": uploaded_file["file_id"]}
            for uploaded_file in uploaded_files
        )
    elif agent.llm["llm_name"] == "gemini":
        message_content = [{"type": "input_text", "text": _msg_text}]

        # Add each file reference to content array
        message_content.extend(
            {"type": "input_file", "file_name": uploaded_file["file_name"]}
            for uploaded_file in uploaded_files
        )
    elif agent.llm["llm_name"] == "claude":
        message_content = [{"type": "text", "text": _msg_text}]

        # Add each file reference to content array
        if uploaded_files[0]["code_execution_tool"]:
            message_content.extend(
                {"type": "container_upload", "file_id": uploaded_file["file_id"]}
                for uploaded_file in uploaded_files
            )

        else:
            message_content.extend(
                {
                    "type": "document",
                    "source": {"type": "file", "file_id": uploaded_file["file_id"]},
                }
                for uploaded_file in uploaded_files
            )
    else:
        raise Exception(f"Unsupported LLM: {agent.llm['llm_name']}")

    get_repo("message").insert_update(
        info,
        **{
            "thread_uuid": _msg.get("thread_uuid") or _msg.get("run", {}).get("thread", {}).get("thread_uuid"),
            "message_uuid": _msg.get("message_uuid"),
            "message": Serializer.json_dumps(message_content),
            "updated_by": updated_by,
        },
    )

    return


def upload_file(info: ResolveInfo, **kwargs: Dict[str, Any]) -> FileType:
    # Retrieve AI agent configuration
    agent = _get_agent(info, kwargs["agent_uuid"])

    if not agent:
        raise ValueError("Invalid agent")
    # ai_agent_handler_class = getattr(
    #     __import__(agent.llm["module_name"]),
    #     agent.llm["class_name"],
    # )
    # ai_agent_handler = ai_agent_handler_class(
    #     info.context.get("logger"),
    #     agent.__dict__,
    #     **info.context.get("setting", {}),
    # )
    ai_agent_handler = get_ai_agent_handler(info=info, agent=agent)
    ai_agent_handler.endpoint_id = info.context["endpoint_id"]
    ai_agent_handler.part_id = info.context.get("part_id")
    file = ai_agent_handler.insert_file(**kwargs["arguments"])

    if agent.llm["llm_name"] == "gemini":
        return FileType(
            **{
                "identity": "file_name",
                "value": file.file_name,
                "file_detail": file.__dict__,
            }
        )
    elif agent.llm["llm_name"] == "gpt":
        return FileType(**{"identity": "id", "value": file["id"], "file_detail": file})
    else:
        raise Exception(f"Unsupported LLM: {agent.llm['llm_name']}")


def get_file(info: ResolveInfo, **kwargs: Dict[str, Any]) -> FileType:
    # Retrieve AI agent configuration
    agent = _get_agent(info, kwargs["agent_uuid"])

    # ai_agent_handler_class = getattr(
    #     __import__(agent.llm["module_name"]),
    #     agent.llm["class_name"],
    # )
    # ai_agent_handler = ai_agent_handler_class(
    #     info.context.get("logger"),
    #     agent.__dict__,
    #     **info.context.get("setting", {}),
    # )
    if not agent:
        raise ValueError("Invalid agent")

    ai_agent_handler = get_ai_agent_handler(info=info, agent=agent)
    ai_agent_handler.endpoint_id = info.context["endpoint_id"]
    ai_agent_handler.part_id = info.context.get("part_id")

    file = ai_agent_handler.get_file(**kwargs["arguments"])

    if agent.llm["llm_name"] == "gpt":
        return FileType(**{"identity": "id", "value": file["id"], "file_detail": file})
    elif agent.llm["llm_name"] == "gemini":
        return FileType(
            **{
                "identity": "file_name",
                "value": file.file_name,
                "file_detail": file.__dict__,
            }
        )
    else:
        raise Exception(f"Unsupported LLM: {agent.llm['llm_name']}")


def get_output_file(info: ResolveInfo, **kwargs: Dict[str, Any]) -> FileType:
    # Retrieve AI agent configuration
    agent = _get_agent(info, kwargs["agent_uuid"])

    # ai_agent_handler_class = getattr(
    #     __import__(agent.llm["module_name"]),
    #     agent.llm["class_name"],
    # )
    # ai_agent_handler = ai_agent_handler_class(
    #     info.context.get("logger"),
    #     agent.__dict__,
    #     **info.context.get("setting", {}),
    # )
    if not agent:
        raise ValueError("Invalid agent")

    ai_agent_handler = get_ai_agent_handler(info=info, agent=agent)
    ai_agent_handler.endpoint_id = info.context["endpoint_id"]
    ai_agent_handler.part_id = info.context.get("part_id")

    file = ai_agent_handler.get_output_file(**kwargs["arguments"])

    if agent.llm["llm_name"] == "gpt":
        return FileType(**{"identity": "id", "value": file["id"], "file_detail": file})
    else:
        raise Exception(f"Unsupported LLM: {agent.llm['llm_name']}")


def get_presigned_aws_s3_url(
    info: ResolveInfo, **kwargs: Dict[str, Any]
) -> PresignedAWSS3UrlType:
    # bucket_name, object_key, expiration=3600):
    """
    Generate a presigned URL to upload a file to an S3 bucket.

    :param bucket_name: Name of the S3 bucket.
    :param object_key: Name of the file to be uploaded (object key).
    :param expiration: Time in seconds for the presigned URL to remain valid.
    :return: Presigned URL as a string.
    """
    client_method = kwargs.get("client_method", "put_object")
    bucket_name = info.context["setting"].get("aws_s3_bucket")
    object_key = kwargs.get("object_key")
    expiration = int(
        kwargs.get("expiration") or info.context["setting"].get("expiration", 3600)
    )  # Default to 1 hour

    # Generate the presigned URL for put_object
    try:
        response = Config.aws_s3.generate_presigned_url(
            ClientMethod=client_method,
            Params={"Bucket": bucket_name, "Key": object_key},
            ExpiresIn=expiration,
            HttpMethod="PUT" if client_method == "put_object" else "GET",
        )

        return PresignedAWSS3UrlType(
            url=response,
            object_key=object_key,
            expiration=expiration,
        )
    except Exception as e:
        log = traceback.format_exc()
        info.context.get("logger").error(log)
        raise e
