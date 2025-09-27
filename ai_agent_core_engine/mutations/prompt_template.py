# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import traceback
from typing import Any, Dict

from graphene import Boolean, Field, List, Mutation, String

from silvaengine_utility import JSON

from ..models.prompt_template import delete_prompt_template, insert_update_prompt_template
from ..queries.prompt_template import resolve_prompt_template_list
from ..types.prompt_template import PromptTemplateType


class InsertUpdatePromptTemplate(Mutation):
    prompt_template = Field(PromptTemplateType)

    class Arguments:
        prompt_version_uuid = String(required=False)
        prompt_uuid = String(required=False)
        prompt_type = String(required=True)
        prompt_name = String(required=True)
        prompt_description = String(required=False)
        template_context = String(required=True)
        variables = List(JSON, required=False)
        mcp_servers = List(JSON, required=False)
        ui_components = List(JSON, required=False)
        status = String(required=False)
        updated_by = String(required=True)

    @staticmethod
    def mutate(root: Any, info: Any, **kwargs: Dict[str, Any]) -> "InsertUpdatePromptTemplate":
        try:
            # Use cascading cache purging for prompt templates
            from ..models.cache import purge_prompt_template_cascading_cache

            cache_result = purge_prompt_template_cascading_cache(
                endpoint_id=info.context["endpoint_id"],
                prompt_version_uuid=kwargs.get("prompt_version_uuid"),
                prompt_uuid=kwargs.get("prompt_uuid"),
                logger=info.context.get("logger"),
            )

            prompt_template = insert_update_prompt_template(info, **kwargs)
        except Exception as e:
            log = traceback.format_exc()
            info.context.get("logger").error(log)
            raise e

        return InsertUpdatePromptTemplate(prompt_template=prompt_template)


class DeletePromptTemplate(Mutation):
    ok = Boolean()

    class Arguments:
        prompt_version_uuid = String(required=True)

    @staticmethod
    def mutate(root: Any, info: Any, **kwargs: Dict[str, Any]) -> "DeletePromptTemplate":
        try:
            # Use cascading cache purging for prompt templates
            from ..models.cache import purge_prompt_template_cascading_cache

            cache_result = purge_prompt_template_cascading_cache(
                endpoint_id=info.context["endpoint_id"],
                prompt_version_uuid=kwargs.get("prompt_version_uuid"),
                logger=info.context.get("logger"),
            )

            ok = delete_prompt_template(info, **kwargs)
        except Exception as e:
            log = traceback.format_exc()
            info.context.get("logger").error(log)
            raise e

        return DeletePromptTemplate(ok=ok)