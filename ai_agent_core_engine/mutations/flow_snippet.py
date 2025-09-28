# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import traceback
from typing import Any, Dict

from graphene import Boolean, Field, Mutation, String

from ..models.flow_snippet import (
    delete_flow_snippet,
    insert_update_flow_snippet,
)
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
        status = String(required=False)
        updated_by = String(required=True)

    @staticmethod
    def mutate(
        root: Any, info: Any, **kwargs: Dict[str, Any]
    ) -> "InsertUpdateFlowSnippet":
        try:
            # Use cascading cache purging for flow snippets
            from ..models.cache import purge_flow_snippet_cascading_cache

            cache_result = purge_flow_snippet_cascading_cache(
                endpoint_id=info.context["endpoint_id"],
                flow_snippet_version_uuid=kwargs.get("flow_snippet_version_uuid"),
                flow_snippet_uuid=kwargs.get("flow_snippet_uuid"),
                logger=info.context.get("logger"),
            )

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
            # Use cascading cache purging for flow snippets
            from ..models.fine_tuning_message import resolve_fine_tuning_message
            from ..models.cache import purge_flow_snippet_cascading_cache

            flow_snippet_entity = resolve_flow_snippet(
                info,
                **{"flow_snippet_version_uuid": kwargs.get("flow_snippet_version_uuid")},
            )

            cache_result = purge_flow_snippet_cascading_cache(
                endpoint_id=info.context["endpoint_id"],
                flow_snippet_version_uuid=kwargs.get("flow_snippet_version_uuid"),
                flow_snippet_uuid=(
                    flow_snippet_entity.flow_snippet_uuid if flow_snippet_entity else None
                ),
                logger=info.context.get("logger"),
            )

            ok = delete_flow_snippet(info, **kwargs)
        except Exception as e:
            log = traceback.format_exc()
            info.context.get("logger").error(log)
            raise e

        return DeleteFlowSnippet(ok=ok)
