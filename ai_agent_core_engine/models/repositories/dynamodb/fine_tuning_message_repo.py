# -*- coding: utf-8 -*-
"""DynamoDB repository for fine_tuning_message entity."""
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict, Optional

from ...repositories.base import EntityRepository
from ._base import _normalize

from ...dynamodb import fine_tuning_message as _fine_tuning_message_mod


class FineTuningMessageRepository(EntityRepository):
    """DynamoDB repository for fine_tuning_message entity."""

    @property
    def entity_type(self) -> str:
        return "fine_tuning_message"

    def get(self, **keys: Any) -> Optional[Dict[str, Any]]:
        agent_uuid = keys.get("agent_uuid")
        message_uuid = keys.get("message_uuid")
        if not agent_uuid or not message_uuid:
            return None
        count = _fine_tuning_message_mod.get_fine_tuning_message_count(
            agent_uuid, message_uuid
        )
        if count == 0:
            return None
        return _normalize(
            _fine_tuning_message_mod.get_fine_tuning_message(agent_uuid, message_uuid)
        )

    def count(self, **keys: Any) -> int:
        agent_uuid = keys.get("agent_uuid")
        message_uuid = keys.get("message_uuid")
        if not agent_uuid or not message_uuid:
            return 0
        return _fine_tuning_message_mod.get_fine_tuning_message_count(
            agent_uuid, message_uuid
        )

    def list(self, info: Any, **filters: Any) -> Any:
        return _fine_tuning_message_mod.resolve_fine_tuning_message_list(info, **filters)

    def insert_update(self, info: Any, **kwargs: Any) -> Optional[Dict[str, Any]]:
        return _fine_tuning_message_mod.insert_update_fine_tuning_message(
            info, **kwargs
        )

    def delete(self, info: Any, **kwargs: Any) -> bool:
        return _fine_tuning_message_mod.delete_fine_tuning_message(info, **kwargs)

    def get_type(self, info: Any, instance: Any) -> Any:
        return _fine_tuning_message_mod.get_fine_tuning_message_type(info, instance)

    def resolve_single(self, info: Any, **kwargs: Any) -> Any:
        return _fine_tuning_message_mod.resolve_fine_tuning_message(info, **kwargs)