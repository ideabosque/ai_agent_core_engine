# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import traceback
from typing import Any, Dict

from graphene import Boolean, Field, Int, List, Mutation, String

from silvaengine_utility import JSON

from ..models.wizard_group import delete_wizard_group, insert_update_wizard_group
from ..queries.wizard_group import resolve_wizard_group_list
from ..types.wizard_group import WizardGroupType


class InsertUpdateWizardGroup(Mutation):
    wizard_group = Field(WizardGroupType)

    class Arguments:
        wizard_group_uuid = String(required=False)
        wizard_group_name = String(required=True)
        wizard_group_description = String(required=False)
        weight = Int(required=False)
        wizard_uuids = List(String, required=False)
        updated_by = String(required=True)

    @staticmethod
    def mutate(
        root: Any, info: Any, **kwargs: Dict[str, Any]
    ) -> "InsertUpdateWizardGroup":
        try:
            if hasattr(resolve_wizard_group_list, "cache_clear"):
                resolve_wizard_group_list.cache_clear()  # Clear wizard group lists
            wizard_group = insert_update_wizard_group(info, **kwargs)
        except Exception as e:
            log = traceback.format_exc()
            info.context.get("logger").error(log)
            raise e

        return InsertUpdateWizardGroup(wizard_group=wizard_group)


class DeleteWizardGroup(Mutation):
    ok = Boolean()

    class Arguments:
        wizard_group_uuid = String(required=True)

    @staticmethod
    def mutate(root: Any, info: Any, **kwargs: Dict[str, Any]) -> "DeleteWizardGroup":
        try:
            if hasattr(resolve_wizard_group_list, "cache_clear"):
                resolve_wizard_group_list.cache_clear()  # Clear wizard group lists
            ok = delete_wizard_group(info, **kwargs)
        except Exception as e:
            log = traceback.format_exc()
            info.context.get("logger").error(log)
            raise e

        return DeleteWizardGroup(ok=ok)
