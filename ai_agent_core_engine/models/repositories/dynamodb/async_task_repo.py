# -*- coding: utf-8 -*-
"""DynamoDB repository for async_task entity."""
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict, Optional

from ...repositories.base import EntityRepository
from ._base import _normalize

from ...dynamodb import async_task as _async_task_mod


class AsyncTaskRepository(EntityRepository):
    """DynamoDB repository for async_task entity."""

    @property
    def entity_type(self) -> str:
        return "async_task"

    def get(self, **keys: Any) -> Optional[Dict[str, Any]]:
        function_name = keys.get("function_name")
        async_task_uuid = keys.get("async_task_uuid")
        if not function_name or not async_task_uuid:
            return None
        count = _async_task_mod.get_async_task_count(function_name, async_task_uuid)
        if count == 0:
            return None
        return _normalize(_async_task_mod.get_async_task(function_name, async_task_uuid))

    def count(self, **keys: Any) -> int:
        function_name = keys.get("function_name")
        async_task_uuid = keys.get("async_task_uuid")
        if not function_name or not async_task_uuid:
            return 0
        return _async_task_mod.get_async_task_count(function_name, async_task_uuid)

    def list(self, info: Any, **filters: Any) -> Any:
        return _async_task_mod.resolve_async_task_list(info, **filters)

    def insert_update(self, info: Any, **kwargs: Any) -> Optional[Dict[str, Any]]:
        return _async_task_mod.insert_update_async_task(info, **kwargs)

    def delete(self, info: Any, **kwargs: Any) -> bool:
        return _async_task_mod.delete_async_task(info, **kwargs)

    def get_type(self, info: Any, instance: Any) -> Any:
        return _async_task_mod.get_async_task_type(info, instance)

    def resolve_single(self, info: Any, **kwargs: Any) -> Any:
        return _async_task_mod.resolve_async_task(info, **kwargs)