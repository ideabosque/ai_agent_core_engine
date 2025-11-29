#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from graphene import DateTime, List, ObjectType, String
from promise import Promise
from silvaengine_dynamodb_base import ListObjectType
from silvaengine_utility import JSON, Utility

from ..types.mcp_server import MCPServerType
from ..types.ui_component import UIComponentType


def _normalize_to_json(item):
    """Convert various object shapes to a JSON-serializable dict/primitive."""
    if isinstance(item, dict):
        return Utility.json_normalize(item)
    if hasattr(item, "attribute_values"):
        return Utility.json_normalize(item.attribute_values)
    if hasattr(item, "__dict__"):
        return Utility.json_normalize(
            {k: v for k, v in vars(item).items() if not k.startswith("_")}
        )
    return item


class PromptTemplateBaseType(ObjectType):
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


class PromptTemplateType(PromptTemplateBaseType):

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
        existing = getattr(parent, "mcp_servers", None)
        if isinstance(existing, list):
            return [_normalize_to_json(server) for server in existing]

        # Case 2: Load via DataLoader using mcp_server_refs
        mcp_server_refs = getattr(parent, "mcp_server_refs", None)
        if not mcp_server_refs:
            return []

        from ..models.batch_loaders import get_loaders

        endpoint_id = parent.endpoint_id
        loaders = get_loaders(info.context)

        promises = [
            loaders.mcp_server_loader.load((endpoint_id, ref["mcp_server_uuid"]))
            for ref in mcp_server_refs
            if "mcp_server_uuid" in ref
        ]

        return Promise.all(promises).then(
            lambda mcp_server_dicts: [
                _normalize_to_json(mcp_dict)
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
        existing = getattr(parent, "ui_components", None)
        if isinstance(existing, list):
            return [_normalize_to_json(ui_comp) for ui_comp in existing]

        # Case 2: Load via DataLoader using ui_component_refs
        ui_component_refs = getattr(parent, "ui_component_refs", None)
        if not ui_component_refs:
            return []

        from ..models.batch_loaders import get_loaders

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
    prompt_template_list = List(PromptTemplateBaseType)
