# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import logging
import time
import traceback
from typing import Any, Dict, Tuple

from graphene import ResolveInfo

from silvaengine_utility import Utility

from ..models.async_task import insert_update_async_task
from ..models.run import insert_update_run
from ..models.thread import insert_thread, resolve_thread
from ..types.ai_agent import AskModelType
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
        function_name, async_task_uuid = start_async_task(
            info,
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


def start_async_task(info: ResolveInfo, **arguments: Dict[str, Any]) -> Tuple[str, str]:
    """
    Initialize and trigger an asynchronous task for processing the model request.

    Args:
        info: GraphQL resolver context with AWS Lambda configuration
        **arguments: Task parameters including thread, run and query details

    Returns:
        Tuple containing:
            - function_name: Name of async handler function
            - async_task_uuid: Unique identifier for tracking the task
    """
    # Set async function name
    function_name = "async_ask_model"

    # Create task record in database
    async_task = insert_update_async_task(
        info,
        **{
            "function_name": function_name,
            "arguments": arguments,
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
        "async_execute_ask_model",
        params=params,
        setting=info.context["setting"],
        test_mode=info.context["setting"].get("test_mode"),
        aws_lambda=Config.aws_lambda,
    )

    return function_name, async_task.async_task_uuid
