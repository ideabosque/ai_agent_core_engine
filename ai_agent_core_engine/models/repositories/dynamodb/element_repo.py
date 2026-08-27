# -*- coding: utf-8 -*-
"""DynamoDB repository for element entity."""
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict, Optional

from ...repositories.base import EntityRepository
from ._base import _normalize

from ...dynamodb import element as _element_mod


class ElementRepository(EntityRepository):
    """DynamoDB repository for element entity."""

    @property
    def entity_type(self) -> str:
        return "element"

    def get(self, **keys: Any) -> Optional[Dict[str, Any]]:
        partition_key = keys.get("partition_key")
        element_uuid = keys.get("element_uuid")
        if not partition_key or not element_uuid:
            return None
        count = _element_mod.get_element_count(partition_key, element_uuid)
        if count == 0:
            return None
        return _normalize(_element_mod.get_element(partition_key, element_uuid))

    def count(self, **keys: Any) -> int:
        partition_key = keys.get("partition_key")
        element_uuid = keys.get("element_uuid")
        if not partition_key or not element_uuid:
            return 0
        return _element_mod.get_element_count(partition_key, element_uuid)

    def list(self, info: Any, **filters: Any) -> Any:
        return _element_mod.resolve_element_list(info, **filters)

    def insert_update(self, info: Any, **kwargs: Any) -> Optional[Dict[str, Any]]:
        return _element_mod.insert_update_element(info, **kwargs)

    def delete(self, info: Any, **kwargs: Any) -> bool:
        return _element_mod.delete_element(info, **kwargs)

    def get_type(self, info: Any, instance: Any) -> Any:
        return _element_mod.get_element_type(info, instance)

    def resolve_single(self, info: Any, **kwargs: Any) -> Any:
        return _element_mod.resolve_element(info, **kwargs)