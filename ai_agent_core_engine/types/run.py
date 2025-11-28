#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from graphene import DateTime, Field, Int, List, ObjectType, String

from silvaengine_dynamodb_base import ListObjectType

from .thread import ThreadType


def _get_tool_call_type():
    from .tool_call import ToolCallType

    return ToolCallType


class RunType(ObjectType):
    thread_uuid = String()
    endpoint_id = String()
    run_uuid = String()
    run_id = String()
    completion_tokens = Int()
    prompt_tokens = Int()
    total_tokens = Int()
    time_spent = Int()
    updated_by = String()
    created_at = DateTime()
    updated_at = DateTime()

    # Nested resolvers with DataLoader batch fetching for efficient database access
    thread = Field(lambda: ThreadType)
    tool_calls = List(_get_tool_call_type)

    # ------- Nested resolvers -------

    def resolve_thread(parent, info):
        """Resolve nested Thread for this run using DataLoader."""
        from ..models.batch_loaders import get_loaders

        # Case 2: already embedded
        existing = getattr(parent, "thread", None)
        if isinstance(existing, dict):
            return ThreadType(**existing)

        # Case 1: need to fetch using DataLoader
        endpoint_id = getattr(parent, "endpoint_id", None) or info.context.get(
            "endpoint_id"
        )
        thread_uuid = getattr(parent, "thread_uuid", None)
        if not endpoint_id or not thread_uuid:
            return None

        loaders = get_loaders(info.context)
        return loaders.thread_loader.load((endpoint_id, thread_uuid)).then(
            lambda thread_dict: ThreadType(**thread_dict) if thread_dict else None
        )

    def resolve_tool_calls(parent, info):
        """Resolve nested ToolCalls for this run using DataLoader.

        Note: Uses ToolCallsByRunLoader for efficient batch loading of one-to-many
        relationships with caching support.
        """
        from ..models.batch_loaders import get_loaders
        from .tool_call import ToolCallType

        # Check if already embedded
        existing = getattr(parent, "tool_calls", None)
        if isinstance(existing, list) and existing:
            return [
                ToolCallType(**tc) if isinstance(tc, dict) else tc for tc in existing
            ]

        # Fetch tool calls for this run
        run_uuid = getattr(parent, "run_uuid", None)
        if not run_uuid:
            return []

        loaders = get_loaders(info.context)
        return loaders.tool_calls_by_run_loader.load(run_uuid).then(
            lambda tc_dicts: [ToolCallType(**tc_dict) for tc_dict in tc_dicts]
        )


class RunListType(ListObjectType):
    run_list = List(RunType)
