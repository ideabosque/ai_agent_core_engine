#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import logging
import uuid
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

from ..types.mcp_server import MCPServerListType, MCPServerType


class MCPServerModel(BaseModel):
    class Meta(BaseModel.Meta):
        table_name = "aace-mcp_servers"

    endpoint_id = UnicodeAttribute(hash_key=True)
    mcp_server_uuid = UnicodeAttribute(range_key=True)
    mcp_label = UnicodeAttribute()
    mcp_server_url = UnicodeAttribute()
    headers = MapAttribute()
    updated_by = UnicodeAttribute()
    created_at = UTCDateTimeAttribute()
    updated_at = UTCDateTimeAttribute()


def create_mcp_server_table(logger: logging.Logger) -> bool:
    """Create the MCPServer table if it doesn't exist."""
    if not MCPServerModel.exists():
        # Create with on-demand billing (PAY_PER_REQUEST)
        MCPServerModel.create_table(billing_mode="PAY_PER_REQUEST", wait=True)
        logger.info("The MCPServer table has been created.")
    return True


@retry(
    reraise=True,
    wait=wait_exponential(multiplier=1, max=60),
    stop=stop_after_attempt(5),
)
def get_mcp_server(endpoint_id: str, mcp_server_uuid: str) -> MCPServerModel:
    return MCPServerModel.get(endpoint_id, mcp_server_uuid)


def get_mcp_server_count(endpoint_id: str, mcp_server_uuid: str) -> int:
    return MCPServerModel.count(
        endpoint_id, MCPServerModel.mcp_server_uuid == mcp_server_uuid
    )


def get_mcp_server_type(info: ResolveInfo, mcp_server: MCPServerModel) -> MCPServerType:
    mcp_server = mcp_server.__dict__["attribute_values"]
    return MCPServerType(**Utility.json_loads(Utility.json_dumps(mcp_server)))


def resolve_mcp_server(info: ResolveInfo, **kwargs: Dict[str, Any]) -> MCPServerType:
    count = get_mcp_server_count(info.context["endpoint_id"], kwargs["mcp_server_uuid"])
    if count == 0:
        return None

    return get_mcp_server_type(
        info, get_mcp_server(info.context["endpoint_id"], kwargs["mcp_server_uuid"])
    )


@monitor_decorator
@resolve_list_decorator(
    attributes_to_get=["endpoint_id", "mcp_server_uuid"],
    list_type_class=MCPServerListType,
    type_funct=get_mcp_server_type,
)
def resolve_mcp_server_list(info: ResolveInfo, **kwargs: Dict[str, Any]) -> Any:
    endpoint_id = kwargs.get("endpoint_id")
    mcp_label = kwargs.get("mcp_label")

    args = []
    inquiry_funct = MCPServerModel.scan
    count_funct = MCPServerModel.count
    if endpoint_id:
        args = [endpoint_id, None]
        inquiry_funct = MCPServerModel.query

    the_filters = None
    if mcp_label:
        the_filters &= MCPServerModel.mcp_label == mcp_label
    if the_filters is not None:
        args.append(the_filters)

    return inquiry_funct, count_funct, args


@insert_update_decorator(
    keys={
        "hash_key": "endpoint_id",
        "range_key": "mcp_server_uuid",
    },
    model_funct=get_mcp_server,
    count_funct=get_mcp_server_count,
    type_funct=get_mcp_server_type,
)
def insert_update_mcp_server(info: ResolveInfo, **kwargs: Dict[str, Any]) -> None:
    endpoint_id = kwargs.get("endpoint_id")
    mcp_server_uuid = kwargs.get("mcp_server_uuid")

    if kwargs.get("entity") is None:
        cols = {
            "mcp_label": kwargs["mcp_label"],
            "mcp_server_url": kwargs["mcp_server_url"],
            "headers": kwargs.get("headers", {}),
            "updated_by": kwargs["updated_by"],
            "created_at": pendulum.now("UTC"),
            "updated_at": pendulum.now("UTC"),
        }
        MCPServerModel(
            endpoint_id,
            mcp_server_uuid,
            **cols,
        ).save()
        return

    mcp_server = kwargs.get("entity")
    actions = [
        MCPServerModel.updated_by.set(kwargs["updated_by"]),
        MCPServerModel.updated_at.set(pendulum.now("UTC")),
    ]

    field_map = {
        "mcp_label": MCPServerModel.mcp_label,
        "mcp_server_url": MCPServerModel.mcp_server_url,
        "headers": MCPServerModel.headers,
    }

    for key, field in field_map.items():
        if key in kwargs:
            actions.append(field.set(None if kwargs[key] == "null" else kwargs[key]))

    mcp_server.update(actions=actions)
    return


@delete_decorator(
    keys={
        "hash_key": "endpoint_id",
        "range_key": "mcp_server_uuid",
    },
    model_funct=get_mcp_server,
)
def delete_mcp_server(info: ResolveInfo, **kwargs: Dict[str, Any]) -> bool:
    kwargs["entity"].delete()
    return True
