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
    Resolver function for the AskModelType.
    Args:
        obj: The object being resolved.
        info: Information about the GraphQL query.
        **kwargs: Additional keyword arguments.
    Returns:
        An instance of AskModelType.
    """
    try:
        info.context.get("logger").info(
            f"endpoint_id: {info.context.get('endpoint_id')}"
        )
        info.context.get("logger").info(
            f"connection_id: {info.context.get('connectionId')}"
        )

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

        run = insert_update_run(
            info,
            **{
                "thread_uuid": thread.thread_uuid,
                "updated_by": kwargs["updated_by"],
            },
        )

        arguments = {
            "thread_uuid": thread.thread_uuid,
            "run_uuid": run.run_uuid,
            "agent_uuid": kwargs["agent_uuid"],
            "user_query": kwargs["user_query"],
            "stream": kwargs.get("stream", False),
            "updated_by": kwargs["updated_by"],
        }

        function_name, async_task_uuid = start_async_task(
            info,
            **arguments,
        )

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
    Start an asynchronous task.
    Args:
        info: Information about the GraphQL query.
        **arguments: Additional keyword arguments.
    Returns:
        A tuple containing the function name, asynchronous task UUID, and current run ID.
    """
    function_name = "async_ask_model"
    async_task = insert_update_async_task(
        info,
        **{
            "function_name": function_name,
            "arguments": arguments,
            "updated_by": arguments["updated_by"],
        },
    )

    params = {
        "async_task_uuid": async_task.async_task_uuid,
        "arguments": arguments,
    }
    if info.context.get("connectionId"):
        params["connection_id"] = info.context.get("connectionId")

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
