#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict

from graphene import ResolveInfo

from silvaengine_utility import method_cache

from ..handlers.config import Config

from ..models import flow_snippet
from ..types.flow_snippet import FlowSnippetListType, FlowSnippetType


def resolve_flow_snippet(info: ResolveInfo, **kwargs: Dict[str, Any]) -> FlowSnippetType:
    return flow_snippet.resolve_flow_snippet(info, **kwargs)


@method_cache(ttl=Config.get_cache_ttl(), cache_name=Config.get_cache_name('queries', 'flow_snippet'))
def resolve_flow_snippet_list(info: ResolveInfo, **kwargs: Dict[str, Any]) -> FlowSnippetListType:
    return flow_snippet.resolve_flow_snippet_list(info, **kwargs)