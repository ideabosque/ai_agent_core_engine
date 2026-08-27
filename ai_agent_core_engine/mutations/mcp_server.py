# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import traceback
from typing import Any, Dict
from graphene import Boolean, Field, Mutation, String
from silvaengine_utility import JSONCamelCase

from ..models.repositories import get_repo
from ..types.mcp_server import MCPServerType


class InsertUpdateMCPServer(Mutation):
    mcp_server = Field(MCPServerType)

    class Arguments:
        mcp_server_uuid = String(required=False)
        mcp_label = String(required=True)
        mcp_server_url = String(required=True)
        headers = JSONCamelCase(required=False)
        updated_by = String(required=True)

    @staticmethod
    def mutate(root: Any, info: Any, **kwargs: Dict[str, Any]) -> "InsertUpdateMCPServer":
        try:
            mcp_server = get_repo("mcp_server").insert_update(info, **kwargs)
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
            ok = get_repo("mcp_server").delete(info, **kwargs)
        except Exception as e:
            log = traceback.format_exc()
            info.context.get("logger").error(log)
            raise e

        return DeleteMCPServer(ok=ok)