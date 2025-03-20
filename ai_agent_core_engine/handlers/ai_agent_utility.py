#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import logging
import traceback
from typing import Any, Dict, List

import humps
import tiktoken
from graphene import ResolveInfo

from silvaengine_utility import Utility

from ..models.message import resolve_message_list
from ..models.tool_call import resolve_tool_call_list
from .config import Config


# Fetches and caches GraphQL schema for a given function
def fetch_graphql_schema(
    logger: logging.Logger,
    endpoint_id: str,
    function_name: str,
    setting: Dict[str, Any] = {},
) -> Dict[str, Any]:
    # Check if schema exists in cache, if not fetch and store it
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


# Executes a GraphQL query with the given parameters
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
    # Get schema and execute query
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


# Handles execution of AI model queries
def execute_ask_model_handler(
    logger: logging.Logger,
    endpoint_id: str,
    setting: Dict[str, Any] = None,
    connection_id: str = None,
    **variables: Dict[str, Any],
) -> Dict[str, Any]:
    """Executes an AI model query and returns decamelized response"""
    execute_ask_model = execute_graphql_query(
        logger,
        endpoint_id,
        "ai_agent_core_graphql",
        "executeAskModel",
        "Mutation",
        variables,
        setting=setting,
        connection_id=connection_id,
    )["executeAskModel"]
    return humps.decamelize(execute_ask_model)


def get_tool_call_list(
    logger: logging.Logger,
    endpoint_id: str,
    setting: Dict[str, Any] = None,
    **variables: Dict[str, Any],
) -> Dict[str, Any]:
    """Creates or updates a tool call and returns decamelized response"""
    tool_call_list = execute_graphql_query(
        logger,
        endpoint_id,
        "ai_agent_core_graphql",
        "toolCallList",
        "Query",
        variables,
        setting=setting,
    )["toolCallList"]
    return humps.decamelize(tool_call_list)


# Handles tool call mutations
def insert_update_tool_call(
    logger: logging.Logger,
    endpoint_id: str,
    setting: Dict[str, Any] = None,
    **variables: Dict[str, Any],
) -> Dict[str, Any]:
    """Creates or updates a tool call and returns decamelized response"""
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


# Retrieves and formats message history for a thread
def get_input_messages(info: ResolveInfo, thread_uuid: str) -> List[Dict[str, any]]:
    """Retrieves the last 10 messages from a thread in chronological order"""
    try:
        # Get message list for thread
        message_list = resolve_message_list(info, **{"thread_uuid": thread_uuid})
        # Get tool call list for thread
        tool_call_list = resolve_tool_call_list(info, **{"thread_uuid": thread_uuid})

        # Return empty list if no messages or no tool_call found
        if message_list.total == 0 and tool_call_list.total == 0:
            return []

        # Format messages with role, content and timestamp
        messages = [
            {
                "message": {
                    "role": message.role,
                    "content": message.message,
                },
                "created_at": message.created_at,
            }
            for message in message_list.message_list
        ]

        # Add tool call messages to the list
        for tool_call in tool_call_list.tool_call_list:
            # Add tool response message
            messages.append(
                {
                    "message": {
                        "role": "system",
                        "content": tool_call.content,
                    },
                    "created_at": tool_call.created_at,
                }
            )

        # Return last 10 messages sorted by creation time (most recent first)
        # Remove timestamps and reverse to get chronological order
        return [
            msg["message"]
            for msg in sorted(messages, key=lambda x: x["created_at"], reverse=True)
        ][:30][::-1]
    except Exception as e:
        # Log error and re-raise with full traceback
        info.context["logger"].error(traceback.format_exc())
        raise e


def calculate_num_tokens(model: str, text: str) -> int:
    """Calculates the number of tokens for a given model

    Args:
        model (str): The name of the model to calculate tokens for (e.g. 'gpt-3.5-turbo')
        text (str): The input text to tokenize

    Returns:
        int: Number of tokens in the text for the specified model

    Raises:
        Exception: If there is an error getting the encoding or calculating tokens
    """
    try:
        encoding = tiktoken.encoding_for_model(model)
        num_tokens = len(encoding.encode(text))
        return num_tokens
    except Exception as e:
        # Log error and re-raise
        raise e
