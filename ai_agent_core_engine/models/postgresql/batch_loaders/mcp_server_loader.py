# -*- coding: utf-8 -*-
"""PostgreSQL DataLoader for MCPServerModel records keyed by (partition_key, mcp_server_uuid).

Mirrors the DynamoDB McpServerLoader contract:
.load((partition_key, mcp_server_uuid)) returns a Promise that resolves to the
normalized MCP-server dict or None.
"""
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict, List, Optional

from .base import SafeDataLoader


class McpServerLoader(SafeDataLoader):
    """Batch loader for MCPServerModel keyed by (partition_key, mcp_server_uuid)."""

    def _batch_load_fn(
        self, keys: List[tuple]
    ) -> Dict[tuple, Optional[Dict[str, Any]]]:
        from ....handlers.config import Config
        from ...postgresql.mcp_server import MCPServerModel
        from ...repositories.postgresql._base import _normalize

        unique_keys = list(dict.fromkeys(keys))
        partition_keys = set()
        server_uuids = set()
        for pk, msu in unique_keys:
            partition_keys.add(pk)
            server_uuids.add(msu)

        session = Config.db_session()
        try:
            rows = (
                session.query(MCPServerModel)
                .filter(
                    MCPServerModel.partition_key.in_(partition_keys),
                    MCPServerModel.mcp_server_uuid.in_(server_uuids),
                )
                .all()
            )
        except Exception:
            session.rollback()
            raise

        key_map: Dict[tuple, Optional[Dict[str, Any]]] = {}
        for row in rows:
            key = (row.partition_key, row.mcp_server_uuid)
            key_map[key] = _normalize(row)

        return {key: key_map.get(key) for key in keys}


__all__ = ["McpServerLoader"]