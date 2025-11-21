#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from graphene import Boolean, DateTime, List, ObjectType, String

from silvaengine_dynamodb_base import ListObjectType
from silvaengine_utility import JSON


class FlowSnippetBaseType(ObjectType):
    endpoint_id = String()
    flow_snippet_version_uuid = String()
    flow_snippet_uuid = String()
    prompt_template = JSON()
    flow_name = String()
    status = String()
    updated_by = String()
    created_at = DateTime()
    updated_at = DateTime()


class FlowSnippetType(FlowSnippetBaseType):
    flow_relationship = String()
    flow_context = String()


class FlowSnippetListType(ListObjectType):
    flow_snippet_list = List(FlowSnippetBaseType)
