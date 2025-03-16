# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import traceback
from typing import Any, Dict

from graphene import Boolean, Field, Int, List, Mutation, String

from silvaengine_utility import JSON

from ..models.tool_call import delete_tool_call, insert_tool_call
from ..types.tool_call import ToolCallType


class InsertToolCall(Mutation):
    tool_call = Field(ToolCallType)

    class Arguments:
        thread_uuid = String(required=True)
        tool_call_id = String(required=True)
        run_id = String(required=False)
        tool_type = String(required=False)
        name = String(required=False)
        arguments = JSON(required=False)
        content = String(required=False)

    @staticmethod
    def mutate(root: Any, info: Any, **kwargs: Dict[str, Any]) -> "InsertToolCall":
        try:
            tool_call = insert_tool_call(info, **kwargs)
        except Exception as e:
            log = traceback.format_exc()
            info.context.get("logger").error(log)
            raise e

        return InsertToolCall(tool_call=tool_call)


class DeleteToolCall(Mutation):
    ok = Boolean()

    class Arguments:
        thread_uuid = String(required=True)
        tool_call_id = String(required=True)

    @staticmethod
    def mutate(root: Any, info: Any, **kwargs: Dict[str, Any]) -> "DeleteToolCall":
        try:
            ok = delete_tool_call(info, **kwargs)
        except Exception as e:
            log = traceback.format_exc()
            info.context.get("logger").error(log)
            raise e

        return DeleteToolCall(ok=ok)
