#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict

from graphene import ResolveInfo

from silvaengine_utility import method_cache

from ..handlers.config import Config

from ..models import wizard_schema
from ..types.wizard_schema import WizardSchemaListType, WizardSchemaType


def resolve_wizard_schema(info: ResolveInfo, **kwargs: Dict[str, Any]) -> WizardSchemaType:
    return wizard_schema.resolve_wizard_schema(info, **kwargs)


@method_cache(ttl=Config.get_cache_ttl(), cache_name=Config.get_cache_name('queries', 'wizard_schema'))
def resolve_wizard_schema_list(info: ResolveInfo, **kwargs: Dict[str, Any]) -> WizardSchemaListType:
    return wizard_schema.resolve_wizard_schema_list(info, **kwargs)
