#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from graphene import DateTime, Int, List, ObjectType, String

from silvaengine_dynamodb_base import ListObjectType
from silvaengine_utility import JSON


class WizardType(ObjectType):
    endpoint_id = String()
    wizard_uuid = String()
    wizard_title = String()
    wizard_description = String()
    wizard_type = String()
    wizard_schema = JSON()
    wizard_attributes = List(JSON)
    wizard_elements = List(JSON)
    priority = Int()
    updated_by = String()
    created_at = DateTime()
    updated_at = DateTime()


class WizardListType(ListObjectType):
    wizard_list = List(WizardType)
