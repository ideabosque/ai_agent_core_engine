#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict

from graphene import ResolveInfo

from silvaengine_utility import method_cache

from ..handlers.config import Config

from ..models import wizard
from ..types.wizard import WizardListType, WizardType


def resolve_wizard(info: ResolveInfo, **kwargs: Dict[str, Any]) -> WizardType | None:
    return wizard.resolve_wizard(info, **kwargs)


@method_cache(
    ttl=Config.get_cache_ttl(),
    cache_name=Config.get_cache_name("queries", "wizard"),
    cache_enabled=Config.is_cache_enabled,
)
def resolve_wizard_list(
    info: ResolveInfo, **kwargs: Dict[str, Any]
) -> WizardListType | None:
    return wizard.resolve_wizard_list(info, **kwargs)
