# -*- coding: utf-8 -*-
"""PostgreSQL DataLoader for PromptTemplateModel records keyed by (partition_key, prompt_uuid).

Mirrors the DynamoDB PromptTemplateLoader contract:
.load((partition_key, prompt_uuid)) returns a Promise that resolves to the
**active** prompt-template dict or None.

Only the active version (status = 'active') is returned, matching the
DynamoDB loader which calls ``_get_active_prompt_template``.
"""
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict, List, Optional

from .base import SafeDataLoader


class PromptTemplateLoader(SafeDataLoader):
    """Batch loader for PromptTemplateModel keyed by (partition_key, prompt_uuid), active only."""

    def _batch_load_fn(
        self, keys: List[tuple]
    ) -> Dict[tuple, Optional[Dict[str, Any]]]:
        from ....handlers.config import Config
        from ...postgresql.prompt_template import PromptTemplateModel
        from ...repositories.postgresql._base import _normalize

        unique_keys = list(dict.fromkeys(keys))
        partition_keys = set()
        prompt_uuids = set()
        for pk, pu in unique_keys:
            partition_keys.add(pk)
            prompt_uuids.add(pu)

        session = Config.db_session()
        try:
            rows = (
                session.query(PromptTemplateModel)
                .filter(
                    PromptTemplateModel.partition_key.in_(partition_keys),
                    PromptTemplateModel.prompt_uuid.in_(prompt_uuids),
                    PromptTemplateModel.status == "active",
                )
                .all()
            )
        except Exception:
            session.rollback()
            raise

        # Map (partition_key, prompt_uuid) -> normalized dict.
        # Multiple versions may exist; pick the first active one per key.
        key_map: Dict[tuple, Optional[Dict[str, Any]]] = {}
        for row in rows:
            key = (row.partition_key, row.prompt_uuid)
            if key not in key_map:
                key_map[key] = _normalize(row)

        return {key: key_map.get(key) for key in keys}


__all__ = ["PromptTemplateLoader"]