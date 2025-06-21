#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict

from graphene import ResolveInfo

from ..models import wizard_group
from ..types.wizard_group import WizardGroupListType, WizardGroupType


def resolve_wizard_group(info: ResolveInfo, **kwargs: Dict[str, Any]) -> WizardGroupType:
    return wizard_group.resolve_wizard_group(info, **kwargs)


def resolve_wizard_group_list(info: ResolveInfo, **kwargs: Dict[str, Any]) -> WizardGroupListType:
    return wizard_group.resolve_wizard_group_list(info, **kwargs)