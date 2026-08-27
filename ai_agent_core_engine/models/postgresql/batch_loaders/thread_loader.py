# -*- coding: utf-8 -*-
"""PostgreSQL DataLoader for ThreadModel records keyed by (partition_key, thread_uuid).

Mirrors the DynamoDB ThreadLoader contract:
.load((partition_key, thread_uuid)) returns a Promise that resolves to the
normalized thread dict or None.
"""
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict, List, Optional

from .base import SafeDataLoader


class ThreadLoader(SafeDataLoader):
    """Batch loader for ThreadModel keyed by (partition_key, thread_uuid)."""

    def _batch_load_fn(
        self, keys: List[tuple]
    ) -> Dict[tuple, Optional[Dict[str, Any]]]:
        from ....handlers.config import Config
        from ...postgresql.thread import ThreadModel
        from ...repositories.postgresql._base import _normalize

        unique_keys = list(dict.fromkeys(keys))
        partition_keys = set()
        thread_uuids = set()
        for pk, tu in unique_keys:
            partition_keys.add(pk)
            thread_uuids.add(tu)

        session = Config.db_session()
        try:
            rows = (
                session.query(ThreadModel)
                .filter(
                    ThreadModel.partition_key.in_(partition_keys),
                    ThreadModel.thread_uuid.in_(thread_uuids),
                )
                .all()
            )
        except Exception:
            session.rollback()
            raise

        key_map: Dict[tuple, Optional[Dict[str, Any]]] = {}
        for row in rows:
            key = (row.partition_key, row.thread_uuid)
            key_map[key] = _normalize(row)

        return {key: key_map.get(key) for key in keys}


__all__ = ["ThreadLoader"]