# -*- coding: utf-8 -*-
"""PostgreSQL DataLoader for AgentModel records keyed by (partition_key, agent_uuid).

Mirrors the DynamoDB AgentLoader contract: .load((partition_key, agent_uuid))
returns a Promise that resolves to the normalized agent dict or None.

Only the **active** agent version is returned (status = 'active').
"""
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict, List, Optional

from .base import SafeDataLoader


class AgentLoader(SafeDataLoader):
    """Batch loader for AgentModel records keyed by (partition_key, agent_uuid)."""

    def _batch_load_fn(
        self, keys: List[tuple]
    ) -> Dict[tuple, Optional[Dict[str, Any]]]:
        from ....handlers.config import Config
        from ...postgresql.agent import AgentModel
        from ...repositories.postgresql._base import _normalize

        unique_keys = list(dict.fromkeys(keys))
        partition_keys = set()
        agent_uuids = set()
        for pk, au in unique_keys:
            partition_keys.add(pk)
            agent_uuids.add(au)

        session = Config.db_session()
        try:
            rows = (
                session.query(AgentModel)
                .filter(
                    AgentModel.partition_key.in_(partition_keys),
                    AgentModel.agent_uuid.in_(agent_uuids),
                    AgentModel.status == "active",
                )
                .all()
            )
        except Exception:
            session.rollback()
            raise

        # Map (partition_key, agent_uuid) -> normalized dict.
        # Multiple versions may exist; pick the first active one per key.
        key_map: Dict[tuple, Optional[Dict[str, Any]]] = {}
        for row in rows:
            key = (row.partition_key, row.agent_uuid)
            if key not in key_map:
                key_map[key] = _normalize(row)

        return {key: key_map.get(key) for key in keys}


__all__ = ["AgentLoader"]