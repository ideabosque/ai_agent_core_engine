#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import logging
import traceback
from typing import Any, Dict

import pendulum
from graphene import ResolveInfo
from pynamodb.attributes import MapAttribute, UnicodeAttribute, UTCDateTimeAttribute
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

from ..types.tool_call import ToolCallListType, ToolCallType
from .utils import _get_run


class RunIdIndex(LocalSecondaryIndex):
    """
    This class represents a local secondary index
    """

    class Meta:
        billing_mode = "PAY_PER_REQUEST"
        # All attributes are projected
        projection = AllProjection()
        index_name = "run_id-index"

    thread_uuid = UnicodeAttribute(hash_key=True)
    run_id = UnicodeAttribute(range_key=True)


class ToolCallModel(BaseModel):
    class Meta(BaseModel.Meta):
        table_name = "aace-tool_calls"

    thread_uuid = UnicodeAttribute(hash_key=True)
    tool_call_id = UnicodeAttribute(range_key=True)
    run_id = UnicodeAttribute()
    tool_type = UnicodeAttribute()
    name = UnicodeAttribute()
    arguments = MapAttribute()
    content = UnicodeAttribute(null=True)
    created_at = UTCDateTimeAttribute()
    run_id_index = RunIdIndex()


def create_tool_call_table(logger: logging.Logger) -> bool:
    """Create the ToolCall table if it doesn't exist."""
    if not ToolCallModel.exists():
        # Create with on-demand billing (PAY_PER_REQUEST)
        ToolCallModel.create_table(billing_mode="PAY_PER_REQUEST", wait=True)
        logger.info("The ToolCall table has been created.")
    return True


@retry(
    reraise=True,
    wait=wait_exponential(multiplier=1, max=60),
    stop=stop_after_attempt(5),
)
def get_tool_call(thread_uuid: str, tool_call_id: str) -> ToolCallModel:
    return ToolCallModel.get(thread_uuid, tool_call_id)


def get_tool_call_count(thread_uuid: str, tool_call_id: str) -> int:
    return ToolCallModel.count(thread_uuid, ToolCallModel.tool_call_id == tool_call_id)


def get_tool_call_type(info: ResolveInfo, tool_call: ToolCallModel) -> ToolCallType:
    try:
        run = _get_run(tool_call.thread_uuid, tool_call.run_id)
    except Exception as e:
        log = traceback.format_exc()
        info.context.get("logger").exception(log)
        raise e
    tool_call = tool_call.__dict__["attribute_values"]
    tool_call["run"] = run
    tool_call.pop("thread_uuid")
    tool_call.pop("run_id")
    return ToolCallType(**Utility.json_loads(Utility.json_dumps(tool_call)))


def resolve_tool_call(info: ResolveInfo, **kwargs: Dict[str, Any]) -> ToolCallType:
    return get_tool_call_type(
        info, get_tool_call(kwargs["thread_uuid"], kwargs["tool_call_id"])
    )


@monitor_decorator
@resolve_list_decorator(
    attributes_to_get=["thread_uuid", "tool_call_id", "run_id"],
    list_type_class=ToolCallListType,
    type_funct=get_tool_call_type,
)
def resolve_tool_call_list(info: ResolveInfo, **kwargs: Dict[str, Any]) -> Any:
    thread_uuid = kwargs.get("thread_uuid")
    run_id = kwargs.get("run_id")
    tool_type = kwargs.get("tool_type")
    name = kwargs.get("name")

    args = []
    inquiry_funct = ToolCallModel.scan
    count_funct = ToolCallModel.count
    if thread_uuid:
        args = [thread_uuid, None]
        inquiry_funct = ToolCallModel.query
        if run_id:
            args[1] = ToolCallModel.run_id == run_id
            count_funct = ToolCallModel.run_id_index.count

    the_filters = None
    if tool_type:
        the_filters &= ToolCallModel.tool_type == tool_type
    if name:
        the_filters &= ToolCallModel.name == name
    if the_filters is not None:
        args.append(the_filters)

    return inquiry_funct, count_funct, args


@insert_update_decorator(
    keys={"hash_key": "thread_uuid", "range_key": "tool_call_id"},
    range_key_required=True,
    model_funct=get_tool_call,
    count_funct=get_tool_call_count,
    type_funct=get_tool_call_type,
    # data_attributes_except_for_data_diff=["created_at", "updated_at"],
    # activity_history_funct=None,
)
def insert_tool_call(info: ResolveInfo, **kwargs: Dict[str, Any]) -> None:
    thread_uuid = kwargs.get("thread_uuid")
    tool_call_id = kwargs.get("tool_call_id")
    if kwargs.get("entity") is None:
        cols = {
            "run_id": kwargs["run_id"],
            "tool_type": kwargs["tool_type"],
            "name": kwargs["name"],
            "arguments": kwargs["arguments"],
            "created_at": pendulum.now("UTC"),
        }

        for key in ["content"]:
            if key in kwargs:
                cols[key] = kwargs[key]

        ToolCallModel(
            thread_uuid,
            tool_call_id,
            **cols,
        ).save()
        return
    return


@delete_decorator(
    keys={"hash_key": "thread_uuid", "range_key": "tool_call_id"},
    model_funct=get_tool_call,
)
def delete_tool_call(info: ResolveInfo, **kwargs: Dict[str, Any]) -> bool:
    kwargs.get("entity").delete()
    return True
