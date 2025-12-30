#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from graphene import DateTime, Field, Int, List, ObjectType, String
from promise import Promise
from silvaengine_dynamodb_base import ListObjectType
from silvaengine_utility import JSON

from ..utils.normalization import normalize_to_json


class AgentTypeBase(ObjectType):
    """
    Base GraphQL type for Agent - Exposes all scalar fields.

    MIGRATION PATTERN (GraphQL Type Layer):
    1. Expose partition_key as a String field (composite: "endpoint_id#part_id")
    2. Expose denormalized endpoint_id and part_id fields for client convenience
    3. Store foreign keys (llm_provider, llm_name, mcp_server_uuids, flow_snippet_version_uuid)
       for nested resolvers to use

    USAGE:
    - Use AgentTypeBase for list queries where nested data is not needed
    - Use AgentType (extends this) when nested objects (llm, mcp_servers, flow_snippet) are required

    MIGRATION NOTE:
    - partition_key field added (was: only endpoint_id)
    - part_id field added (denormalized for client access)
    - Foreign keys exposed to support lazy loading in nested resolvers
    """

    # Primary Key (MIGRATED)
    partition_key = String()  # Composite: "endpoint_id#part_id" (assembled in main.py)
    agent_version_uuid = String()

    # Denormalized attributes (NEW - exposed for client convenience)
    endpoint_id = String()  # Platform partition (e.g., "aws-prod-us-east-1")
    part_id = String()  # Business partition (e.g., "acme-corp")

    # Agent identifiers
    agent_uuid = String()
    agent_name = String()
    agent_description = String()

    # Foreign keys for nested resolvers (stored for lazy loading)
    llm_provider = String()  # FK for resolve_llm
    llm_name = String()  # FK for resolve_llm
    mcp_server_uuids = List(String)  # FKs for resolve_mcp_servers
    flow_snippet_version_uuid = String()  # FK for resolve_flow_snippet

    instructions = String()
    configuration = JSON()
    variables = List(JSON)
    num_of_messages = Int()
    tool_call_role = String()
    status = String()
    updated_by = String()
    created_at = DateTime()
    updated_at = DateTime()


class AgentType(AgentTypeBase):
    """
    Full GraphQL type for Agent with nested resolvers.

    NESTED RESOLVER PATTERN:
    - Uses DataLoader for batch fetching to avoid N+1 queries
    - Resolvers check for embedded data first (Case 2), then fetch via DataLoader (Case 1)
    - Nested data is loaded lazily only when requested in the GraphQL query

    MIGRATION NOTE (Nested Resolvers):
    - All nested resolvers extract partition_key from info.context
    - DataLoaders use (partition_key, foreign_key) tuples instead of (endpoint_id, foreign_key)
    - This maintains efficient batch loading with the new composite key pattern
    """

    # Nested resolvers with DataLoader batch fetching for efficient database access
    llm = Field(
        lambda: LlmType
    )  # Resolved via resolve_llm using llm_provider + llm_name
    mcp_servers = List(JSON)  # Resolved via resolve_mcp_servers using mcp_server_uuids
    flow_snippet = Field(
        lambda: FlowSnippetType
    )  # Resolved via resolve_flow_snippet using flow_snippet_version_uuid

    # ------- Nested resolvers -------

    def resolve_llm(parent, info):
        """
        Resolve nested LLM for this agent using DataLoader.

        MIGRATION NOTE: LLM uses (llm_provider, llm_name) composite key, NOT partition_key.
        LLMs are global entities, not partitioned by endpoint/part.

        Pattern:
        1. Check if already embedded (Case 2)
        2. Fetch via DataLoader if needed (Case 1)
        """
        from ..models.batch_loaders import get_loaders

        # Case 2: already embedded
        existing = getattr(parent, "llm", None)
        if isinstance(existing, dict):
            return LlmType(**existing)
        if isinstance(existing, LlmType):
            return existing

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
        from ..models.batch_loaders import get_loaders

        # Check if already embedded
        existing = getattr(parent, "mcp_servers", None)
        if isinstance(existing, list):
            return [normalize_to_json(mcp_dict) for mcp_dict in existing]

        # Fetch MCP servers for this agent
        # MIGRATION: Extract partition_key from context (was: endpoint_id)
        partition_key = info.context.get("partition_key")
        mcp_server_uuids = getattr(parent, "mcp_server_uuids", None)
        if not partition_key or not mcp_server_uuids:
            return []

        loaders = get_loaders(info.context)
        # Load all MCP servers in parallel using (partition_key, uuid) tuples
        promises = [
            loaders.mcp_server_loader.load((partition_key, mcp_uuid))
            for mcp_uuid in mcp_server_uuids
        ]

        def filter_results(mcp_dicts):
            # Keep payload JSON-ready; filter out missing lookups.
            return [normalize_to_json(mcp_dict) for mcp_dict in mcp_dicts if mcp_dict]

        return Promise.all(promises).then(filter_results)

    def resolve_flow_snippet(parent, info):
        from ..models.batch_loaders import get_loaders

        # Check if already embedded
        existing = getattr(parent, "flow_snippet", None)

        if isinstance(existing, dict):
            return [
                FlowSnippetType(**flow_snippet_dict) for flow_snippet_dict in existing
            ]

        # Fetch flow snippet if version UUID exists
        # MIGRATION: Extract partition_key from context (was: endpoint_id)
        partition_key = info.context.get("partition_key")
        flow_snippet_version_uuid = getattr(parent, "flow_snippet_version_uuid", None)

        if not partition_key or not flow_snippet_version_uuid:
            return None

        loaders = get_loaders(info.context)
        # Load using (partition_key, version_uuid) tuple
        return loaders.flow_snippet_loader.load(
            (partition_key, flow_snippet_version_uuid)
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
