# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import traceback
from typing import Any, Dict

from graphene import Boolean, Field, Mutation, String

from ..models.flow_snippet import delete_flow_snippet, insert_update_flow_snippet
from ..types.flow_snippet import FlowSnippetType


class InsertUpdateFlowSnippet(Mutation):
    flow_snippet = Field(FlowSnippetType)

    class Arguments:
        flow_snippet_version_uuid = String(required=False)
        flow_snippet_uuid = String(required=False)
        prompt_uuid = String(required=True)
        flow_name = String(required=True)
        flow_relationship = String(required=False)
        flow_context = String(required=True)
        status = String(required=False)
        updated_by = String(required=True)

    @staticmethod
    def mutate(root: Any, info: Any, **kwargs: Dict[str, Any]) -> "InsertUpdateFlowSnippet":
        try:
            flow_snippet = insert_update_flow_snippet(info, **kwargs)
        except Exception as e:
            log = traceback.format_exc()
            info.context.get("logger").error(log)
            raise e

        return InsertUpdateFlowSnippet(flow_snippet=flow_snippet)


class DeleteFlowSnippet(Mutation):
    ok = Boolean()

    class Arguments:
        flow_snippet_version_uuid = String(required=True)

    @staticmethod
    def mutate(root: Any, info: Any, **kwargs: Dict[str, Any]) -> "DeleteFlowSnippet":
        try:
            ok = delete_flow_snippet(info, **kwargs)
        except Exception as e:
            log = traceback.format_exc()
            info.context.get("logger").error(log)
            raise e

        return DeleteFlowSnippet(ok=ok)