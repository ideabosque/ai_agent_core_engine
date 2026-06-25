# -*- coding: utf-8 -*-
"""DynamoDB repository for agent entity."""
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict, Optional

from ...repositories.base import EntityRepository
from ._base import _normalize

from ...dynamodb import agent as _agent_mod


class AgentRepository(EntityRepository):
    """DynamoDB repository for agent entity."""

    @property
    def entity_type(self) -> str:
        return "agent"

    def get(self, **keys: Any) -> Optional[Dict[str, Any]]:
        partition_key = keys.get("partition_key")
        agent_version_uuid = keys.get("agent_version_uuid")
        if not partition_key or not agent_version_uuid:
            return None
        count = _agent_mod.get_agent_count(partition_key, agent_version_uuid)
        if count == 0:
            return None
        return _normalize(_agent_mod.get_agent(partition_key, agent_version_uuid))

    def count(self, **keys: Any) -> int:
        partition_key = keys.get("partition_key")
        agent_version_uuid = keys.get("agent_version_uuid")
        if not partition_key or not agent_version_uuid:
            return 0
        return _agent_mod.get_agent_count(partition_key, agent_version_uuid)

    def list(self, info: Any, **filters: Any) -> Any:
        return _agent_mod.resolve_agent_list(info, **filters)

    def insert_update(self, info: Any, **kwargs: Any) -> Optional[Dict[str, Any]]:
        return _agent_mod.insert_update_agent(info, **kwargs)

    def delete(self, info: Any, **kwargs: Any) -> bool:
        return _agent_mod.delete_agent(info, **kwargs)

    def get_type(self, info: Any, instance: Any) -> Any:
        return _agent_mod.get_agent_type(info, instance)

    def resolve_single(self, info: Any, **kwargs: Any) -> Any:
        return _agent_mod.resolve_agent(info, **kwargs)

    def resolve_active(self, partition_key: str, entity_uuid: str = None, **kwargs: Any) -> Any:
        if entity_uuid:
            return _agent_mod._get_active_agent(partition_key, entity_uuid)
        return _agent_mod._get_active_agent(partition_key, **kwargs)