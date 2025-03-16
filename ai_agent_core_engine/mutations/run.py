# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import traceback
from typing import Any, Dict

from graphene import Boolean, Field, Int, List, Mutation, String

from silvaengine_utility import JSON

from ..models.run import delete_run, insert_update_run
from ..types.run import RunType


class InsertUpdateRun(Mutation):
    run = Field(RunType)

    class Arguments:
        thread_uuid = String(required=True)
        run_id = String(required=True)
        completion_tokens = Int(required=False)
        prompt_tokens = Int(required=False)
        total_tokens = Int(required=False)
        updated_by = String(required=True)

    @staticmethod
    def mutate(root: Any, info: Any, **kwargs: Dict[str, Any]) -> "InsertUpdateRun":
        try:
            run = insert_update_run(info, **kwargs)
        except Exception as e:
            log = traceback.format_exc()
            info.context.get("logger").error(log)
            raise e

        return InsertUpdateRun(run=run)


class DeleteRun(Mutation):
    ok = Boolean()

    class Arguments:
        thread_uuid = String(required=True)
        run_id = String(required=True)

    @staticmethod
    def mutate(root: Any, info: Any, **kwargs: Dict[str, Any]) -> "DeleteRun":
        try:
            ok = delete_run(info, **kwargs)
        except Exception as e:
            log = traceback.format_exc()
            info.context.get("logger").error(log)
            raise e

        return DeleteRun(ok=ok)
