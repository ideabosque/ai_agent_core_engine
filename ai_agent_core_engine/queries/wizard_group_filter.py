#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict

from graphene import ResolveInfo

from silvaengine_utility import method_cache

from ..handlers.config import Config
from ..models import wizard_group_filter
from ..types.wizard_group_filter import WizardGroupFilterListType, WizardGroupFilterType


def resolve_wizard_group_filter(
    info: ResolveInfo, **kwargs: Dict[str, Any]
) -> WizardGroupFilterType:
    return wizard_group_filter.resolve_wizard_group_filter(info, **kwargs)


@method_cache(
    ttl=Config.get_cache_ttl(),
    cache_name=Config.get_cache_name("queries", "wizard_group_filter"),
)
def resolve_wizard_group_filter_list(
    info: ResolveInfo, **kwargs: Dict[str, Any]
) -> WizardGroupFilterListType:
    return wizard_group_filter.resolve_wizard_group_filter_list(info, **kwargs)
