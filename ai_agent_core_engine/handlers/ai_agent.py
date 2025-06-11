# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import threading
import traceback
from queue import Queue
from typing import Any, Dict, Tuple

from graphene import ResolveInfo

from silvaengine_utility import Utility

from ..models.agent import resolve_agent
from ..models.async_task import insert_update_async_task
from ..models.message import insert_update_message
from ..models.run import insert_update_run
from ..models.thread import insert_thread, resolve_thread
from ..types.ai_agent import AskModelType
from ..types.async_task import AsyncTaskType
from .ai_agent_utility import calculate_num_tokens, get_input_messages, start_async_task
from .config import Config


def ask_model(info: ResolveInfo, **kwargs: Dict[str, Any]) -> AskModelType:
    """
    Process a user query through an AI model and return the response asynchronously.

    Args:
        info: GraphQL resolver context containing logger, endpoint and connection info
        **kwargs: Parameters including:
            - thread_uuid: Optional ID of existing conversation thread
            - agent_uuid: ID of AI agent to use
            - user_id: Optional ID of the user
            - user_query: The actual query text
            - stream: Whether to stream responses (default False)
            - updated_by: User making the request

    Returns:
        AskModelType containing thread, task and run identifiers
    """
    try:
        # Log request details
        info.context.get("logger").info(
            f"endpoint_id: {info.context.get('endpoint_id')}"
        )
        info.context.get("logger").info(
            f"connection_id: {info.context.get('connectionId')}"
        )

        # Get or create conversation thread
        thread = None
        if "thread_uuid" in kwargs:
            thread = resolve_thread(
                info,
                **{"thread_uuid": kwargs["thread_uuid"]},
            )
        else:
            thread = insert_thread(
                info,
                **{
                    "agent_uuid": kwargs["agent_uuid"],
                    "user_id": kwargs.get("user_id"),
                    "updated_by": kwargs["updated_by"],
                },
            )

        # Create new run instance for this request
        run = insert_update_run(
            info,
            **{
                "thread_uuid": thread.thread_uuid,
                "updated_by": kwargs["updated_by"],
            },
        )

        # Prepare arguments for async processing
        arguments = {
            "thread_uuid": thread.thread_uuid,
            "run_uuid": run.run_uuid,
            "agent_uuid": kwargs["agent_uuid"],
            "user_query": kwargs["user_query"],
            "stream": kwargs.get("stream", False),
            "updated_by": kwargs["updated_by"],
        }

        # Start async task and get identifiers
        function_name = "async_execute_ask_model"
        async_task_uuid = start_async_task(
            info,
            function_name,
            **arguments,
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


def execute_ask_model(info: ResolveInfo, **kwargs: Dict[str, Any]) -> AsyncTaskType:
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
        info.context.get("logger").info(
            f"endpoint_id: {info.context.get('endpoint_id')}"
        )
        info.context.get("logger").info(
            f"connection_id: {info.context.get('connectionId')}"
        )
        endpoint_id = info.context.get("endpoint_id")
        connection_id = info.context.get("connectionId")
        async_task_uuid = kwargs["async_task_uuid"]
        arguments = kwargs["arguments"]

        # Initialize async task as in-progress
        info.context.get("logger").info(
            f"async_task_uuid: {async_task_uuid}/in_progress."
        )
        async_task = insert_update_async_task(
            info,
            **{
                "function_name": "async_execute_ask_model",
                "async_task_uuid": async_task_uuid,
                "status": "in_progress",
                "updated_by": arguments["updated_by"],
            },
        )

        # Retrieve AI agent configuration
        agent = resolve_agent(info, **{"agent_uuid": arguments["agent_uuid"]})

        # Build conversation history and add new user query
        input_messages = get_input_messages(
            info,
            arguments["thread_uuid"],
            int(agent.num_of_messages),
            agent.tool_call_role,
        )

        # Check if string starts with { or [ to identify potential JSON
        is_potential_json = arguments["user_query"].strip().startswith(("{", "["))

        if is_potential_json:
            try:
                user_query = Utility.json_loads(arguments["user_query"])
            except:
                user_query = arguments["user_query"]
        else:
            user_query = arguments["user_query"]

        input_messages.append({"role": "user", "content": user_query})

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
        info.context.get("logger").info(f"User Message: {user_message.__dict__}.")

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

        # Dynamically load and initialize AI agent handler
        ai_agent_handler_class = getattr(
            __import__(agent.llm["module_name"]),
            agent.llm["class_name"],
        )
        ai_agent_handler = ai_agent_handler_class(
            info.context.get("logger"),
            agent.__dict__,
            **info.context.get("setting", {}),
        )
        ai_agent_handler.endpoint_id = endpoint_id
        ai_agent_handler.run = run.__dict__
        ai_agent_handler.connection_id = connection_id
        ai_agent_handler.task_queue = Config.task_queue

        if connection_id or arguments.get("stream", False):
            stream_queue = Queue()
            stream_event = threading.Event()

            # Trigger a streaming ask_model in a separate thread if desired:
            stream_thread = threading.Thread(
                target=ai_agent_handler.ask_model,
                args=[input_messages, stream_queue, stream_event],
                daemon=True,
            )
            stream_thread.start()

            # Wait until we get the run_id from the queue
            current_run = stream_queue.get()
            if current_run["name"] == "run_id":
                run_id = current_run["value"]
                info.context["logger"].info(f"Current Run ID: {current_run['value']}")

            # Wait until streaming is done, timeout after 60 second
            stream_event.wait(timeout=120)
            info.context["logger"].info("Streaming ask_model finished.")
        else:
            # Process query through AI model
            run_id = ai_agent_handler.ask_model(input_messages)

        # Verify final_output is a dict and contains required fields message_id, role, content with non-empty values
        assert isinstance(ai_agent_handler.final_output, dict) and all(
            key in ai_agent_handler.final_output and ai_agent_handler.final_output[key]
            for key in ["message_id", "role", "content"]
        ), "final_output must be a dict containing non-empty values for message_id, role and content fields"

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
        info.context.get("logger").info(
            f"Assistant Message: {assistant_message.__dict__}."
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
                "status": "completed",
                "updated_by": arguments["updated_by"],
            },
        )

        info.context.get("logger").info(f"Async Task: {async_task.__dict__}.")

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
