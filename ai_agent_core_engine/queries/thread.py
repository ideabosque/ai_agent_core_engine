#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict

from graphene import ResolveInfo

from silvaengine_utility import method_cache

from ..handlers.config import Config

from ..models.repositories import get_repo
from ..types.thread import ThreadListType, ThreadType


def resolve_thread(info: ResolveInfo, **kwargs: Dict[str, Any]) -> ThreadType | None:
    return get_repo("thread").resolve_single(info, **kwargs)


@method_cache(
    ttl=Config.get_cache_ttl(),
    cache_name=Config.get_cache_name("queries", "thread"),
    cache_enabled=Config.is_cache_enabled,
)
def resolve_thread_list(
    info: ResolveInfo, **kwargs: Dict[str, Any]
) -> ThreadListType | None:
    return get_repo("thread").list(info, **kwargs)