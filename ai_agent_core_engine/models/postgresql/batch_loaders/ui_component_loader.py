# -*- coding: utf-8 -*-
"""PostgreSQL DataLoader for UIComponentModel records keyed by (ui_component_type, ui_component_uuid).

Mirrors the DynamoDB UIComponentLoader contract:
.load((ui_component_type, ui_component_uuid)) returns a Promise that resolves
to the normalized UI-component dict or None.
"""
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict, List, Optional

from .base import SafeDataLoader


class UiComponentLoader(SafeDataLoader):
    """Batch loader for UIComponentModel keyed by (ui_component_type, ui_component_uuid)."""

    def _batch_load_fn(
        self, keys: List[tuple]
    ) -> Dict[tuple, Optional[Dict[str, Any]]]:
        from ....handlers.config import Config
        from ...postgresql.ui_component import UIComponentModel
        from ...repositories.postgresql._base import _normalize

        unique_keys = list(dict.fromkeys(keys))
        component_types = set()
        component_uuids = set()
        for ct, cu in unique_keys:
            component_types.add(ct)
            component_uuids.add(cu)

        session = Config.db_session()
        try:
            rows = (
                session.query(UIComponentModel)
                .filter(
                    UIComponentModel.ui_component_type.in_(component_types),
                    UIComponentModel.ui_component_uuid.in_(component_uuids),
                )
                .all()
            )
        except Exception:
            session.rollback()
            raise

        key_map: Dict[tuple, Optional[Dict[str, Any]]] = {}
        for row in rows:
            key = (row.ui_component_type, row.ui_component_uuid)
            key_map[key] = _normalize(row)

        return {key: key_map.get(key) for key in keys}


__all__ = ["UiComponentLoader"]