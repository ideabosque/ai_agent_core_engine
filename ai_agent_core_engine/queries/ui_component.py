#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict

from graphene import ResolveInfo

from silvaengine_utility import method_cache

from ..handlers.config import Config

from ..models import ui_component
from ..types.ui_component import UIComponentListType, UIComponentType


def resolve_ui_component(info: ResolveInfo, **kwargs: Dict[str, Any]) -> UIComponentType:
    return ui_component.resolve_ui_component(info, **kwargs)


@method_cache(ttl=Config.get_cache_ttl(), cache_name=Config.get_cache_name('queries', 'ui_component'))
def resolve_ui_component_list(info: ResolveInfo, **kwargs: Dict[str, Any]) -> UIComponentListType:
    return ui_component.resolve_ui_component_list(info, **kwargs)