# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import traceback
from typing import Any, Dict

from graphene import Boolean, Field, List, Mutation, String

from silvaengine_utility import JSON

from ..models.prompt_template import (
    delete_prompt_template,
    insert_update_prompt_template,
)
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
    def mutate(
        root: Any, info: Any, **kwargs: Dict[str, Any]
    ) -> "InsertUpdatePromptTemplate":
        try:
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
    def mutate(
        root: Any, info: Any, **kwargs: Dict[str, Any]
    ) -> "DeletePromptTemplate":
        try:
            ok = delete_prompt_template(info, **kwargs)
        except Exception as e:
            log = traceback.format_exc()
            info.context.get("logger").error(log)
            raise e

        return DeletePromptTemplate(ok=ok)
