#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from graphene import DateTime, Int, List, ObjectType, String
from promise import Promise
from silvaengine_dynamodb_base import ListObjectType
from silvaengine_utility import JSONCamelCase

from ..types.wizard import WizardType
from ..utils.normalization import normalize_to_json


class WizardGroupType(ObjectType):
    partition_key = String()
    endpoint_id = String()
    part_id = String()
    wizard_group_uuid = String()
    wizard_group_name = String()
    wizard_group_description = String()
    weight = Int()
    # Store raw wizard UUIDs
    wizard_uuids = List(String)
    updated_by = String()
    created_at = DateTime()
    updated_at = DateTime()

    # Nested resolver for strongly-typed relationships
    wizards = List(JSONCamelCase)
    wizard_items = List(lambda: WizardType)

    def resolve_wizards(parent, info):
        """
        Resolve wizards for this wizard group.
        Two cases:
        1. If wizards is already embedded, return as-is
        2. Otherwise, use wizard_uuids to load wizards via DataLoader
        """
        """Resolve nested Run for this tool call using DataLoader."""
        from ..models.batch_loaders import get_loaders

        # Case 1: Already embedded (backward compatibility)
        existing = getattr(parent, "wizards", None)

        if isinstance(existing, list):
            return existing

        # Case 2: Load via DataLoader using wizard_uuids
        wizard_uuids = getattr(parent, "wizard_uuids", None)

        if not wizard_uuids:
            return []

        partition_key = parent.partition_key

        
        try:
            loaders = get_loaders(info.context)

            promises = [
                loaders.wizard_loader.load((partition_key, wizard_uuid))
                for wizard_uuid in wizard_uuids
            ]

            def build_wizards(wizard_dicts):
                from ..models.wizard_schema import get_wizard_schema
                wizards = []
                def build_wizard_elements(wizard_dict):
                    wizard_elements = []
                    element_refs = [
                        wizard_element_dict
                        for wizard_element_dict in wizard_dict.get("wizard_elements", [])
                        if "element_uuid" in wizard_element_dict
                    ]
                    if len(element_refs) == 0:
                        return []
                    element_promises = [
                        loaders.element_loader.load((partition_key, ref["element_uuid"]))
                        for ref in wizard_dict.get("wizard_elements", [])
                        if "element_uuid" in ref
                    ]
                    element_dicts = Promise.all(element_promises).get()
                    for i, element_dict in enumerate(element_dicts):
                        if element_dict is not None:
                            ref = element_refs[i]
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
                
                for i, wizard_dict in enumerate(wizard_dicts):
                    if wizard_dict is not None:
                        # ref = wizard_element_refs[i]
                        wizard_schema = None
                        if wizard_dict.get("wizard_schema_type") and wizard_dict.get("wizard_schema_name"):
                            wizard_schema = get_wizard_schema(
                                wizard_dict.get("wizard_schema_type"),
                                wizard_dict.get("wizard_schema_name"),
                            )
                        wizards.append(
                            
                            normalize_to_json(
                                dict(
                                    wizard_dict,
                                    **{
                                        "wizard_schema": wizard_schema,
                                        "wizard_elements": build_wizard_elements(wizard_dict)
                                    }
                                )
                            )
                        )
                return wizards

            return (
                Promise.all(promises)
                .then(
                    build_wizards
                )
                .catch(lambda error: [])
            )
        except ImportError as exc:
            info.context.get("logger").error(
                "Failed to import DataLoader module: %s", exc, exc_info=True
            )
            return []
        except Exception as exc:
            info.context.get("logger").error(
                "Unexpected error in resolve_wizards for group %s: %s",
                getattr(parent, "wizard_group_uuid", "unknown"),
                exc,
                exc_info=True,
            )
            return []
    
    def resolve_wizard_items(parent, info):
        """
        Resolve wizards for this wizard group.
        Two cases:
        1. If wizards is already embedded, return as-is
        2. Otherwise, use wizard_uuids to load wizards via DataLoader
        """
        """Resolve nested Run for this tool call using DataLoader."""
        from ..models.batch_loaders import get_loaders

        # Case 1: Already embedded (backward compatibility)
        existing = getattr(parent, "wizards", None)

        if isinstance(existing, list):
            return existing

        # Case 2: Load via DataLoader using wizard_uuids
        wizard_uuids = getattr(parent, "wizard_uuids", None)

        if not wizard_uuids:
            return []

        partition_key = parent.partition_key

        
        try:
            loaders = get_loaders(info.context)

            promises = [
                loaders.wizard_loader.load((partition_key, wizard_uuid))
                for wizard_uuid in wizard_uuids
            ]

            return (
                Promise.all(promises)
                .then(
                    lambda wizard_dicts: [
                        WizardType(**wizard_dict) if wizard_dict else None
                        for wizard_dict in wizard_dicts
                    ]
                )
                .catch(lambda error: [])
            )
        except ImportError as exc:
            info.context.get("logger").error(
                "Failed to import DataLoader module: %s", exc, exc_info=True
            )
            return []
        except Exception as exc:
            info.context.get("logger").error(
                "Unexpected error in resolve_wizards for group %s: %s",
                getattr(parent, "wizard_group_uuid", "unknown"),
                exc,
                exc_info=True,
            )
            return []
        
class WizardGroupListType(ListObjectType):
    wizard_group_list = List(WizardGroupType)
