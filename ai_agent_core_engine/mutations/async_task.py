# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import traceback
from typing import Any, Dict

from graphene import Boolean, Field, Int, List, Mutation, String

from silvaengine_utility import JSON

from ..models.async_task import delete_async_task, insert_update_async_task
from ..types.async_task import AsyncTaskType


class InsertUpdateAsyncTask(Mutation):
    async_task = Field(AsyncTaskType)

    class Arguments:
        function_name = String(required=True)
        async_task_uuid = String(required=False)
        task_type = String(required=False)
        arguments = JSON(required=False)
        result = String(required=False)
        output_files = List(JSON, required=False)
        status = String(required=False)
        notes = String(required=False)
        updated_by = String(required=True)

    @staticmethod
    def mutate(
        root: Any, info: Any, **kwargs: Dict[str, Any]
    ) -> "InsertUpdateAsyncTask":
        try:
            async_task = insert_update_async_task(info, **kwargs)
        except Exception as e:
            log = traceback.format_exc()
            info.context.get("logger").error(log)
            raise e

        return InsertUpdateAsyncTask(async_task=async_task)


class DeleteAsyncTask(Mutation):
    ok = Boolean()

    class Arguments:
        function_name = String(required=True)
        async_task_uuid = String(required=True)

    @staticmethod
    def mutate(root: Any, info: Any, **kwargs: Dict[str, Any]) -> "DeleteAsyncTask":
        try:
            ok = delete_async_task(info, **kwargs)
        except Exception as e:
            log = traceback.format_exc()
            info.context.get("logger").error(log)
            raise e

        return DeleteAsyncTask(ok=ok)
