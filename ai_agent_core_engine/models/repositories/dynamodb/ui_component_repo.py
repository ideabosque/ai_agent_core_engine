# -*- coding: utf-8 -*-
"""DynamoDB repository for ui_component entity."""
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict, Optional

from ...repositories.base import EntityRepository
from ._base import _normalize

from ...dynamodb import ui_component as _ui_component_mod


class UiComponentRepository(EntityRepository):
    """DynamoDB repository for ui_component entity."""

    @property
    def entity_type(self) -> str:
        return "ui_component"

    def get(self, **keys: Any) -> Optional[Dict[str, Any]]:
        ui_component_type = keys.get("ui_component_type")
        ui_component_uuid = keys.get("ui_component_uuid")
        if not ui_component_type or not ui_component_uuid:
            return None
        count = _ui_component_mod.get_ui_component_count(
            ui_component_type, ui_component_uuid
        )
        if count == 0:
            return None
        return _normalize(
            _ui_component_mod.get_ui_component(ui_component_type, ui_component_uuid)
        )

    def count(self, **keys: Any) -> int:
        ui_component_type = keys.get("ui_component_type")
        ui_component_uuid = keys.get("ui_component_uuid")
        if not ui_component_type or not ui_component_uuid:
            return 0
        return _ui_component_mod.get_ui_component_count(
            ui_component_type, ui_component_uuid
        )

    def list(self, info: Any, **filters: Any) -> Any:
        return _ui_component_mod.resolve_ui_component_list(info, **filters)

    def insert_update(self, info: Any, **kwargs: Any) -> Optional[Dict[str, Any]]:
        return _ui_component_mod.insert_update_ui_component(info, **kwargs)

    def delete(self, info: Any, **kwargs: Any) -> bool:
        return _ui_component_mod.delete_ui_component(info, **kwargs)

    def get_type(self, info: Any, instance: Any) -> Any:
        return _ui_component_mod.get_ui_component_type(info, instance)

    def resolve_single(self, info: Any, **kwargs: Any) -> Any:
        return _ui_component_mod.resolve_ui_component(info, **kwargs)