# -*- coding: utf-8 -*-
"""DynamoDB repository for prompt_template entity."""
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict, Optional

from ...repositories.base import EntityRepository
from ._base import _normalize

from ...dynamodb import prompt_template as _prompt_template_mod


class PromptTemplateRepository(EntityRepository):
    """DynamoDB repository for prompt_template entity."""

    @property
    def entity_type(self) -> str:
        return "prompt_template"

    def get(self, **keys: Any) -> Optional[Dict[str, Any]]:
        partition_key = keys.get("partition_key")
        prompt_version_uuid = keys.get("prompt_version_uuid")
        if not partition_key or not prompt_version_uuid:
            return None
        count = _prompt_template_mod.get_prompt_template_count(
            partition_key, prompt_version_uuid
        )
        if count == 0:
            return None
        return _normalize(
            _prompt_template_mod.get_prompt_template(partition_key, prompt_version_uuid)
        )

    def count(self, **keys: Any) -> int:
        partition_key = keys.get("partition_key")
        prompt_version_uuid = keys.get("prompt_version_uuid")
        if not partition_key or not prompt_version_uuid:
            return 0
        return _prompt_template_mod.get_prompt_template_count(
            partition_key, prompt_version_uuid
        )

    def list(self, info: Any, **filters: Any) -> Any:
        return _prompt_template_mod.resolve_prompt_template_list(info, **filters)

    def insert_update(self, info: Any, **kwargs: Any) -> Optional[Dict[str, Any]]:
        return _prompt_template_mod.insert_update_prompt_template(info, **kwargs)

    def delete(self, info: Any, **kwargs: Any) -> bool:
        return _prompt_template_mod.delete_prompt_template(info, **kwargs)

    def get_type(self, info: Any, instance: Any) -> Any:
        return _prompt_template_mod.get_prompt_template_type(info, instance)

    def resolve_single(self, info: Any, **kwargs: Any) -> Any:
        return _prompt_template_mod.resolve_prompt_template(info, **kwargs)

    def resolve_active(self, partition_key: str, entity_uuid: str = None, **kwargs: Any) -> Any:
        if entity_uuid:
            return _prompt_template_mod._get_active_prompt_template(partition_key, entity_uuid)
        return _prompt_template_mod._get_active_prompt_template(partition_key, **kwargs)