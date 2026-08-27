# -*- coding: utf-8 -*-
"""PostgreSQL DataLoader for WizardGroupModel records keyed by (partition_key, wizard_group_uuid).

Mirrors the DynamoDB WizardGroupLoader contract:
.load((partition_key, wizard_group_uuid)) returns a Promise that resolves to
the normalized wizard-group dict or None.
"""
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict, List, Optional

from .base import SafeDataLoader


class WizardGroupLoader(SafeDataLoader):
    """Batch loader for WizardGroupModel keyed by (partition_key, wizard_group_uuid)."""

    def _batch_load_fn(
        self, keys: List[tuple]
    ) -> Dict[tuple, Optional[Dict[str, Any]]]:
        from ....handlers.config import Config
        from ...postgresql.wizard_group import WizardGroupModel
        from ...repositories.postgresql._base import _normalize

        unique_keys = list(dict.fromkeys(keys))
        partition_keys = set()
        group_uuids = set()
        for pk, wgu in unique_keys:
            partition_keys.add(pk)
            group_uuids.add(wgu)

        session = Config.db_session()
        try:
            rows = (
                session.query(WizardGroupModel)
                .filter(
                    WizardGroupModel.partition_key.in_(partition_keys),
                    WizardGroupModel.wizard_group_uuid.in_(group_uuids),
                )
                .all()
            )
        except Exception:
            session.rollback()
            raise

        key_map: Dict[tuple, Optional[Dict[str, Any]]] = {}
        for row in rows:
            key = (row.partition_key, row.wizard_group_uuid)
            key_map[key] = _normalize(row)

        return {key: key_map.get(key) for key in keys}


__all__ = ["WizardGroupLoader"]