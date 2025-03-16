#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict

from graphene import ResolveInfo

from ..models import fine_tuning_message
from ..types.fine_tuning_message import FineTuningMessageListType, FineTuningMessageType


def resolve_fine_tuning_message(
    info: ResolveInfo, **kwargs: Dict[str, Any]
) -> FineTuningMessageType:
    return fine_tuning_message.resolve_fine_tuning_message(info, **kwargs)


def resolve_fine_tuning_message_list(
    info: ResolveInfo, **kwargs: Dict[str, Any]
) -> FineTuningMessageListType:
    return fine_tuning_message.resolve_fine_tuning_message_list(info, **kwargs)
