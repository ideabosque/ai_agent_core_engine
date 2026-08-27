# -*- coding: utf-8 -*-
"""PostgreSQL DataLoader for RunModel records keyed by (thread_uuid, run_uuid).

Mirrors the DynamoDB RunLoader contract: .load((thread_uuid, run_uuid)) returns a
Promise that resolves to the normalized Run dict or None.
"""
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict, List, Optional

from .base import SafeDataLoader


class RunLoader(SafeDataLoader):
    """Batch loader for RunModel records keyed by (thread_uuid, run_uuid)."""

    def _batch_load_fn(self, keys: List[tuple]) -> Dict[tuple, Optional[Dict[str, Any]]]:
        from ....handlers.config import Config
        from ...postgresql.run import RunModel
        from ...repositories.postgresql._base import _normalize

        # keys is a list of (thread_uuid, run_uuid) tuples
        unique_keys = list(dict.fromkeys(keys))
        thread_uuids = set()
        run_uuids = set()
        for thread_uuid, run_uuid in unique_keys:
            thread_uuids.add(thread_uuid)
            run_uuids.add(run_uuid)

        session = Config.db_session()
        try:
            rows = (
                session.query(RunModel)
                .filter(
                    RunModel.thread_uuid.in_(thread_uuids),
                    RunModel.run_uuid.in_(run_uuids),
                )
                .all()
            )
        except Exception:
            session.rollback()
            raise

        key_map: Dict[tuple, Optional[Dict[str, Any]]] = {}
        for row in rows:
            key = (row.thread_uuid, row.run_uuid)
            key_map[key] = _normalize(row)

        return {key: key_map.get(key) for key in keys}


__all__ = ["RunLoader"]