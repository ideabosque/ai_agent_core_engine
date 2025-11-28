#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from graphene import DateTime, Field, Int, List, ObjectType, String
from silvaengine_dynamodb_base import ListObjectType

from .run import RunType


class ToolCallType(ObjectType):
    thread_uuid = String()
    run_uuid = String()
    tool_call_uuid = String()
    tool_call_id = String()
    tool_type = String()
    name = String()
    arguments = String()
    content = String()
    status = String()
    notes = String()
    time_spent = Int()
    updated_by = String()
    created_at = DateTime()
    updated_at = DateTime()

    # Nested resolvers with DataLoader batch fetching for efficient database access
    run = Field(lambda: RunType)

    # ------- Nested resolvers -------

    def resolve_run(parent, info):
        """Resolve nested Run for this tool call using DataLoader."""
        from ..models.batch_loaders import get_loaders

        # Case 2: already embedded
        existing = getattr(parent, "run", None)
        if isinstance(existing, dict):
            return RunType(**existing)

        # Case 1: need to fetch using DataLoader
        thread_uuid = getattr(parent, "thread_uuid", None)
        run_uuid = getattr(parent, "run_uuid", None)
        if not thread_uuid or not run_uuid:
            return None

        loaders = get_loaders(info.context)
        return loaders.run_loader.load((thread_uuid, run_uuid)).then(
            lambda run_dict: RunType(**run_dict) if run_dict else None
        )


class ToolCallListType(ListObjectType):
    tool_call_list = List(ToolCallType)
