#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import logging
import traceback
from typing import Any, Dict, List

import anthropic
import tiktoken
from google import genai
from graphene import ResolveInfo

from silvaengine_utility import Utility

from ..models.async_task import insert_update_async_task
from ..models.message import resolve_message_list
from ..models.tool_call import resolve_tool_call_list
from .config import Config


def create_listener_info(
    logger: logging.Logger,
    field_name: str,
    setting: Dict[str, Any],
    **kwargs: Dict[str, Any],
) -> ResolveInfo:
    # Minimal example: some parameters can be None if you're only testing
    info = ResolveInfo(
        field_name=field_name,
        field_asts=[],  # or [some_field_node]
        return_type=None,  # e.g., GraphQLString
        parent_type=None,  # e.g., schema.get_type("Query")
        schema=None,  # your GraphQLSchema
        fragments={},
        root_value=None,
        operation=None,
        variable_values={},
        context={
            "setting": setting,
            "endpoint_id": kwargs.get("endpoint_id"),
            "logger": logger,
            "connectionId": kwargs.get("connection_id"),
        },
        path=None,
    )
    return info


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
            "arguments": {k: v for k, v in arguments.items() if k != "updated_by"},
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
        invocation_type="Event",
    )

    return async_task.async_task_uuid


# Retrieves and formats message history for a thread
def get_input_messages(
    info: ResolveInfo,
    thread_uuid: str,
    num_of_messages: int,
    tool_call_role: str,
) -> List[Dict[str, any]]:
    """
    Retrieves message history for a thread.

    Args:
        info: GraphQL resolver info
        thread_uuid: UUID of the thread to get messages for
        num_of_messages: Number of messages to retrieve
        tool_call_role: Role to assign to tool call messages

    Returns:
        List of message dictionaries in chronological order, combining both regular messages
        and tool call messages. Each message contains role and content fields.

    Raises:
        Exception: If there is an error retrieving messages from either message_list or tool_call_list
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
                        "role": tool_call_role,
                        "content": Utility.json_dumps(
                            {
                                "tool": {
                                    "tool_type": tool_call.tool_type,
                                    "name": tool_call.name,
                                    "arguments": tool_call.arguments,
                                },
                                "output": tool_call.content,
                            }
                        ),
                    },
                    "created_at": tool_call.created_at,
                }
            )

        # TODO: Implement message processing pipeline (long term memory) to:
        # 1. Update conversation context in the graph database
        # 2. Retrieve relevant long-term memory based on message content
        # 3. Integrate memory retrieval with vector embeddings for semantic search
        # 4. Handle memory pruning/summarization for efficient storage
        # Notes:
        # Asynchronously update long-term memory with new conversation context
        # Synchronously fetch relevant historical context from long-term memory store
        # Combine historical context with current conversation thread
        # Use semantic similarity to prioritize most relevant memories
        # Prune and summarize older memories to maintain storage efficiency

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


def calculate_num_tokens(agent: dict[str, Any], text: str) -> int:
    """
    Calculates the number of tokens for a given model.

    Args:
        agent: Dictionary containing LLM configuration including model name and API key
        text: The input text to tokenize

    Returns:
        Number of tokens in the text for the specified model

    Raises:
        Exception: If there is an error getting the encoding or calculating tokens
    """
    try:
        if agent.llm["llm_name"] == "openai":
            encoding = tiktoken.encoding_for_model(agent.configuration["model"])
            num_tokens = len(encoding.encode(text))
            return num_tokens
        elif agent.llm["llm_name"] == "gemini":
            client = genai.Client(api_key=agent.configuration["api_key"])
            num_tokens = client.models.count_tokens(
                model=agent.configuration["model"], contents=text
            ).total_tokens
            return num_tokens
        elif agent.llm["llm_name"] == "anthropic":
            client = anthropic.Anthropic(api_key=agent.configuration["api_key"])
            num_tokens = client.messages.count_tokens(
                model=agent.configuration["model"],
                messages=[{"role": "user", "content": text}],
            ).input_tokens
            return num_tokens
        else:
            raise Exception(f"Unsupported LLM: {agent.llm['llm_name']}")
    except Exception as e:
        # Log error and re-raise
        raise e
