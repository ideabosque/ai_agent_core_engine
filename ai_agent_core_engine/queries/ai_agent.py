#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict

from graphene import ResolveInfo

from ..handlers import ai_agent
from ..types.ai_agent import AskModelType, UploadedFileType


def resolve_ask_model(info: ResolveInfo, **kwargs: Dict[str, Any]) -> AskModelType:
    return ai_agent.ask_model(info, **kwargs)


def resolve_uploaded_file(
    info: ResolveInfo, **kwargs: Dict[str, Any]
) -> UploadedFileType:
    return ai_agent.get_file(info, **kwargs)
