#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict

from graphene import ResolveInfo

from silvaengine_utility import method_cache

from ..handlers.config import Config

from ..models.repositories import get_repo
from ..types.element import ElementListType, ElementType


def resolve_element(info: ResolveInfo, **kwargs: Dict[str, Any]) -> ElementType | None:
    return get_repo("element").resolve_single(info, **kwargs)


@method_cache(
    ttl=Config.get_cache_ttl(),
    cache_name=Config.get_cache_name("queries", "element"),
    cache_enabled=Config.is_cache_enabled,
)
def resolve_element_list(
    info: ResolveInfo, **kwargs: Dict[str, Any]
) -> ElementListType | None:
    return get_repo("element").list(info, **kwargs)