# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import traceback
from typing import Any, Dict

from graphene import Boolean, Field, List, Mutation, String

from silvaengine_utility import JSON

from ..models.llm import delete_llm, insert_update_llm
from ..types.llm import LlmType


class InsertUpdateLlm(Mutation):
    llm = Field(LlmType)

    class Arguments:
        llm_provider = String(required=True)
        llm_name = String(required=True)
        module_name = String(required=False)
        class_name = String(required=False)
        configuration_schema = JSON(required=False)
        updated_by = String(required=True)

    @staticmethod
    def mutate(root: Any, info: Any, **kwargs: Dict[str, Any]) -> "InsertUpdateLlm":
        try:
            # Use cascading cache purging for LLMs
            from ..models.cache import purge_llm_cascading_cache

            cache_result = purge_llm_cascading_cache(
                llm_provider=kwargs.get("llm_provider"),
                llm_name=kwargs.get("llm_name"),
                logger=info.context.get("logger"),
            )

            llm = insert_update_llm(info, **kwargs)
        except Exception as e:
            log = traceback.format_exc()
            info.context.get("logger").error(log)
            raise e

        return InsertUpdateLlm(llm=llm)


class DeleteLlm(Mutation):
    ok = Boolean()

    class Arguments:
        llm_provider = String(required=True)
        llm_name = String(required=True)

    @staticmethod
    def mutate(root: Any, info: Any, **kwargs: Dict[str, Any]) -> "DeleteLlm":
        try:
            # Use cascading cache purging for LLMs
            from ..models.cache import purge_llm_cascading_cache

            cache_result = purge_llm_cascading_cache(
                llm_provider=kwargs.get("llm_provider"),
                llm_name=kwargs.get("llm_name"),
                logger=info.context.get("logger"),
            )

            ok = delete_llm(info, **kwargs)
        except Exception as e:
            log = traceback.format_exc()
            info.context.get("logger").error(log)
            raise e

        return DeleteLlm(ok=ok)
