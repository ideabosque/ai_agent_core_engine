# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import traceback
from typing import Any, Dict

from graphene import Boolean, Field, Int, List, Mutation, String

from silvaengine_utility import JSONCamelCase

from ..models.fine_tuning_message import (
    delete_fine_tuning_message,
    insert_update_fine_tuning_message,
)
from ..types.fine_tuning_message import FineTuningMessageType


class InsertUpdateFineTuningMessage(Mutation):
    fine_tuning_message = Field(FineTuningMessageType)

    class Arguments:
        agent_uuid = String(required=True)
        message_uuid = String(required=True)
        thread_uuid = String(required=False)
        timestamp = Int(required=False)
        role = String(required=False)
        tool_calls = List(JSONCamelCase, required=False)
        tool_call_uuid = String(required=False)
        content = String(required=False)
        weight = Int(required=False)
        trained = Boolean(required=False)
        updated_by = String(required=True)

    @staticmethod
    def mutate(
        root: Any, info: Any, **kwargs: Dict[str, Any]
    ) -> "InsertUpdateFineTuningMessage":
        try:
            fine_tuning_message = insert_update_fine_tuning_message(info, **kwargs)
        except Exception as e:
            log = traceback.format_exc()
            info.context.get("logger").error(log)
            raise e

        return InsertUpdateFineTuningMessage(fine_tuning_message=fine_tuning_message)


class DeleteFineTuningMessage(Mutation):
    ok = Boolean()

    class Arguments:
        agent_uuid = String(required=True)
        message_uuid = String(required=True)

    @staticmethod
    def mutate(
        root: Any, info: Any, **kwargs: Dict[str, Any]
    ) -> "DeleteFineTuningMessage":
        try:
            ok = delete_fine_tuning_message(info, **kwargs)
        except Exception as e:
            log = traceback.format_exc()
            info.context.get("logger").error(log)
            raise e

        return DeleteFineTuningMessage(ok=ok)
