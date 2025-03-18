#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from graphene import DateTime, Int, List, ObjectType, String

from silvaengine_dynamodb_base import ListObjectType
from silvaengine_utility import JSON


class ToolCallType(ObjectType):
    run = JSON()
    tool_call_uuid = String()
    tool_call_id = String()
    tool_type = String()
    name = String()
    arguments = JSON()
    content = String()
    status = String()
    notes = String()
    time_spent = Int()
    updated_by = String()
    created_at = DateTime()
    updated_at = DateTime()


class ToolCallListType(ListObjectType):
    tool_call_list = List(ToolCallType)
