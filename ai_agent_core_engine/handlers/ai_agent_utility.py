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

from ..models.async_task import insert_update_async_task
from ..models.message import resolve_message_list
from ..models.tool_call import resolve_tool_call_list
from .config import Config


def start_async_task(
    info: ResolveInfo, function_name: str, **arguments: Dict[str, Any]
) -> str:
    """
    Initialize and trigger an asynchronous task for processing the model request.
    Creates a task record in the database and invokes an AWS Lambda function asynchronously.

    Args:
        info: GraphQL resolver context containing logger, endpoint_id, connectionId and settings
        function_name: Name of the Lambda function to invoke
        **arguments: Task parameters including thread_uuid, run_uuid, agent_uuid, user_query etc.

    Returns:
        async_task_uuid: Unique identifier for tracking the async task

    Note:
        The function creates an async task record, prepares Lambda invocation parameters,
        and triggers the Lambda function asynchronously using the Utility helper.
    """

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
        function_name,
        params=params,
        setting=info.context["setting"],
        test_mode=info.context["setting"].get("test_mode"),
        aws_lambda=Config.aws_lambda,
    )

    return async_task.async_task_uuid


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
    """
    Executes a GraphQL query with the provided parameters.

    Args:
        logger: Logger instance for error reporting
        endpoint_id: ID of the endpoint to execute query against
        function_name: Name of function to execute
        operation_name: Name of the GraphQL operation
        operation_type: Type of operation (query/mutation)
        variables: Variables to pass to the query
        setting: Optional settings dictionary
        connection_id: Optional connection ID

    Returns:
        Dict containing the query results
    """
    # Get schema and execute query
    schema = Config.fetch_graphql_schema(
        logger, endpoint_id, function_name, setting=setting
    )
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
    """
    Executes an AI model query and returns decamelized response.

    Args:
        logger: Logger instance for error reporting
        endpoint_id: ID of the endpoint to execute query against
        setting: Optional settings dictionary
        connection_id: Optional connection ID
        **variables: Variables to pass to the query

    Returns:
        Dict containing the decamelized query response
    """
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
    """
    Retrieves a list of tool calls.

    Args:
        logger: Logger instance for error reporting
        endpoint_id: ID of the endpoint to query
        setting: Optional settings dictionary
        **variables: Variables to pass to the query

    Returns:
        Dict containing the decamelized tool call list
    """
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
    """
    Creates or updates a tool call.

    Args:
        logger: Logger instance for error reporting
        endpoint_id: ID of the endpoint to execute mutation against
        setting: Optional settings dictionary
        **variables: Variables to pass to the mutation

    Returns:
        Dict containing the decamelized tool call data
    """
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
def get_input_messages(
    info: ResolveInfo, thread_uuid: str, num_of_messages: int
) -> List[Dict[str, any]]:
    """
    Retrieves message history for a thread.

    Args:
        info: GraphQL resolver info
        thread_uuid: UUID of the thread to get messages for
        num_of_messages: Number of messages to retrieve

    Returns:
        List of message dictionaries in chronological order

    Raises:
        Exception: If there is an error retrieving messages
    """
    try:
        # Get message list for thread
        message_list = resolve_message_list(info, **{"thread_uuid": thread_uuid})
        # Get tool call list for thread
        tool_call_list = resolve_tool_call_list(info, **{"thread_uuid": thread_uuid})

        # Return empty list if no messages or no tool_call found
        if message_list.total == 0 and tool_call_list.total == 0:
            return []

        # Combine messages from both message_list and tool_call_list
        seen_contents = set()
        messages = []

        # Add regular messages
        for message in message_list.message_list:
            if message.message in seen_contents:
                continue

            seen_contents.add(message.message)
            messages.append(
                {
                    "message": {
                        "role": message.role,
                        "content": message.message,
                    },
                    "created_at": message.created_at,
                }
            )

        # Add tool call messages
        for tool_call in tool_call_list.tool_call_list:
            if tool_call.content in seen_contents:
                continue

            seen_contents.add(tool_call.content)
            messages.append(
                {
                    "message": {
                        "role": "system",
                        "content": tool_call.content,
                    },
                    "created_at": tool_call.created_at,
                }
            )

        # TODO: Implement message processing pipeline (long term memory) to:
        # 1. Update conversation context in the graph database
        # 2. Retrieve relevant long-term memory based on message content
        # 3. Integrate memory retrieval with vector embeddings for semantic search
        # 4. Handle memory pruning/summarization for efficient storage

        # Return last 10 messages sorted by creation time (most recent first)
        # Remove timestamps and reverse to get chronological order
        return [
            msg["message"]
            for msg in sorted(messages, key=lambda x: x["created_at"], reverse=True)
        ][:num_of_messages][::-1]
    except Exception as e:
        # Log error and re-raise with full traceback
        info.context["logger"].error(traceback.format_exc())
        raise e


def calculate_num_tokens(model: str, text: str) -> int:
    """
    Calculates the number of tokens for a given model.

    Args:
        model: The name of the model to calculate tokens for (e.g. 'gpt-3.5-turbo')
        text: The input text to tokenize

    Returns:
        Number of tokens in the text for the specified model

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
