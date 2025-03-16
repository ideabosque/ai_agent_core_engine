#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict

from graphene import ResolveInfo

from ..models import tool_call
from ..types.tool_call import ToolCallListType, ToolCallType


def resolve_tool_call(info: ResolveInfo, **kwargs: Dict[str, Any]) -> ToolCallType:
    return tool_call.resolve_tool_call(info, **kwargs)


def resolve_tool_call_list(
    info: ResolveInfo, **kwargs: Dict[str, Any]
) -> ToolCallListType:
    return tool_call.resolve_tool_call_list(info, **kwargs)
