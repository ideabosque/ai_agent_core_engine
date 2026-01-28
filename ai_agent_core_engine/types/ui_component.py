#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from graphene import DateTime, List, ObjectType, String

from silvaengine_dynamodb_base import ListObjectType
from silvaengine_utility import JSONCamelCase


class UIComponentType(ObjectType):
    ui_component_type = String()
    ui_component_uuid = String()
    tag_name = String()
    parameters = List(JSONCamelCase)
    wait_for = String()
    updated_by = String()
    created_at = DateTime()
    updated_at = DateTime()


class UIComponentListType(ListObjectType):
    ui_component_list = List(UIComponentType)
