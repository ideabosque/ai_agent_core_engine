#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict

from graphene import ResolveInfo

from ..models import element
from ..types.element import ElementListType, ElementType


def resolve_element(info: ResolveInfo, **kwargs: Dict[str, Any]) -> ElementType:
    return element.resolve_element(info, **kwargs)


def resolve_element_list(info: ResolveInfo, **kwargs: Dict[str, Any]) -> ElementListType:
    return element.resolve_element_list(info, **kwargs)