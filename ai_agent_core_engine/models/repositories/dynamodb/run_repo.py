# -*- coding: utf-8 -*-
"""DynamoDB repository for run entity."""
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict, Optional

from ...repositories.base import EntityRepository
from ._base import _normalize

from ...dynamodb import run as _run_mod


class RunRepository(EntityRepository):
    """DynamoDB repository for run entity."""

    @property
    def entity_type(self) -> str:
        return "run"

    def get(self, **keys: Any) -> Optional[Dict[str, Any]]:
        thread_uuid = keys.get("thread_uuid")
        run_uuid = keys.get("run_uuid")
        if not thread_uuid or not run_uuid:
            return None
        count = _run_mod.get_run_count(thread_uuid, run_uuid)
        if count == 0:
            return None
        return _normalize(_run_mod.get_run(thread_uuid, run_uuid))

    def count(self, **keys: Any) -> int:
        thread_uuid = keys.get("thread_uuid")
        run_uuid = keys.get("run_uuid")
        if not thread_uuid or not run_uuid:
            return 0
        return _run_mod.get_run_count(thread_uuid, run_uuid)

    def list(self, info: Any, **filters: Any) -> Any:
        return _run_mod.resolve_run_list(info, **filters)

    def insert_update(self, info: Any, **kwargs: Any) -> Optional[Dict[str, Any]]:
        return _run_mod.insert_update_run(info, **kwargs)

    def delete(self, info: Any, **kwargs: Any) -> bool:
        return _run_mod.delete_run(info, **kwargs)

    def get_type(self, info: Any, instance: Any) -> Any:
        return _run_mod.get_run_type(info, instance)

    def resolve_single(self, info: Any, **kwargs: Any) -> Any:
        return _run_mod.resolve_run(info, **kwargs)

    def get_by_thread(self, thread_uuid: str) -> Any:
        return _run_mod.get_runs_by_thread(thread_uuid)