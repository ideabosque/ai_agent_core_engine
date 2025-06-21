#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict

from graphene import ResolveInfo

from ..models import ui_component
from ..types.ui_component import UIComponentListType, UIComponentType


def resolve_ui_component(info: ResolveInfo, **kwargs: Dict[str, Any]) -> UIComponentType:
    return ui_component.resolve_ui_component(info, **kwargs)


def resolve_ui_component_list(info: ResolveInfo, **kwargs: Dict[str, Any]) -> UIComponentListType:
    return ui_component.resolve_ui_component_list(info, **kwargs)