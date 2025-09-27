# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import traceback
from typing import Any, Dict

from graphene import Boolean, Field, Int, List, Mutation, String

from silvaengine_utility import JSON

from ..models.element import delete_element, insert_update_element
from ..queries.element import resolve_element_list
from ..types.element import ElementType


class InsertUpdateElement(Mutation):
    element = Field(ElementType)

    class Arguments:
        element_uuid = String(required=False)
        data_type = String(required=True)
        element_title = String(required=True)
        priority = Int(required=False)
        attribute_name = String(required=True)
        attribute_type = String(required=True)
        option_values = List(JSON, required=False)
        conditions = List(JSON, required=False)
        updated_by = String(required=True)

    @staticmethod
    def mutate(root: Any, info: Any, **kwargs: Dict[str, Any]) -> "InsertUpdateElement":
        try:
            # Use cascading cache purging for elements
            from ..models.cache import purge_element_cascading_cache

            cache_result = purge_element_cascading_cache(
                endpoint_id=info.context["endpoint_id"],
                element_uuid=kwargs.get("element_uuid"),
                logger=info.context.get("logger"),
            )

            element = insert_update_element(info, **kwargs)
        except Exception as e:
            log = traceback.format_exc()
            info.context.get("logger").error(log)
            raise e

        return InsertUpdateElement(element=element)


class DeleteElement(Mutation):
    ok = Boolean()

    class Arguments:
        element_uuid = String(required=True)

    @staticmethod
    def mutate(root: Any, info: Any, **kwargs: Dict[str, Any]) -> "DeleteElement":
        try:
            # Use cascading cache purging for elements
            from ..models.cache import purge_element_cascading_cache

            cache_result = purge_element_cascading_cache(
                endpoint_id=info.context["endpoint_id"],
                element_uuid=kwargs.get("element_uuid"),
                logger=info.context.get("logger"),
            )

            ok = delete_element(info, **kwargs)
        except Exception as e:
            log = traceback.format_exc()
            info.context.get("logger").error(log)
            raise e

        return DeleteElement(ok=ok)
