# -*- coding: utf-8 -*-
"""PostgreSQL DataLoader for LlmModel records keyed by (llm_provider, llm_name).

Mirrors the DynamoDB LlmLoader contract: .load((provider, name)) returns a
Promise that resolves to the normalized LLM dict or None.
"""
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict, List, Optional

from promise import Promise

from .base import SafeDataLoader


class LlmLoader(SafeDataLoader):
    """Batch loader for LlmModel records keyed by (llm_provider, llm_name)."""

    def _batch_load_fn(self, keys: List[tuple]) -> Dict[tuple, Optional[Dict[str, Any]]]:
        from ....handlers.config import Config
        from ...postgresql.llm import LlmModel
        from ...repositories.postgresql._base import _normalize

        # keys is a list of (llm_provider, llm_name) tuples
        # Deduplicate
        unique_keys = list(dict.fromkeys(keys))
        providers = set()
        names = set()
        for provider, name in unique_keys:
            providers.add(provider)
            names.add(name)

        session = Config.db_session()
        try:
            rows = (
                session.query(LlmModel)
                .filter(
                    LlmModel.llm_provider.in_(providers),
                    LlmModel.llm_name.in_(names),
                )
                .all()
            )
        except Exception:
            session.rollback()
            raise

        key_map: Dict[tuple, Optional[Dict[str, Any]]] = {}
        for row in rows:
            key = (row.llm_provider, row.llm_name)
            key_map[key] = _normalize(row)

        # Map back to original key order, defaulting to None
        return {key: key_map.get(key) for key in keys}


__all__ = ["LlmLoader"]