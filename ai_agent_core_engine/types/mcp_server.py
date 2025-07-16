#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from graphene import Boolean, DateTime, List, ObjectType, String

from silvaengine_dynamodb_base import ListObjectType
from silvaengine_utility import JSON


class MCPServerType(ObjectType):
    endpoint_id = String()
    mcp_server_uuid = String()
    mcp_label = String()
    mcp_server_url = String()
    headers = JSON()
    tools = List(JSON)
    updated_by = String()
    created_at = DateTime()
    updated_at = DateTime()


class MCPServerListType(ListObjectType):
    mcp_server_list = List(MCPServerType)
