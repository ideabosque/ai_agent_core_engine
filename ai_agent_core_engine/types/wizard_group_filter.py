#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from graphene import DateTime, Field, Int, List, ObjectType, String
from silvaengine_dynamodb_base import ListObjectType
from silvaengine_utility import JSON

from ..types.wizard_group import WizardGroupType


class WizardGroupFilterType(ObjectType):
    endpoint_id = String()
    wizard_group_filter_uuid = String()
    wizard_group_filter_name = String()
    wizard_group_filter_description = String()
    region = String()
    criteria = JSON()
    weight = Int()
    # Store foreign key for wizard_group
    wizard_group_uuid = String()
    updated_by = String()
    created_at = DateTime()
    updated_at = DateTime()

    # Nested resolver for strongly-typed relationship
    wizard_group = Field(lambda: WizardGroupType)

    def resolve_wizard_group(parent, info):
        """
        Resolve wizard group for this wizard group filter.
        Two cases:
        1. If wizard_group is already embedded (dict), convert to WizardGroupType
        2. Otherwise, use wizard_group_uuid to load via DataLoader
        """

        """Resolve nested Run for this tool call using DataLoader."""
        from ..models.batch_loaders import get_loaders

        # Case 1: Already embedded (backward compatibility)
        if hasattr(parent, "wizard_group") and parent.wizard_group:
            return WizardGroupType(**parent.wizard_group)

        # Case 2: Load via DataLoader using wizard_group_uuid
        wizard_group_uuid = getattr(parent, "wizard_group_uuid", None)
        if not wizard_group_uuid:
            return None

        endpoint_id = parent.endpoint_id
        loaders = get_loaders(info.context)

        return loaders.wizard_group_loader.load((endpoint_id, wizard_group_uuid)).then(
            lambda wizard_group_dict: (
                WizardGroupType(**wizard_group_dict) if wizard_group_dict else None
            )
        )


class WizardGroupFilterListType(ListObjectType):
    wizard_group_filter_list = List(WizardGroupFilterType)
