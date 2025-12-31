#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from graphene import DateTime, Field, Int, List, ObjectType, String

from silvaengine_dynamodb_base import ListObjectType

from .thread import ThreadType


class RunType(ObjectType):
    thread_uuid = String()
    partition_key = String()
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

    # ------- Nested resolvers -------

    def resolve_thread(parent, info):
        """Resolve nested Thread for this run using DataLoader."""
        from ..models.batch_loaders import get_loaders

        # Case 2: already embedded
        existing = getattr(parent, "thread", None)
        if isinstance(existing, dict):
            return ThreadType(**existing)
        if isinstance(existing, ThreadType):
            return existing

        # Case 1: need to fetch using DataLoader
        partition_key = getattr(parent, "partition_key", None) or info.context.get(
            "partition_key"
        )
        thread_uuid = getattr(parent, "thread_uuid", None)
        if not partition_key or not thread_uuid:
            return None

        loaders = get_loaders(info.context)
        return loaders.thread_loader.load((partition_key, thread_uuid)).then(
            lambda thread_dict: ThreadType(**thread_dict) if thread_dict else None
        ).get()


class RunListType(ListObjectType):
    run_list = List(RunType)
