# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import traceback
from typing import Any, Dict

from graphene import Boolean, Field, Int, List, Mutation, String

from silvaengine_utility import JSON

from ..models.message import delete_message, insert_update_message
from ..queries.message import resolve_message_list
from ..types.message import MessageType


class InsertUpdateMessage(Mutation):
    message = Field(MessageType)

    class Arguments:
        thread_uuid = String(required=True)
        message_uuid = String(required=False)
        run_uuid = String(required=False)
        message_id = String(required=False)
        role = String(required=False)
        message = String(required=False)
        updated_by = String(required=True)

    @staticmethod
    def mutate(root: Any, info: Any, **kwargs: Dict[str, Any]) -> "InsertUpdateMessage":
        try:
            if hasattr(resolve_message_list, "cache_clear"):
                resolve_message_list.cache_clear()  # Clear message lists
            message = insert_update_message(info, **kwargs)
        except Exception as e:
            log = traceback.format_exc()
            info.context.get("logger").error(log)
            raise e

        return InsertUpdateMessage(message=message)


class DeleteMessage(Mutation):
    ok = Boolean()

    class Arguments:
        thread_uuid = String(required=True)
        message_uuid = String(required=True)

    @staticmethod
    def mutate(root: Any, info: Any, **kwargs: Dict[str, Any]) -> "DeleteMessage":
        try:
            if hasattr(resolve_message_list, "cache_clear"):
                resolve_message_list.cache_clear()  # Clear message lists
            ok = delete_message(info, **kwargs)
        except Exception as e:
            log = traceback.format_exc()
            info.context.get("logger").error(log)
            raise e

        return DeleteMessage(ok=ok)
