#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

# import asyncio
import functools
import logging
import traceback
from typing import Any, Dict

import pendulum
from graphene import ResolveInfo
from pynamodb.attributes import MapAttribute, UnicodeAttribute, UTCDateTimeAttribute
from pynamodb.indexes import AllProjection, LocalSecondaryIndex
from tenacity import retry, stop_after_attempt, wait_exponential

try:
    from mcp_http_client import MCPHttpClient
except (ModuleNotFoundError, ImportError):
    MCPHttpClient = None
from silvaengine_dynamodb_base import (
    BaseModel,
    delete_decorator,
    insert_update_decorator,
    monitor_decorator,
    resolve_list_decorator,
)
from silvaengine_utility import Debugger, Invoker, Serializer, method_cache

from ..handlers.config import Config
from ..types.mcp_server import MCPServerListType, MCPServerType


class UpdatedAtIndex(LocalSecondaryIndex):
    """
    This class represents a local secondary index
    """

    class Meta:
        billing_mode = "PAY_PER_REQUEST"
        # All attributes are projected
        projection = AllProjection()
        index_name = "updated_at-index"

    partition_key = UnicodeAttribute(hash_key=True)
    updated_at = UnicodeAttribute(range_key=True)


class MCPServerModel(BaseModel):
    class Meta(BaseModel.Meta):
        table_name = "aace-mcp_servers"

    partition_key = UnicodeAttribute(hash_key=True)
    mcp_server_uuid = UnicodeAttribute(range_key=True)
    endpoint_id = UnicodeAttribute()
    part_id = UnicodeAttribute()
    mcp_label = UnicodeAttribute()
    mcp_server_url = UnicodeAttribute()
    headers = MapAttribute()
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
                    entity_keys["mcp_server_uuid"] = getattr(
                        entity, "mcp_server_uuid", None
                    )

                # Fallback to kwargs (for creates/deletes)
                if not entity_keys.get("mcp_server_uuid"):
                    entity_keys["mcp_server_uuid"] = kwargs.get("mcp_server_uuid")

                # Get partition_key from context or kwargs
                partition_key = args[0].context.get("partition_key") or kwargs.get(
                    "partition_key"
                )

                # Only purge if we have the required keys
                if entity_keys.get("mcp_server_uuid"):
                    purge_entity_cascading_cache(
                        args[0].context.get("logger"),
                        entity_type="mcp_server",
                        context_keys=(
                            {"partition_key": partition_key} if partition_key else None
                        ),
                        entity_keys=entity_keys,
                        cascade_depth=3,
                    )

                # Also purge mcp_server_tools cache
                from silvaengine_utility.cache import HybridCacheEngine

                tools_cache = HybridCacheEngine(
                    Config.get_cache_name("models", "mcp_server_tools")
                )
                tools_cache.clear()

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
    cache_name=Config.get_cache_name("models", "mcp_server"),
    cache_enabled=Config.is_cache_enabled,
)
def get_mcp_server(partition_key: str, mcp_server_uuid: str) -> MCPServerModel:
    return MCPServerModel.get(partition_key, mcp_server_uuid)


def get_mcp_server_count(partition_key: str, mcp_server_uuid: str) -> int:
    return MCPServerModel.count(
        partition_key, MCPServerModel.mcp_server_uuid == mcp_server_uuid
    )


# @method_cache(
#     ttl=Config.get_cache_ttl(),
#     cache_name=Config.get_cache_name("models", "mcp_server_tools"),
#     cache_enabled=Config.is_cache_enabled,
# )
async def _run_list_tools(
    logger: logging.Logger, mcp_server: MCPServerModel | Dict[str, Any]
):
    if MCPHttpClient is None:
        raise ImportError("mcp_http_client is required to list MCP server tools.")

    if isinstance(mcp_server, MCPServerModel):
        base_url = mcp_server.mcp_server_url
        headers = mcp_server.headers.__dict__["attribute_values"]
    else:
        base_url = mcp_server["mcp_server_url"]
        headers = mcp_server["headers"]

    mcp_http_client = MCPHttpClient(
        logger,
        **{
            "base_url": base_url,
            "headers": headers,
        },
    )

    async with mcp_http_client as client:
        return await client.list_tools()


@method_cache(
    ttl=Config.get_cache_ttl(),
    cache_name=Config.get_cache_name("models", "mcp_server_tools"),
    cache_enabled=Config.is_cache_enabled,
)
def _load_list_tools(
    logger: logging.Logger, mcp_server: MCPServerModel | Dict[str, Any]
):
    tools = []

    try:
        # tools = asyncio.run(_run_list_tools(info, mcp_server))
        tools = Invoker.sync_call_async_compatible(_run_list_tools(logger, mcp_server))
    except Exception as e:
        mcp_server_uuid = "internal_mcp"

        if isinstance(mcp_server, MCPServerModel) and hasattr(
            mcp_server, "mcp_server_uuid"
        ):
            mcp_server_uuid = mcp_server.mcp_server_uuid
        elif "mcp_server_uuid" in mcp_server:
            mcp_server_uuid = mcp_server["mcp_server_uuid"]
        logger.error(
            f"Failed to list tools from MCP server {mcp_server_uuid}: {str(e)}"
        )

    return [
        {
            "name": tool.name,
            "description": tool.description,
            "input_schema": tool.get("inputSchema", tool.get("input_schema", {}))
            if isinstance(tool, dict)
            else getattr(tool, "input_schema", getattr(tool, "inputSchema", {})),
        }
        for tool in tools
    ]


def get_mcp_server_type(
    info: ResolveInfo, mcp_server: MCPServerModel | Dict[str, Any]
) -> MCPServerType:
    try:
        # tools = asyncio.run(_run_list_tools(info, mcp_server))
        tools = Invoker.sync_call_async_compatible(
            _run_list_tools(info.context["logger"], mcp_server)
        )
    except Exception as e:
        mcp_server_uuid = "internal_mcp"
        if isinstance(mcp_server, MCPServerModel):
            if hasattr(mcp_server, "mcp_server_uuid"):
                mcp_server_uuid = mcp_server.mcp_server_uuid
        elif "mcp_server_uuid" in mcp_server:
            mcp_server_uuid = mcp_server["mcp_server_uuid"]
        info.context["logger"].error(
            f"Failed to list tools from MCP server {mcp_server_uuid}: {str(e)}"
        )
        tools = []

    if isinstance(mcp_server, MCPServerModel):
        mcp_server = mcp_server.__dict__["attribute_values"]
    mcp_server["tools"] = [
        {
            "name": tool.name,
            "description": tool.description,
            "input_schema": tool.input_schema,
        }
        for tool in tools
    ]

    return MCPServerType(**Serializer.json_normalize(mcp_server))


def resolve_mcp_server(
    info: ResolveInfo, **kwargs: Dict[str, Any]
) -> MCPServerType | None:
    count = get_mcp_server_count(
        info.context["partition_key"], kwargs["mcp_server_uuid"]
    )
    if count == 0:
        return None

    return get_mcp_server_type(
        info, get_mcp_server(info.context["partition_key"], kwargs["mcp_server_uuid"])
    )


@monitor_decorator
@resolve_list_decorator(
    attributes_to_get=["partition_key", "mcp_server_uuid", "updated_at"],
    list_type_class=MCPServerListType,
    type_funct=get_mcp_server_type,
)
def resolve_mcp_server_list(info: ResolveInfo, **kwargs: Dict[str, Any]) -> Any:
    partition_key = info.context["partition_key"]
    mcp_label = kwargs.get("mcp_label")
    updated_at_gt = kwargs.get("updated_at_gt")
    updated_at_lt = kwargs.get("updated_at_lt")

    args = []
    inquiry_funct = MCPServerModel.scan
    count_funct = MCPServerModel.count
    range_key_condition = None
    if partition_key:
        # Build range key condition for updated_at when using updated_at_index
        if updated_at_gt is not None and updated_at_lt is not None:
            range_key_condition = MCPServerModel.updated_at.between(
                updated_at_gt, updated_at_lt
            )
        elif updated_at_gt is not None:
            range_key_condition = MCPServerModel.updated_at > updated_at_gt
        elif updated_at_lt is not None:
            range_key_condition = MCPServerModel.updated_at < updated_at_lt

        args = [partition_key, range_key_condition]
        inquiry_funct = MCPServerModel.updated_at_index.query
        count_funct = MCPServerModel.updated_at_index.count

    the_filters = None
    if mcp_label:
        the_filters &= MCPServerModel.mcp_label == mcp_label
    if the_filters is not None:
        args.append(the_filters)

    return inquiry_funct, count_funct, args


@insert_update_decorator(
    keys={
        "hash_key": "partition_key",
        "range_key": "mcp_server_uuid",
    },
    model_funct=get_mcp_server,
    count_funct=get_mcp_server_count,
    type_funct=get_mcp_server_type,
)
@purge_cache()
def insert_update_mcp_server(info: ResolveInfo, **kwargs: Dict[str, Any]) -> Any:
    partition_key = kwargs.get("partition_key")
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
        cols["endpoint_id"] = info.context.get("endpoint_id")
        cols["part_id"] = info.context.get("part_id")
        MCPServerModel(
            partition_key,
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
        "hash_key": "partition_key",
        "range_key": "mcp_server_uuid",
    },
    model_funct=get_mcp_server,
)
@purge_cache()
def delete_mcp_server(info: ResolveInfo, **kwargs: Dict[str, Any]) -> bool:
    kwargs["entity"].delete()
    return True
