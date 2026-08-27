# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict, List

from graphene import ResolveInfo

from ..models.repositories import get_repo
from ..types.wizard_group import WizardGroupType


def insert_update_wizard_group_with_wizards(
    info: ResolveInfo, **kwargs: Dict[str, Any]
) -> WizardGroupType:
    partition_key = info.context.get("partition_key") or kwargs.get("partition_key")
    updated_by = kwargs.get("updated_by")
    wizard_group_data = {
        "partition_key": partition_key,
        "wizard_group_name": kwargs.get("wizard_group_name"),
        "wizard_group_description": kwargs.get("wizard_group_description"),
        "weight": kwargs.get("weight"),
        "updated_by": updated_by,
    }
    wizard_group_uuid = kwargs.get("wizard_group_uuid")
    if wizard_group_uuid is not None:
        wizard_group_data["wizard_group_uuid"] = wizard_group_uuid
    wizards = kwargs.get("wizards", [])
    wizard_uuids = insert_update_wizards(info, wizards, partition_key, updated_by)
    if wizard_group_uuid is not None:
        try:
            _wg = get_repo("wizard_group").get(
                partition_key=partition_key, wizard_group_uuid=wizard_group_uuid
            )
            _wg_dict = _wg if isinstance(_wg, dict) else _wg.__dict__
            wizard_group_wizard_uuids = _wg_dict.get("wizard_uuids") or []
            delete_wizard_uuids = [
                uuid for uuid in wizard_group_wizard_uuids if uuid not in wizard_uuids
            ]
            if len(delete_wizard_uuids) > 0:
                for wizard_uuid in delete_wizard_uuids:
                    get_repo("wizard").delete(
                        info, **{"partition_key": partition_key, "wizard_uuid": wizard_uuid}
                    )
        except Exception as e:
            wizard_group_wizard_uuids = []
    wizard_group_data["wizard_uuids"] = wizard_uuids
    return get_repo("wizard_group").insert_update(info, **wizard_group_data)


def delete_wizard_from_wizard_group(
    info: ResolveInfo, **kwargs: Dict[str, Any]
) -> bool:
    partition_key = info.context.get("partition_key") or kwargs.get("partition_key")
    wizard_uuid = kwargs.get("wizard_uuid")
    wizard_group_uuid = kwargs.get("wizard_group_uuid")
    updated_by = kwargs.get("updated_by")
    wizard_count = get_repo("wizard").count(
        partition_key=partition_key, wizard_uuid=wizard_uuid
    )
    if wizard_count == 0:
        raise Exception("Wizard is not exist")

    _wg = get_repo("wizard_group").get(
        partition_key=partition_key, wizard_group_uuid=wizard_group_uuid
    )
    _wg_dict = _wg if isinstance(_wg, dict) else _wg.__dict__
    wizard_group_wizard_uuids = _wg_dict.get("wizard_uuids") or []
    if wizard_uuid not in wizard_group_wizard_uuids:
        raise Exception("Wizard is not in this wizard group")

    wizard_group_wizard_uuids = [
        uuid for uuid in wizard_group_wizard_uuids if uuid != wizard_uuid
    ]
    get_repo("wizard_group").insert_update(
        info,
        **{
            "partition_key": partition_key,
            "wizard_group_uuid": wizard_group_uuid,
            "wizard_uuids": wizard_group_wizard_uuids,
            "updated_by": updated_by,
        },
    )
    return get_repo("wizard").delete(
        info, **{"partition_key": partition_key, "wizard_uuid": wizard_uuid}
    )


def insert_update_wizards(
    info: ResolveInfo, wizards: Dict[str, Any], partition_key: str, updated_by: Any
) -> List[str]:
    wizard_uuids = []
    if len(wizards) > 0:
        for wizard in wizards:
            wizard_data = {
                "partition_key": partition_key,
                "wizard_uuid": wizard.get("wizard_uuid"),
                "wizard_title": wizard.get("wizard_title"),
                "wizard_description": wizard.get("wizard_description"),
                "wizard_type": wizard.get("wizard_type"),
                "wizard_schema_type": wizard.get("wizard_schema_type"),
                "wizard_schema_name": wizard.get("wizard_schema_name"),
                "wizard_attributes": [
                    {
                        "name": wizard_attribute.get("name"),
                        "value": wizard_attribute.get("value"),
                    }
                    for wizard_attribute in wizard.get("wizard_attributes", [])
                ],
                "wizard_elements": insert_update_wizard_elements(
                    info, wizard.get("wizard_elements"), partition_key, updated_by
                ),
                "priority": wizard.get("priority"),
                "updated_by": updated_by,
            }
            saved_wizard = get_repo("wizard").insert_update(info, **wizard_data)
            _saved_wizard_dict = saved_wizard if isinstance(saved_wizard, dict) else saved_wizard.__dict__
            wizard_uuids.append(_saved_wizard_dict.get("wizard_uuid"))
    return wizard_uuids


def insert_update_wizard_elements(
    info: ResolveInfo,
    wizard_elements: Dict[str, Any],
    partition_key: str,
    updated_by: Any,
):
    wizard_element_list = []
    for wizard_element in wizard_elements:
        element_uuid = wizard_element.get("element_uuid")
        wizard_element_data = {
            "required": wizard_element.get("required"),
            "placeholder": wizard_element.get("placeholder"),
        }
        if element_uuid is None and wizard_element.get("element") is None:
            raise Exception("Element is required")

        if wizard_element.get("element") is not None:
            element = wizard_element.get("element", {})
            element_data = {
                "partition_key": partition_key,
                "element_uuid": element_uuid,
                "data_type": element.get("data_type"),
                "element_title": element.get("element_title"),
                "priority": element.get("priority"),
                "attribute_name": element.get("attribute_name"),
                "attribute_type": element.get("attribute_type"),
                "option_values": element.get("option_values", []),
                "pattern": element.get("pattern"),
                "conditions": element.get("conditions", []),
                "updated_by": updated_by,
            }
            saved_element = get_repo("element").insert_update(info, **element_data)
            if element_uuid is None:
                _saved_el_dict = saved_element if isinstance(saved_element, dict) else saved_element.__dict__
                element_uuid = _saved_el_dict.get("element_uuid")

        wizard_element_data["element_uuid"] = element_uuid
        wizard_element_list.append(wizard_element_data)
    return wizard_element_list
