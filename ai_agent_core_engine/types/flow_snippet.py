#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from graphene import DateTime, Field, List, ObjectType, String
from silvaengine_dynamodb_base import ListObjectType

from .prompt_template import PromptTemplateType


class FlowSnippetBaseType(ObjectType):
    endpoint_id = String()
    flow_snippet_version_uuid = String()
    flow_snippet_uuid = String()
    prompt_uuid = String()
    flow_name = String()
    status = String()
    updated_by = String()
    created_at = DateTime()
    updated_at = DateTime()

    # Nested resolvers with DataLoader batch fetching for efficient database access
    prompt_template = Field(lambda: PromptTemplateType)
    agents = List(lambda: AgentType)

    # ------- Nested resolvers -------

    def resolve_prompt_template(parent, info):
        """Resolve nested PromptTemplate for this flow snippet using DataLoader."""
        from ..models.batch_loaders import get_loaders

        # Case 2: already embedded
        existing = getattr(parent, "prompt_template", None)
        if isinstance(existing, dict):
            return PromptTemplateType(**existing)

        # Case 1: need to fetch using DataLoader
        endpoint_id = getattr(parent, "endpoint_id", None) or info.context.get(
            "endpoint_id"
        )
        prompt_uuid = getattr(parent, "prompt_uuid", None)
        if not endpoint_id or not prompt_uuid:
            return None

        loaders = get_loaders(info.context)
        return loaders.prompt_template_loader.load((endpoint_id, prompt_uuid)).then(
            lambda prompt_dict: (
                PromptTemplateType(**prompt_dict) if prompt_dict else None
            )
        )

    def resolve_agents(parent, info):
        """Resolve nested Agents that use this flow snippet using DataLoader.

        Note: Uses AgentsByFlowSnippetLoader for efficient batch loading of one-to-many
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

        # Fetch agents that use this flow snippet
        endpoint_id = info.context.get("endpoint_id")
        flow_snippet_version_uuid = getattr(parent, "flow_snippet_version_uuid", None)
        if not endpoint_id or not flow_snippet_version_uuid:
            return []

        loaders = get_loaders(info.context)
        return loaders.agents_by_flow_snippet_loader.load(
            (endpoint_id, flow_snippet_version_uuid)
        ).then(
            lambda agent_dicts: [AgentType(**agent_dict) for agent_dict in agent_dicts]
        )


class FlowSnippetType(FlowSnippetBaseType):
    flow_relationship = String()
    flow_context = String()


class FlowSnippetListType(ListObjectType):
    flow_snippet_list = List(FlowSnippetBaseType)


# Import at end to avoid circular dependency
from .agent import AgentType  # noqa: E402
