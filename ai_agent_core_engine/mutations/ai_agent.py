# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import traceback
from typing import Any, Dict

from graphene import Boolean, Field, Mutation, String

from silvaengine_utility import JSON

from ..handlers import ai_agent
from ..types.ai_agent import FileType


class ExecuteAskModel(Mutation):
    ok = Boolean()

    class Arguments:
        async_task_uuid = String(required=True)
        arguments = JSON(required=True)

    @staticmethod
    def mutate(root: Any, info: Any, **kwargs: Dict[str, Any]) -> "ExecuteAskModel":
        try:
            ok = ai_agent.execute_ask_model(info, **kwargs)
        except Exception as e:
            log = traceback.format_exc()
            info.context.get("logger").error(log)
            raise e

        return ExecuteAskModel(ok=ok)


class UploadFile(Mutation):
    uploaded_file = Field(FileType)

    class Arguments:
        agent_uuid = String(required=True)
        arguments = JSON(required=True)

    @staticmethod
    def mutate(root: Any, info: Any, **kwargs: Dict[str, Any]) -> "UploadFile":
        try:
            uploaded_file = ai_agent.upload_file(info, **kwargs)
        except Exception as e:
            log = traceback.format_exc()
            info.context.get("logger").error(log)
            raise e

        return UploadFile(uploaded_file=uploaded_file)
