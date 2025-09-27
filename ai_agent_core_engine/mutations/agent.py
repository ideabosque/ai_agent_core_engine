# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import traceback
from typing import Any, Dict

from graphene import Boolean, Field, Int, List, Mutation, String

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
        instructions = String(required=False)
        configuration = JSON(required=False)
        mcp_server_uuids = List(String, required=False)
        variables = List(JSON, required=False)
        num_of_messages = Int(required=False)
        tool_call_role = String(required=False)
        flow_snippet_version_uuid = String(required=False)
        status = String(required=False)
        updated_by = String(required=True)

    @staticmethod
    def mutate(root: Any, info: Any, **kwargs: Dict[str, Any]) -> "InsertUpdateAgent":
        try:
            # Use cascading cache purging for agents
            from ..models.cache import purge_agent_cascading_cache

            cache_result = purge_agent_cascading_cache(
                endpoint_id=info.context["endpoint_id"],
                agent_uuid=kwargs.get("agent_uuid"),
                agent_version_uuid=kwargs.get("agent_version_uuid"),
                logger=info.context.get("logger"),
            )

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
            # Use cascading cache purging for agents
            # Get agent info before deletion for cache purging
            from ..models.agent import get_agent
            from ..models.cache import purge_agent_cascading_cache

            agent_entity = None
            try:
                agent_entity = get_agent(
                    info.context["endpoint_id"], kwargs["agent_version_uuid"]
                )
            except:
                pass  # Agent might not exist, continue with deletion

            cache_result = purge_agent_cascading_cache(
                endpoint_id=info.context["endpoint_id"],
                agent_uuid=agent_entity.agent_uuid if agent_entity else None,
                agent_version_uuid=kwargs.get("agent_version_uuid"),
                logger=info.context.get("logger"),
            )

            ok = delete_agent(info, **kwargs)
        except Exception as e:
            log = traceback.format_exc()
            info.context.get("logger").error(log)
            raise e

        return DeleteAgent(ok=ok)
