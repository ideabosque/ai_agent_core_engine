#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict

from graphene import ResolveInfo

from silvaengine_utility import method_cache

from ..handlers.config import Config

from ..models import async_task
from ..types.async_task import AsyncTaskListType, AsyncTaskType


def resolve_async_task(info: ResolveInfo, **kwargs: Dict[str, Any]) -> AsyncTaskType:
    return async_task.resolve_async_task(info, **kwargs)


@method_cache(ttl=Config.get_cache_ttl(), cache_name=Config.get_cache_name('queries', 'async_task'))
def resolve_async_task_list(
    info: ResolveInfo, **kwargs: Dict[str, Any]
) -> AsyncTaskListType:
    return async_task.resolve_async_task_list(info, **kwargs)
