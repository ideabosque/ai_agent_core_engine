#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from graphene import DateTime, List, ObjectType, String, Boolean


class AskModelType(ObjectType):
    agent_uuid = String()
    thread_uuid = String()
    user_query = String()
    function_name = String()
    async_task_uuid = String()
    current_run_uuid = String()
