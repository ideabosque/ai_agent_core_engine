#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import logging
import traceback
from typing import Any, Dict

import pendulum
from graphene import ResolveInfo
from pynamodb.attributes import UnicodeAttribute, UTCDateTimeAttribute
from pynamodb.indexes import AllProjection, LocalSecondaryIndex
from tenacity import retry, stop_after_attempt, wait_exponential

from silvaengine_dynamodb_base import (
    BaseModel,
    delete_decorator,
    insert_update_decorator,
    monitor_decorator,
    resolve_list_decorator,
)
from silvaengine_utility import Utility

from ..types.thread import ThreadListType, ThreadType
from .run import resolve_run_list
from .utils import _get_agent


class AgentUuidIndex(LocalSecondaryIndex):
    """
    This class represents a local secondary index
    """

    class Meta:
        billing_mode = "PAY_PER_REQUEST"
        # All attributes are projected
        projection = AllProjection()
        index_name = "agent_uuid-index"

    endpoint_id = UnicodeAttribute(hash_key=True)
    agent_uuid = UnicodeAttribute(range_key=True)


class ThreadModel(BaseModel):
    class Meta(BaseModel.Meta):
        table_name = "aace-threads"

    endpoint_id = UnicodeAttribute(hash_key=True)
    thread_uuid = UnicodeAttribute(range_key=True)
    agent_uuid = UnicodeAttribute()
    user_id = UnicodeAttribute(null=True)
    created_at = UTCDateTimeAttribute()
    agent_uuid_index = AgentUuidIndex()


def create_thread_table(logger: logging.Logger) -> bool:
    """Create the Thread table if it doesn't exist."""
    if not ThreadModel.exists():
        # Create with on-demand billing (PAY_PER_REQUEST)
        ThreadModel.create_table(billing_mode="PAY_PER_REQUEST", wait=True)
        logger.info("The Thread table has been created.")
    return True


@retry(
    reraise=True,
    wait=wait_exponential(multiplier=1, max=60),
    stop=stop_after_attempt(5),
)
def get_thread(endpoint_id: str, thread_uuid: str) -> ThreadModel:
    return ThreadModel.get(endpoint_id, thread_uuid)


def get_thread_count(endpoint_id: str, thread_uuid: str) -> int:
    return ThreadModel.count(endpoint_id, ThreadModel.thread_uuid == thread_uuid)


def get_thread_type(info: ResolveInfo, thread: ThreadModel) -> ThreadType:
    try:
        agent = _get_agent(thread.endpoint_id, thread.agent_uuid)
    except Exception as e:
        log = traceback.format_exc()
        info.context.get("logger").exception(log)
        raise e
    thread = thread.__dict__["attribute_values"]
    thread["agent"] = agent
    thread.pop("endpoint_id")
    thread.pop("agent_uuid")
    return ThreadType(**Utility.json_loads(Utility.json_dumps(thread)))


def resolve_thread(info: ResolveInfo, **kwargs: Dict[str, Any]) -> ThreadType:
    count = get_thread_count(info.context["endpoint_id"], kwargs["thread_uuid"])
    if count == 0:
        return None

    return get_thread_type(
        info, get_thread(info.context["endpoint_id"], kwargs["thread_uuid"])
    )


@monitor_decorator
@resolve_list_decorator(
    attributes_to_get=["endpoint_id", "thread_uuid", "agent_uuid", "user_id"],
    list_type_class=ThreadListType,
    type_funct=get_thread_type,
)
def resolve_thread_list(info: ResolveInfo, **kwargs: Dict[str, Any]) -> Any:
    endpoint_id = info.context["endpoint_id"]
    agent_uuid = kwargs.get("agent_uuid", None)
    user_id = kwargs.get("user_id", None)

    args = []
    inquiry_funct = ThreadModel.scan
    count_funct = ThreadModel.count
    if endpoint_id:
        args = [endpoint_id, None]
        inquiry_funct = ThreadModel.query
        if agent_uuid:
            inquiry_funct = ThreadModel.agent_uuid_index.query
            args[1] = ThreadModel.agent_uuid == agent_uuid
            count_funct = ThreadModel.agent_uuid_index.count

    the_filters = None
    if user_id is not None:
        the_filters &= ThreadModel.user_id.exists()
        the_filters &= ThreadModel.user_id == user_id
    if the_filters is not None:
        args.append(the_filters)

    return inquiry_funct, count_funct, args


@insert_update_decorator(
    keys={
        "hash_key": "endpoint_id",
        "range_key": "thread_uuid",
    },
    model_funct=get_thread,
    count_funct=get_thread_count,
    type_funct=get_thread_type,
    # data_attributes_except_for_data_diff=["created_at", "updated_at"],
    # activity_history_funct=None,
)
def insert_thread(info: ResolveInfo, **kwargs: Dict[str, Any]) -> None:
    endpoint_id = kwargs.get("endpoint_id")
    thread_uuid = kwargs.get("thread_uuid")
    if kwargs.get("entity") is None:
        cols = {
            "agent_uuid": kwargs["agent_uuid"],
            "created_at": pendulum.now("UTC"),
        }
        for key in ["user_id"]:
            if key in kwargs:
                cols[key] = kwargs[key]

        ThreadModel(
            endpoint_id,
            thread_uuid,
            **cols,
        ).save()
        return
    return


@delete_decorator(
    keys={
        "hash_key": "endpoint_id",
        "range_key": "thread_uuid",
    },
    model_funct=get_thread,
)
def delete_thread(info: ResolveInfo, **kwargs: Dict[str, Any]) -> bool:
    run_list = resolve_run_list(
        info,
        **{
            "endpoint_id": kwargs["entity"].endpoint_id,
            "thread_uuid": kwargs["entity"].thread_uuid,
        },
    )
    if run_list.total > 0:
        return False

    kwargs["entity"].delete()
    return True
