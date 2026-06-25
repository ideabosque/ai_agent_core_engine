# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import traceback
from typing import Any, Dict
from graphene import Boolean, Field, List, Mutation, String
from silvaengine_utility import JSONCamelCase

from ..models.repositories import get_repo
from ..types.ui_component import UIComponentType


class InsertUpdateUIComponent(Mutation):
    ui_component = Field(UIComponentType)

    class Arguments:
        ui_component_uuid = String(required=False)
        ui_component_type = String(required=True)
        tag_name = String(required=True)
        tag_alias = String(required=False)
        parameters = List(JSONCamelCase, required=False)
        wait_for = String(required=False)
        updated_by = String(required=True)

    @staticmethod
    def mutate(root: Any, info: Any, **kwargs: Dict[str, Any]) -> "InsertUpdateUIComponent":
        try:
            ui_component = get_repo("ui_component").insert_update(info, **kwargs)
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
            ok = get_repo("ui_component").delete(info, **kwargs)
        except Exception as e:
            log = traceback.format_exc()
            info.context.get("logger").error(log)
            raise e

        return DeleteUIComponent(ok=ok)