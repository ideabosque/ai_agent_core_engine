#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import asyncio
import logging
from typing import Any, Dict

import pendulum
from graphene import ResolveInfo
from pynamodb.attributes import MapAttribute, UnicodeAttribute, UTCDateTimeAttribute
from tenacity import retry, stop_after_attempt, wait_exponential

from mcp_http_client import MCPHttpClient
from silvaengine_dynamodb_base import (
    BaseModel,
    delete_decorator,
    insert_update_decorator,
    monitor_decorator,
    resolve_list_decorator,
)
from silvaengine_utility import Utility, method_cache

from ..handlers.config import Config
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
@method_cache(ttl=Config.get_cache_ttl(), cache_name=Config.get_cache_name('models', 'mcp_server'))
def get_mcp_server(endpoint_id: str, mcp_server_uuid: str) -> MCPServerModel:
    return MCPServerModel.get(endpoint_id, mcp_server_uuid)


def get_mcp_server_count(endpoint_id: str, mcp_server_uuid: str) -> int:
    return MCPServerModel.count(
        endpoint_id, MCPServerModel.mcp_server_uuid == mcp_server_uuid
    )


async def _run_list_tools(info: ResolveInfo, mcp_server: MCPServerModel):
    mcp_http_client = MCPHttpClient(
        info.context["logger"],
        **{
            "base_url": mcp_server.mcp_server_url,
            "headers": mcp_server.headers.__dict__["attribute_values"],
        },
    )
    async with mcp_http_client as client:
        return await client.list_tools()


def get_mcp_server_type(info: ResolveInfo, mcp_server: MCPServerModel) -> MCPServerType:
    tools = asyncio.run(_run_list_tools(info, mcp_server))
    mcp_server = mcp_server.__dict__["attribute_values"]
    mcp_server["tools"] = [
        {
            "name": tool.name,
            "description": tool.description,
            "input_schema": tool.input_schema,
        }
        for tool in tools
    ]
    return MCPServerType(**Utility.json_normalize(mcp_server))


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
    endpoint_id = info.context["endpoint_id"]
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
    # Use cascading cache purging for mcp servers
    from ..models.cache import purge_mcp_server_cascading_cache

    cache_result = purge_mcp_server_cascading_cache(
        endpoint_id=kwargs.get("endpoint_id"),
        mcp_server_uuid=kwargs.get("mcp_server_uuid"),
        logger=info.context.get("logger"),
    )

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
    # Use cascading cache purging for mcp servers
    from ..models.cache import purge_mcp_server_cascading_cache

    cache_result = purge_mcp_server_cascading_cache(
        endpoint_id=kwargs.get("endpoint_id"),
        mcp_server_uuid=kwargs.get("mcp_server_uuid"),
        logger=info.context.get("logger"),
    )

    kwargs["entity"].delete()
    return True
