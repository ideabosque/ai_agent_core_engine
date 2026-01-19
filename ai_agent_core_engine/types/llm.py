#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from graphene import DateTime, List, ObjectType, String

from silvaengine_dynamodb_base import ListObjectType
from silvaengine_utility import JSONCamelCase


class LlmType(ObjectType):
    llm_provider = String()
    llm_name = String()
    module_name = String()
    class_name = String()
    configuration_schema = Field(JSONCamelCase)
    updated_by = String()
    created_at = DateTime()
    updated_at = DateTime()


class LlmListType(ListObjectType):
    llm_list = List(LlmType)
