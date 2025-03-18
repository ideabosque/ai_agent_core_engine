#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from graphene import DateTime, Int, List, ObjectType, String

from silvaengine_dynamodb_base import ListObjectType
from silvaengine_utility import JSON


class RunType(ObjectType):
    thread = JSON()
    run_uuid = String()
    run_id = String()
    completion_tokens = Int()
    prompt_tokens = Int()
    total_tokens = Int()
    time_spent = Int()
    updated_by = String()
    created_at = DateTime()
    updated_at = DateTime()


class RunListType(ListObjectType):
    run_list = List(RunType)
