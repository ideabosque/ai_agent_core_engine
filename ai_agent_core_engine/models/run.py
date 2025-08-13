#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import logging
import traceback
from typing import Any, Dict

import pendulum
from graphene import ResolveInfo
from pynamodb.indexes import AllProjection, LocalSecondaryIndex
from pynamodb.attributes import NumberAttribute, UnicodeAttribute, UTCDateTimeAttribute
from tenacity import retry, stop_after_attempt, wait_exponential

from silvaengine_dynamodb_base import (
    BaseModel,
    delete_decorator,
    insert_update_decorator,
    monitor_decorator,
    resolve_list_decorator,
)
from silvaengine_utility import Utility

from ..types.run import RunListType, RunType
from .message import resolve_message_list
from .tool_call import resolve_tool_call_list
from .utils import _get_thread

class UpdatedAtIndex(LocalSecondaryIndex):
    """
    This class represents a local secondary index
    """

    class Meta:
        billing_mode = "PAY_PER_REQUEST"
        # All attributes are projected
        projection = AllProjection()
        index_name = "updated_at-index"

    thread_uuid = UnicodeAttribute(hash_key=True)
    updated_at = UnicodeAttribute(range_key=True)

class RunModel(BaseModel):
    class Meta(BaseModel.Meta):
        table_name = "aace-runs"

    thread_uuid = UnicodeAttribute(hash_key=True)
    run_uuid = UnicodeAttribute(range_key=True)
    run_id = UnicodeAttribute(null=True)
    endpoint_id = UnicodeAttribute()
    completion_tokens = NumberAttribute(default=0)
    prompt_tokens = NumberAttribute(default=0)
    total_tokens = NumberAttribute(default=0)
    time_spent = NumberAttribute(null=True)
    updated_by = UnicodeAttribute()
    created_at = UTCDateTimeAttribute()
    updated_at = UTCDateTimeAttribute()
    updated_at_index = UpdatedAtIndex()


def create_run_table(logger: logging.Logger) -> bool:
    """Create the Run table if it doesn't exist."""
    if not RunModel.exists():
        # Create with on-demand billing (PAY_PER_REQUEST)
        RunModel.create_table(billing_mode="PAY_PER_REQUEST", wait=True)
        logger.info("The Run table has been created.")
    return True


@retry(
    reraise=True,
    wait=wait_exponential(multiplier=1, max=60),
    stop=stop_after_attempt(5),
)
def get_run(thread_uuid: str, run_uuid: str) -> RunModel:
    return RunModel.get(thread_uuid, run_uuid)


def get_run_count(thread_uuid: str, run_uuid: str) -> int:
    return RunModel.count(thread_uuid, RunModel.run_uuid == run_uuid)


def get_run_type(info: ResolveInfo, run: RunModel) -> RunType:
    try:
        thread = _get_thread(run.endpoint_id, run.thread_uuid)
    except Exception as e:
        log = traceback.format_exc()
        info.context.get("logger").exception(log)
        raise e
    run = run.__dict__["attribute_values"]
    run["thread"] = thread
    run.pop("thread_uuid")
    run.pop("endpoint_id")
    return RunType(**Utility.json_loads(Utility.json_dumps(run)))


def resolve_run(info: ResolveInfo, **kwargs: Dict[str, Any]) -> RunType:
    count = get_run_count(kwargs["thread_uuid"], kwargs["run_uuid"])
    if count == 0:
        return None

    return get_run_type(info, get_run(kwargs["thread_uuid"], kwargs["run_uuid"]))


@monitor_decorator
@resolve_list_decorator(
    attributes_to_get=["thread_uuid", "run_uuid", "updated_at"],
    list_type_class=RunListType,
    type_funct=get_run_type,
)
def resolve_run_list(info: ResolveInfo, **kwargs: Dict[str, Any]) -> Any:
    thread_uuid = kwargs.get("thread_uuid")
    run_id = kwargs.get("run_id")
    endpoint_id = info.context["endpoint_id"]
    token_type = kwargs.get("token_type")
    great_token = kwargs.get("great_token")
    less_token = kwargs.get("less_token")

    args = []
    inquiry_funct = RunModel.scan
    count_funct = RunModel.count
    if thread_uuid:
        args = [thread_uuid, None]
        inquiry_funct = RunModel.updated_at_index.query
        count_funct = RunModel.updated_at_index.count

    the_filters = None  # We can add filters for the query.
    if endpoint_id:
        the_filters &= RunModel.endpoint_id == endpoint_id
    if run_id:
        the_filters &= RunModel.run_id.exists()
        the_filters &= RunModel.run_id == run_id
    if token_type == "completion":
        if great_token:
            the_filters &= RunModel.completion_tokens < great_token
        if less_token:
            the_filters &= RunModel.completion_tokens >= less_token
    if token_type == "prompt":
        if great_token:
            the_filters &= RunModel.prompt_tokens < great_token
        if less_token:
            the_filters &= RunModel.prompt_tokens >= less_token
    if token_type == "total":
        if great_token:
            the_filters &= RunModel.total_tokens < great_token
        if less_token:
            the_filters &= RunModel.total_tokens >= less_token
    if the_filters is not None:
        args.append(the_filters)

    return inquiry_funct, count_funct, args


@insert_update_decorator(
    keys={
        "hash_key": "thread_uuid",
        "range_key": "run_uuid",
    },
    model_funct=get_run,
    count_funct=get_run_count,
    type_funct=get_run_type,
    # data_attributes_except_for_data_diff=["created_at", "updated_at"],
    # activity_history_funct=None,
)
def insert_update_run(info: ResolveInfo, **kwargs: Dict[str, Any]) -> None:
    thread_uuid = kwargs.get("thread_uuid")
    run_uuid = kwargs.get("run_uuid")
    if kwargs.get("entity") is None:
        cols = {
            "endpoint_id": info.context["endpoint_id"],
            "updated_by": kwargs["updated_by"],
            "created_at": pendulum.now("UTC"),
            "updated_at": pendulum.now("UTC"),
        }
        for key in ["run_id", "completion_tokens", "prompt_tokens", "total_tokens"]:
            if key in kwargs:
                cols[key] = kwargs[key]

        RunModel(
            thread_uuid,
            run_uuid,
            **cols,
        ).save()
        return

    run = kwargs.get("entity")
    if "completion_tokens" in kwargs and kwargs["completion_tokens"] > 0:
        kwargs["total_tokens"] = kwargs["completion_tokens"] + run.prompt_tokens
        kwargs["time_spent"] = pendulum.now("UTC").diff(run.created_at).in_seconds()
    actions = [
        RunModel.updated_by.set(kwargs["updated_by"]),
        RunModel.updated_at.set(pendulum.now("UTC")),
    ]
    # Map of potential keys in kwargs to RunModel attributes
    field_map = {
        "run_id": RunModel.run_id,
        "completion_tokens": RunModel.completion_tokens,
        "prompt_tokens": RunModel.prompt_tokens,
        "total_tokens": RunModel.total_tokens,
        "time_spent": RunModel.time_spent,
    }

    # Check if a key exists in kwargs before adding it to the update actions
    for key, field in field_map.items():
        if key in kwargs:  # Check if the key exists in kwargs
            actions.append(field.set(kwargs[key]))

    # Update the run
    run.update(actions=actions)
    return


@delete_decorator(
    keys={
        "hash_key": "thread_uuid",
        "range_key": "run_uuid",
    },
    model_funct=get_run,
)
def delete_run(info: ResolveInfo, **kwargs: Dict[str, Any]) -> bool:
    message_list = resolve_message_list(
        info,
        **{
            "thread_uuid": kwargs["entity"].thread_uuid,
            "run_uuid": kwargs["entity"].run_uuid,
        },
    )
    if message_list.total > 0:
        return False

    tool_call_list = resolve_tool_call_list(
        info,
        **{
            "thread_uuid": kwargs["entity"].thread_uuid,
            "run_uuid": kwargs["entity"].run_uuid,
        },
    )
    if tool_call_list.total > 0:
        return False

    kwargs["entity"].delete()
    return True
