# -*- coding: utf-8 -*-
"""DynamoDB repository for tool_call entity."""
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict, Optional

from ...repositories.base import EntityRepository
from ._base import _normalize

from ...dynamodb import tool_call as _tool_call_mod


class ToolCallRepository(EntityRepository):
    """DynamoDB repository for tool_call entity."""

    @property
    def entity_type(self) -> str:
        return "tool_call"

    def get(self, **keys: Any) -> Optional[Dict[str, Any]]:
        thread_uuid = keys.get("thread_uuid")
        tool_call_uuid = keys.get("tool_call_uuid")
        if not thread_uuid or not tool_call_uuid:
            return None
        count = _tool_call_mod.get_tool_call_count(thread_uuid, tool_call_uuid)
        if count == 0:
            return None
        return _normalize(_tool_call_mod.get_tool_call(thread_uuid, tool_call_uuid))

    def count(self, **keys: Any) -> int:
        thread_uuid = keys.get("thread_uuid")
        tool_call_uuid = keys.get("tool_call_uuid")
        if not thread_uuid or not tool_call_uuid:
            return 0
        return _tool_call_mod.get_tool_call_count(thread_uuid, tool_call_uuid)

    def list(self, info: Any, **filters: Any) -> Any:
        return _tool_call_mod.resolve_tool_call_list(info, **filters)

    def insert_update(self, info: Any, **kwargs: Any) -> Optional[Dict[str, Any]]:
        return _tool_call_mod.insert_update_tool_call(info, **kwargs)

    def delete(self, info: Any, **kwargs: Any) -> bool:
        return _tool_call_mod.delete_tool_call(info, **kwargs)

    def get_type(self, info: Any, instance: Any) -> Any:
        return _tool_call_mod.get_tool_call_type(info, instance)

    def resolve_single(self, info: Any, **kwargs: Any) -> Any:
        return _tool_call_mod.resolve_tool_call(info, **kwargs)

    def get_by_run(self, run_uuid: str) -> Any:
        return _tool_call_mod.get_tool_calls_by_run(run_uuid)

    def get_by_thread(self, thread_uuid: str) -> Any:
        return _tool_call_mod.get_tool_calls_by_thread(thread_uuid)