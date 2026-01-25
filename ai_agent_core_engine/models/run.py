#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import functools
import traceback
from typing import Any, Dict, List, Optional

import pendulum
from graphene import ResolveInfo
from pynamodb.attributes import NumberAttribute, UnicodeAttribute, UTCDateTimeAttribute
from pynamodb.indexes import AllProjection, LocalSecondaryIndex
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
from ..types.run import RunListType, RunType
from ..utils.normalization import normalize_to_json
from .message import resolve_message_list
from .tool_call import resolve_tool_call_list


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
    partition_key = UnicodeAttribute()
    completion_tokens = NumberAttribute(default=0)
    prompt_tokens = NumberAttribute(default=0)
    total_tokens = NumberAttribute(default=0)
    time_spent = NumberAttribute(null=True)
    updated_by = UnicodeAttribute()
    created_at = UTCDateTimeAttribute()
    updated_at = UTCDateTimeAttribute()
    updated_at_index = UpdatedAtIndex()


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
                    entity_keys["thread_uuid"] = getattr(entity, "thread_uuid", None)
                    entity_keys["run_uuid"] = getattr(entity, "run_uuid", None)

                # Fallback to kwargs (for creates/deletes)
                if not entity_keys.get("thread_uuid"):
                    entity_keys["thread_uuid"] = kwargs.get("thread_uuid")
                if not entity_keys.get("run_uuid"):
                    entity_keys["run_uuid"] = kwargs.get("run_uuid")

                # Only purge if we have the required keys
                if entity_keys.get("thread_uuid") and entity_keys.get("run_uuid"):
                    purge_entity_cascading_cache(
                        args[0].context.get("logger"),
                        entity_type="run",
                        context_keys=None,  # Runs don't use partition_key
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
    cache_name=Config.get_cache_name("models", "run"),
    cache_enabled=Config.is_cache_enabled,
)
def get_run(thread_uuid: str, run_uuid: str) -> RunModel:
    return RunModel.get(thread_uuid, run_uuid)


def get_run_count(thread_uuid: str, run_uuid: str) -> int:
    return RunModel.count(thread_uuid, RunModel.run_uuid == run_uuid)


def get_run_type(info: ResolveInfo, run: RunModel) -> RunType:
    """
    Nested resolver approach: return minimal run data.
    - Do NOT embed 'thread', 'messages', 'tool_calls'.
    These are resolved lazily by RunType.resolve_thread, resolve_messages, resolve_tool_calls.
    """
    try:
        run_dict: Dict = run.__dict__["attribute_values"]
        # Keep foreign keys for nested resolvers
        # No need to fetch thread, messages, or tool_calls here
    except Exception as e:
        log = traceback.format_exc()
        info.context.get("logger").exception(log)
        raise e
    return RunType(**normalize_to_json(run_dict))


def resolve_run(info: ResolveInfo, **kwargs: Dict[str, Any]) -> RunType | None:
    count = get_run_count(kwargs["thread_uuid"], kwargs["run_uuid"])
    if count == 0:
        return None

    return get_run_type(info, get_run(kwargs["thread_uuid"], kwargs["run_uuid"]))


@monitor_decorator
@resolve_list_decorator(
    attributes_to_get=["thread_uuid", "run_uuid", "updated_at"],
    list_type_class=RunListType,
    type_funct=get_run_type,
    scan_index_forward=False,
)
def resolve_run_list(info: ResolveInfo, **kwargs: Dict[str, Any]) -> Any:
    thread_uuid = kwargs.get("thread_uuid")
    run_id = kwargs.get("run_id")
    partition_key = info.context["partition_key"]
    token_type = kwargs.get("token_type")
    great_token = kwargs.get("great_token")
    less_token = kwargs.get("less_token")
    updated_at_gt = kwargs.get("updated_at_gt")
    updated_at_lt = kwargs.get("updated_at_lt")

    args = []
    inquiry_funct = RunModel.scan
    count_funct = RunModel.count
    range_key_condition = None
    if thread_uuid:
        # Build range key condition for updated_at
        if updated_at_gt is not None and updated_at_lt is not None:
            range_key_condition = RunModel.updated_at.between(
                updated_at_gt, updated_at_lt
            )
        elif updated_at_gt is not None:
            range_key_condition = RunModel.updated_at > updated_at_gt
        elif updated_at_lt is not None:
            range_key_condition = RunModel.updated_at < updated_at_lt

        args = [thread_uuid, range_key_condition]
        inquiry_funct = RunModel.updated_at_index.query
        count_funct = RunModel.updated_at_index.count

    the_filters = None  # We can add filters for the query.
    if partition_key:
        the_filters &= RunModel.partition_key == partition_key
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
@purge_cache()
def insert_update_run(info: ResolveInfo, **kwargs: Dict[str, Any]) -> None:
    """
    Insert or update a RunModel record in the database.

    Args:
        info: GraphQL context and metadata
        **kwargs: Request parameters including:
            - thread_uuid: Unique identifier for the thread
            - run_uuid: Unique identifier for the run
            - entity: Existing RunModel instance (for update)
            - updated_by: User/process that updated the record
            - run_id, completion_tokens, prompt_tokens, total_tokens, time_spent: Run metadata

    Returns:
        None
    """
    thread_uuid = kwargs.get("thread_uuid")
    run_uuid = kwargs.get("run_uuid")
    updated_by = kwargs.get("updated_by")
    run = kwargs.get("entity")

    if not all([thread_uuid, run_uuid, updated_by]):
        raise ValueError(
            f"Missing required parameters: thread_uuid={thread_uuid}, "
            f"run_uuid={run_uuid}, updated_by={updated_by}"
        )

    now_utc = pendulum.now("UTC")

    if not run:
        insert_fields = {
            "partition_key": info.context.get("partition_key"),
            "updated_by": updated_by,
            "created_at": now_utc,
            "updated_at": now_utc,
        }

        optional_insert_fields = [
            "run_id",
            "completion_tokens",
            "prompt_tokens",
            "total_tokens",
        ]

        for field in optional_insert_fields:
            if field in kwargs:
                insert_fields[field] = kwargs[field]

        try:
            RunModel(thread_uuid, run_uuid, **insert_fields).save()
        except Exception as e:
            logger = info.context.get("logger")

            if logger:
                logger.error(
                    f"Failed to insert RunModel (thread={thread_uuid}, run={run_uuid}): {str(e)}",
                    exc_info=True,
                )
            raise

        return

    FIELD_MAP = {
        "run_id": RunModel.run_id,
        "completion_tokens": RunModel.completion_tokens,
        "prompt_tokens": RunModel.prompt_tokens,
        "total_tokens": RunModel.total_tokens,
        "time_spent": RunModel.time_spent,
    }

    update_actions: List[Any] = [
        RunModel.updated_by.set(updated_by),
        RunModel.updated_at.set(now_utc),
    ]
    completion_tokens = kwargs.get("completion_tokens")

    if completion_tokens is not None:
        try:
            completion_tokens_float = float(completion_tokens)
            if completion_tokens_float > 0:
                prompt_tokens = getattr(run, "prompt_tokens", 0)
                kwargs["total_tokens"] = completion_tokens_float + prompt_tokens
                time_spent = int(now_utc.diff(run.created_at).in_seconds() * 1000)
                kwargs["time_spent"] = time_spent
        except (ValueError, TypeError) as e:
            logger = info.context.get("logger")

            if logger:
                logger.warning(
                    f"Invalid completion_tokens value '{completion_tokens}': {str(e)}",
                    exc_info=True,
                )

    for field_name, model_field in FIELD_MAP.items():
        if field_name in kwargs:
            update_actions.append(model_field.set(kwargs[field_name]))

    try:
        run.update(actions=update_actions)
    except Exception as e:
        logger = info.context.get("logger")

        if logger:
            logger.error(
                f"Failed to update RunModel (thread={thread_uuid}, run={run_uuid}): {str(e)}",
                exc_info=True,
            )
        raise


@delete_decorator(
    keys={
        "hash_key": "thread_uuid",
        "range_key": "run_uuid",
    },
    model_funct=get_run,
)
@purge_cache()
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


@retry(
    reraise=True,
    wait=wait_exponential(multiplier=1, max=60),
    stop=stop_after_attempt(5),
)
@method_cache(
    ttl=Config.get_cache_ttl(),
    cache_name=Config.get_cache_name("models", "run"),
    cache_enabled=Config.is_cache_enabled,
)
def get_runs_by_thread(thread_uuid: str) -> Any:
    runs = []
    for run in RunModel.query(thread_uuid):
        runs.append(run)
    return runs
