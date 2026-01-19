#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from graphene import DateTime, List, ObjectType, String
from silvaengine_dynamodb_base import ListObjectType
from silvaengine_utility import JSON
from ..utils.normalization import normalize_to_json


class MCPServerType(ObjectType):
    partition_key = String()
    endpoint_id = String()
    part_id = String()
    mcp_server_uuid = String()
    mcp_label = String()
    mcp_server_url = String()
    headers = JSON()
    tools = List(JSON)
    updated_by = String()
    created_at = DateTime()
    updated_at = DateTime()

    def resolve_tools(parent, info):

        tools = getattr(parent, "tools", None)
        if tools is not None:
            return tools
        
        if isinstance(parent, dict):
            mcp_server_url = parent.get("mcp_server_url", None)
            headers = parent.get("headers", None)
        else:
            mcp_server_url = getattr(parent, "prompt_uuid", None)
            headers = getattr(parent, "headers", None)

        if not mcp_server_url or not headers:
            return None
        from ..models.batch_loaders import get_loaders

        loaders = get_loaders(info.context)

        return (
            loaders.mcp_server_tool_loader.load((mcp_server_url, tuple(headers.items())))
            .then(
                lambda mcp_server_tool_dicts: [
                    normalize_to_json(mcp_tool_dict)
                    for mcp_tool_dict in mcp_server_tool_dicts
                    if mcp_tool_dict is not None
                ]
            )
        )


class MCPServerListType(ListObjectType):
    mcp_server_list = List(MCPServerType)
