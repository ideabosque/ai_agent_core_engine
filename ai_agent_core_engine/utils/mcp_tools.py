# -*- coding: utf-8 -*-
"""Shared MCP tool-listing utilities — transport-level HTTP calls.

These functions fetch tools from remote MCP servers via HTTP. They are
backend-agnostic: they accept a plain dict with ``mcp_server_url`` and
``headers`` keys, not a backend-specific model instance.

Previously these lived in ``models/dynamodb/mcp_server.py`` which forced
PostgreSQL code to cross-import from the DynamoDB module. Moving them
here breaks that coupling.
"""
from __future__ import print_function

__author__ = "bibow"

import logging
from typing import Any, Dict, List

from silvaengine_utility import Invoker

try:
    from mcp_http_client import MCPHttpClient
except (ModuleNotFoundError, ImportError):
    MCPHttpClient = None


async def _run_list_tools(
    logger: logging.Logger, mcp_server: Dict[str, Any]
):
    """Async helper: call ``tools/list`` on the MCP server via HTTP."""
    if MCPHttpClient is None:
        raise ImportError("mcp_http_client is required to list MCP server tools.")

    base_url = mcp_server["mcp_server_url"]
    headers = mcp_server["headers"]

    mcp_http_client = MCPHttpClient(
        logger,
        **{
            "base_url": base_url,
            "headers": headers,
        },
    )

    async with mcp_http_client as client:
        return await client.list_tools()


def load_list_tools(
    logger: logging.Logger, mcp_server: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Fetch the tool list from a remote MCP server.

    Args:
        logger: Logger instance.
        mcp_server: Dict with ``mcp_server_url`` and ``headers`` keys.

    Returns:
        List of tool dicts with ``name``, ``description``, and ``input_schema``.
    """
    try:
        tools = Invoker.sync_call_async_compatible(
            _run_list_tools(logger, mcp_server)
        )
    except Exception as e:
        tools = []
        mcp_server_uuid = "internal_mcp"
        if isinstance(mcp_server, dict) and "mcp_server_uuid" in mcp_server:
            mcp_server_uuid = mcp_server["mcp_server_uuid"]
        logger.error(
            f"Failed to list tools from MCP server {mcp_server_uuid}: {str(e)}"
        )

    return [
        {
            "name": tool.name,
            "description": tool.description,
            "input_schema": (
                tool.get("inputSchema", tool.get("input_schema", {}))
                if isinstance(tool, dict)
                else getattr(tool, "input_schema", getattr(tool, "inputSchema", {}))
            ),
        }
        for tool in tools
    ]


__all__ = ["load_list_tools"]