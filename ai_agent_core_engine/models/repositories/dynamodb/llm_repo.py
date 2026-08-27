# -*- coding: utf-8 -*-
"""DynamoDB repository for llm entity."""
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict, Optional

from ...repositories.base import EntityRepository
from ._base import _normalize

from ...dynamodb import llm as _llm_mod


class LlmRepository(EntityRepository):
    """DynamoDB repository for llm entity."""

    @property
    def entity_type(self) -> str:
        return "llm"

    def get(self, **keys: Any) -> Optional[Dict[str, Any]]:
        llm_provider = keys.get("llm_provider")
        llm_name = keys.get("llm_name")
        if not llm_provider or not llm_name:
            return None
        count = _llm_mod.get_llm_count(llm_provider, llm_name)
        if count == 0:
            return None
        return _normalize(_llm_mod.get_llm(llm_provider, llm_name))

    def count(self, **keys: Any) -> int:
        llm_provider = keys.get("llm_provider")
        llm_name = keys.get("llm_name")
        if not llm_provider or not llm_name:
            return 0
        return _llm_mod.get_llm_count(llm_provider, llm_name)

    def list(self, info: Any, **filters: Any) -> Any:
        return _llm_mod.resolve_llm_list(info, **filters)

    def insert_update(self, info: Any, **kwargs: Any) -> Optional[Dict[str, Any]]:
        return _llm_mod.insert_update_llm(info, **kwargs)

    def delete(self, info: Any, **kwargs: Any) -> bool:
        return _llm_mod.delete_llm(info, **kwargs)

    def get_type(self, info: Any, instance: Any) -> Any:
        return _llm_mod.get_llm_type(info, instance)

    def resolve_single(self, info: Any, **kwargs: Any) -> Any:
        return _llm_mod.resolve_llm(info, **kwargs)