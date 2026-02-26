#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from graphene import DateTime, Field, List, ObjectType, String
from promise import Promise

from silvaengine_dynamodb_base import ListObjectType
from silvaengine_utility import JSONCamelCase

from ..utils.normalization import normalize_to_json


class ThreadType(ObjectType):
    partition_key = String()
    endpoint_id = String()
    part_id = String()
    thread_uuid = String()
    agent_uuid = String()
    user_id = String()
    created_at = DateTime()

    # Nested resolvers: strongly-typed nested relationships
    agent = Field(lambda: AgentType)
    messages = List(JSONCamelCase)
    tool_calls = List(JSONCamelCase)

    # ------- Nested resolvers -------

    def resolve_agent(parent, info):
        """Resolve nested Agent for this thread using DataLoader."""
        from ..models.batch_loaders import get_loaders
        from .agent import AgentType

        # Case 2: already embedded
        existing = getattr(parent, "agent", None)
        if isinstance(existing, dict):
            return AgentType(**existing)
        if isinstance(existing, AgentType):
            return existing

        # Case 1: need to fetch using DataLoader
        partition_key = getattr(parent, "partition_key", None) or info.context.get(
            "partition_key"
        )
        agent_uuid = getattr(parent, "agent_uuid", None)
        if not partition_key or not agent_uuid:
            return None

        loaders = get_loaders(info.context)
        return loaders.agent_loader.load((partition_key, agent_uuid)).then(
            lambda agent_dict: AgentType(**agent_dict) if agent_dict else None
        )

    def resolve_messages(parent, info):
        """Resolve nested Messages for this thread as JSON-friendly list."""
        from silvaengine_utility import Serializer

        from ..models.batch_loaders import get_loaders

        # Check if already embedded
        existing = getattr(parent, "messages", None)
        if isinstance(existing, list) and existing:
            return [normalize_to_json(messages) for messages in existing]

        # Fetch messages for this thread
        thread_uuid = getattr(parent, "thread_uuid", None)
        if not thread_uuid:
            return []

        # Get agent to determine tool_call_role
        partition_key = getattr(parent, "partition_key", None) or info.context.get(
            "partition_key"
        )
        agent_uuid = getattr(parent, "agent_uuid", None)
        if not partition_key or not agent_uuid:
            return []

        loaders = get_loaders(info.context)

        # Load agent to get tool_call_role
        def process_messages_and_tool_calls(results):
            agent_dict, message_dicts, tool_call_dicts = results

            tool_call_role = (
                agent_dict.get("tool_call_role", "developer")
                if agent_dict
                else "developer"
            )

            # Return empty list if no messages or no tool_call found
            if not message_dicts and not tool_call_dicts:
                return []

            # Combine messages from both message_list and tool_call_list
            seen_contents = set()
            messages = []

            # Add regular messages
            for message_dict in message_dicts:
                message_content = message_dict.get("message")
                if message_content in seen_contents:
                    continue

                seen_contents.add(message_content)

                # Get run info if available
                run_uuid = message_dict.get("run_uuid")
                run_info = {
                    "run_uuid": run_uuid,
                    "prompt_tokens": message_dict.get("prompt_tokens", 0),
                    "completion_tokens": message_dict.get("completion_tokens", 0),
                    "total_tokens": message_dict.get("total_tokens", 0),
                }

                messages.append(
                    {
                        "message": {
                            "run": run_info,
                            "role": message_dict.get("role"),
                            "content": message_content,
                        },
                        "created_at": message_dict.get("created_at"),
                    }
                )

            # Add tool call messages
            for tool_call_dict in tool_call_dicts:
                content = tool_call_dict.get("content")
                if content in seen_contents:
                    continue

                seen_contents.add(content)
                messages.append(
                    {
                        "message": {
                            "role": tool_call_role,
                            "content": Serializer.json_dumps(
                                {
                                    "tool": {
                                        "tool_call_id": tool_call_dict.get(
                                            "tool_call_id"
                                        ),
                                        "tool_type": tool_call_dict.get("tool_type"),
                                        "name": tool_call_dict.get("name"),
                                        "arguments": tool_call_dict.get("arguments"),
                                    },
                                    "output": content,
                                }
                            ),
                        },
                        "created_at": tool_call_dict.get("created_at"),
                    }
                )

            # Sort by created_at
            return normalize_to_json(
                sorted(messages, key=lambda x: x["created_at"], reverse=False)
            )

        # Load agent, messages, and tool calls in parallel using batch loaders
        return Promise.all(
            [
                loaders.agent_loader.load((partition_key, agent_uuid)),
                loaders.messages_by_thread_loader.load(thread_uuid),
                loaders.tool_calls_by_thread_loader.load(thread_uuid),
            ]
        ).then(process_messages_and_tool_calls)

    def resolve_tool_calls(parent, info):
        """Resolve nested Tool Calls for this thread as JSON-friendly list."""
        from ..models.batch_loaders import get_loaders

        # Check if already embedded
        existing = getattr(parent, "tool_calls", None)
        if isinstance(existing, list) and existing:
            return existing

        # Fetch tool calls for this thread
        thread_uuid = getattr(parent, "thread_uuid", None)
        if not thread_uuid:
            return []

        loaders = get_loaders(info.context)
        return loaders.tool_calls_by_thread_loader.load(thread_uuid).then(
            lambda tool_call_dicts: (
                [
                    normalize_to_json(tool_call_dict)
                    for tool_call_dict in tool_call_dicts
                ]
                if tool_call_dicts
                else []
            )
        )


class ThreadListType(ListObjectType):
    thread_list = List(ThreadType)


# Import at end to avoid circular dependency
from .agent import AgentType  # noqa: E402
