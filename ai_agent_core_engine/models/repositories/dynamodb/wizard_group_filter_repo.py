# -*- coding: utf-8 -*-
"""DynamoDB repository for wizard_group_filter entity."""
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict, Optional

from ...repositories.base import EntityRepository
from ._base import _normalize

from ...dynamodb import wizard_group_filter as _wizard_group_filter_mod


class WizardGroupFilterRepository(EntityRepository):
    """DynamoDB repository for wizard_group_filter entity."""

    @property
    def entity_type(self) -> str:
        return "wizard_group_filter"

    def get(self, **keys: Any) -> Optional[Dict[str, Any]]:
        partition_key = keys.get("partition_key")
        wizard_group_filter_uuid = keys.get("wizard_group_filter_uuid")
        if not partition_key or not wizard_group_filter_uuid:
            return None
        count = _wizard_group_filter_mod.get_wizard_group_filter_count(
            partition_key, wizard_group_filter_uuid
        )
        if count == 0:
            return None
        return _normalize(
            _wizard_group_filter_mod.get_wizard_group_filter(
                partition_key, wizard_group_filter_uuid
            )
        )

    def count(self, **keys: Any) -> int:
        partition_key = keys.get("partition_key")
        wizard_group_filter_uuid = keys.get("wizard_group_filter_uuid")
        if not partition_key or not wizard_group_filter_uuid:
            return 0
        return _wizard_group_filter_mod.get_wizard_group_filter_count(
            partition_key, wizard_group_filter_uuid
        )

    def list(self, info: Any, **filters: Any) -> Any:
        return _wizard_group_filter_mod.resolve_wizard_group_filter_list(info, **filters)

    def insert_update(self, info: Any, **kwargs: Any) -> Optional[Dict[str, Any]]:
        return _wizard_group_filter_mod.insert_update_wizard_group_filter(
            info, **kwargs
        )

    def delete(self, info: Any, **kwargs: Any) -> bool:
        return _wizard_group_filter_mod.delete_wizard_group_filter(info, **kwargs)

    def get_type(self, info: Any, instance: Any) -> Any:
        return _wizard_group_filter_mod.get_wizard_group_filter_type(info, instance)

    def resolve_single(self, info: Any, **kwargs: Any) -> Any:
        return _wizard_group_filter_mod.resolve_wizard_group_filter(info, **kwargs)