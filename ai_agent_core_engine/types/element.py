#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from graphene import DateTime, Int, List, ObjectType, String

from silvaengine_dynamodb_base import ListObjectType
from silvaengine_utility import JSON


class ElementType(ObjectType):
    partition_key = String()
    endpoint_id = String()
    part_id = String()
    element_uuid = String()
    data_type = String()
    element_title = String()
    priority = Int()
    attribute_name = String()
    attribute_type = String()
    option_values = List(JSON)
    conditions = List(JSON)
    pattern = String()
    updated_by = String()
    created_at = DateTime()
    updated_at = DateTime()


class ElementListType(ListObjectType):
    element_list = List(ElementType)
