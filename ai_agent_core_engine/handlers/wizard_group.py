# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import threading
import traceback
from queue import Queue
from typing import Any, Dict, List

from graphene import ResolveInfo

from silvaengine_utility import Utility

from ..models.wizard_group import insert_update_wizard_group, get_wizard_group
from ..models.wizard import insert_update_wizard, delete_wizard, get_wizard_count
from ..models.element import insert_update_element
from .config import Config
from ..types.wizard_group import WizardGroupType

def insert_update_wizard_group_with_wizards(info: ResolveInfo, **kwargs: Dict[str, Any]) -> WizardGroupType:
    endpoint_id = info.context.get("endpoint_id") or kwargs.get("endpoint_id")
    updated_by = kwargs.get("updated_by")
    wizard_group_data = {
        "endpoint_id": endpoint_id,
        "wizard_group_name": kwargs.get("wizard_group_name"),
        "wizard_group_description": kwargs.get("wizard_group_description"),
        "weight": kwargs.get("weight"),
        "updated_by": updated_by
    }
    wizard_group_uuid = kwargs.get("wizard_group_uuid")
    if wizard_group_uuid is not None:
        wizard_group_data["wizard_group_uuid"] = wizard_group_uuid
    wizards = kwargs.get("wizards", [])
    wizard_uuids = insert_update_wizards(info, wizards, endpoint_id, updated_by)
    wizard_group_data["wizard_uuids"] = wizard_uuids
    return insert_update_wizard_group(info, **wizard_group_data)

def delete_wizard_from_wizard_group(info: ResolveInfo, **kwargs: Dict[str, Any]) -> bool:
    endpoint_id = info.context.get("endpoint_id") or kwargs.get("endpoint_id")
    wizard_uuid = kwargs.get("wizard_uuid")
    wizard_group_uuid = kwargs.get("wizard_group_uuid")
    updated_by = kwargs.get("updated_by")
    wizard_count = get_wizard_count(endpoint_id, wizard_uuid)
    if wizard_count == 0:
        raise Exception("Wizard is not exist")
    
    wizard_group = get_wizard_group(endpoint_id, wizard_group_uuid)
    wizard_group_wizard_uuids = wizard_group.wizard_uuids
    if wizard_uuid not in wizard_group.wizard_uuids:
        raise Exception("Wizard is not in this wizard group")
    
    wizard_group_wizard_uuids = [uuid for uuid in wizard_group_wizard_uuids if uuid != wizard_uuid]
    wizard_group = insert_update_wizard_group(info, **{
        "endpoint_id": endpoint_id,
        "wizard_group_uuid": wizard_group_uuid,
        "wizard_uuids": wizard_group_wizard_uuids,
        "updated_by": updated_by
    })
    return delete_wizard(info, **{"endpoint_id": endpoint_id, "wizard_uuid": wizard_uuid})


def insert_update_wizards(info: ResolveInfo, wizards: Dict[str, Any], endpoint_id: str, updated_by: Any) -> List[str]:
    wizard_uuids = []
    if len(wizards) > 0:
        for wizard in wizards:
            wizard_data = {
                "endpoint_id": endpoint_id,
                "wizard_uuid": wizard.get("wizard_uuid"),
                "wizard_title": wizard.get("wizard_title"),
                "wizard_description": wizard.get("wizard_description"),
                "wizard_type": wizard.get("wizard_type"),
                "wizard_schema_type": wizard.get("wizard_schema_type"),
                "wizard_schema_name": wizard.get("wizard_schema_name"),
                "wizard_attributes": [
                    {
                        "name": wizard_attribute.get("name"),
                        "value": wizard_attribute.get("value")
                    }
                    for wizard_attribute in wizard.get("wizard_attributes", [])
                ],
                "wizard_elements": insert_update_wizard_elements(info, wizard.get("wizard_elements"), endpoint_id, updated_by),
                "priority": wizard.get("priority"),
                "updated_by": updated_by
            }
            saved_wizard = insert_update_wizard(info, **wizard_data)
            wizard_uuids.append(saved_wizard.wizard_uuid)
    return wizard_uuids

def insert_update_wizard_elements(info: ResolveInfo, wizard_elements: Dict[str, Any], endpoint_id: str, updated_by: Any):
    wizard_element_list = []
    for wizard_element in wizard_elements:
        element_uuid = wizard_element.get("element_uuid")
        wizard_element_data ={
            "required": wizard_element.get("required"),
            "placeholder": wizard_element.get("placeholder"),
        }
        if element_uuid is None and wizard_element.get("element") is None:
            raise Exception("Element is required")
        
        if wizard_element.get("element") is not None:
            element = wizard_element.get("element", {})
            element_data = {
                "endpoint_id": endpoint_id,
                "element_uuid": element_uuid,
                "data_type": element.get("data_type"),
                "element_title": element.get("element_title"),
                "priority": element.get("priority"),
                "attribute_name": element.get("attribute_name"),
                "attribute_type": element.get("attribute_type"),
                "option_vlaues": element.get("option_vlaues", []),
                "pattern": element.get("pattern"),
                "conditions": element.get("conditions", []),
                "updated_by": updated_by,
            }
            saved_element = insert_update_element(info, **element_data)
            if element_uuid is None:
                element_uuid = saved_element.element_uuid

        wizard_element_data["element_uuid"] = element_uuid
        wizard_element_list.append(wizard_element_data)
    return wizard_element_list
