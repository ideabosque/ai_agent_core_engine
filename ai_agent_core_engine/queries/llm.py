#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict

from graphene import ResolveInfo

from silvaengine_utility import method_cache

from ..handlers.config import Config

from ..models import llm
from ..types.llm import LlmListType, LlmType


def resolve_llm(info: ResolveInfo, **kwargs: Dict[str, Any]) -> LlmType:
    return llm.resolve_llm(info, **kwargs)


@method_cache(ttl=Config.get_cache_ttl(), cache_name=Config.get_cache_name('queries', 'llm'))
def resolve_llm_list(info: ResolveInfo, **kwargs: Dict[str, Any]) -> LlmListType:
    return llm.resolve_llm_list(info, **kwargs)
