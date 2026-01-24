#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import functools
import traceback
from typing import Any, Dict

import pendulum
from graphene import ResolveInfo
from pynamodb.attributes import (
    ListAttribute,
    MapAttribute,
    NumberAttribute,
    UnicodeAttribute,
    UTCDateTimeAttribute,
)
from pynamodb.indexes import AllProjection, GlobalSecondaryIndex
from silvaengine_dynamodb_base import (
    BaseModel,
    delete_decorator,
    insert_update_decorator,
    monitor_decorator,
    resolve_list_decorator,
)
from silvaengine_utility import method_cache
from tenacity import retry, stop_after_attempt, wait_exponential

from ..handlers.config import Config
from ..types.async_task import AsyncTaskListType, AsyncTaskType
from ..utils.normalization import normalize_to_json


class PartitionKeyUpdatedAtIndex(GlobalSecondaryIndex):
    """
    This class represents a local secondary index
    """

    class Meta:
        billing_mode = "PAY_PER_REQUEST"
        # All attributes are projected
        projection = AllProjection()
        index_name = "partition_key-updated_at-index"

    partition_key = UnicodeAttribute(hash_key=True)
    updated_at = UnicodeAttribute(range_key=True)


class AsyncTaskModel(BaseModel):
    class Meta(BaseModel.Meta):
        table_name = "aace-async_tasks"

    function_name = UnicodeAttribute(hash_key=True)
    async_task_uuid = UnicodeAttribute(range_key=True)
    partition_key = UnicodeAttribute()
    arguments = MapAttribute(null=True)
    result = UnicodeAttribute(null=True)
    output_files = ListAttribute(of=MapAttribute)
    status = UnicodeAttribute(default="initial")
    notes = UnicodeAttribute(null=True)
    time_spent = NumberAttribute(null=True)
    updated_by = UnicodeAttribute()
    created_at = UTCDateTimeAttribute()
    updated_at = UTCDateTimeAttribute()
    partition_key_updated_at_index = PartitionKeyUpdatedAtIndex()


def purge_cache():
    def actual_decorator(original_function):
        @functools.wraps(original_function)
        def wrapper_function(*args, **kwargs):
            try:
                # Execute original function first
                result = original_function(*args, **kwargs)

                # Then purge cache after successful operation
                from ..models.cache import purge_entity_cascading_cache

                # Get entity keys from kwargs or entity parameter
                entity_keys = {}

                # Try to get from entity parameter first (for updates)
                entity = kwargs.get("entity")
                if entity:
                    entity_keys["function_name"] = getattr(
                        entity, "function_name", None
                    )
                    entity_keys["async_task_uuid"] = getattr(
                        entity, "async_task_uuid", None
                    )

                # Fallback to kwargs (for creates/deletes)
                if not entity_keys.get("function_name"):
                    entity_keys["function_name"] = kwargs.get("function_name")
                if not entity_keys.get("async_task_uuid"):
                    entity_keys["async_task_uuid"] = kwargs.get("async_task_uuid")

                # Only purge if we have the required keys
                if entity_keys.get("function_name") and entity_keys.get(
                    "async_task_uuid"
                ):
                    purge_entity_cascading_cache(
                        args[0].context.get("logger"),
                        entity_type="async_task",
                        context_keys=None,  # Async tasks don't use partition_key
                        entity_keys=entity_keys,
                        cascade_depth=3,
                    )

                return result
            except Exception as e:
                log = traceback.format_exc()
                args[0].context.get("logger").error(log)
                raise e

        return wrapper_function

    return actual_decorator


@retry(
    reraise=True,
    wait=wait_exponential(multiplier=1, max=60),
    stop=stop_after_attempt(5),
)
@method_cache(
    ttl=Config.get_cache_ttl(),
    cache_name=Config.get_cache_name("models", "async_task"),
    cache_enabled=Config.is_cache_enabled,
)
def get_async_task(function_name: str, async_task_uuid: str) -> AsyncTaskModel:

    async_task = AsyncTaskModel.get(function_name, async_task_uuid)
    return async_task


def get_async_task_count(partition_key: str, async_task_uuid: str) -> int:
    return AsyncTaskModel.count(
        partition_key, AsyncTaskModel.async_task_uuid == async_task_uuid
    )


def get_async_task_type(info: ResolveInfo, async_task: AsyncTaskModel) -> AsyncTaskType:
    async_task = async_task.__dict__["attribute_values"]
    return AsyncTaskType(**normalize_to_json(async_task))


def resolve_async_task(
    info: ResolveInfo, **kwargs: Dict[str, Any]
) -> AsyncTaskType | None:
    count = get_async_task_count(kwargs["function_name"], kwargs["async_task_uuid"])
    if count == 0:
        return None

    return get_async_task_type(
        info,
        get_async_task(kwargs["function_name"], kwargs["async_task_uuid"]),
    )


@monitor_decorator
@resolve_list_decorator(
    attributes_to_get=[
        "partition_key",
        "function_name",
        "async_task_uuid",
        "updated_at",
    ],
    list_type_class=AsyncTaskListType,
    type_funct=get_async_task_type,
    scan_index_forward=False,
)
def resolve_async_task_list(info: ResolveInfo, **kwargs: Dict[str, Any]) -> Any:
    function_name = kwargs.get("function_name")
    partition_key = info.context["partition_key"]
    statuses = kwargs.get("statuses")

    args = [partition_key, None]
    inquiry_funct = AsyncTaskModel.partition_key_updated_at_index.query
    count_funct = AsyncTaskModel.partition_key_updated_at_index.count
    if function_name:
        args = [function_name, None]
        inquiry_funct = AsyncTaskModel.query

    the_filters = None
    if partition_key and function_name:
        the_filters &= AsyncTaskModel.partition_key == partition_key
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
@purge_cache()
def insert_update_async_task(info: ResolveInfo, **kwargs: Dict[str, Any]) -> Any:

    function_name = kwargs.get("function_name")
    async_task_uuid = kwargs.get("async_task_uuid")

    if hasattr(get_async_task, "cache_delete"):
        get_async_task.cache_delete(function_name, async_task_uuid)

    if kwargs.get("entity") is None:
        cols = {
            "partition_key": info.context["partition_key"],
            "output_files": [],
            "updated_by": kwargs["updated_by"],
            "created_at": pendulum.now("UTC"),
            "updated_at": pendulum.now("UTC"),
        }
        for key in [
            "arguments",
            "result",
            "output_files",
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
    if "status" in kwargs and kwargs["status"] == "completed":
        kwargs["time_spent"] = int(
            pendulum.now("UTC").diff(async_task.created_at).in_seconds() * 1000
        )
    actions = [
        AsyncTaskModel.updated_by.set(kwargs["updated_by"]),
        AsyncTaskModel.updated_at.set(pendulum.now("UTC")),
    ]
    # Map of potential keys in kwargs to AsyncTaskModel attributes
    field_map = {
        "partition_key": AsyncTaskModel.partition_key,
        "arguments": AsyncTaskModel.arguments,
        "result": AsyncTaskModel.result,
        "output_files": AsyncTaskModel.output_files,
        "status": AsyncTaskModel.status,
        "notes": AsyncTaskModel.notes,
        "time_spent": AsyncTaskModel.time_spent,
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
@purge_cache()
def delete_async_task(info: ResolveInfo, **kwargs: Dict[str, Any]) -> bool:

    kwargs.get("entity").delete()
    return True
