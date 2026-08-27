# -*- coding: utf-8 -*-
"""DynamoDB repository for thread entity."""
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict, Optional

from ...repositories.base import EntityRepository
from ._base import _normalize

from ...dynamodb import thread as _thread_mod


class ThreadRepository(EntityRepository):
    """DynamoDB repository for thread entity."""

    @property
    def entity_type(self) -> str:
        return "thread"

    def get(self, **keys: Any) -> Optional[Dict[str, Any]]:
        partition_key = keys.get("partition_key")
        thread_uuid = keys.get("thread_uuid")
        if not partition_key or not thread_uuid:
            return None
        count = _thread_mod.get_thread_count(partition_key, thread_uuid)
        if count == 0:
            return None
        return _normalize(_thread_mod.get_thread(partition_key, thread_uuid))

    def count(self, **keys: Any) -> int:
        partition_key = keys.get("partition_key")
        thread_uuid = keys.get("thread_uuid")
        if not partition_key or not thread_uuid:
            return 0
        return _thread_mod.get_thread_count(partition_key, thread_uuid)

    def list(self, info: Any, **filters: Any) -> Any:
        return _thread_mod.resolve_thread_list(info, **filters)

    def insert_update(self, info: Any, **kwargs: Any) -> Optional[Dict[str, Any]]:
        return _thread_mod.insert_thread(info, **kwargs)

    def delete(self, info: Any, **kwargs: Any) -> bool:
        return _thread_mod.delete_thread(info, **kwargs)

    def get_type(self, info: Any, instance: Any) -> Any:
        return _thread_mod.get_thread_type(info, instance)

    def resolve_single(self, info: Any, **kwargs: Any) -> Any:
        return _thread_mod.resolve_thread(info, **kwargs)