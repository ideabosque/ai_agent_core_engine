# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import traceback
from typing import Any, Dict

from graphene import Boolean, Field, Int, List, Mutation, String

from silvaengine_utility import JSON

from ..models.wizard import (
    delete_wizard,
    insert_update_wizard,
)
from ..types.wizard import WizardType


class InsertUpdateWizard(Mutation):
    wizard = Field(WizardType)

    class Arguments:
        wizard_uuid = String(required=False)
        wizard_title = String(required=True)
        wizard_description = String(required=False)
        wizard_type = String(required=True)
        form_schema = String(required=False)
        priority = Int(required=False)
        element_uuids = List(String, required=False)
        updated_by = String(required=True)

    @staticmethod
    def mutate(root: Any, info: Any, **kwargs: Dict[str, Any]) -> "InsertUpdateWizard":
        try:
            wizard = insert_update_wizard(info, **kwargs)
        except Exception as e:
            log = traceback.format_exc()
            info.context.get("logger").error(log)
            raise e

        return InsertUpdateWizard(wizard=wizard)


class DeleteWizard(Mutation):
    ok = Boolean()

    class Arguments:
        wizard_uuid = String(required=True)

    @staticmethod
    def mutate(root: Any, info: Any, **kwargs: Dict[str, Any]) -> "DeleteWizard":
        try:
            ok = delete_wizard(info, **kwargs)
        except Exception as e:
            log = traceback.format_exc()
            info.context.get("logger").error(log)
            raise e

        return DeleteWizard(ok=ok)
