#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict

from graphene import ResolveInfo

from ..models import message
from ..types.message import MessageListType, MessageType


def resolve_message(info: ResolveInfo, **kwargs: Dict[str, Any]) -> MessageType:
    return message.resolve_message(info, **kwargs)


def resolve_message_list(
    info: ResolveInfo, **kwargs: Dict[str, Any]
) -> MessageListType:
    return message.resolve_message_list(info, **kwargs)
