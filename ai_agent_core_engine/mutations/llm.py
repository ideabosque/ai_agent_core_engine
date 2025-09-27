# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import traceback
from typing import Any, Dict

from graphene import Boolean, Field, List, Mutation, String

from silvaengine_utility import JSON

from ..models.llm import delete_llm, insert_update_llm
from ..queries.llm import resolve_llm_list
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
            if hasattr(resolve_llm_list, "cache_clear"):
                resolve_llm_list.cache_clear()  # Clear llm lists
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
            if hasattr(resolve_llm_list, "cache_clear"):
                resolve_llm_list.cache_clear()  # Clear llm lists
            ok = delete_llm(info, **kwargs)
        except Exception as e:
            log = traceback.format_exc()
            info.context.get("logger").error(log)
            raise e

        return DeleteLlm(ok=ok)
