# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import traceback
from typing import Any, Dict

from graphene import Boolean, Field, Int, List, Mutation, String

from silvaengine_utility import JSON

# from ..models.wizard_group import delete_wizard_group, insert_update_wizard_group
from ..handlers.wizard_group import insert_update_wizard_group_with_wizards, delete_wizard_from_wizard_group
from ..types.wizard_group import WizardGroupType



class InsertUpdateWizardGroupWithWizards(Mutation):
    wizard_group = Field(WizardGroupType)

    class Arguments:
        wizard_group_uuid = String(required=False)
        wizard_group_name = String(required=True)
        wizard_group_description = String(required=False)
        weight = Int(required=False)
        wizards = List(JSON, required=True)
        updated_by = String(required=True)

    @staticmethod
    def mutate(
        root: Any, info: Any, **kwargs: Dict[str, Any]
    ) -> "InsertUpdateWizardGroupWithWizards":
        try:
            wizard_group = insert_update_wizard_group_with_wizards(info, **kwargs)
        except Exception as e:
            log = traceback.format_exc()
            info.context.get("logger").error(log)
            raise e

        return InsertUpdateWizardGroupWithWizards(wizard_group=wizard_group)
    

class DeleteWizardFromWizardGroup(Mutation):
    ok = Boolean()

    class Arguments:
        wizard_uuid = String(required=True)
        wizard_group_uuid = String(required=True)
        updated_by = String(required=False)
    @staticmethod
    def mutate(root: Any, info: Any, **kwargs: Dict[str, Any]) -> "DeleteWizardFromWizardGroup":
        try:
            ok = delete_wizard_from_wizard_group(info, **kwargs)
        except Exception as e:
            log = traceback.format_exc()
            info.context.get("logger").error(log)
            raise e

        return DeleteWizardFromWizardGroup(ok=ok)
