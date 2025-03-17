#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from graphene import Boolean, DateTime, Float, Int, List, ObjectType, String

from silvaengine_dynamodb_base import ListObjectType
from silvaengine_utility import JSON


class FineTuningMessageType(ObjectType):
    agent_uuid = String()
    message_uuid = String()
    thread_uuid = String()
    timestamp = Int()
    endpoint_id = String()
    role = String()
    tool_calls = List(JSON)
    tool_call_uuid = String()
    content = String()
    weight = Float()
    trained = Boolean()
    updated_by = String()
    updated_at = DateTime()


class FineTuningMessageListType(ListObjectType):
    fine_tuning_message_list = List(FineTuningMessageType)
