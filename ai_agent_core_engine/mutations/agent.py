# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import traceback
from typing import Any, Dict

from graphene import Boolean, Field, List, Mutation, String

from silvaengine_utility import JSON

from ..models.agent import delete_agent, insert_update_agent
from ..types.agent import AgentType


class InsertUpdateAgent(Mutation):
    agent = Field(AgentType)

    class Arguments:
        agent_version_uuid = String(required=False)
        agent_uuid = String(required=False)
        agent_name = String(required=False)
        agent_description = String(required=False)
        llm_provider = String(required=False)
        llm_name = String(required=False)
        llm_configuration = JSON(required=False)
        instructions = String(required=False)
        configuration = JSON(required=False)
        function_configuration = JSON(required=False)
        functions = JSON(required=False)
        status = String(required=False)
        updated_by = String(required=True)

    @staticmethod
    def mutate(root: Any, info: Any, **kwargs: Dict[str, Any]) -> "InsertUpdateAgent":
        try:
            agent = insert_update_agent(info, **kwargs)
        except Exception as e:
            log = traceback.format_exc()
            info.context.get("logger").error(log)
            raise e

        return InsertUpdateAgent(agent=agent)


class DeleteAgent(Mutation):
    ok = Boolean()

    class Arguments:
        agent_version_uuid = String(required=True)

    @staticmethod
    def mutate(root: Any, info: Any, **kwargs: Dict[str, Any]) -> "DeleteAgent":
        try:
            ok = delete_agent(info, **kwargs)
        except Exception as e:
            log = traceback.format_exc()
            info.context.get("logger").error(log)
            raise e

        return DeleteAgent(ok=ok)
