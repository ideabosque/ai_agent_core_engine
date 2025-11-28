#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from graphene import DateTime, Field, Int, List, ObjectType, String
from promise import Promise

from silvaengine_dynamodb_base import ListObjectType
from silvaengine_utility import JSON

from .mcp_server import MCPServerType


class AgentType(ObjectType):
    endpoint_id = String()
    agent_version_uuid = String()
    agent_uuid = String()
    agent_name = String()
    agent_description = String()

    # Store raw foreign keys
    llm_provider = String()
    llm_name = String()
    mcp_server_uuids = List(String)
    flow_snippet_version_uuid = String()

    instructions = String()
    configuration = JSON()
    variables = List(JSON)
    num_of_messages = Int()
    tool_call_role = String()
    status = String()
    updated_by = String()
    created_at = DateTime()
    updated_at = DateTime()

    # Nested resolvers with DataLoader batch fetching for efficient database access
    llm = Field(lambda: LlmType)
    mcp_servers = List(lambda: MCPServerType)
    flow_snippet = Field(lambda: FlowSnippetType)

    # ------- Nested resolvers -------

    def resolve_llm(parent, info):
        """Resolve nested LLM for this agent using DataLoader."""
        from ..models.batch_loaders import get_loaders
        from .llm import LlmType

        # Case 2: already embedded
        existing = getattr(parent, "llm", None)
        if isinstance(existing, dict):
            return LlmType(**existing)

        # Case 1: need to fetch using DataLoader
        llm_provider = getattr(parent, "llm_provider", None)
        llm_name = getattr(parent, "llm_name", None)
        if not llm_provider or not llm_name:
            return None

        loaders = get_loaders(info.context)
        return loaders.llm_loader.load((llm_provider, llm_name)).then(
            lambda llm_dict: LlmType(**llm_dict) if llm_dict else None
        )

    def resolve_mcp_servers(parent, info):
        """Resolve nested MCP Servers for this agent using DataLoader."""
        from ..models.batch_loaders import get_loaders

        # Check if already embedded
        existing = getattr(parent, "mcp_servers", None)
        if isinstance(existing, list) and existing:

            return [
                MCPServerType(**mcp) if isinstance(mcp, dict) else mcp
                for mcp in existing
            ]

        # Fetch MCP servers for this agent
        endpoint_id = info.context.get("endpoint_id")
        mcp_server_uuids = getattr(parent, "mcp_server_uuids", None)
        if not endpoint_id or not mcp_server_uuids:
            return []

        loaders = get_loaders(info.context)
        # Load all MCP servers in parallel
        promises = [
            loaders.mcp_server_loader.load((endpoint_id, mcp_uuid))
            for mcp_uuid in mcp_server_uuids
        ]

        def convert_to_types(mcp_dicts):
            return [
                MCPServerType(**mcp_dict) if mcp_dict else None
                for mcp_dict in mcp_dicts
            ]

        return Promise.all(promises).then(convert_to_types)

    def resolve_flow_snippet(parent, info):
        """Resolve nested FlowSnippet for this agent using DataLoader."""
        from ..models.batch_loaders import get_loaders
        from .flow_snippet import FlowSnippetType

        # Check if already embedded
        existing = getattr(parent, "flow_snippet", None)
        if isinstance(existing, dict):

            return FlowSnippetType(**existing)

        # Fetch flow snippet if version UUID exists
        endpoint_id = info.context.get("endpoint_id")
        flow_snippet_version_uuid = getattr(parent, "flow_snippet_version_uuid", None)
        if not endpoint_id or not flow_snippet_version_uuid:
            return None

        loaders = get_loaders(info.context)
        return loaders.flow_snippet_loader.load(
            (endpoint_id, flow_snippet_version_uuid)
        ).then(
            lambda flow_snippet_dict: (
                FlowSnippetType(**flow_snippet_dict) if flow_snippet_dict else None
            )
        )


class AgentListType(ListObjectType):
    agent_list = List(AgentType)


# Import at end to avoid circular dependency
from .flow_snippet import FlowSnippetType  # noqa: E402
from .llm import LlmType  # noqa: E402
from .thread import ThreadType  # noqa: E402
