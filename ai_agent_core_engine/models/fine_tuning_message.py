# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import logging
import time
from typing import Any, Dict

import pendulum
from graphene import ResolveInfo
from pynamodb.attributes import (
    BooleanAttribute,
    ListAttribute,
    MapAttribute,
    NumberAttribute,
    UnicodeAttribute,
    UTCDateTimeAttribute,
)
from pynamodb.indexes import AllProjection, LocalSecondaryIndex
from tenacity import retry, stop_after_attempt, wait_exponential

from silvaengine_dynamodb_base import (
    BaseModel,
    delete_decorator,
    insert_update_decorator,
    monitor_decorator,
    resolve_list_decorator,
)
from silvaengine_utility import Utility, method_cache

from ..handlers.config import Config
from ..types.fine_tuning_message import FineTuningMessageListType, FineTuningMessageType


class ThreadIdIndex(LocalSecondaryIndex):
    """
    This class represents a local secondary index
    """

    class Meta:
        billing_mode = "PAY_PER_REQUEST"
        # All attributes are projected
        projection = AllProjection()
        index_name = "thread_uuid-index"

    agent_uuid = UnicodeAttribute(hash_key=True)
    thread_uuid = UnicodeAttribute(range_key=True)


class TimestampIndex(LocalSecondaryIndex):
    """
    This class represents a local secondary index
    """

    class Meta:
        billing_mode = "PAY_PER_REQUEST"
        # All attributes are projected
        projection = AllProjection()
        index_name = "timestamp-index"

    agent_uuid = UnicodeAttribute(hash_key=True)
    timestamp = NumberAttribute(range_key=True)


class FineTuningMessageModel(BaseModel):
    class Meta(BaseModel.Meta):
        table_name = "aace-fine_tuning_messages"

    agent_uuid = UnicodeAttribute(hash_key=True)
    message_uuid = UnicodeAttribute(range_key=True)
    thread_uuid = UnicodeAttribute()
    timestamp = NumberAttribute()
    endpoint_id = UnicodeAttribute()
    role = UnicodeAttribute()
    tool_calls = ListAttribute(of=MapAttribute, null=True)
    tool_call_uuid = UnicodeAttribute(null=True)
    content = UnicodeAttribute(null=True)
    weight = NumberAttribute(default=0)
    trained = BooleanAttribute(default=False)
    updated_at = UTCDateTimeAttribute()
    updated_by = UnicodeAttribute()
    thread_uuid_index = ThreadIdIndex()
    timestamp_index = TimestampIndex()


def create_fine_tuning_message_table(logger: logging.Logger) -> bool:
    """Create the FineTuningMessage table if it doesn't exist."""
    if not FineTuningMessageModel.exists():
        # Create with on-demand billing (PAY_PER_REQUEST)
        FineTuningMessageModel.create_table(billing_mode="PAY_PER_REQUEST", wait=True)
        logger.info("The FineTuningMessage has been created.")
    return True


@retry(
    reraise=True,
    wait=wait_exponential(multiplier=1, max=60),
    stop=stop_after_attempt(5),
)
@method_cache(ttl=Config.get_cache_ttl(), cache_name=Config.get_cache_name('models', 'fine_tuning_message'))
def get_fine_tuning_message(
    agent_uuid: str, message_uuid: str
) -> FineTuningMessageModel:
    return FineTuningMessageModel.get(agent_uuid, message_uuid)


def get_fine_tuning_message_count(agent_uuid: str, message_uuid: str) -> int:
    return FineTuningMessageModel.count(
        agent_uuid, FineTuningMessageModel.message_uuid == message_uuid
    )


def get_fine_tuning_message_type(
    info: ResolveInfo, fine_tuning_message: FineTuningMessageModel
) -> FineTuningMessageType:
    fine_tuning_message = fine_tuning_message.__dict__["attribute_values"]
    return FineTuningMessageType(
        **Utility.json_normalize(fine_tuning_message)
    )


def resolve_fine_tuning_message(
    info: ResolveInfo, **kwargs: Dict[str, Any]
) -> FineTuningMessageType:
    count = get_fine_tuning_message_count(kwargs["agent_uuid"], kwargs["message_uuid"])
    if count == 0:
        return None

    return get_fine_tuning_message_type(
        info,
        get_fine_tuning_message(kwargs["agent_uuid"], kwargs["message_uuid"]),
    )


@monitor_decorator
@resolve_list_decorator(
    attributes_to_get=["agent_uuid", "message_uuid"],
    list_type_class=FineTuningMessageListType,
    type_funct=get_fine_tuning_message_type,
)
def resolve_fine_tuning_message_list(
    info: ResolveInfo, **kwargs: Dict[str, Any]
) -> Any:
    agent_uuid = kwargs.get("agent_uuid")
    thread_uuid = kwargs.get("thread_uuid")
    roles = kwargs.get("roles")
    trained = kwargs.get("trained")
    from_date = kwargs.get("from_date")
    to_date = kwargs.get("to_date")
    if from_date is not None:
        # Convert the date to UTC
        utc_from_date = pendulum.instance(from_date).in_timezone("UTC")

        # Convert the UTC date to a Unix timestamp
        from_timestamp = int(time.mktime(utc_from_date.timetuple()))

    if to_date is None:
        # Get current UTC time using pendulum
        current_utc = pendulum.now("UTC")

        # Convert the current UTC time to a Unix timestamp
        to_timestamp = int(time.mktime(current_utc.timetuple()))
    else:
        # Convert the date to UTC
        utc_to_date = pendulum.instance(to_date).in_timezone("UTC")

        # Convert the UTC date to a Unix timestamp
        to_timestamp = int(time.mktime(utc_to_date.timetuple()))

    args = []
    inquiry_funct = FineTuningMessageModel.scan
    count_funct = FineTuningMessageModel.count
    if agent_uuid:
        args = [agent_uuid, None]
        inquiry_funct = FineTuningMessageModel.query
        if thread_uuid:
            inquiry_funct = FineTuningMessageModel.thread_uuid_index.query
            args[1] = FineTuningMessageModel.thread_uuid == thread_uuid
            count_funct = FineTuningMessageModel.thread_uuid_index.count
        if from_date and to_date:
            inquiry_funct = FineTuningMessageModel.timestamp_index.query
            args[1] = FineTuningMessageModel.timestamp.between(
                from_timestamp, to_timestamp
            )
            count_funct = FineTuningMessageModel.timestamp_index.count

    the_filters = None
    if roles:
        the_filters &= FineTuningMessageModel.role.is_in(*roles)
    if trained is not None:
        the_filters &= FineTuningMessageModel.trained == trained
    if the_filters is not None:
        args.append(the_filters)

    return inquiry_funct, count_funct, args


@insert_update_decorator(
    keys={
        "hash_key": "agent_uuid",
        "range_key": "message_uuid",
    },
    range_key_required=True,
    model_funct=get_fine_tuning_message,
    count_funct=get_fine_tuning_message_count,
    type_funct=get_fine_tuning_message_type,
)
def insert_update_fine_tuning_message(
    info: ResolveInfo, **kwargs: Dict[str, Any]
) -> None:
    # Use cascading cache purging for fine tuning messages
    from ..models.cache import purge_fine_tuning_message_cascading_cache

    cache_result = purge_fine_tuning_message_cascading_cache(
        agent_uuid=kwargs.get("agent_uuid"),
        thread_uuid=kwargs.get("thread_uuid"),
        message_uuid=kwargs.get("message_uuid"),
        logger=info.context.get("logger"),
    )

    agent_uuid = kwargs["agent_uuid"]
    message_uuid = kwargs["message_uuid"]
    if kwargs.get("entity") is None:
        cols = {
            "thread_uuid": kwargs["thread_uuid"],
            "timestamp": int(time.time()),
            "endpoint_id": info.context["endpoint_id"],
            "role": kwargs["role"],
            "updated_by": kwargs["updated_by"],
            "updated_at": pendulum.now("UTC"),
        }
        for key in ["tool_calls", "tool_call_uuid", "content", "weight", "trained"]:
            if key in kwargs:
                cols[key] = kwargs[key]

        FineTuningMessageModel(
            agent_uuid,
            message_uuid,
            **cols,
        ).save()
        return

    fine_tuning_message = kwargs.get("entity")
    actions = [
        FineTuningMessageModel.updated_by.set(kwargs["updated_by"]),
        FineTuningMessageModel.updated_at.set(pendulum.now("UTC")),
    ]
    # Map of potential keys in kwargs to FineTuningMessageModel attributes
    field_map = {
        "tool_calls": FineTuningMessageModel.tool_calls,
        "tool_call_uuid": FineTuningMessageModel.tool_call_uuid,
        "content": FineTuningMessageModel.content,
        "weight": FineTuningMessageModel.weight,
        "trained": FineTuningMessageModel.trained,
    }

    # Check if a key exists in kwargs before adding it to the update actions
    for key, field in field_map.items():
        if key in kwargs:  # Check if the key exists in kwargs
            actions.append(field.set(kwargs[key]))

    # Update the fine_tuning_message
    fine_tuning_message.update(actions=actions)


    return


@delete_decorator(
    keys={
        "hash_key": "agent_uuid",
        "range_key": "message_uuid",
    },
    model_funct=get_fine_tuning_message,
)
def delete_fine_tuning_message(info: ResolveInfo, **kwargs: Dict[str, Any]) -> bool:
    # Use cascading cache purging for fine tuning messages
    from ..models.cache import purge_fine_tuning_message_cascading_cache

    cache_result = purge_fine_tuning_message_cascading_cache(
        agent_uuid=kwargs.get("agent_uuid"),
        thread_uuid=kwargs.get("thread_uuid"),
        message_uuid=kwargs.get("message_uuid"),
        logger=info.context.get("logger"),
    )

    kwargs.get("entity").delete()
    return True
