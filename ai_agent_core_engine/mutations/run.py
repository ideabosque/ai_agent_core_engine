# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import traceback
from typing import Any, Dict

from graphene import Boolean, Field, Int, List, Mutation, String

from silvaengine_utility import JSON

from ..models.run import delete_run, insert_update_run
from ..queries.run import resolve_run_list
from ..types.run import RunType


class InsertUpdateRun(Mutation):
    run = Field(RunType)

    class Arguments:
        thread_uuid = String(required=True)
        run_uuid = String(required=False)
        run_id = String(required=False)
        completion_tokens = Int(required=False)
        prompt_tokens = Int(required=False)
        total_tokens = Int(required=False)
        updated_by = String(required=True)

    @staticmethod
    def mutate(root: Any, info: Any, **kwargs: Dict[str, Any]) -> "InsertUpdateRun":
        try:
            if hasattr(resolve_run_list, "cache_clear"):
                resolve_run_list.cache_clear()  # Clear run lists
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
        run_uuid = String(required=True)

    @staticmethod
    def mutate(root: Any, info: Any, **kwargs: Dict[str, Any]) -> "DeleteRun":
        try:
            if hasattr(resolve_run_list, "cache_clear"):
                resolve_run_list.cache_clear()  # Clear run lists
            ok = delete_run(info, **kwargs)
        except Exception as e:
            log = traceback.format_exc()
            info.context.get("logger").error(log)
            raise e

        return DeleteRun(ok=ok)
