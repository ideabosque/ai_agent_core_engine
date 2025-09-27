#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import logging
import traceback
from typing import Any, Dict

import pendulum
from graphene import ResolveInfo
from pynamodb.attributes import (
    ListAttribute,
    MapAttribute,
    NumberAttribute,
    UnicodeAttribute,
    UTCDateTimeAttribute,
)
from pynamodb.indexes import AllProjection, LocalSecondaryIndex
from tenacity import retry, stop_after_attempt, wait_exponential

from silvaengine_dynamodb_base import (
    BaseModel,
    delete_decorator,
    insert_update_decorator,
    monitor_decorator,
    resolve_list_decorator,
)
from silvaengine_utility import Utility, method_cache

from ..types.wizard_group import WizardGroupListType, WizardGroupType
from .utils import _get_wizard


class WizardGroupModel(BaseModel):
    class Meta(BaseModel.Meta):
        table_name = "aace-wizard_groups"

    endpoint_id = UnicodeAttribute(hash_key=True)
    wizard_group_uuid = UnicodeAttribute(range_key=True)
    wizard_group_name = UnicodeAttribute()
    wizard_group_description = UnicodeAttribute(null=True)
    weight = NumberAttribute(default=0)
    wizard_uuids = ListAttribute(null=True)
    updated_by = UnicodeAttribute()
    created_at = UTCDateTimeAttribute()
    updated_at = UTCDateTimeAttribute()


def create_wizard_group_table(logger: logging.Logger) -> bool:
    """Create the WizardGroup table if it doesn't exist."""
    if not WizardGroupModel.exists():
        # Create with on-demand billing (PAY_PER_REQUEST)
        WizardGroupModel.create_table(billing_mode="PAY_PER_REQUEST", wait=True)
        logger.info("The WizardGroup table has been created.")
    return True


@retry(
    reraise=True,
    wait=wait_exponential(multiplier=1, max=60),
    stop=stop_after_attempt(5),
)
def get_wizard_group(endpoint_id: str, wizard_group_uuid: str) -> WizardGroupModel:
    return WizardGroupModel.get(endpoint_id, wizard_group_uuid)


def get_wizard_group_count(endpoint_id: str, wizard_group_uuid: str) -> int:
    return WizardGroupModel.count(
        endpoint_id, WizardGroupModel.wizard_group_uuid == wizard_group_uuid
    )


@method_cache(ttl=1800, cache_name="ai_agent_core_engine.models.wizard_group")
def get_wizard_group_type(
    info: ResolveInfo, wizard_group: WizardGroupModel
) -> WizardGroupType:
    try:
        wizards = [
            _get_wizard(wizard_group.endpoint_id, wizard_uuid)
            for wizard_uuid in wizard_group.wizard_uuids
        ]
    except Exception as e:
        log = traceback.format_exc()
        info.context.get("logger").exception(log)
        raise e
    wizard_group = wizard_group.__dict__["attribute_values"]
    wizard_group["wizards"] = wizards
    wizard_group.pop("wizard_uuids")
    return WizardGroupType(**Utility.json_normalize(wizard_group))


def resolve_wizard_group(
    info: ResolveInfo, **kwargs: Dict[str, Any]
) -> WizardGroupType:
    count = get_wizard_group_count(
        info.context["endpoint_id"], kwargs["wizard_group_uuid"]
    )
    if count == 0:
        return None

    return get_wizard_group_type(
        info, get_wizard_group(info.context["endpoint_id"], kwargs["wizard_group_uuid"])
    )


@monitor_decorator
@resolve_list_decorator(
    attributes_to_get=["endpoint_id", "wizard_group_uuid"],
    list_type_class=WizardGroupListType,
    type_funct=get_wizard_group_type,
)
def resolve_wizard_group_list(info: ResolveInfo, **kwargs: Dict[str, Any]) -> Any:
    endpoint_id = info.context["endpoint_id"]
    wizard_group_name = kwargs.get("wizard_group_name")

    args = []
    inquiry_funct = WizardGroupModel.scan
    count_funct = WizardGroupModel.count
    if endpoint_id:
        args = [endpoint_id, None]
        inquiry_funct = WizardGroupModel.query

    the_filters = None
    if wizard_group_name:
        the_filters &= WizardGroupModel.wizard_group_name == wizard_group_name
    if the_filters is not None:
        args.append(the_filters)

    return inquiry_funct, count_funct, args


@insert_update_decorator(
    keys={
        "hash_key": "endpoint_id",
        "range_key": "wizard_group_uuid",
    },
    model_funct=get_wizard_group,
    count_funct=get_wizard_group_count,
    type_funct=get_wizard_group_type,
)
def insert_update_wizard_group(info: ResolveInfo, **kwargs: Dict[str, Any]) -> None:
    endpoint_id = kwargs.get("endpoint_id")
    wizard_group_uuid = kwargs.get("wizard_group_uuid")

    if kwargs.get("entity") is None:
        cols = {
            "wizard_group_name": kwargs["wizard_group_name"],
            "wizard_group_description": kwargs.get("wizard_group_description"),
            "weight": kwargs.get("weight", 0),
            "wizard_uuids": kwargs.get("wizard_uuids", []),
            "updated_by": kwargs["updated_by"],
            "created_at": pendulum.now("UTC"),
            "updated_at": pendulum.now("UTC"),
        }
        WizardGroupModel(
            endpoint_id,
            wizard_group_uuid,
            **cols,
        ).save()
        return

    wizard_group = kwargs.get("entity")
    actions = [
        WizardGroupModel.updated_by.set(kwargs["updated_by"]),
        WizardGroupModel.updated_at.set(pendulum.now("UTC")),
    ]

    field_map = {
        "wizard_group_name": WizardGroupModel.wizard_group_name,
        "wizard_group_description": WizardGroupModel.wizard_group_description,
        "weight": WizardGroupModel.weight,
        "wizard_uuids": WizardGroupModel.wizard_uuids,
    }

    for key, field in field_map.items():
        if key in kwargs:
            actions.append(field.set(None if kwargs[key] == "null" else kwargs[key]))

    wizard_group.update(actions=actions)

    # Clear cache for the updated wizard group
    if hasattr(get_wizard_group_type, 'cache_delete'):
        get_wizard_group_type.cache_delete(info, wizard_group)

    return


@delete_decorator(
    keys={
        "hash_key": "endpoint_id",
        "range_key": "wizard_group_uuid",
    },
    model_funct=get_wizard_group,
)
def delete_wizard_group(info: ResolveInfo, **kwargs: Dict[str, Any]) -> bool:
    # Clear cache BEFORE deletion while entity still exists
    if kwargs.get("entity") and hasattr(get_wizard_group_type, 'cache_delete'):
        get_wizard_group_type.cache_delete(info, kwargs["entity"])

    kwargs["entity"].delete()
    return True
