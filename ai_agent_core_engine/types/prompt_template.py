#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from graphene import Boolean, DateTime, List, ObjectType, String

from silvaengine_dynamodb_base import ListObjectType
from silvaengine_utility import JSON


class PromptTemplateType(ObjectType):
    endpoint_id = String()
    prompt_version_uuid = String()
    prompt_uuid = String()
    prompt_type = String()
    prompt_name = String()
    prompt_description = String()
    template_context = String()
    variables = List(JSON)
    mcp_servers = List(JSON)
    ui_components = List(JSON)
    status = String()
    updated_by = String()
    created_at = DateTime()
    updated_at = DateTime()


class PromptTemplateListType(ListObjectType):
    prompt_template_list = List(PromptTemplateType)
