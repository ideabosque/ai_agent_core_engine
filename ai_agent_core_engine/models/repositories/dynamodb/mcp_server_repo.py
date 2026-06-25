# -*- coding: utf-8 -*-
"""DynamoDB repository for mcp_server entity."""
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict, Optional

from ...repositories.base import EntityRepository
from ._base import _normalize

from ...dynamodb import mcp_server as _mcp_server_mod


class McpServerRepository(EntityRepository):
    """DynamoDB repository for mcp_server entity."""

    @property
    def entity_type(self) -> str:
        return "mcp_server"

    def get(self, **keys: Any) -> Optional[Dict[str, Any]]:
        partition_key = keys.get("partition_key")
        mcp_server_uuid = keys.get("mcp_server_uuid")
        if not partition_key or not mcp_server_uuid:
            return None
        count = _mcp_server_mod.get_mcp_server_count(partition_key, mcp_server_uuid)
        if count == 0:
            return None
        return _normalize(_mcp_server_mod.get_mcp_server(partition_key, mcp_server_uuid))

    def count(self, **keys: Any) -> int:
        partition_key = keys.get("partition_key")
        mcp_server_uuid = keys.get("mcp_server_uuid")
        if not partition_key or not mcp_server_uuid:
            return 0
        return _mcp_server_mod.get_mcp_server_count(partition_key, mcp_server_uuid)

    def list(self, info: Any, **filters: Any) -> Any:
        return _mcp_server_mod.resolve_mcp_server_list(info, **filters)

    def insert_update(self, info: Any, **kwargs: Any) -> Optional[Dict[str, Any]]:
        return _mcp_server_mod.insert_update_mcp_server(info, **kwargs)

    def delete(self, info: Any, **kwargs: Any) -> bool:
        return _mcp_server_mod.delete_mcp_server(info, **kwargs)

    def get_type(self, info: Any, instance: Any) -> Any:
        return _mcp_server_mod.get_mcp_server_type(info, instance)

    def resolve_single(self, info: Any, **kwargs: Any) -> Any:
        return _mcp_server_mod.resolve_mcp_server(info, **kwargs)