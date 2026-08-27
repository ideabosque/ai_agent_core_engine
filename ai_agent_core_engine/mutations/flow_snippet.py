# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import traceback
from typing import Any, Dict

from graphene import Boolean, Field, List, Mutation, String

from ..models.repositories import get_repo
from ..types.flow_snippet import FlowSnippetType


class InsertUpdateFlowSnippet(Mutation):
    flow_snippet = Field(FlowSnippetType)

    class Arguments:
        flow_snippet_version_uuid = String(required=False)
        flow_snippet_uuid = String(required=False)
        prompt_uuid = String(required=False)
        flow_name = String(required=False)
        flow_relationship = String(required=False)
        flow_context = String(required=False)
        enabled_tools = List(String, required=False)
        status = String(required=False)
        duplicate = Boolean(required=False)
        updated_by = String(required=True)

    @staticmethod
    def mutate(
        root: Any, info: Any, **kwargs: Dict[str, Any]
    ) -> "InsertUpdateFlowSnippet":
        try:
            flow_snippet = get_repo("flow_snippet").insert_update(info, **kwargs)
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
            ok = get_repo("flow_snippet").delete(info, **kwargs)
        except Exception as e:
            log = traceback.format_exc()
            info.context.get("logger").error(log)
            raise e

        return DeleteFlowSnippet(ok=ok)
