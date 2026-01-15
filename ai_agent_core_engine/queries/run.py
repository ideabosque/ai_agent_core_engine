#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict

from graphene import ResolveInfo

from silvaengine_utility import method_cache

from ..handlers.config import Config

from ..models import run
from ..types.run import RunListType, RunType


def resolve_run(info: ResolveInfo, **kwargs: Dict[str, Any]) -> RunType | None:
    return run.resolve_run(info, **kwargs)


@method_cache(
    ttl=Config.get_cache_ttl(),
    cache_name=Config.get_cache_name("queries", "run"),
    cache_enabled=Config.is_cache_enabled,
)
def resolve_run_list(
    info: ResolveInfo, **kwargs: Dict[str, Any]
) -> RunListType | None:
    return run.resolve_run_list(info, **kwargs)
