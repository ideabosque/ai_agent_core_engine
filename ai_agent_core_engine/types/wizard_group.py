#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from graphene import DateTime, Int, List, ObjectType, String

from silvaengine_dynamodb_base import ListObjectType
from silvaengine_utility import JSON


class WizardGroupType(ObjectType):
    endpoint_id = String()
    wizard_group_uuid = String()
    wizard_group_name = String()
    wizard_group_description = String()
    weight = Int()
    wizard_uuids = List(String)
    updated_by = String()
    created_at = DateTime()
    updated_at = DateTime()


class WizardGroupListType(ListObjectType):
    wizard_group_list = List(WizardGroupType)
