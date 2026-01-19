#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from graphene import DateTime, Int, List, ObjectType, String

from silvaengine_dynamodb_base import ListObjectType
from silvaengine_utility import JSONCamelCase


class AsyncTaskType(ObjectType):
    function_name = String()
    async_task_uuid = String()
    partition_key = String()
    arguments = Field(JSONCamelCase)
    result = String()
    output_files = List(JSONCamelCase)
    status = String()
    notes = String()
    time_spent = Int()
    updated_by = String()
    created_at = DateTime()
    updated_at = DateTime()


class AsyncTaskListType(ListObjectType):
    async_task_list = List(AsyncTaskType)
