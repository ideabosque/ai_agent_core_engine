# -*- coding: utf-8 -*-
"""PostgreSQL DataLoader for ToolCallModel records by (thread_uuid, run_uuid) (one-to-many).

Mirrors the DynamoDB ToolCallsByRunLoader contract:
.load((thread_uuid, run_uuid)) returns a Promise that resolves to a **list** of
normalized tool-call dicts for the given run.
"""
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict, List, Optional

from .base import SafeDataLoader


class ToolCallsByRunLoader(SafeDataLoader):
    """Batch loader for ToolCallModel keyed by (thread_uuid, run_uuid) (returns lists)."""

    def _batch_load_fn(
        self, keys: List[tuple]
    ) -> Dict[tuple, List[Dict[str, Any]]]:
        from ....handlers.config import Config
        from ...postgresql.tool_call import ToolCallModel
        from ...repositories.postgresql._base import _normalize

        unique_keys = list(dict.fromkeys(keys))
        thread_uuids = set()
        run_uuids = set()
        for tu, ru in unique_keys:
            thread_uuids.add(tu)
            run_uuids.add(ru)

        session = Config.db_session()
        try:
            rows = (
                session.query(ToolCallModel)
                .filter(
                    ToolCallModel.thread_uuid.in_(thread_uuids),
                    ToolCallModel.run_uuid.in_(run_uuids),
                )
                .order_by(ToolCallModel.created_at.desc())
                .all()
            )
        except Exception:
            session.rollback()
            raise

        key_map: Dict[tuple, List[Dict[str, Any]]] = {k: [] for k in unique_keys}
        for row in rows:
            key = (row.thread_uuid, row.run_uuid)
            if key in key_map:
                key_map[key].append(_normalize(row))

        return {key: key_map.get(key, []) for key in keys}


__all__ = ["ToolCallsByRunLoader"]