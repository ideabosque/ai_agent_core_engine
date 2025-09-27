#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict

from graphene import ResolveInfo

from silvaengine_utility import method_cache

from ..handlers.config import Config

from ..models import mcp_server
from ..types.mcp_server import MCPServerListType, MCPServerType


def resolve_mcp_server(info: ResolveInfo, **kwargs: Dict[str, Any]) -> MCPServerType:
    return mcp_server.resolve_mcp_server(info, **kwargs)


@method_cache(ttl=Config.get_cache_ttl(), cache_name=Config.get_cache_name('queries', 'mcp_server'))
def resolve_mcp_server_list(info: ResolveInfo, **kwargs: Dict[str, Any]) -> MCPServerListType:
    return mcp_server.resolve_mcp_server_list(info, **kwargs)