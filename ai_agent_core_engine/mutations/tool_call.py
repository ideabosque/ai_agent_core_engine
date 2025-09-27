# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import traceback
from typing import Any, Dict

from graphene import Boolean, Field, Int, List, Mutation, String

from silvaengine_utility import JSON

from ..models.tool_call import delete_tool_call, insert_update_tool_call
from ..queries.tool_call import resolve_tool_call_list
from ..types.tool_call import ToolCallType


class InsertUpdateToolCall(Mutation):
    tool_call = Field(ToolCallType)

    class Arguments:
        thread_uuid = String(required=True)
        tool_call_uuid = String(required=False)
        run_uuid = String(required=False)
        tool_call_id = String(required=False)
        tool_type = String(required=False)
        name = String(required=False)
        arguments = String(required=False)
        content = String(required=False)
        status = String(required=False)
        notes = String(required=False)
        updated_by = String(required=True)

    @staticmethod
    def mutate(
        root: Any, info: Any, **kwargs: Dict[str, Any]
    ) -> "InsertUpdateToolCall":
        try:
            if hasattr(resolve_tool_call_list, "cache_clear"):
                resolve_tool_call_list.cache_clear()  # Clear tool call lists
            tool_call = insert_update_tool_call(info, **kwargs)
        except Exception as e:
            log = traceback.format_exc()
            info.context.get("logger").error(log)
            raise e

        return InsertUpdateToolCall(tool_call=tool_call)


class DeleteToolCall(Mutation):
    ok = Boolean()

    class Arguments:
        thread_uuid = String(required=True)
        tool_call_uuid = String(required=True)

    @staticmethod
    def mutate(root: Any, info: Any, **kwargs: Dict[str, Any]) -> "DeleteToolCall":
        try:
            if hasattr(resolve_tool_call_list, "cache_clear"):
                resolve_tool_call_list.cache_clear()  # Clear tool call lists
            ok = delete_tool_call(info, **kwargs)
        except Exception as e:
            log = traceback.format_exc()
            info.context.get("logger").error(log)
            raise e

        return DeleteToolCall(ok=ok)
