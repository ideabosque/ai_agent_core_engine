# -*- coding: utf-8 -*-
"""Shared helpers for PostgreSQL repositories."""
from __future__ import print_function

__author__ = "bibow"

import logging
import math
from typing import Any, Dict, List, Optional, Tuple

from ...postgresql.base import normalize_row


def _normalize(row: Any) -> Optional[Dict[str, Any]]:
    """Convert a SQLAlchemy ORM row to a normalized dict.

    Delegates to ``normalize_row`` from the PG base module.
    """
    return normalize_row(row)


def _get_logger(info: Any) -> logging.Logger:
    """Extract a logger from the GraphQL ResolveInfo context."""
    try:
        ctx = getattr(info, "context", None) or {}
        return ctx.get("logger") or logging.getLogger()
    except Exception:
        return logging.getLogger()


def _get_partition_key(info: Any) -> Optional[str]:
    """Extract partition_key from the GraphQL ResolveInfo context."""
    try:
        ctx = getattr(info, "context", None) or {}
        return ctx.get("partition_key")
    except Exception:
        return None


def _get_updated_by(info: Any) -> Optional[str]:
    """Extract updated_by from the GraphQL ResolveInfo context."""
    try:
        ctx = getattr(info, "context", None) or {}
        return ctx.get("updated_by")
    except Exception:
        return None


def _apply_pagination(
    query: Any, page_number: int, limit: int
) -> Tuple[Any, int, int]:
    """Apply offset/limit pagination to a SQLAlchemy query.

    Returns the (paginated_query, offset, limit) tuple.
    """
    page_number = max(1, int(page_number or 1))
    limit = max(1, int(limit or 100))
    offset = (page_number - 1) * limit
    return query.offset(offset).limit(limit), offset, limit


def _purge_cache(
    info: Any, entity_type: str, entity_keys: Dict[str, Any],
    context_keys: Optional[Dict[str, Any]] = None,
) -> None:
    """Purge cascading cache after a successful mutation."""
    try:
        from ...dynamodb.cache import purge_entity_cascading_cache

        logger = _get_logger(info)
        purge_entity_cascading_cache(
            logger,
            entity_type=entity_type,
            context_keys=context_keys,
            entity_keys=entity_keys,
            cascade_depth=3,
        )

        if entity_type == "agent":
            from ....handlers.ai_agent import clear_cached_agent

            ctx = getattr(info, "context", None) or {}
            clear_cached_agent(
                agent_uuid=entity_keys.get("agent_uuid"),
                endpoint_id=ctx.get("endpoint_id"),
                part_id=ctx.get("part_id"),
                partition_key=(context_keys or {}).get("partition_key"),
            )
    except Exception as exc:  # pragma: no cover - defensive
        _get_logger(info).debug("Cache purge skipped: %s", exc)


__all__ = [
    "_normalize",
    "_get_logger",
    "_get_partition_key",
    "_get_updated_by",
    "_apply_pagination",
    "_purge_cache",
]