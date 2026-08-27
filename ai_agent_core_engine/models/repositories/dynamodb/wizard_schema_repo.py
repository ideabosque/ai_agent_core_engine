# -*- coding: utf-8 -*-
"""DynamoDB repository for wizard_schema entity."""
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict, Optional

from ...repositories.base import EntityRepository
from ._base import _normalize

from ...dynamodb import wizard_schema as _wizard_schema_mod


class WizardSchemaRepository(EntityRepository):
    """DynamoDB repository for wizard_schema entity."""

    @property
    def entity_type(self) -> str:
        return "wizard_schema"

    def get(self, **keys: Any) -> Optional[Dict[str, Any]]:
        wizard_schema_type = keys.get("wizard_schema_type")
        wizard_schema_name = keys.get("wizard_schema_name")
        if not wizard_schema_type or not wizard_schema_name:
            return None
        count = _wizard_schema_mod.get_wizard_schema_count(
            wizard_schema_type, wizard_schema_name
        )
        if count == 0:
            return None
        return _normalize(
            _wizard_schema_mod.get_wizard_schema(wizard_schema_type, wizard_schema_name)
        )

    def count(self, **keys: Any) -> int:
        wizard_schema_type = keys.get("wizard_schema_type")
        wizard_schema_name = keys.get("wizard_schema_name")
        if not wizard_schema_type or not wizard_schema_name:
            return 0
        return _wizard_schema_mod.get_wizard_schema_count(
            wizard_schema_type, wizard_schema_name
        )

    def list(self, info: Any, **filters: Any) -> Any:
        return _wizard_schema_mod.resolve_wizard_schema_list(info, **filters)

    def insert_update(self, info: Any, **kwargs: Any) -> Optional[Dict[str, Any]]:
        return _wizard_schema_mod.insert_update_wizard_schema(info, **kwargs)

    def delete(self, info: Any, **kwargs: Any) -> bool:
        return _wizard_schema_mod.delete_wizard_schema(info, **kwargs)

    def get_type(self, info: Any, instance: Any) -> Any:
        return _wizard_schema_mod.get_wizard_schema_type(info, instance)

    def resolve_single(self, info: Any, **kwargs: Any) -> Any:
        return _wizard_schema_mod.resolve_wizard_schema(info, **kwargs)