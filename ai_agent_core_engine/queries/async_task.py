#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict

from graphene import ResolveInfo

from silvaengine_utility import method_cache

from ..handlers.config import Config

from ..models.repositories import get_repo
from ..types.async_task import AsyncTaskListType, AsyncTaskType


def resolve_async_task(
    info: ResolveInfo, **kwargs: Dict[str, Any]
) -> AsyncTaskType | None:
    return get_repo("async_task").resolve_single(info, **kwargs)


@method_cache(
    ttl=Config.get_cache_ttl(),
    cache_name=Config.get_cache_name("queries", "async_task"),
    cache_enabled=Config.is_cache_enabled,
)
def resolve_async_task_list(
    info: ResolveInfo, **kwargs: Dict[str, Any]
) -> AsyncTaskListType | None:
    return get_repo("async_task").list(info, **kwargs)