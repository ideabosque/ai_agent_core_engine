# -*- coding: utf-8 -*-
"""DynamoDB repository for the usage entity (usage_limit / usage_summary).

Thin wrapper over ``models.dynamodb.usage``.  Beyond the ``EntityRepository``
contract it exposes two domain methods used by
``utils.decorators.check_usage_limit``:

* ``resolve_usage_limit(partition_key, usage_key)`` — the active usage_limit as
  an attribute-accessible object (``.status`` / ``.period_end`` / ``.usage_limit``).
* ``add_usage_summary(partition_key, usage_key, usage_key_period_start, limit)``
  — atomic increment that raises ``Exception("Usage Limit Exceeded")`` once the
  period total reaches ``limit``.
"""
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict, Optional

from ...repositories.base import EntityRepository
from ._base import _normalize

from ...dynamodb import usage as _usage_mod


class UsageRepository(EntityRepository):
    """DynamoDB repository for the usage entity."""

    @property
    def entity_type(self) -> str:
        return "usage"

    # ---- EntityRepository contract (usage_limit is the addressable row) ----

    def get(self, **keys: Any) -> Optional[Dict[str, Any]]:
        partition_key = keys.get("partition_key")
        usage_key = keys.get("usage_key")
        if not partition_key or not usage_key:
            return None
        return _normalize(_usage_mod.get_usage_limit(partition_key, usage_key))

    def count(self, **keys: Any) -> int:
        partition_key = keys.get("partition_key")
        usage_key = keys.get("usage_key")
        if not partition_key or not usage_key:
            return 0
        return 1 if _usage_mod.get_usage_limit(partition_key, usage_key) is not None else 0

    def list(self, info: Any, **filters: Any) -> Any:
        raise NotImplementedError("usage entity does not support list()")

    def insert_update(self, info: Any, **kwargs: Any) -> Optional[Dict[str, Any]]:
        _usage_mod.insert_update_usage_limit(**kwargs)
        return _normalize(
            _usage_mod.get_usage_limit(
                kwargs.get("partition_key"), kwargs.get("usage_key")
            )
        )

    def delete(self, info: Any, **kwargs: Any) -> bool:
        entity = _usage_mod.get_usage_limit(
            kwargs.get("partition_key"), kwargs.get("usage_key")
        )
        if entity is None:
            return False
        entity.delete()
        return True

    # ---- domain methods (used by utils.decorators.check_usage_limit) ----

    def resolve_usage_limit(
        self, partition_key: str, usage_key: str
    ) -> Optional[Any]:
        """Return the active usage_limit model (attribute-accessible) or None."""
        return _usage_mod.get_usage_limit(partition_key, usage_key)

    def add_usage_summary(
        self,
        partition_key: str,
        usage_key: str,
        usage_key_period_start: str,
        limit: int,
    ) -> None:
        """Atomically increment the period total, raising once it reaches ``limit``."""
        return _usage_mod.add_usage_summary(
            partition_key, usage_key, usage_key_period_start, limit
        )


__all__ = ["UsageRepository"]
