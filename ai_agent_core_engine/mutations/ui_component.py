# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import traceback
from typing import Any, Dict

from graphene import Boolean, Field, List, Mutation, String

from silvaengine_utility import JSON

from ..models.ui_component import delete_ui_component, insert_update_ui_component
from ..queries.ui_component import resolve_ui_component_list
from ..types.ui_component import UIComponentType


class InsertUpdateUIComponent(Mutation):
    ui_component = Field(UIComponentType)

    class Arguments:
        ui_component_uuid = String(required=False)
        ui_component_type = String(required=True)
        tag_name = String(required=True)
        parameters = List(JSON, required=False)
        wait_for = String(required=False)
        updated_by = String(required=True)

    @staticmethod
    def mutate(root: Any, info: Any, **kwargs: Dict[str, Any]) -> "InsertUpdateUIComponent":
        try:
            # Use cascading cache purging for UI components
            from ..models.cache import purge_ui_component_cascading_cache

            cache_result = purge_ui_component_cascading_cache(
                ui_component_type=kwargs.get("ui_component_type"),
                ui_component_uuid=kwargs.get("ui_component_uuid"),
                logger=info.context.get("logger"),
            )

            ui_component = insert_update_ui_component(info, **kwargs)
        except Exception as e:
            log = traceback.format_exc()
            info.context.get("logger").error(log)
            raise e

        return InsertUpdateUIComponent(ui_component=ui_component)


class DeleteUIComponent(Mutation):
    ok = Boolean()

    class Arguments:
        ui_component_type = String(required=True)
        ui_component_uuid = String(required=True)

    @staticmethod
    def mutate(root: Any, info: Any, **kwargs: Dict[str, Any]) -> "DeleteUIComponent":
        try:
            # Use cascading cache purging for UI components
            from ..models.cache import purge_ui_component_cascading_cache

            cache_result = purge_ui_component_cascading_cache(
                ui_component_type=kwargs.get("ui_component_type"),
                ui_component_uuid=kwargs.get("ui_component_uuid"),
                logger=info.context.get("logger"),
            )

            ok = delete_ui_component(info, **kwargs)
        except Exception as e:
            log = traceback.format_exc()
            info.context.get("logger").error(log)
            raise e

        return DeleteUIComponent(ok=ok)