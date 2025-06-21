#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict

from graphene import ResolveInfo

from ..models import wizard
from ..types.wizard import WizardListType, WizardType


def resolve_wizard(info: ResolveInfo, **kwargs: Dict[str, Any]) -> WizardType:
    return wizard.resolve_wizard(info, **kwargs)


def resolve_wizard_list(info: ResolveInfo, **kwargs: Dict[str, Any]) -> WizardListType:
    return wizard.resolve_wizard_list(info, **kwargs)
