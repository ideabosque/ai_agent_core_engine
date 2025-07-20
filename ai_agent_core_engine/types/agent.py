#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from graphene import DateTime, Int, List, ObjectType, String

from silvaengine_dynamodb_base import ListObjectType
from silvaengine_utility import JSON


class AgentType(ObjectType):
    endpoint_id = String()
    agent_version_uuid = String()
    agent_uuid = String()
    agent_name = String()
    agent_description = String()
    llm = JSON()
    instructions = String()
    configuration = JSON()
    function_configuration = JSON()
    functions = JSON()
    num_of_messages = Int()
    tool_call_role = String()
    flow_snippet = JSON()
    status = String()
    updated_by = String()
    created_at = DateTime()
    updated_at = DateTime()


class AgentListType(ListObjectType):
    agent_list = List(AgentType)
