__author__ = "bibow"

import traceback
from typing import Any, Dict

from graphene import Boolean, Field, List, Mutation, String

from silvaengine_utility import JSONCamelCase

from ..models.thread import delete_thread, insert_thread
from ..types.thread import ThreadType


class InsertThread(Mutation):
    thread = Field(ThreadType)

    class Arguments:
        thread_uuid = String(required=False)
        agent_uuid = String(required=False)
        user_id = String(required=False)

    @staticmethod
    def mutate(root: Any, info: Any, **kwargs: Dict[str, Any]) -> "InsertThread":
        try:
            thread = insert_thread(info, **kwargs)
        except Exception as e:
            log = traceback.format_exc()
            info.context.get("logger").error(log)
            raise e

        return InsertThread(thread=thread)


class DeleteThread(Mutation):
    ok = Boolean()

    class Arguments:
        thread_uuid = String(required=True)

    @staticmethod
    def mutate(root: Any, info: Any, **kwargs: Dict[str, Any]) -> "DeleteThread":
        try:
            ok = delete_thread(info, **kwargs)
        except Exception as e:
            log = traceback.format_exc()
            info.context.get("logger").error(log)
            raise e

        return DeleteThread(ok=ok)
