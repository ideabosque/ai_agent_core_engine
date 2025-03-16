#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from graphene import DateTime, List, ObjectType, String

from silvaengine_dynamodb_base import ListObjectType
from silvaengine_utility import JSON


class ThreadType(ObjectType):
    agent = JSON()
    thread_uuid = String()
    user_id = String()
    created_at = DateTime()


class ThreadListType(ListObjectType):
    thread_list = List(ThreadType)
