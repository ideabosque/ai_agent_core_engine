# -*- coding: utf-8 -*-
"""PostgreSQL DataLoader for ToolCallModel records by thread_uuid (one-to-many).

Mirrors the DynamoDB ToolCallsByThreadLoader contract:
.load(thread_uuid) returns a Promise that resolves to a **list** of normalized
tool-call dicts for the given thread.
"""
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict, List, Optional

from .base import SafeDataLoader


class ToolCallsByThreadLoader(SafeDataLoader):
    """Batch loader for ToolCallModel keyed by thread_uuid (returns lists)."""

    def _batch_load_fn(
        self, keys: List[str]
    ) -> Dict[str, List[Dict[str, Any]]]:
        from ....handlers.config import Config
        from ...postgresql.tool_call import ToolCallModel
        from ...repositories.postgresql._base import _normalize

        unique_keys = list(dict.fromkeys(keys))

        session = Config.db_session()
        try:
            rows = (
                session.query(ToolCallModel)
                .filter(ToolCallModel.thread_uuid.in_(unique_keys))
                .order_by(ToolCallModel.created_at.desc())
                .all()
            )
        except Exception:
            session.rollback()
            raise

        key_map: Dict[str, List[Dict[str, Any]]] = {k: [] for k in unique_keys}
        for row in rows:
            key_map[row.thread_uuid].append(_normalize(row))

        return {key: key_map.get(key, []) for key in keys}


__all__ = ["ToolCallsByThreadLoader"]