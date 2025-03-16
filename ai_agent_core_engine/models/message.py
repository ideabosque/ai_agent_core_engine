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
        index_name = "run_id-index"

    thread_uuid = UnicodeAttribute(hash_key=True)
    run_id = UnicodeAttribute(range_key=True)


class MessageModel(BaseModel):
    class Meta(BaseModel.Meta):
        table_name = "aace-messages"

    thread_uuid = UnicodeAttribute(hash_key=True)
    message_id = UnicodeAttribute(range_key=True)
    run_id = UnicodeAttribute()
    role = UnicodeAttribute()
    message = UnicodeAttribute()
    created_at = UTCDateTimeAttribute()
    run_id_index = RunIdIndex()


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
def get_message(thread_uuid: str, message_id: str) -> MessageModel:
    return MessageModel.get(thread_uuid, message_id)


def get_message_count(thread_uuid: str, message_id: str) -> int:
    return MessageModel.count(thread_uuid, MessageModel.message_id == message_id)


def get_message_type(info: ResolveInfo, message: MessageModel) -> MessageType:
    try:
        run = _get_run(message.thread_uuid, message.run_id)
    except Exception as e:
        log = traceback.format_exc()
        info.context.get("logger").exception(log)
        raise e
    message = message.__dict__["attribute_values"]
    message["run"] = run
    message.pop("thread_uuid")
    message.pop("run_id")
    return MessageType(**Utility.json_loads(Utility.json_dumps(message)))


def resolve_message(info: ResolveInfo, **kwargs: Dict[str, Any]) -> MessageType:
    return get_message_type(
        info, get_message(kwargs["thread_uuid"], kwargs["message_id"])
    )


@monitor_decorator
@resolve_list_decorator(
    attributes_to_get=["thread_uuid", "message_id", "run_id"],
    list_type_class=MessageListType,
    type_funct=get_message_type,
)
def resolve_message_list(info: ResolveInfo, **kwargs: Dict[str, Any]) -> Any:
    thread_uuid = kwargs.get("thread_uuid")
    run_id = kwargs.get("run_id")
    roles = kwargs.get("roles")

    args = []
    inquiry_funct = MessageModel.scan
    count_funct = MessageModel.count
    if thread_uuid:
        args = [thread_uuid, None]
        inquiry_funct = MessageModel.query
        if run_id:
            args[1] = MessageModel.run_id == run_id
            count_funct = MessageModel.run_id_index.count

    the_filters = None
    if roles:
        the_filters &= MessageModel.role.is_in(*roles)
    if the_filters is not None:
        args.append(the_filters)

    return inquiry_funct, count_funct, args


@insert_update_decorator(
    keys={"hash_key": "thread_uuid", "range_key": "message_id"},
    range_key_required=True,
    model_funct=get_message,
    count_funct=get_message_count,
    type_funct=get_message_type,
    # data_attributes_except_for_data_diff=["created_at", "updated_at"],
    # activity_history_funct=None,
)
def insert_message(info: ResolveInfo, **kwargs: Dict[str, Any]) -> None:
    thread_uuid = kwargs.get("thread_uuid")
    message_id = kwargs.get("message_id")
    if kwargs.get("entity") is None:
        cols = {
            "run_id": kwargs["run_id"],
            "role": kwargs["role"],
            "message": kwargs["message"],
            "created_at": pendulum.now("UTC"),
        }
        MessageModel(
            thread_uuid,
            message_id,
            **cols,
        ).save()
        return
    return


@delete_decorator(
    keys={"hash_key": "thread_uuid", "range_key": "message_id"},
    model_funct=get_message,
)
def delete_message(info: ResolveInfo, **kwargs: Dict[str, Any]) -> bool:
    kwargs.get("entity").delete()
    return True
