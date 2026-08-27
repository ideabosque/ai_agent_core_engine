# -*- coding: utf-8 -*-
"""DynamoDB repository for message entity."""
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict, Optional

from ...repositories.base import EntityRepository
from ._base import _normalize

from ...dynamodb import message as _message_mod


class MessageRepository(EntityRepository):
    """DynamoDB repository for message entity."""

    @property
    def entity_type(self) -> str:
        return "message"

    def get(self, **keys: Any) -> Optional[Dict[str, Any]]:
        thread_uuid = keys.get("thread_uuid")
        message_uuid = keys.get("message_uuid")
        if not thread_uuid or not message_uuid:
            return None
        count = _message_mod.get_message_count(thread_uuid, message_uuid)
        if count == 0:
            return None
        return _normalize(_message_mod.get_message(thread_uuid, message_uuid))

    def count(self, **keys: Any) -> int:
        thread_uuid = keys.get("thread_uuid")
        message_uuid = keys.get("message_uuid")
        if not thread_uuid or not message_uuid:
            return 0
        return _message_mod.get_message_count(thread_uuid, message_uuid)

    def list(self, info: Any, **filters: Any) -> Any:
        return _message_mod.resolve_message_list(info, **filters)

    def insert_update(self, info: Any, **kwargs: Any) -> Optional[Dict[str, Any]]:
        return _message_mod.insert_update_message(info, **kwargs)

    def delete(self, info: Any, **kwargs: Any) -> bool:
        return _message_mod.delete_message(info, **kwargs)

    def get_type(self, info: Any, instance: Any) -> Any:
        return _message_mod.get_message_type(info, instance)

    def resolve_single(self, info: Any, **kwargs: Any) -> Any:
        return _message_mod.resolve_message(info, **kwargs)

    def get_by_thread(self, thread_uuid: str) -> Any:
        return _message_mod.get_messages_by_thread(thread_uuid)