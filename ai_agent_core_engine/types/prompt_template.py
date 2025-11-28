#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from graphene import Boolean, DateTime, Field, List, ObjectType, String
from promise import Promise
from silvaengine_dynamodb_base import ListObjectType
from silvaengine_utility import JSON

from ..types.mcp_server import MCPServerType
from ..types.ui_component import UIComponentType


def get_loaders(context):
    """Get or create request-scoped loaders from context."""
    if not hasattr(context, "loaders"):
        from ..models.batch_loaders import RequestLoaders

        context.loaders = RequestLoaders(context, cache_enabled=True)
    return context.loaders


class PromptTemplateType(ObjectType):
    endpoint_id = String()
    prompt_version_uuid = String()
    prompt_uuid = String()
    prompt_type = String()
    prompt_name = String()
    prompt_description = String()
    template_context = String()
    variables = List(JSON)
    # Store raw list for mcp_servers and ui_components
    mcp_server_refs = List(JSON)  # List of {mcp_server_uuid: ...}
    ui_component_refs = List(
        JSON
    )  # List of {ui_component_type: ..., ui_component_uuid: ...}
    status = String()
    updated_by = String()
    created_at = DateTime()
    updated_at = DateTime()

    # Nested resolvers with DataLoader batch fetching for efficient database access
    mcp_servers = List(lambda: MCPServerType)
    ui_components = List(lambda: UIComponentType)

    def resolve_mcp_servers(parent, info):
        """
        Resolve MCP servers for this prompt template.
        Two cases:
        1. If mcp_servers is already embedded (dict list), convert to MCPServerType
        2. Otherwise, use mcp_server_refs to load via DataLoader
        """

        # Case 1: Already embedded (backward compatibility)
        if hasattr(parent, "mcp_servers") and parent.mcp_servers:
            return [MCPServerType(**server) for server in parent.mcp_servers]

        # Case 2: Load via DataLoader using mcp_server_refs
        mcp_server_refs = getattr(parent, "mcp_server_refs", None)
        if not mcp_server_refs:
            return []

        endpoint_id = parent.endpoint_id
        loaders = get_loaders(info.context)

        promises = [
            loaders.mcp_server_loader.load((endpoint_id, ref["mcp_server_uuid"]))
            for ref in mcp_server_refs
            if "mcp_server_uuid" in ref
        ]

        return Promise.all(promises).then(
            lambda mcp_server_dicts: [
                MCPServerType(**mcp_dict)
                for mcp_dict in mcp_server_dicts
                if mcp_dict is not None
            ]
        )

    def resolve_ui_components(parent, info):
        """
        Resolve UI components for this prompt template using DataLoader.
        Two cases:
        1. If ui_components is already embedded (dict list), convert to UIComponentType
        2. Otherwise, use ui_component_refs to load via DataLoader
        """
        # Case 1: Already embedded (backward compatibility)
        if hasattr(parent, "ui_components") and parent.ui_components:
            return [
                UIComponentType(**ui_comp) if isinstance(ui_comp, dict) else ui_comp
                for ui_comp in parent.ui_components
            ]

        # Case 2: Load via DataLoader using ui_component_refs
        ui_component_refs = getattr(parent, "ui_component_refs", None)
        if not ui_component_refs:
            return []

        loaders = get_loaders(info.context)

        promises = [
            loaders.ui_component_loader.load(
                (ref["ui_component_type"], ref["ui_component_uuid"])
            )
            for ref in ui_component_refs
            if "ui_component_type" in ref and "ui_component_uuid" in ref
        ]

        return Promise.all(promises).then(
            lambda ui_component_dicts: [
                UIComponentType(**ui_comp_dict)
                for ui_comp_dict in ui_component_dicts
                if ui_comp_dict is not None
            ]
        )


class PromptTemplateListType(ListObjectType):
    prompt_template_list = List(PromptTemplateType)
