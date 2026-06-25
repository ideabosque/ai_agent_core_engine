#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict

from graphene import ResolveInfo

from silvaengine_utility import method_cache

from ..handlers.config import Config

from ..models.repositories import get_repo
from ..types.fine_tuning_message import FineTuningMessageListType, FineTuningMessageType


def resolve_fine_tuning_message(
    info: ResolveInfo, **kwargs: Dict[str, Any]
) -> FineTuningMessageType | None:
    return get_repo("fine_tuning_message").resolve_single(info, **kwargs)


@method_cache(
    ttl=Config.get_cache_ttl(),
    cache_name=Config.get_cache_name("queries", "fine_tuning_message"),
    cache_enabled=Config.is_cache_enabled,
)
def resolve_fine_tuning_message_list(
    info: ResolveInfo, **kwargs: Dict[str, Any]
) -> FineTuningMessageListType | None:
    return get_repo("fine_tuning_message").list(info, **kwargs)