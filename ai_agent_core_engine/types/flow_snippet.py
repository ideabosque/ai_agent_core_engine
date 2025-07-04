#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from graphene import Boolean, DateTime, List, ObjectType, String

from silvaengine_dynamodb_base import ListObjectType
from silvaengine_utility import JSON


class FlowSnippetType(ObjectType):
    endpoint_id = String()
    flow_snippet_version_uuid = String()
    flow_snippet_uuid = String()
    prompt_version_uuid = String()
    prompt_uuid = String()
    flow_name = String()
    flow_relationship = String()
    flow_context = String()
    status = String()
    updated_by = String()
    created_at = DateTime()
    updated_at = DateTime()


class FlowSnippetListType(ListObjectType):
    flow_snippet_list = List(FlowSnippetType)
