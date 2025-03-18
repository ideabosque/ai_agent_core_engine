#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import logging
import traceback
from typing import Any, Dict, List

import humps
from graphene import ResolveInfo

from silvaengine_utility import Utility  # Reuse existing utility functions

from ..models.message import resolve_message_list
from .config import Config  # Import Config class


def fetch_graphql_schema(
    logger: logging.Logger,
    endpoint_id: str,
    function_name: str,
    setting: Dict[str, Any] = {},
) -> Dict[str, Any]:
    if Config.schemas.get(function_name) is None:
        Config.schemas[function_name] = Utility.fetch_graphql_schema(
            logger,
            endpoint_id,
            function_name,
            setting=setting,
            aws_lambda=Config.aws_lambda,
            test_mode=setting.get("test_mode"),
        )
    return Config.schemas[function_name]


def execute_graphql_query(
    logger: logging.Logger,
    endpoint_id: str,
    function_name: str,
    operation_name: str,
    operation_type: str,
    variables: Dict[str, Any],
    setting: Dict[str, Any] = {},
    connection_id: str = None,
) -> Dict[str, Any]:
    schema = fetch_graphql_schema(logger, endpoint_id, function_name, setting=setting)
    result = Utility.execute_graphql_query(
        logger,
        endpoint_id,
        function_name,
        Utility.generate_graphql_operation(operation_name, operation_type, schema),
        variables,
        setting=setting,
        aws_lambda=Config.aws_lambda,
        connection_id=connection_id,
        test_mode=setting.get("test_mode"),
    )
    return result


def execute_ask_model_handler(
    logger: logging.Logger,
    endpoint_id: str,
    setting: Dict[str, Any] = None,
    connection_id: str = None,
    **variables: Dict[str, Any],
) -> Dict[str, Any]:
    """Insert update AsyncTask."""
    execute_ask_model = execute_graphql_query(
        logger,
        endpoint_id,
        "ai_agent_core_graphql",
        "executeAskModel",
        "Query",
        variables,
        setting=setting,
        connection_id=connection_id,
    )["executeAskModel"]
    return humps.decamelize(execute_ask_model)


def insert_update_tool_call(
    logger: logging.Logger,
    endpoint_id: str,
    setting: Dict[str, Any] = None,
    **variables: Dict[str, Any],
) -> Dict[str, Any]:
    """Insert update AsyncTask."""
    tool_call = execute_graphql_query(
        logger,
        endpoint_id,
        "ai_agent_core_graphql",
        "insertUpdateToolCall",
        "Mutation",
        variables,
        setting=setting,
    )["insertUpdateToolCall"]["toolCall"]
    return humps.decamelize(tool_call)


def get_input_messages(info: ResolveInfo, thread_uuid: str) -> List[Dict[str, any]]:
    """Get messages."""
    try:
        message_list = resolve_message_list(info, **{"threadUuid": thread_uuid})

        if message_list.total == 0:
            return []

        messages = [
            {
                "role": message.role,
                "message": message.message,
                "created_at": message.created_at,
            }
            for message in message_list.message_list
        ]

        return [
            {"role": msg["role"], "content": msg["message"]}
            for msg in sorted(messages, key=lambda x: x["created_at"], reverse=True)[
                :10
            ]
        ]

    except Exception as e:
        info.context["logger"].error(traceback.format_exc())
        raise e
