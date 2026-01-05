# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import logging
import traceback
from typing import Any, Dict

from silvaengine_utility import Serializer

from ..models.tool_call import insert_update_tool_call, resolve_tool_call_list
from ..utils.listener import create_listener_info
from .ai_agent import execute_ask_model
from .config import Config


def async_execute_ask_model(
    logger: logging.Logger, setting: Dict[str, Any], **kwargs: Dict[str, Any]
) -> None:
    """
    Wrapper function to execute ask_model asynchronously.

    Args:
        logger: Logger instance for tracking execution
        kwargs: Dictionary containing:
            - endpoint_id: Endpoint identifier
            - async_task_uuid: Async task UUID (required)
            - arguments: Execution arguments (required)
            - connection_id: Connection identifier
            - setting: Additional settings dict
    """
    info = create_listener_info(logger, "ask_model", setting, **kwargs)

    execute_ask_model(
        info,
        **{
            "async_task_uuid": kwargs["async_task_uuid"],
            "arguments": kwargs["arguments"],
        },
    )


def async_insert_update_tool_call(
    logger: logging.Logger, setting: Dict[str, Any], **kwargs: Dict[str, Any]
) -> None:
    """
    Asynchronously insert or update a tool call record.

    Args:
        logger: Logger instance for tracking execution
        kwargs: Dictionary containing tool call parameters
    """
    # Create info object with context
    info = create_listener_info(logger, "insert_update_tool_call", setting, **kwargs)

    # Get existing tool call if it exists
    tool_call_list = resolve_tool_call_list(
        info,
        thread_uuid=kwargs.get("thread_uuid"),
        tool_call_id=kwargs.get("tool_call_id"),
    )

    tool_call_uuid = (
        tool_call_list.tool_call_list[0].tool_call_uuid
        if tool_call_list.total > 0
        else None
    )

    # Insert/update tool call with filtered parameters
    tool_call_params = {
        "thread_uuid": kwargs.get("thread_uuid"),
        "tool_call_uuid": tool_call_uuid,
        "run_uuid": kwargs.get("run_uuid"),
        "tool_call_id": kwargs.get("tool_call_id"),
        "tool_type": kwargs.get("tool_type"),
        "name": kwargs.get("name"),
        "arguments": kwargs.get("arguments"),
        "content": kwargs.get("content"),
        "status": kwargs.get("status"),
        "notes": kwargs.get("notes"),
        "updated_by": kwargs.get("updated_by"),
    }

    tool_call = insert_update_tool_call(
        info, **{k: v for k, v in tool_call_params.items() if v is not None}
    )

    logger.info(f"Tool Call: {tool_call.__dict__}.")


def send_data_to_stream(logger: logging.Logger, **kwargs: Dict[str, Any]) -> bool:
    try:
        # Send the message to the WebSocket client using the connection ID
        connection_id = kwargs["connection_id"]
        data = kwargs["data"]
        Config.apigw_client.post_to_connection(
            ConnectionId=connection_id, Data=Serializer.json_dumps(data)
        )

        return True
    except Exception as e:
        log = traceback.format_exc()
        logger.error(log)
        raise e
