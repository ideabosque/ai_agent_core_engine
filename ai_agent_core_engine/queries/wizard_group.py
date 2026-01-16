#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict

from graphene import ResolveInfo

from silvaengine_utility import method_cache

from ..handlers.config import Config

from ..models import wizard_group
from ..types.wizard_group import WizardGroupListType, WizardGroupType


def resolve_wizard_group(
    info: ResolveInfo, **kwargs: Dict[str, Any]
) -> WizardGroupType | None:
    return wizard_group.resolve_wizard_group(info, **kwargs)


@method_cache(
    ttl=Config.get_cache_ttl(),
    cache_name=Config.get_cache_name("queries", "wizard_group"),
    cache_enabled=Config.is_cache_enabled,
)
def resolve_wizard_group_list(
    info: ResolveInfo, **kwargs: Dict[str, Any]
) -> WizardGroupListType | None:
    return wizard_group.resolve_wizard_group_list(info, **kwargs)