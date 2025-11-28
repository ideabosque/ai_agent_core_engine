# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import traceback
from typing import Any, Dict

from graphene import Boolean, Field, Int, Mutation, String

from silvaengine_utility import JSON

from ..models.wizard_group_filter import (
    delete_wizard_group_filter,
    insert_update_wizard_group_filter,
)
from ..types.wizard_group_filter import WizardGroupFilterType


class InsertUpdateWizardGroupFilter(Mutation):
    wizard_group_filter = Field(WizardGroupFilterType)

    class Arguments:
        wizard_group_filter_uuid = String(required=False)
        wizard_group_filter_name = String(required=True)
        wizard_group_filter_description = String(required=False)
        region = String(required=True)
        criteria = JSON(required=False)
        weight = Int(required=False)
        wizard_group_uuid = String(required=False)
        updated_by = String(required=True)

    @staticmethod
    def mutate(
        root: Any, info: Any, **kwargs: Dict[str, Any]
    ) -> "InsertUpdateWizardGroupFilter":
        try:
            wizard_group_filter = insert_update_wizard_group_filter(info, **kwargs)
        except Exception as e:
            log = traceback.format_exc()
            info.context.get("logger").error(log)
            raise e

        return InsertUpdateWizardGroupFilter(wizard_group_filter=wizard_group_filter)


class DeleteWizardGroupFilter(Mutation):
    ok = Boolean()

    class Arguments:
        wizard_group_filter_uuid = String(required=True)

    @staticmethod
    def mutate(
        root: Any, info: Any, **kwargs: Dict[str, Any]
    ) -> "DeleteWizardGroupFilter":
        try:
            ok = delete_wizard_group_filter(info, **kwargs)
        except Exception as e:
            log = traceback.format_exc()
            info.context.get("logger").error(log)
            raise e

        return DeleteWizardGroupFilter(ok=ok)
