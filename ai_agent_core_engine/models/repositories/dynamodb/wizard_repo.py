# -*- coding: utf-8 -*-
"""DynamoDB repository for wizard entity."""
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict, Optional

from ...repositories.base import EntityRepository
from ._base import _normalize

from ...dynamodb import wizard as _wizard_mod


class WizardRepository(EntityRepository):
    """DynamoDB repository for wizard entity."""

    @property
    def entity_type(self) -> str:
        return "wizard"

    def get(self, **keys: Any) -> Optional[Dict[str, Any]]:
        partition_key = keys.get("partition_key")
        wizard_uuid = keys.get("wizard_uuid")
        if not partition_key or not wizard_uuid:
            return None
        count = _wizard_mod.get_wizard_count(partition_key, wizard_uuid)
        if count == 0:
            return None
        return _normalize(_wizard_mod.get_wizard(partition_key, wizard_uuid))

    def count(self, **keys: Any) -> int:
        partition_key = keys.get("partition_key")
        wizard_uuid = keys.get("wizard_uuid")
        if not partition_key or not wizard_uuid:
            return 0
        return _wizard_mod.get_wizard_count(partition_key, wizard_uuid)

    def list(self, info: Any, **filters: Any) -> Any:
        return _wizard_mod.resolve_wizard_list(info, **filters)

    def insert_update(self, info: Any, **kwargs: Any) -> Optional[Dict[str, Any]]:
        return _wizard_mod.insert_update_wizard(info, **kwargs)

    def delete(self, info: Any, **kwargs: Any) -> bool:
        return _wizard_mod.delete_wizard(info, **kwargs)

    def get_type(self, info: Any, instance: Any) -> Any:
        return _wizard_mod.get_wizard_type(info, instance)

    def resolve_single(self, info: Any, **kwargs: Any) -> Any:
        return _wizard_mod.resolve_wizard(info, **kwargs)