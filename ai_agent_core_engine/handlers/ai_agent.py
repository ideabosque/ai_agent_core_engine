# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import threading
import time
import traceback
from collections.abc import Iterable
from queue import Queue
from typing import Any, Dict, List

import pendulum
from graphene import ResolveInfo
from silvaengine_utility import Debugger, Invoker, Serializer

from ..models.agent import resolve_agent
from ..models.async_task import insert_update_async_task
from ..models.message import insert_update_message
from ..models.run import insert_update_run
from ..models.thread import insert_thread, resolve_thread, resolve_thread_list
from ..types.ai_agent import AskModelType, FileType, PresignedAWSS3UrlType
from ..types.message import MessageType
from ..types.thread import ThreadListType, ThreadType
from .ai_agent_utility import (
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

        start_time = time.perf_counter()
        # Log request details
        thread = _get_thread(info=info, **kwargs)

        if not thread:
            raise ValueError("Not found any thread")

        print(
            f"\n{'*' * 20} `{__file__}._get_thread` spent {time.perf_counter() - start_time} s."
        )
        start_time = time.perf_counter()

        # Create new run instance for this request
        run = insert_update_run(
            info,
            **{
                "thread_uuid": thread.thread_uuid,
                "updated_by": kwargs.get("updated_by"),
            },
        )

        if not run:
            raise ValueError("Invalid run entity")

        print(
            f"\n{'*' * 20} `{__file__}.insert_update_run` spent {time.perf_counter() - start_time} s."
        )
        start_time = time.perf_counter()

        # Prepare arguments for async processing
        arguments = {
            "thread_uuid": thread.thread_uuid,
            "run_uuid": run.run_uuid,
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

        print(
            f"\n{'*' * 20}`{__file__}.start_async_task` spent {time.perf_counter() - start_time} s."
        )

        # Return response with all relevant IDs
        return AskModelType(
            agent_uuid=kwargs["agent_uuid"],
            thread_uuid=thread.thread_uuid,
            user_query=kwargs["user_query"],
            function_name=function_name,
            async_task_uuid=async_task_uuid,
            current_run_uuid=run.run_uuid,
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
            thread_list: ThreadListType = resolve_thread_list(
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

        thread = insert_thread(
            info,
            **{
                "agent_uuid": kwargs["agent_uuid"],
                "user_id": kwargs.get("user_id"),
                "updated_by": kwargs["updated_by"],
            },
        )
        return thread
    except Exception as e:
        log = traceback.format_exc()
        info.context.get("logger").error(log)
        raise e


def _get_agent(info: ResolveInfo, agent_uuid: str):
    from ..models.batch_loaders import get_loaders

    agent = resolve_agent(info, **{"agent_uuid": agent_uuid})

    if not agent:
        return None

    # Use the DataLoader to fetch LLM data (triggers nested resolver)
    agent.llm = (
        get_loaders(info.context)
        .llm_loader.load((agent.llm_provider, agent.llm_name))
        .get()
    )

    if isinstance(agent.mcp_server_uuids, Iterable):
        from ..models.utils import get_mcp_servers

        mcp_servers = [
            {"mcp_server_uuid": mcp_server_uuid}
            for mcp_server_uuid in agent.mcp_server_uuids
        ]

        agent.mcp_servers = [
            {
                "name": mcp_server["mcp_label"],
                "mcp_server_uuid": mcp_server["mcp_server_uuid"],
                "setting": {
                    "base_url": mcp_server["mcp_server_url"],
                    "headers": mcp_server["headers"],
                },
            }
            for mcp_server in get_mcp_servers(info, mcp_servers)
        ]

    return agent


def execute_ask_model(info: ResolveInfo, **kwargs: Dict[str, Any]) -> bool:
    """
    Execute an AI model query and handle the response asynchronously.

    Args:
        info: GraphQL resolve info containing context and connection details
        kwargs: Dictionary containing async_task_uuid and arguments

    Returns:
        AsyncTaskType: The async task object with query results

    Raises:
        Exception: If any error occurs during execution
    """
    try:
        # Log endpoint and connection IDs for tracing
        async_task_uuid = kwargs["async_task_uuid"]
        arguments = kwargs["arguments"]

        if not async_task_uuid or not arguments:
            raise Exception("Missing required parameter(s)")

        # Initialize async task as in-progress
        async_task = insert_update_async_task(
            info,
            **{
                "function_name": "async_execute_ask_model",
                "async_task_uuid": async_task_uuid,
                "status": "in_progress",
                "updated_by": arguments["updated_by"],
            },
        )

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

        # Record user message in thread
        user_message = insert_update_message(
            info,
            **{
                "thread_uuid": arguments["thread_uuid"],
                "run_uuid": arguments["run_uuid"],
                "role": "user",
                "message": arguments["user_query"],
                "updated_by": arguments["updated_by"],
            },
        )

        # Initialize run record
        run = insert_update_run(
            info,
            **{
                "thread_uuid": arguments["thread_uuid"],
                "run_uuid": arguments["run_uuid"],
                "prompt_tokens": calculate_num_tokens(
                    agent,
                    "\n".join(
                        [msg["content"] for msg in input_messages if "content" in msg]
                    ),
                ),
                "updated_by": arguments["updated_by"],
            },
        )

        ai_agent_handler = get_ai_agent_handler(info=info, agent=agent)
        ai_agent_handler.context = info.context
        ai_agent_handler.run = run.__dict__
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

            # Wait until streaming is done, timeout after 60 second
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
            return False

        if ai_agent_handler.uploaded_files:
            _update_user_message_with_files(
                info,
                agent,
                user_message,
                ai_agent_handler.uploaded_files,
                arguments["updated_by"],
            )

        # Record AI assistant response
        assistant_message = insert_update_message(
            info,
            **{
                "thread_uuid": arguments["thread_uuid"],
                "run_uuid": arguments["run_uuid"],
                "message_id": ai_agent_handler.final_output["message_id"],
                "role": ai_agent_handler.final_output["role"],
                "message": ai_agent_handler.final_output["content"],
                "updated_by": arguments["updated_by"],
            },
        )

        # Update run with completion details
        run = insert_update_run(
            info,
            **{
                "thread_uuid": arguments["thread_uuid"],
                "run_uuid": arguments["run_uuid"],
                "run_id": run_id,
                "completion_tokens": calculate_num_tokens(
                    agent, ai_agent_handler.final_output["content"]
                ),
                "updated_by": arguments["updated_by"],
            },
        )
        # Mark async task as completed with results
        async_task = insert_update_async_task(
            info,
            **{
                "function_name": "async_execute_ask_model",
                "async_task_uuid": async_task_uuid,
                "result": ai_agent_handler.final_output["content"],
                "output_files": ai_agent_handler.final_output.get("output_files", []),
                "status": "completed",
                "updated_by": arguments["updated_by"],
            },
        )

        # TODO: Implement MCP Prompt and update system prmompt by analyzing user query and assistant response.
        # TODO: Invoke execute_ask_model with the updated system prompt by dispatching thread.

        return True

    except Exception as e:
        # Log and record any errors
        log = traceback.format_exc()
        info.context["logger"].error(log)
        async_task = insert_update_async_task(
            info,
            **{
                "function_name": "async_execute_ask_model",
                "async_task_uuid": async_task_uuid,
                "status": "failed",
                "updated_by": arguments["updated_by"],
                "notes": log,
            },
        )
        raise e


def _update_user_message_with_files(
    info: ResolveInfo,
    agent: Dict[str, Any],
    user_message: MessageType,
    uploaded_files: List[Dict[str, Any]],
    updated_by: str,
) -> None:
    """Helper function to update message content with file references"""
    if agent.llm["llm_name"] == "gpt":
        message_content = [{"type": "input_text", "text": user_message.message}]

        # Add each file reference to content array
        message_content.extend(
            {"type": "input_file", "file_id": uploaded_file["file_id"]}
            for uploaded_file in uploaded_files
        )
    elif agent.llm["llm_name"] == "gemini":
        message_content = [{"type": "input_text", "text": user_message.message}]

        # Add each file reference to content array
        message_content.extend(
            {"type": "input_file", "file_name": uploaded_file["file_name"]}
            for uploaded_file in uploaded_files
        )
    elif agent.llm["llm_name"] == "claude":
        message_content = [{"type": "text", "text": user_message.message}]

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

    insert_update_message(
        info,
        **{
            "thread_uuid": user_message.run["thread"]["thread_uuid"],
            "message_uuid": user_message.message_uuid,
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
