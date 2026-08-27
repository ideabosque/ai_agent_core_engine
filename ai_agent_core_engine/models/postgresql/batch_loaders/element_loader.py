# -*- coding: utf-8 -*-
"""PostgreSQL DataLoader for ElementModel records keyed by (partition_key, element_uuid).

Mirrors the DynamoDB ElementLoader contract: .load((partition_key, element_uuid))
returns a Promise that resolves to the normalized element dict or None.
"""
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict, List, Optional

from .base import SafeDataLoader


class ElementLoader(SafeDataLoader):
    """Batch loader for ElementModel records keyed by (partition_key, element_uuid)."""

    def _batch_load_fn(
        self, keys: List[tuple]
    ) -> Dict[tuple, Optional[Dict[str, Any]]]:
        from ....handlers.config import Config
        from ...postgresql.element import ElementModel
        from ...repositories.postgresql._base import _normalize

        unique_keys = list(dict.fromkeys(keys))
        partition_keys = set()
        element_uuids = set()
        for pk, eu in unique_keys:
            partition_keys.add(pk)
            element_uuids.add(eu)

        session = Config.db_session()
        try:
            rows = (
                session.query(ElementModel)
                .filter(
                    ElementModel.partition_key.in_(partition_keys),
                    ElementModel.element_uuid.in_(element_uuids),
                )
                .all()
            )
        except Exception:
            session.rollback()
            raise

        key_map: Dict[tuple, Optional[Dict[str, Any]]] = {}
        for row in rows:
            key = (row.partition_key, row.element_uuid)
            key_map[key] = _normalize(row)

        return {key: key_map.get(key) for key in keys}


__all__ = ["ElementLoader"]