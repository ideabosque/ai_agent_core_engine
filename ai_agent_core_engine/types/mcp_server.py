#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from graphene import DateTime, List, ObjectType, String
from silvaengine_dynamodb_base import ListObjectType
from silvaengine_utility import JSONCamelCase


class MCPServerType(ObjectType):
    partition_key = String()
    endpoint_id = String()
    part_id = String()
    mcp_server_uuid = String()
    mcp_label = String()
    mcp_server_url = String()
    headers = Field(JSONCamelCase)
    tools = List(JSONCamelCase)
    updated_by = String()
    created_at = DateTime()
    updated_at = DateTime()


class MCPServerListType(ListObjectType):
    mcp_server_list = List(MCPServerType)
