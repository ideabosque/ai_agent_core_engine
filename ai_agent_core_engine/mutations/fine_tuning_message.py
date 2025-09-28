# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import traceback
from typing import Any, Dict

from graphene import Boolean, Field, Int, List, Mutation, String

from silvaengine_utility import JSON

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
        tool_calls = List(JSON, required=False)
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
            # Use cascading cache purging for fine tuning messages

            from ..models.cache import purge_fine_tuning_message_cascading_cache

            cache_result = purge_fine_tuning_message_cascading_cache(
                agent_uuid=kwargs.get("agent_uuid"),
                thread_uuid=kwargs.get("thread_uuid"),
                message_uuid=kwargs.get("message_uuid"),
                logger=info.context.get("logger"),
            )

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
            # Use cascading cache purging for fine tuning messages
            from ..models.fine_tuning_message import resolve_fine_tuning_message
            from ..models.cache import purge_fine_tuning_message_cascading_cache

            fine_tuning_entity = resolve_fine_tuning_message(
                info,
                **{
                    "agent_uuid": kwargs.get("agent_uuid"),
                    "message_uuid": kwargs.get("message_uuid"),
                },
            )

            cache_result = purge_fine_tuning_message_cascading_cache(
                agent_uuid=kwargs.get("agent_uuid"),
                thread_uuid=(
                    fine_tuning_entity.thread_uuid if fine_tuning_entity else None
                ),
                message_uuid=kwargs.get("message_uuid"),
                logger=info.context.get("logger"),
            )

            ok = delete_fine_tuning_message(info, **kwargs)
        except Exception as e:
            log = traceback.format_exc()
            info.context.get("logger").error(log)
            raise e

        return DeleteFineTuningMessage(ok=ok)
