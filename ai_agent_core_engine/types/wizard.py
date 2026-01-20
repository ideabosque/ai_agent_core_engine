#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from graphene import DateTime, Field, Int, List, ObjectType, String
from promise import Promise
from silvaengine_dynamodb_base import ListObjectType
from silvaengine_utility import JSONCamelCase

from ..types.wizard_schema import WizardSchemaType
from ..types.element import ElementType
from ..utils.normalization import normalize_to_json


class WizardType(ObjectType):
    partition_key = String()
    endpoint_id = String()
    part_id = String()
    wizard_uuid = String()
    wizard_title = String()
    wizard_description = String()
    wizard_type = String()
    # Store foreign keys for wizard_schema
    wizard_schema_type = String()
    wizard_schema_name = String()
    wizard_attributes = List(JSONCamelCase)
    # Store raw element references
    wizard_element_refs = List(JSONCamelCase)  # List of {element_uuid, required, placeholder}
    priority = Int()
    updated_by = String()
    created_at = DateTime()
    updated_at = DateTime()

    # Nested resolvers for strongly-typed relationships
    wizard_schema = Field(lambda: WizardSchemaType)
    wizard_elements = List(JSONCamelCase)  # Will include both element data and metadata

    def resolve_wizard_schema(parent, info):
        """
        Resolve wizard schema for this wizard.
        Two cases:
        1. If wizard_schema is already embedded (dict), convert to WizardSchemaType
        2. Otherwise, fetch via direct query using wizard_schema_type and wizard_schema_name
        """

        """Resolve nested Run for this tool call using DataLoader."""
        # from ..models.batch_loaders import get_loaders

        # Case 1: Already embedded (backward compatibility)
        if hasattr(parent, "wizard_schema") and parent.wizard_schema:
            return WizardSchemaType(**parent.wizard_schema)

        # Case 2: Fetch directly (wizard_schema uses different key structure)
        wizard_schema_type = getattr(parent, "wizard_schema_type", None)
        wizard_schema_name = getattr(parent, "wizard_schema_name", None)
        if not wizard_schema_type or not wizard_schema_name:
            return None

        from ..models.wizard_schema import get_wizard_schema

        try:
            wizard_schema = get_wizard_schema(wizard_schema_type, wizard_schema_name)
            return WizardSchemaType(**wizard_schema.__dict__["attribute_values"])
        except Exception:
            return None

    def resolve_wizard_elements(parent, info):
        """
        Resolve wizard elements for this wizard.
        Two cases:
        1. If wizard_elements is already embedded, return as-is
        2. Otherwise, use wizard_element_refs to load elements via DataLoader
        """
        """Resolve nested Run for this tool call using DataLoader."""
        from ..models.batch_loaders import get_loaders

        # Case 1: Already embedded (backward compatibility)
        # if hasattr(parent, "wizard_elements") and parent.wizard_elements:
        #     return parent.wizard_elements

        # Case 2: Load via DataLoader using wizard_element_refs
        # wizard_element_refs = getattr(parent, "wizard_element_refs", None)
        # if not wizard_element_refs:
        #     return []

        wizard_element_refs = parent.wizard_elements
        partition_key = parent.partition_key
        loaders = get_loaders(info.context)

        promises = [
            loaders.element_loader.load((partition_key, ref["element_uuid"]))
            for ref in wizard_element_refs
            if "element_uuid" in ref
        ]

        def build_wizard_elements(element_dicts):
            wizard_elements = []
            for i, element_dict in enumerate(element_dicts):
                if element_dict is not None:
                    ref = wizard_element_refs[i]
                    wizard_elements.append(
                        normalize_to_json(
                            {
                                "element": element_dict,
                                "required": ref.get("required", False),
                                "placeholder": ref.get("placeholder"),
                            }
                        )
                    )
            return wizard_elements

        return Promise.all(promises).then(build_wizard_elements)


class WizardListType(ListObjectType):
    wizard_list = List(WizardType)
