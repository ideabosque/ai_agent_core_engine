#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict

from graphene import ResolveInfo

from ..models import run
from ..types.run import RunListType, RunType


def resolve_run(info: ResolveInfo, **kwargs: Dict[str, Any]) -> RunType:
    return run.resolve_run(info, **kwargs)


def resolve_run_list(info: ResolveInfo, **kwargs: Dict[str, Any]) -> RunListType:
    return run.resolve_run_list(info, **kwargs)
