#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict

from graphene import ResolveInfo

from ..models import async_task
from ..types.async_task import AsyncTaskListType, AsyncTaskType


def resolve_async_task(info: ResolveInfo, **kwargs: Dict[str, Any]) -> AsyncTaskType:
    return async_task.resolve_async_task(info, **kwargs)


def resolve_async_task_list(
    info: ResolveInfo, **kwargs: Dict[str, Any]
) -> AsyncTaskListType:
    return async_task.resolve_async_task_list(info, **kwargs)
