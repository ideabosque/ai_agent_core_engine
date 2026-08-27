# -*- coding: utf-8 -*-
"""PostgreSQL DataLoader for FlowSnippetModel records keyed by (partition_key, flow_snippet_version_uuid).

Mirrors the DynamoDB FlowSnippetLoader contract:
.load((partition_key, flow_snippet_version_uuid)) returns a Promise that
resolves to the normalized flow snippet dict or None.
"""
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict, List, Optional

from .base import SafeDataLoader


class FlowSnippetLoader(SafeDataLoader):
    """Batch loader for FlowSnippetModel keyed by (partition_key, flow_snippet_version_uuid)."""

    def _batch_load_fn(
        self, keys: List[tuple]
    ) -> Dict[tuple, Optional[Dict[str, Any]]]:
        from ....handlers.config import Config
        from ...postgresql.flow_snippet import FlowSnippetModel
        from ...repositories.postgresql._base import _normalize

        unique_keys = list(dict.fromkeys(keys))
        partition_keys = set()
        version_uuids = set()
        for pk, fsv in unique_keys:
            partition_keys.add(pk)
            version_uuids.add(fsv)

        session = Config.db_session()
        try:
            rows = (
                session.query(FlowSnippetModel)
                .filter(
                    FlowSnippetModel.partition_key.in_(partition_keys),
                    FlowSnippetModel.flow_snippet_version_uuid.in_(version_uuids),
                )
                .all()
            )
        except Exception:
            session.rollback()
            raise

        key_map: Dict[tuple, Optional[Dict[str, Any]]] = {}
        for row in rows:
            key = (row.partition_key, row.flow_snippet_version_uuid)
            key_map[key] = _normalize(row)

        return {key: key_map.get(key) for key in keys}


__all__ = ["FlowSnippetLoader"]