# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import logging
import traceback
from typing import Any, Dict

from silvaengine_utility import Utility

from .ai_agent_utility import (
    execute_ask_model_handler,
    get_tool_call_list,
    insert_update_tool_call,
)
from .config import Config


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

    logger.info(f"Execute Ask Model: {execute_ask_model}.")


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
    tool_call_list = get_tool_call_list(
        logger,
        endpoint_id,
        setting=setting,
        **{
            "threadUuid": kwargs.get("thread_uuid"),
            "toolCallId": kwargs.get("tool_call_id"),
        },
    )

    tool_call_uuid = None
    if tool_call_list["total"] > 0:
        tool_call_uuid = tool_call_list["tool_call_list"][0]["tool_call_uuid"]

    tool_call = insert_update_tool_call(
        logger,
        endpoint_id,
        setting=setting,
        **{
            "threadUuid": kwargs.get("thread_uuid"),
            "toolCallUuid": tool_call_uuid,
            "runUuid": kwargs.get("run_uuid"),
            "toolCallId": kwargs.get("tool_call_id"),
            "toolType": kwargs.get("tool_type"),
            "name": kwargs.get("name"),
            "arguments": kwargs.get("arguments"),
            "content": kwargs.get("content"),
            "status": kwargs.get("status"),
            "notes": kwargs.get("notes"),
            "updatedBy": kwargs.get("updated_by"),
        },
    )

    logger.info(f"Tool Call: {tool_call}.")


def send_data_to_websocket(logger: logging.Logger, **kwargs: Dict[str, Any]) -> None:
    try:
        # Send the message to the WebSocket client using the connection ID
        connection_id = kwargs["connection_id"]
        data = kwargs["data"]
        Config.apigw_client.post_to_connection(
            ConnectionId=connection_id, Data=Utility.json_dumps(data)
        )

        return True
    except Exception as e:
        log = traceback.format_exc()
        logger.error(log)
        raise e
