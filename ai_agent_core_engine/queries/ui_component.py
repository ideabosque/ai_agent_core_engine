#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict

from graphene import ResolveInfo

from silvaengine_utility import method_cache

from ..handlers.config import Config

from ..models.repositories import get_repo
from ..types.ui_component import UIComponentListType, UIComponentType


def resolve_ui_component(
    info: ResolveInfo, **kwargs: Dict[str, Any]
) -> UIComponentType | None:
    return get_repo("ui_component").resolve_single(info, **kwargs)


@method_cache(
    ttl=Config.get_cache_ttl(),
    cache_name=Config.get_cache_name("queries", "ui_component"),
    cache_enabled=Config.is_cache_enabled,
)
def resolve_ui_component_list(
    info: ResolveInfo, **kwargs: Dict[str, Any]
) -> UIComponentListType | None:
    return get_repo("ui_component").list(info, **kwargs)