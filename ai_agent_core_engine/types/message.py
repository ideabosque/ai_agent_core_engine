#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from graphene import DateTime, List, ObjectType, String

from silvaengine_dynamodb_base import ListObjectType
from silvaengine_utility import JSON


class MessageType(ObjectType):
    run = JSON()
    message_uuid = String()
    message_id = String()
    role = String()
    message = String()
    updated_by = String()
    created_at = DateTime()
    updated_at = DateTime()


class MessageListType(ListObjectType):
    message_list = List(MessageType)
