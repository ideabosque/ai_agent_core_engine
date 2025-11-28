#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from graphene import DateTime, Field, List, ObjectType, String
from silvaengine_dynamodb_base import ListObjectType


class ThreadType(ObjectType):
    endpoint_id = String()
    thread_uuid = String()
    agent_uuid = String()
    user_id = String()
    created_at = DateTime()

    # Nested resolvers: strongly-typed nested relationships
    agent = Field(lambda: AgentType)
    messages = List(lambda: MessageType)
    runs = List(lambda: RunType)

    # ------- Nested resolvers -------

    def resolve_agent(parent, info):
        """Resolve nested Agent for this thread using DataLoader."""
        from ..models.batch_loaders import get_loaders
        from .agent import AgentType

        # Case 2: already embedded
        existing = getattr(parent, "agent", None)
        if isinstance(existing, dict):
            return AgentType(**existing)

        # Case 1: need to fetch using DataLoader
        endpoint_id = getattr(parent, "endpoint_id", None) or info.context.get(
            "endpoint_id"
        )
        agent_uuid = getattr(parent, "agent_uuid", None)
        if not endpoint_id or not agent_uuid:
            return None

        loaders = get_loaders(info.context)
        return loaders.agent_loader.load((endpoint_id, agent_uuid)).then(
            lambda agent_dict: AgentType(**agent_dict) if agent_dict else None
        )

    def resolve_messages(parent, info):
        """Resolve nested Messages for this thread using DataLoader.

        Note: Uses MessagesByThreadLoader and ToolCallsByThreadLoader for efficient
        batch loading with caching support. Combines messages and tool calls similar
        to combine_thread_messages but with batch loading.
        """
        from ..models.batch_loaders import get_loaders
        from silvaengine_utility import Utility

        # Check if already embedded
        existing = getattr(parent, "messages", None)
        if isinstance(existing, list) and existing:
            return existing

        # Fetch messages for this thread
        thread_uuid = getattr(parent, "thread_uuid", None)
        if not thread_uuid:
            return []

        # Get agent to determine tool_call_role
        endpoint_id = getattr(parent, "endpoint_id", None) or info.context.get(
            "endpoint_id"
        )
        agent_uuid = getattr(parent, "agent_uuid", None)
        if not endpoint_id or not agent_uuid:
            return []

        loaders = get_loaders(info.context)

        # Load agent to get tool_call_role
        def process_messages_and_tool_calls(results):
            agent_dict, message_dicts, tool_call_dicts = results

            tool_call_role = (
                agent_dict.get("tool_call_role", "developer")
                if agent_dict else "developer"
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
                            "content": Utility.json_dumps(
                                {
                                    "tool": {
                                        "tool_call_id": tool_call_dict.get("tool_call_id"),
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
            return sorted(messages, key=lambda x: x["created_at"], reverse=False)

        # Load agent, messages, and tool calls in parallel using batch loaders
        from promise import Promise

        return Promise.all([
            loaders.agent_loader.load((endpoint_id, agent_uuid)),
            loaders.messages_by_thread_loader.load(thread_uuid),
            loaders.tool_calls_by_thread_loader.load(thread_uuid),
        ]).then(process_messages_and_tool_calls)

    def resolve_runs(parent, info):
        """Resolve nested Runs for this thread using DataLoader.

        Note: Uses RunsByThreadLoader for efficient batch loading of one-to-many
        relationships with caching support.
        """
        from ..models.batch_loaders import get_loaders
        from .run import RunType

        # Check if already embedded
        existing = getattr(parent, "runs", None)
        if isinstance(existing, list) and existing:
            return [
                RunType(**run) if isinstance(run, dict) else run for run in existing
            ]

        # Fetch runs for this thread
        thread_uuid = getattr(parent, "thread_uuid", None)
        if not thread_uuid:
            return []

        loaders = get_loaders(info.context)
        return loaders.runs_by_thread_loader.load(thread_uuid).then(
            lambda run_dicts: [RunType(**run_dict) for run_dict in run_dicts]
        )


class ThreadListType(ListObjectType):
    thread_list = List(ThreadType)


# Import at end to avoid circular dependency
from .agent import AgentType  # noqa: E402
from .message import MessageType  # noqa: E402
from .run import RunType  # noqa: E402
