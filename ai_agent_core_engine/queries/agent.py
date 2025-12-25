#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict

from graphene import ResolveInfo

from silvaengine_utility import method_cache

from ..handlers.config import Config

from ..models import agent
from ..types.agent import AgentListType, AgentType


def resolve_agent(info: ResolveInfo, **kwargs: Dict[str, Any]) -> AgentType:
    return agent.resolve_agent(info, **kwargs)


# @method_cache(ttl=Config.get_cache_ttl(), cache_name=Config.get_cache_name('queries', 'agent'))
def resolve_agent_list(info: ResolveInfo, **kwargs: Dict[str, Any]) -> AgentListType:
    return agent.resolve_agent_list(info, **kwargs)
