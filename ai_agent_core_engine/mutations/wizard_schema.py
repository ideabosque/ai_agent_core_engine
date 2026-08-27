# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import traceback
from typing import Any, Dict
from graphene import Boolean, Field, List, Mutation, String
from silvaengine_utility import JSONCamelCase

from ..models.repositories import get_repo
from ..types.wizard_schema import WizardSchemaType


class InsertUpdateWizardSchema(Mutation):
    wizard_schema = Field(WizardSchemaType)

    class Arguments:
        wizard_schema_type = String(required=True)
        wizard_schema_name = String(required=True)
        wizard_schema_description = String(required=False)
        attributes = List(JSONCamelCase, required=False)
        attribute_groups = List(JSONCamelCase, required=False)
        updated_by = String(required=True)

    @staticmethod
    def mutate(root: Any, info: Any, **kwargs: Dict[str, Any]) -> "InsertUpdateWizardSchema":
        try:
            wizard_schema = get_repo("wizard_schema").insert_update(info, **kwargs)
        except Exception as e:
            log = traceback.format_exc()
            info.context.get("logger").error(log)
            raise e

        return InsertUpdateWizardSchema(wizard_schema=wizard_schema)


class DeleteWizardSchema(Mutation):
    ok = Boolean()

    class Arguments:
        wizard_schema_type = String(required=True)
        wizard_schema_name = String(required=True)

    @staticmethod
    def mutate(root: Any, info: Any, **kwargs: Dict[str, Any]) -> "DeleteWizardSchema":
        try:
            ok = get_repo("wizard_schema").delete(info, **kwargs)
        except Exception as e:
            log = traceback.format_exc()
            info.context.get("logger").error(log)
            raise e

        return DeleteWizardSchema(ok=ok)
