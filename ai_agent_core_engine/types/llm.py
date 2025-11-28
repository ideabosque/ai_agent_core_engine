#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from graphene import DateTime, List, ObjectType, String
from silvaengine_dynamodb_base import ListObjectType
from silvaengine_utility import JSON


class LlmType(ObjectType):
    llm_provider = String()
    llm_name = String()
    module_name = String()
    class_name = String()
    configuration_schema = JSON()
    updated_by = String()
    created_at = DateTime()
    updated_at = DateTime()

    # Nested resolvers with DataLoader batch fetching for efficient database access
    agents = List(lambda: AgentType)

    # ------- Nested resolvers -------

    def resolve_agents(parent, info):
        """Resolve nested Agents for this LLM using DataLoader.

        Note: Uses AgentsByLlmLoader for efficient batch loading of one-to-many
        relationships with caching support.
        """
        from ..models.batch_loaders import get_loaders
        from .agent import AgentType

        # Check if already embedded
        existing = getattr(parent, "agents", None)
        if isinstance(existing, list) and existing:

            return [
                AgentType(**agent) if isinstance(agent, dict) else agent
                for agent in existing
            ]

        # Fetch agents that use this LLM
        llm_provider = getattr(parent, "llm_provider", None)
        llm_name = getattr(parent, "llm_name", None)
        if not llm_provider or not llm_name:
            return []

        endpoint_id = info.context.get("endpoint_id")
        if not endpoint_id:
            return []

        loaders = get_loaders(info.context)
        return loaders.agents_by_llm_loader.load(
            (endpoint_id, llm_provider, llm_name)
        ).then(
            lambda agent_dicts: [AgentType(**agent_dict) for agent_dict in agent_dicts]
        )


class LlmListType(ListObjectType):
    llm_list = List(LlmType)


# Import at end to avoid circular dependency
from .agent import AgentType  # noqa: E402
