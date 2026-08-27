# -*- coding: utf-8 -*-
"""PostgreSQL DataLoader for WizardModel records keyed by (partition_key, wizard_uuid).

Mirrors the DynamoDB WizardLoader contract:
.load((partition_key, wizard_uuid)) returns a Promise that resolves to the
normalized wizard dict or None.
"""
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict, List, Optional

from .base import SafeDataLoader


class WizardLoader(SafeDataLoader):
    """Batch loader for WizardModel keyed by (partition_key, wizard_uuid)."""

    def _batch_load_fn(
        self, keys: List[tuple]
    ) -> Dict[tuple, Optional[Dict[str, Any]]]:
        from ....handlers.config import Config
        from ...postgresql.wizard import WizardModel
        from ...repositories.postgresql._base import _normalize

        unique_keys = list(dict.fromkeys(keys))
        partition_keys = set()
        wizard_uuids = set()
        for pk, wu in unique_keys:
            partition_keys.add(pk)
            wizard_uuids.add(wu)

        session = Config.db_session()
        try:
            rows = (
                session.query(WizardModel)
                .filter(
                    WizardModel.partition_key.in_(partition_keys),
                    WizardModel.wizard_uuid.in_(wizard_uuids),
                )
                .all()
            )
        except Exception:
            session.rollback()
            raise

        key_map: Dict[tuple, Optional[Dict[str, Any]]] = {}
        for row in rows:
            key = (row.partition_key, row.wizard_uuid)
            key_map[key] = _normalize(row)

        return {key: key_map.get(key) for key in keys}


__all__ = ["WizardLoader"]