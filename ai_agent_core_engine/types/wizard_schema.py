#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from graphene import DateTime, Boolean, List, ObjectType, String

from silvaengine_dynamodb_base import ListObjectType
from silvaengine_utility import JSONCamelCase


class WizardSchemaType(ObjectType):
    wizard_schema_type = String()
    wizard_schema_name = String()
    wizard_schema_description = String()
    attributes = List(JSONCamelCase)
    attribute_groups = List(JSONCamelCase)
    updated_by = String()
    created_at = DateTime()
    updated_at = DateTime()


class WizardSchemaListType(ListObjectType):
    wizard_schema_list = List(WizardSchemaType)
