#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict

from graphene import ResolveInfo

from ..handlers import ai_agent, at_agent_listener
from ..types.ai_agent import AskModelType
from ..types.async_task import AsyncTaskType


def resolve_ask_model(info: ResolveInfo, **kwargs: Dict[str, Any]) -> AskModelType:
    return ai_agent.ask_model(info, **kwargs)


def resolve_execute_ask_model(
    info: ResolveInfo, **kwargs: Dict[str, Any]
) -> AsyncTaskType:
    return at_agent_listener.execute_ask_model(info, **kwargs)
