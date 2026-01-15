#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict

from graphene import ResolveInfo

from silvaengine_utility import method_cache

from ..handlers.config import Config

from ..models import tool_call
from ..types.tool_call import ToolCallListType, ToolCallType


def resolve_tool_call(
    info: ResolveInfo, **kwargs: Dict[str, Any]
) -> ToolCallType | None:
    return tool_call.resolve_tool_call(info, **kwargs)


@method_cache(
    ttl=Config.get_cache_ttl(),
    cache_name=Config.get_cache_name("queries", "tool_call"),
    cache_enabled=Config.is_cache_enabled,
)
def resolve_tool_call_list(
    info: ResolveInfo, **kwargs: Dict[str, Any]
) -> ToolCallListType | None:
    return tool_call.resolve_tool_call_list(info, **kwargs)
