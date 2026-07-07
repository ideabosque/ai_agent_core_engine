# -*- coding: utf-8 -*-
"""PostgreSQL DataLoader for MCP server tools fetched via HTTP.

Mirrors the DynamoDB McpServerToolLoader contract:
.load((mcp_server_url, headers_tuple)) returns a Promise that resolves to a
**list** of tool dicts retrieved from the MCP server's ``tools/list`` endpoint.

This loader is **not** a database query — it calls ``load_list_tools`` from the
DynamoDB mcp_server module, which performs an HTTP call to the remote MCP
server.  The PG backend reuses the same fetch function because tool discovery
is transport-level, not storage-level.
"""
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict, List, Optional

from .base import SafeDataLoader


class McpServerToolLoader(SafeDataLoader):
    """Batch loader for MCP server tools keyed by (mcp_server_url, headers_tuple).

    Unlike other PG loaders, this does **not** query PostgreSQL — it fetches
    tools from remote MCP servers via HTTP.  The DynamoDB ``load_list_tools``
    function is reused because tool discovery is transport-level.
    """

    def __init__(self, context: Dict[str, Any], cache_enabled: bool = True) -> None:
        super().__init__(context, cache_enabled=cache_enabled)
        self._internal_mcp: Optional[Dict[str, Any]] = None
        self._internal_mcp_tools: Optional[List] = None

    # Public alias — the MCPServerType resolver calls set_internal_mcp().
    def set_internal_mcp(self, endpoint_id: str, part_id: str) -> None:
        """Lazily fetch the internal MCP config (same as DynamoDB loader)."""
        if self._internal_mcp is not None:
            return
        from ....handlers.config import Config

        self._internal_mcp = Config.get_internal_mcp(endpoint_id, part_id)

    def _get_internal_mcp_tools(self) -> List:
        """Fetch internal MCP tools (cached on the loader instance)."""
        if self._internal_mcp is not None:
            if self._internal_mcp_tools is not None:
                return self._internal_mcp_tools
            from ..dynamodb.mcp_server import load_list_tools

            self._internal_mcp_tools = load_list_tools(
                self._context.get("logger"),
                {
                    "mcp_server_url": self._internal_mcp["base_url"],
                    "headers": self._internal_mcp["headers"],
                },
            )
            return self._internal_mcp_tools
        return []

    def _batch_load_fn(
        self, keys: List[tuple]
    ) -> Dict[tuple, List[Dict[str, Any]]]:
        from ..dynamodb.mcp_server import load_list_tools

        unique_keys = list(dict.fromkeys(keys))
        key_map: Dict[tuple, List[Dict[str, Any]]] = {}

        internal_mcp_tools = self._get_internal_mcp_tools() or []

        for mcp_server_url, headers_tuple in unique_keys:
            tools = load_list_tools(
                self._context.get("logger"),
                {
                    "mcp_server_url": mcp_server_url,
                    "headers": dict(headers_tuple),
                },
            )
            # Merge internal MCP tools into the result
            tools.extend(internal_mcp_tools)
            key_map[(mcp_server_url, headers_tuple)] = tools

        return {key: key_map.get(key, []) for key in keys}


__all__ = ["McpServerToolLoader"]