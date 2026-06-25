# -*- coding: utf-8 -*-
"""PostgreSQL table initialization and shared utilities.

Only imported when DB_BACKEND=postgresql.
"""
from __future__ import print_function

__author__ = "bibow"

import logging
from typing import Any, Dict, List

from .base import Base


def initialize_tables(logger: logging.Logger, db_session: Any, engine: Any = None) -> None:
    """Create all PostgreSQL tables that have been imported.

    This uses SQLAlchemy metadata.create_all() which is idempotent —
    it only creates tables that don't already exist.  After table creation,
    Row-Level Security (RLS) policies are applied to all partition-keyed
    tables to enforce tenant isolation.

    Parameters
    ----------
    logger : logging.Logger
        Logger instance for progress messages.
    db_session : Any
        SQLAlchemy scoped session (used to derive the engine when
        ``engine`` is not supplied).
    engine : Any, optional
        SQLAlchemy engine.  If ``None``, derived from ``db_session.get_bind()``.
    """
    # Import all model modules so their SQLAlchemy classes register
    # with the Base.metadata
    _import_all_models()

    if engine is None:
        engine = db_session.get_bind()

    Base.metadata.create_all(bind=engine, checkfirst=True)
    logger.info("PostgreSQL tables initialized (create_all with checkfirst=True).")

    # Apply Row-Level Security policies on all partition-keyed tables.
    try:
        from ...utils.rls import create_rls_policies

        create_rls_policies(engine)
        logger.info("PostgreSQL RLS policies applied to partition-keyed tables.")
    except Exception as e:
        logger.warning(f"RLS policy creation skipped: {e}")


def _import_all_models() -> None:
    """Import all PostgreSQL model modules to register them with Base.metadata."""
    model_modules = [
        ".agent",
        ".llm",
        ".thread",
        ".run",
        ".message",
        ".tool_call",
        ".async_task",
        ".fine_tuning_message",
        ".element",
        ".wizard",
        ".wizard_schema",
        ".wizard_group",
        ".wizard_group_filter",
        ".mcp_server",
        ".ui_component",
        ".flow_snippet",
        ".prompt_template",
    ]
    for mod_name in model_modules:
        try:
            __import__(
                f"ai_agent_core_engine.models.postgresql{mod_name}",
                fromlist=["x"],
            )
        except ImportError:
            # Model not yet ported — skip silently
            _logger = logging.getLogger(__name__)
            _logger.debug(f"PostgreSQL model not yet available: {mod_name}")


def get_mcp_servers(
    info: Any, mcp_servers: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """PostgreSQL equivalent of dynamodb.utils.get_mcp_servers.

    Resolves MCP server configs by UUID from PostgreSQL, then appends
    the internal MCP server (with tools loaded) the same way the DynamoDB
    path does.
    """
    from ...handlers.config import Config
    from ..dynamodb.mcp_server import load_list_tools
    from ..repositories.dispatch import get_repo

    partition_key = info.context.get("partition_key")
    repo = get_repo("mcp_server")

    resolved_servers: List[Dict[str, Any]] = []
    _strip_keys = {
        "partition_key",
        "endpoint_id",
        "part_id",
        "updated_by",
        "created_at",
        "updated_at",
    }

    for server in mcp_servers:
        mcp_server_uuid = server.get("mcp_server_uuid")
        if not mcp_server_uuid:
            continue
        data = repo.get(partition_key=partition_key, mcp_server_uuid=mcp_server_uuid)
        if data is not None:
            resolved_servers.append({k: v for k, v in data.items() if k not in _strip_keys})

    # Append the internal MCP server (gateway-local MCP daemon)
    internal_mcp = Config.get_internal_mcp(
        info.context["endpoint_id"], part_id=info.context.get("part_id")
    )
    assert internal_mcp is not None and all(
        internal_mcp.get(k) for k in ["headers", "name", "base_url"]
    ), f"Internal MCP ({internal_mcp}) is not configured correctly."

    internal_server = {
        "headers": internal_mcp["headers"],
        "mcp_label": internal_mcp["name"],
        "mcp_server_url": internal_mcp["base_url"],
    }
    internal_server["tools"] = load_list_tools(
        info.context["logger"], internal_server
    )
    resolved_servers.append(internal_server)

    return resolved_servers


__all__ = ["initialize_tables", "get_mcp_servers"]