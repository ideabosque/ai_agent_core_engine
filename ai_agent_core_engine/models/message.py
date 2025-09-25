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

from ..types.message import MessageListType, MessageType
from .utils import _get_run


class RunIdIndex(LocalSecondaryIndex):
    """
    This class represents a local secondary index
    """

    class Meta:
        billing_mode = "PAY_PER_REQUEST"
        # All attributes are projected
        projection = AllProjection()
        index_name = "run_uuid-index"

    thread_uuid = UnicodeAttribute(hash_key=True)
    run_uuid = UnicodeAttribute(range_key=True)


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


class MessageModel(BaseModel):
    class Meta(BaseModel.Meta):
        table_name = "aace-messages"

    thread_uuid = UnicodeAttribute(hash_key=True)
    message_uuid = UnicodeAttribute(range_key=True)
    run_uuid = UnicodeAttribute()
    message_id = UnicodeAttribute(null=True)
    role = UnicodeAttribute()
    message = UnicodeAttribute()
    updated_by = UnicodeAttribute()
    created_at = UTCDateTimeAttribute()
    updated_at = UTCDateTimeAttribute()
    run_uuid_index = RunIdIndex()
    updated_at_index = UpdatedAtIndex()


def create_message_table(logger: logging.Logger) -> bool:
    """Create the Message table if it doesn't exist."""
    if not MessageModel.exists():
        # Create with on-demand billing (PAY_PER_REQUEST)
        MessageModel.create_table(billing_mode="PAY_PER_REQUEST", wait=True)
        logger.info("The Message table has been created.")
    return True


@retry(
    reraise=True,
    wait=wait_exponential(multiplier=1, max=60),
    stop=stop_after_attempt(5),
)
def get_message(thread_uuid: str, message_uuid: str) -> MessageModel:
    return MessageModel.get(thread_uuid, message_uuid)


def get_message_count(thread_uuid: str, message_uuid: str) -> int:
    return MessageModel.count(thread_uuid, MessageModel.message_uuid == message_uuid)


def get_message_type(info: ResolveInfo, message: MessageModel) -> MessageType:
    try:
        run = _get_run(message.thread_uuid, message.run_uuid)
    except Exception as e:
        log = traceback.format_exc()
        info.context.get("logger").exception(log)
        raise e
    message = message.__dict__["attribute_values"]
    message["run"] = run
    message.pop("thread_uuid")
    message.pop("run_uuid")
    return MessageType(**Utility.json_normalize(message))


def resolve_message(info: ResolveInfo, **kwargs: Dict[str, Any]) -> MessageType:
    count = get_message_count(kwargs["thread_uuid"], kwargs["message_uuid"])
    if count == 0:
        return None

    return get_message_type(
        info, get_message(kwargs["thread_uuid"], kwargs["message_uuid"])
    )


@monitor_decorator
@resolve_list_decorator(
    attributes_to_get=["thread_uuid", "message_uuid", "run_uuid", "updated_at"],
    list_type_class=MessageListType,
    type_funct=get_message_type,
)
def resolve_message_list(info: ResolveInfo, **kwargs: Dict[str, Any]) -> Any:
    thread_uuid = kwargs.get("thread_uuid")
    run_uuid = kwargs.get("run_uuid")
    message_id = kwargs.get("message_id")
    roles = kwargs.get("roles")

    args = []
    inquiry_funct = MessageModel.scan
    count_funct = MessageModel.count
    if thread_uuid:
        args = [thread_uuid, None]
        inquiry_funct = MessageModel.updated_at_index.query
        count_funct = MessageModel.updated_at_index.count
        if run_uuid:
            inquiry_funct = MessageModel.run_uuid_index.query
            args[1] = MessageModel.run_uuid == run_uuid
            count_funct = MessageModel.run_uuid_index.count

    the_filters = None
    if message_id:
        the_filters &= MessageModel.message_id.exists()
        the_filters &= MessageModel.message_id == message_id
    if roles:
        the_filters &= MessageModel.role.is_in(*roles)
    if the_filters is not None:
        args.append(the_filters)

    return inquiry_funct, count_funct, args


@insert_update_decorator(
    keys={"hash_key": "thread_uuid", "range_key": "message_uuid"},
    model_funct=get_message,
    count_funct=get_message_count,
    type_funct=get_message_type,
    # data_attributes_except_for_data_diff=["created_at", "updated_at"],
    # activity_history_funct=None,
)
def insert_update_message(info: ResolveInfo, **kwargs: Dict[str, Any]) -> None:
    thread_uuid = kwargs.get("thread_uuid")
    message_uuid = kwargs.get("message_uuid")
    if kwargs.get("entity") is None:
        cols = {
            "run_uuid": kwargs["run_uuid"],
            "role": kwargs["role"],
            "message": kwargs["message"],
            "updated_by": kwargs["updated_by"],
            "created_at": pendulum.now("UTC"),
            "updated_at": pendulum.now("UTC"),
        }
        for key in [
            "message_id",
        ]:
            if key in kwargs:
                cols[key] = kwargs[key]

        MessageModel(
            thread_uuid,
            message_uuid,
            **cols,
        ).save()
        return

    message = kwargs.get("entity")
    actions = [
        MessageModel.updated_by.set(kwargs["updated_by"]),
        MessageModel.updated_at.set(pendulum.now("UTC")),
    ]
    # Map of potential keys in kwargs to MessageModel attributes
    field_map = {
        "run_uuid": MessageModel.run_uuid,
        "message_id": MessageModel.message_id,
        "role": MessageModel.role,
        "message": MessageModel.message,
    }

    # Check if a key exists in kwargs before adding it to the update actions
    for key, field in field_map.items():
        if key in kwargs:  # Check if the key exists in kwargs
            actions.append(field.set(kwargs[key]))

    # Update the message
    message.update(actions=actions)
    return


@delete_decorator(
    keys={"hash_key": "thread_uuid", "range_key": "message_uuid"},
    model_funct=get_message,
)
def delete_message(info: ResolveInfo, **kwargs: Dict[str, Any]) -> bool:
    kwargs.get("entity").delete()
    return True
