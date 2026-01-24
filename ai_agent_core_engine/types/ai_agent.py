#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from graphene import Boolean, DateTime, Field, Int, List, ObjectType, String
from silvaengine_utility import JSONCamelCase


class AskModelType(ObjectType):
    agent_uuid = String()
    thread_uuid = String()
    user_query = String()
    function_name = String()
    async_task_uuid = String()
    current_run_uuid = String()


class FileType(ObjectType):
    identity = String()
    value = String()
    file_detail = Field(JSONCamelCase)


class PresignedAWSS3UrlType(ObjectType):
    url = String()
    object_key = String()
    expiration = Int()
