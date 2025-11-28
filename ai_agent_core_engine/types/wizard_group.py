#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from graphene import DateTime, Int, List, ObjectType, String
from promise import Promise
from silvaengine_dynamodb_base import ListObjectType
from silvaengine_utility import JSON


class WizardGroupType(ObjectType):
    endpoint_id = String()
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
    wizards = List(JSON)

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
        if hasattr(parent, "wizards") and parent.wizards:
            return parent.wizards

        # Case 2: Load via DataLoader using wizard_uuids
        wizard_uuids = getattr(parent, "wizard_uuids", None)
        if not wizard_uuids:
            return []

        endpoint_id = parent.endpoint_id
        loaders = get_loaders(info.context)

        promises = [
            loaders.wizard_loader.load((endpoint_id, wizard_uuid))
            for wizard_uuid in wizard_uuids
        ]

        return Promise.all(promises).then(
            lambda wizard_dicts: [
                wizard_dict for wizard_dict in wizard_dicts if wizard_dict is not None
            ]
        )


class WizardGroupListType(ListObjectType):
    wizard_group_list = List(WizardGroupType)
