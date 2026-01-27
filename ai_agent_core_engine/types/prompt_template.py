#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from graphene import DateTime, Field, List, ObjectType, String
from promise import Promise

from silvaengine_dynamodb_base import ListObjectType
from silvaengine_utility import JSONCamelCase

from ..types.mcp_server import MCPServerType
from ..utils.normalization import normalize_to_json


class PromptTemplateBaseType(ObjectType):
    partition_key = String()
    endpoint_id = String()
    part_id = String()
    prompt_version_uuid = String()
    prompt_uuid = String()
    prompt_type = String()
    prompt_name = String()
    prompt_description = String()
    template_context = String()
    variables = Field(JSONCamelCase)
    status = String()
    updated_by = String()
    created_at = DateTime()
    updated_at = DateTime()


class PromptTemplateType(PromptTemplateBaseType):
    mcp_servers = List(lambda: MCPServerType)
    ui_components = Field(JSONCamelCase)

    # Override mcp_servers and ui_components to return full entity data via DataLoader
    def resolve_mcp_servers(parent, info):
        # Get the MCP server references from the model
        mcp_server_refs = getattr(parent, "mcp_servers", None)

        if not mcp_server_refs:
            return []

        # Check if refs are already full objects (have more than just uuid)
        # If they already have full data (e.g., mcp_label, headers, tools), return them
        if isinstance(mcp_server_refs, list) and len(mcp_server_refs) > 0:
            first_ref = mcp_server_refs[0]
            if isinstance(first_ref, dict) and len(first_ref) > 1:
                # Has more than just mcp_server_uuid, likely full data
                return mcp_server_refs

        # Otherwise, load via DataLoader to get full entity data
        from ..models.batch_loaders import get_loaders

        partition_key = parent.partition_key
        loaders = get_loaders(info.context)

        promises = [
            loaders.mcp_server_loader.load(
                (
                    partition_key,
                    ref["mcp_server_uuid"] if isinstance(ref, dict) else ref,
                )
            )
            for ref in mcp_server_refs
            if (isinstance(ref, dict) and "mcp_server_uuid" in ref)
            or isinstance(ref, str)
        ]

        return Promise.all(promises)

    def resolve_ui_components(parent, info):
        # Get the UI component references from the model
        ui_component_refs = getattr(parent, "ui_components", None)

        if not ui_component_refs:
            return []

        # Check if refs are already full objects (have more than just type and uuid)
        # If they already have full data (e.g., tag_name, parameters, wait_for), return them
        if isinstance(ui_component_refs, list) and len(ui_component_refs) > 0:
            first_ref = ui_component_refs[0]
            if isinstance(first_ref, dict) and len(first_ref) > 2:
                # Has more than just ui_component_type and ui_component_uuid, likely full data
                return [normalize_to_json(ui_comp) for ui_comp in ui_component_refs]

        # Otherwise, load via DataLoader to get full entity data
        from ..models.batch_loaders import get_loaders

        loaders = get_loaders(info.context)

        promises = [
            loaders.ui_component_loader.load(
                (ref["ui_component_type"], ref["ui_component_uuid"])
            )
            for ref in ui_component_refs
            if isinstance(ref, dict)
            and "ui_component_type" in ref
            and "ui_component_uuid" in ref
        ]

        return Promise.all(promises).then(
            lambda ui_component_dicts: [
                normalize_to_json(ui_comp_dict)
                for ui_comp_dict in ui_component_dicts
                if ui_comp_dict is not None
            ]
        )


class PromptTemplateListType(ListObjectType):
    prompt_template_list = List(PromptTemplateBaseType)
