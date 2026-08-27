# -*- coding: utf-8 -*-
"""DynamoDB repository for flow_snippet entity."""
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict, Optional

from ...repositories.base import EntityRepository
from ._base import _normalize

from ...dynamodb import flow_snippet as _flow_snippet_mod


class FlowSnippetRepository(EntityRepository):
    """DynamoDB repository for flow_snippet entity."""

    @property
    def entity_type(self) -> str:
        return "flow_snippet"

    def get(self, **keys: Any) -> Optional[Dict[str, Any]]:
        partition_key = keys.get("partition_key")
        flow_snippet_version_uuid = keys.get("flow_snippet_version_uuid")
        if not partition_key or not flow_snippet_version_uuid:
            return None
        count = _flow_snippet_mod.get_flow_snippet_count(
            partition_key, flow_snippet_version_uuid
        )
        if count == 0:
            return None
        return _normalize(
            _flow_snippet_mod.get_flow_snippet(partition_key, flow_snippet_version_uuid)
        )

    def count(self, **keys: Any) -> int:
        partition_key = keys.get("partition_key")
        flow_snippet_version_uuid = keys.get("flow_snippet_version_uuid")
        if not partition_key or not flow_snippet_version_uuid:
            return 0
        return _flow_snippet_mod.get_flow_snippet_count(
            partition_key, flow_snippet_version_uuid
        )

    def list(self, info: Any, **filters: Any) -> Any:
        return _flow_snippet_mod.resolve_flow_snippet_list(info, **filters)

    def insert_update(self, info: Any, **kwargs: Any) -> Optional[Dict[str, Any]]:
        return _flow_snippet_mod.insert_update_flow_snippet(info, **kwargs)

    def delete(self, info: Any, **kwargs: Any) -> bool:
        return _flow_snippet_mod.delete_flow_snippet(info, **kwargs)

    def get_type(self, info: Any, instance: Any) -> Any:
        return _flow_snippet_mod.get_flow_snippet_type(info, instance)

    def resolve_single(self, info: Any, **kwargs: Any) -> Any:
        return _flow_snippet_mod.resolve_flow_snippet(info, **kwargs)

    def resolve_active(self, partition_key: str, entity_uuid: str = None, **kwargs: Any) -> Any:
        if entity_uuid:
            return _flow_snippet_mod._get_active_flow_snippet(partition_key, entity_uuid)
        return _flow_snippet_mod._get_active_flow_snippet(partition_key, **kwargs)