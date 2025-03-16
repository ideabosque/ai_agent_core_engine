#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import logging
from typing import Any, Dict

import pendulum
from graphene import ResolveInfo
from pynamodb.attributes import MapAttribute, UnicodeAttribute, UTCDateTimeAttribute
from tenacity import retry, stop_after_attempt, wait_exponential

from silvaengine_dynamodb_base import (
    BaseModel,
    delete_decorator,
    insert_update_decorator,
    monitor_decorator,
    resolve_list_decorator,
)
from silvaengine_utility import Utility

from ..types.async_task import AsyncTaskListType, AsyncTaskType


class AsyncTaskModel(BaseModel):
    class Meta(BaseModel.Meta):
        table_name = "aace-async_tasks"

    function_name = UnicodeAttribute(hash_key=True)
    async_task_uuid = UnicodeAttribute(range_key=True)
    endpoint_id = UnicodeAttribute()
    arguments = MapAttribute(null=True)
    result = UnicodeAttribute(null=True)
    status = UnicodeAttribute(default="initial")
    notes = UnicodeAttribute(null=True)
    updated_by = UnicodeAttribute()
    created_at = UTCDateTimeAttribute()
    updated_at = UTCDateTimeAttribute()


def create_async_task_table(logger: logging.Logger) -> bool:
    """Create the AsyncTask table if it doesn't exist."""
    if not AsyncTaskModel.exists():
        # Create with on-demand billing (PAY_PER_REQUEST)
        AsyncTaskModel.create_table(billing_mode="PAY_PER_REQUEST", wait=True)
        logger.info("The AsyncTask table has been created.")
    return True


@retry(
    reraise=True,
    wait=wait_exponential(multiplier=1, max=60),
    stop=stop_after_attempt(5),
)
def get_async_task(function_name: str, async_task_uuid: str) -> AsyncTaskModel:
    async_task = AsyncTaskModel.get(function_name, async_task_uuid)
    return async_task


def get_async_task_count(endpoint_id: str, async_task_uuid: str) -> int:
    return AsyncTaskModel.count(
        endpoint_id, AsyncTaskModel.async_task_uuid == async_task_uuid
    )


def get_async_task_type(info: ResolveInfo, async_task: AsyncTaskModel) -> AsyncTaskType:
    async_task = async_task.__dict__["attribute_values"]
    return AsyncTaskType(**Utility.json_loads(Utility.json_dumps(async_task)))


def resolve_async_task(info: ResolveInfo, **kwargs: Dict[str, Any]) -> AsyncTaskType:
    return get_async_task_type(
        info,
        get_async_task(kwargs["function_name"], kwargs["async_task_uuid"]),
    )


@monitor_decorator
@resolve_list_decorator(
    attributes_to_get=["endpoint_id", "async_task_uuid"],
    list_type_class=AsyncTaskListType,
    type_funct=get_async_task_type,
)
def resolve_async_task_list(info: ResolveInfo, **kwargs: Dict[str, Any]) -> Any:
    function_name = kwargs.get("function_name")
    endpoint_id = info.context["endpoint_id"]
    statuses = kwargs.get("statuses")

    args = []
    inquiry_funct = AsyncTaskModel.scan
    count_funct = AsyncTaskModel.count
    if function_name:
        args = [function_name, None]
        inquiry_funct = AsyncTaskModel.query

    the_filters = None
    if endpoint_id:
        the_filters &= AsyncTaskModel.endpoint_id == endpoint_id
    if statuses:
        the_filters &= AsyncTaskModel.status.is_in(*statuses)
    if the_filters is not None:
        args.append(the_filters)

    return inquiry_funct, count_funct, args


@insert_update_decorator(
    keys={
        "hash_key": "function_name",
        "range_key": "async_task_uuid",
    },
    model_funct=get_async_task,
    count_funct=get_async_task_count,
    type_funct=get_async_task_type,
    # data_attributes_except_for_data_diff=["created_at", "updated_at"],
    # activity_history_funct=None,
)
def insert_update_async_task(info: ResolveInfo, **kwargs: Dict[str, Any]) -> None:
    function_name = kwargs.get("function_name")
    async_task_uuid = kwargs.get("async_task_uuid")
    if kwargs.get("entity") is None:
        cols = {
            "endpoint_id": info.context["endpoint_id"],
            "updated_by": kwargs["updated_by"],
            "created_at": pendulum.now("UTC"),
            "updated_at": pendulum.now("UTC"),
        }
        for key in [
            "arguments",
            "result",
            "status",
            "notes",
        ]:
            if key in kwargs:
                cols[key] = kwargs[key]

        AsyncTaskModel(
            function_name,
            async_task_uuid,
            **cols,
        ).save()
        return

    async_task = kwargs.get("entity")
    actions = [
        AsyncTaskModel.updated_by.set(kwargs["updated_by"]),
        AsyncTaskModel.updated_at.set(pendulum.now("UTC")),
    ]
    # Map of potential keys in kwargs to AsyncTaskModel attributes
    field_map = {
        "endpoint_id": AsyncTaskModel.endpoint_id,
        "arguments": AsyncTaskModel.arguments,
        "result": AsyncTaskModel.result,
        "status": AsyncTaskModel.status,
        "notes": AsyncTaskModel.notes,
    }

    # Check if a key exists in kwargs before adding it to the update actions
    for key, field in field_map.items():
        if key in kwargs:  # Check if the key exists in kwargs
            actions.append(field.set(None if kwargs[key] == "null" else kwargs[key]))

    # Update the async_task
    async_task.update(actions=actions)
    return


@delete_decorator(
    keys={
        "hash_key": "function_name",
        "range_key": "async_task_uuid",
    },
    model_funct=get_async_task,
)
def delete_async_task(info: ResolveInfo, **kwargs: Dict[str, Any]) -> bool:
    kwargs.get("entity").delete()
    return True
