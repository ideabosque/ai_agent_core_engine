#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from graphene import DateTime, Field, List, ObjectType, String
from silvaengine_dynamodb_base import ListObjectType

from .thread import ThreadType


def _get_run_type():
    from .run import RunType

    return RunType


class MessageType(ObjectType):
    thread_uuid = String()
    message_uuid = String()
    run_uuid = String()
    message_id = String()
    role = String()
    message = String()
    updated_by = String()
    created_at = DateTime()
    updated_at = DateTime()

    # Nested resolvers with DataLoader batch fetching for efficient database access
    run = Field(_get_run_type)
    thread = Field(lambda: ThreadType)

    # ------- Nested resolvers -------

    def resolve_run(parent, info):
        """Resolve nested Run for this message using DataLoader."""
        from ..models.batch_loaders import get_loaders
        from .run import RunType

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

    def resolve_thread(parent, info):
        """Resolve nested Thread for this message using DataLoader."""
        from ..models.batch_loaders import get_loaders

        # Case 2: already embedded
        existing = getattr(parent, "thread", None)
        if isinstance(existing, dict):
            return ThreadType(**existing)

        # Case 1: need to fetch using DataLoader
        endpoint_id = info.context.get("endpoint_id")
        thread_uuid = getattr(parent, "thread_uuid", None)
        if not endpoint_id or not thread_uuid:
            return None

        loaders = get_loaders(info.context)
        return loaders.thread_loader.load((endpoint_id, thread_uuid)).then(
            lambda thread_dict: ThreadType(**thread_dict) if thread_dict else None
        )


class MessageListType(ListObjectType):
    message_list = List(MessageType)
