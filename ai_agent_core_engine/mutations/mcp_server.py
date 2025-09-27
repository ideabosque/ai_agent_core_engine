# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import traceback
from typing import Any, Dict

from graphene import Boolean, Field, Mutation, String

from silvaengine_utility import JSON

from ..models.mcp_server import delete_mcp_server, insert_update_mcp_server
from ..queries.mcp_server import resolve_mcp_server_list
from ..types.mcp_server import MCPServerType


class InsertUpdateMCPServer(Mutation):
    mcp_server = Field(MCPServerType)

    class Arguments:
        mcp_server_uuid = String(required=False)
        mcp_label = String(required=True)
        mcp_server_url = String(required=True)
        headers = JSON(required=False)
        updated_by = String(required=True)

    @staticmethod
    def mutate(root: Any, info: Any, **kwargs: Dict[str, Any]) -> "InsertUpdateMCPServer":
        try:
            # Use cascading cache purging for MCP servers
            from ..models.cache import purge_mcp_server_cascading_cache

            cache_result = purge_mcp_server_cascading_cache(
                endpoint_id=info.context["endpoint_id"],
                mcp_server_uuid=kwargs.get("mcp_server_uuid"),
                logger=info.context.get("logger"),
            )

            mcp_server = insert_update_mcp_server(info, **kwargs)
        except Exception as e:
            log = traceback.format_exc()
            info.context.get("logger").error(log)
            raise e

        return InsertUpdateMCPServer(mcp_server=mcp_server)


class DeleteMCPServer(Mutation):
    ok = Boolean()

    class Arguments:
        mcp_server_uuid = String(required=True)

    @staticmethod
    def mutate(root: Any, info: Any, **kwargs: Dict[str, Any]) -> "DeleteMCPServer":
        try:
            # Use cascading cache purging for MCP servers
            from ..models.cache import purge_mcp_server_cascading_cache

            cache_result = purge_mcp_server_cascading_cache(
                endpoint_id=info.context["endpoint_id"],
                mcp_server_uuid=kwargs.get("mcp_server_uuid"),
                logger=info.context.get("logger"),
            )

            ok = delete_mcp_server(info, **kwargs)
        except Exception as e:
            log = traceback.format_exc()
            info.context.get("logger").error(log)
            raise e

        return DeleteMCPServer(ok=ok)