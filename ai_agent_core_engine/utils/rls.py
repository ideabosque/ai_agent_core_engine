# -*- coding: utf-8 -*-
"""Row-Level Security (RLS) helpers for the PostgreSQL backend.

These functions enforce tenant isolation at the database level so that
even if a query forgets to filter on ``partition_key``, the database
will still restrict rows to the current tenant context.

Usage
-----
1. ``set_rls_context(session, partition_key)`` — called at the start of
   each request to set the ``app.tenant_id`` session variable.
2. ``create_rls_policies(engine)`` — called once during table
   initialization to enable RLS and create policies on all
   partition-keyed tables.
"""
from __future__ import print_function

__author__ = "bibow"

from typing import Any

try:
    from sqlalchemy import text
except ImportError:  # pragma: no cover - DynamoDB-only environments
    raise ImportError(
        "SQLAlchemy is required for PostgreSQL backend. "
        "Install with: pip install AI-Agent-Core-Engine[postgresql]"
    )


# Tables that carry a ``partition_key`` column and therefore participate
# in Row-Level Security tenant isolation.  The 9 partition-keyed entities
# plus run, message, tool_call, fine_tuning_message, and async_task.
RLS_TABLES = [
    "agents",
    "threads",
    "elements",
    "wizards",
    "wizard_groups",
    "wizard_group_filters",
    "mcp_servers",
    "flow_snippets",
    "prompt_templates",
    "runs",
    "messages",
    "tool_calls",
    "async_tasks",
    "fine_tuning_messages",
]

# Tables that are global registries (no partition_key) and must NOT have
# RLS applied: llm, wizard_schema, ui_component.


def set_rls_context(session: Any, partition_key: str) -> None:
    """Set the tenant context for the current database session.

    Executes ``SET LOCAL app.tenant_id = :tenant`` so that all subsequent
    queries within this transaction are automatically filtered by the
    RLS policies defined in :func:`create_rls_policies`.

    Parameters
    ----------
    session : Any
        A SQLAlchemy ``Session`` (or scoped session proxy).
    partition_key : str
        The tenant partition key (``"endpoint_id#part_id"``).
    """
    if not partition_key:
        raise ValueError("partition_key must be a non-empty string for RLS context.")

    session.execute(
        text("SET app.tenant_id = :tenant"),
        {"tenant": partition_key},
    )


def create_rls_policies(engine: Any) -> None:
    """Enable Row-Level Security and create tenant-isolation policies.

    For each table listed in :data:`RLS_TABLES` this executes::

        ALTER TABLE <prefix><table> ENABLE ROW LEVEL SECURITY;
        CREATE POLICY tenant_isolation ON <prefix><table>
            USING (partition_key = current_setting('app.tenant_id', true));

    Idempotent: existing policies are dropped before re-creation so the
    function can be called on every startup without error.

    Parameters
    ----------
    engine : Any
        SQLAlchemy engine bound to the PostgreSQL database.
    """
    from ..models.postgresql.base import Base

    prefix = getattr(Base, "table_prefix", "")

    with engine.begin() as conn:
        for table_suffix in RLS_TABLES:
            table_name = f"{prefix}{table_suffix}"

            # Enable RLS on the table (idempotent).
            conn.execute(text(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY;"))
            # Force RLS even for the table owner (otherwise owner bypasses).
            conn.execute(text(f"ALTER TABLE {table_name} FORCE ROW LEVEL SECURITY;"))

            # Drop existing policy if present (idempotent).
            conn.execute(
                text(
                    f"DROP POLICY IF EXISTS tenant_isolation ON {table_name};"
                )
            )

            # Create the tenant-isolation policy.
            conn.execute(
                text(
                    f"CREATE POLICY tenant_isolation ON {table_name} "
                    f"USING (partition_key = current_setting('app.tenant_id', true));"
                )
            )


__all__ = ["set_rls_context", "create_rls_policies", "RLS_TABLES"]