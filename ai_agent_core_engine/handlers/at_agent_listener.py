# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import logging
import traceback
from typing import Any, Dict

from graphene import ResolveInfo

from silvaengine_utility import Utility

from ..models.agent import resolve_agent
from ..models.async_task import insert_update_async_task
from ..models.message import insert_update_message
from ..models.run import insert_update_run
from ..types.async_task import AsyncTaskType
from .ai_agent_utility import (
    execute_ask_model_handler,
    get_input_messages,
    insert_update_tool_call,
)


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
                "function_name": "async_ask_model",
                "async_task_uuid": async_task_uuid,
                "status": "in_progress",
                "updated_by": arguments["updated_by"],
            },
        )

        # Retrieve AI agent configuration
        agent = resolve_agent(info, **{"agent_uuid": arguments["agent_uuid"]})

        # Build conversation history and add new user query
        input_messages = get_input_messages(info, arguments["thread_uuid"])
        input_messages.append({"role": "user", "content": arguments["user_query"]})

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
                "prompt_tokens": 0,  # TODO: Implement token counting for user query
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
            run.__dict__,
            **info.context.get("setting", {}),
        )

        # Process query through AI model
        run_id = ai_agent_handler.ask_model(input_messages)

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
                "completion_tokens": 0,  # TODO: Implement token counting for AI response
                "total_tokens": 0,  # TODO: Implement total token calculation
                "updated_by": arguments["updated_by"],
            },
        )

        # Mark async task as completed with results
        async_task = insert_update_async_task(
            info,
            **{
                "function_name": "async_ask_model",
                "async_task_uuid": async_task_uuid,
                "result": ai_agent_handler.final_output["content"],
                "status": "completed",
                "updated_by": arguments["updated_by"],
            },
        )

        return async_task

    except Exception as e:
        # Log and record any errors
        log = traceback.format_exc()
        info.context["logger"].error(log)
        async_task = insert_update_async_task(
            info,
            **{
                "function_name": "async_ask_model",
                "async_task_uuid": async_task_uuid,
                "status": "failed",
                "updated_by": arguments["updated_by"],
                "notes": log,
            },
        )
        raise e


def async_execute_ask_model(logger: logging.Logger, **kwargs: Dict[str, Any]) -> None:
    """
    Wrapper function to execute ask_model asynchronously.

    Args:
        logger: Logger instance for tracking execution
        kwargs: Dictionary containing execution parameters
    """
    endpoint_id = kwargs.get("endpoint_id")
    async_task_uuid = kwargs["async_task_uuid"]
    arguments = kwargs["arguments"]
    connection_id = kwargs.get("connection_id")
    setting = kwargs.get("setting", {})

    execute_ask_model = execute_ask_model_handler(
        logger,
        endpoint_id,
        setting=setting,
        connection_id=connection_id,
        **{
            "asyncTaskUuid": async_task_uuid,
            "arguments": arguments,
        },
    )


def async_insert_update_tool_call(
    logger: logging.Logger, **kwargs: Dict[str, Any]
) -> None:
    """
    Asynchronously insert or update a tool call record.

    Args:
        logger: Logger instance for tracking execution
        kwargs: Dictionary containing tool call parameters
    """
    endpoint_id = kwargs.get("endpoint_id")
    setting = kwargs.get("setting", {})
    tool_call = insert_update_tool_call(
        logger,
        endpoint_id,
        setting=setting,
        **{
            "threadUuid": kwargs.get("thread_uuid"),
            "toolCallUuid": kwargs.get("tool_call_uuid"),
            "runUuid": kwargs.get("run_uuid"),
            "toolCallId": kwargs.get("tool_call_id"),
            "toolType": kwargs.get("tool_type"),
            "name": kwargs.get("name"),
            "arguments": kwargs.get("arguments"),
            "content": kwargs.get("content"),
            "updatedBy": kwargs.get("updated_by"),
        },
    )
