#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import functools
import logging
import traceback
from typing import Any, Dict

import pendulum
from graphene import ResolveInfo
from pynamodb.attributes import (
    ListAttribute,
    NumberAttribute,
    UnicodeAttribute,
    UTCDateTimeAttribute,
)
from pynamodb.indexes import AllProjection, LocalSecondaryIndex
from silvaengine_dynamodb_base import (
    BaseModel,
    delete_decorator,
    insert_update_decorator,
    monitor_decorator,
    resolve_list_decorator,
)
from silvaengine_utility import Utility, method_cache
from tenacity import retry, stop_after_attempt, wait_exponential

from ..handlers.config import Config
from ..types.wizard_group import WizardGroupListType, WizardGroupType


class UpdatedAtIndex(LocalSecondaryIndex):
    """
    This class represents a local secondary index
    """

    class Meta:
        billing_mode = "PAY_PER_REQUEST"
        # All attributes are projected
        projection = AllProjection()
        index_name = "updated_at-index"

    partition_key = UnicodeAttribute(hash_key=True)
    updated_at = UnicodeAttribute(range_key=True)


class WizardGroupModel(BaseModel):
    class Meta(BaseModel.Meta):
        table_name = "aace-wizard_groups"

    partition_key = UnicodeAttribute(hash_key=True)
    wizard_group_uuid = UnicodeAttribute(range_key=True)
    endpoint_id = UnicodeAttribute()
    part_id = UnicodeAttribute()
    wizard_group_name = UnicodeAttribute()
    wizard_group_description = UnicodeAttribute(null=True)
    weight = NumberAttribute(default=0)
    wizard_uuids = ListAttribute(null=True)
    updated_by = UnicodeAttribute()
    created_at = UTCDateTimeAttribute()
    updated_at = UTCDateTimeAttribute()
    updated_at_index = UpdatedAtIndex()


def purge_cache():
    def actual_decorator(original_function):
        @functools.wraps(original_function)
        def wrapper_function(*args, **kwargs):
            try:
                # Use cascading cache purging for wizard groups
                from ..models.cache import purge_entity_cascading_cache

                try:
                    wizard_group = resolve_wizard_group(args[0], **kwargs)
                except Exception as e:
                    wizard_group = None

                partition_key = args[0].context.get("partition_key") or kwargs.get(
                    "partition_key"
                )
                entity_keys = {}
                if kwargs.get("wizard_group_uuid"):
                    entity_keys["wizard_group_uuid"] = kwargs.get("wizard_group_uuid")
                if wizard_group and wizard_group.wizards:
                    entity_keys["wizard_uuids"] = [
                        wizard["wizard_uuid"] for wizard in wizard_group.wizards
                    ]

                result = purge_entity_cascading_cache(
                    args[0].context.get("logger"),
                    entity_type="wizard_group",
                    context_keys=(
                        {"partition_key": partition_key} if partition_key else None
                    ),
                    entity_keys=entity_keys if entity_keys else None,
                    cascade_depth=3,
                )

                ## Original function.
                result = original_function(*args, **kwargs)

                return result
            except Exception as e:
                log = traceback.format_exc()
                args[0].context.get("logger").error(log)
                raise e

        return wrapper_function

    return actual_decorator


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
@method_cache(
    ttl=Config.get_cache_ttl(),
    cache_name=Config.get_cache_name("models", "wizard_group"),
)
def get_wizard_group(partition_key: str, wizard_group_uuid: str) -> WizardGroupModel:
    return WizardGroupModel.get(partition_key, wizard_group_uuid)


@retry(
    reraise=True,
    wait=wait_exponential(multiplier=1, max=60),
    stop=stop_after_attempt(5),
)
def _get_wizard_group(partition_key: str, wizard_group_uuid: str) -> WizardGroupModel:
    return WizardGroupModel.get(partition_key, wizard_group_uuid)


def get_wizard_group_count(partition_key: str, wizard_group_uuid: str) -> int:
    return WizardGroupModel.count(
        partition_key, WizardGroupModel.wizard_group_uuid == wizard_group_uuid
    )


def get_wizard_group_type(
    info: ResolveInfo, wizard_group: WizardGroupModel
) -> WizardGroupType:
    """
    Nested resolver approach: return minimal wizard group data.
    - Do NOT embed 'wizards'.
    - Keep 'wizard_uuids' as foreign keys.
    - This is resolved lazily by WizardGroupType.resolve_wizards.
    """
    try:
        wizard_group_dict: Dict = wizard_group.__dict__["attribute_values"]
        return WizardGroupType(**Utility.json_normalize(wizard_group_dict))
    except Exception as e:
        log = traceback.format_exc()
        info.context.get("logger").exception(log)
        raise e


def get_wizard_group_list_type(
    info: ResolveInfo, wizard_group: WizardGroupModel
) -> WizardGroupType:
    """
    Nested resolver approach: return minimal wizard group data.
    - Do NOT embed 'wizards'.
    - Keep 'wizard_uuids' as foreign keys.
    """
    try:
        wizard_group_dict: Dict = wizard_group.__dict__["attribute_values"]
        return WizardGroupType(**Utility.json_normalize(wizard_group_dict))
    except Exception as e:
        log = traceback.format_exc()
        info.context.get("logger").exception(log)
        raise e


def resolve_wizard_group(
    info: ResolveInfo, **kwargs: Dict[str, Any]
) -> WizardGroupType | None:
    count = get_wizard_group_count(
        info.context["partition_key"], kwargs["wizard_group_uuid"]
    )
    if count == 0:
        return None

    return get_wizard_group_type(
        info,
        get_wizard_group(info.context["partition_key"], kwargs["wizard_group_uuid"]),
    )


@monitor_decorator
@resolve_list_decorator(
    attributes_to_get=["partition_key", "wizard_group_uuid", "updated_at"],
    list_type_class=WizardGroupListType,
    type_funct=get_wizard_group_list_type,
    scan_index_forward=False,
)
def resolve_wizard_group_list(info: ResolveInfo, **kwargs: Dict[str, Any]) -> Any:
    partition_key = info.context["partition_key"]
    wizard_group_name = kwargs.get("wizard_group_name")
    updated_at_gt = kwargs.get("updated_at_gt")
    updated_at_lt = kwargs.get("updated_at_lt")

    args = []
    inquiry_funct = WizardGroupModel.scan
    count_funct = WizardGroupModel.count
    range_key_condition = None
    if partition_key:
        # Build range key condition for updated_at when using updated_at_index
        if updated_at_gt is not None and updated_at_lt is not None:
            range_key_condition = WizardGroupModel.updated_at.between(
                updated_at_gt, updated_at_lt
            )
        elif updated_at_gt is not None:
            range_key_condition = WizardGroupModel.updated_at > updated_at_gt
        elif updated_at_lt is not None:
            range_key_condition = WizardGroupModel.updated_at < updated_at_lt

        args = [partition_key, range_key_condition]
        inquiry_funct = WizardGroupModel.updated_at_index.query
        count_funct = WizardGroupModel.updated_at_index.count

    the_filters = None
    if wizard_group_name:
        the_filters &= WizardGroupModel.wizard_group_name == wizard_group_name
    if the_filters is not None:
        args.append(the_filters)

    return inquiry_funct, count_funct, args


@purge_cache()
@insert_update_decorator(
    keys={
        "hash_key": "endpoint_id",
        "range_key": "wizard_group_uuid",
    },
    model_funct=_get_wizard_group,
    count_funct=get_wizard_group_count,
    type_funct=get_wizard_group_type,
)
def insert_update_wizard_group(info: ResolveInfo, **kwargs: Dict[str, Any]) -> Any:

    partition_key = kwargs.get("partition_key")
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
        cols["endpoint_id"] = info.context.get("endpoint_id")
        cols["part_id"] = info.context.get("part_id")
        WizardGroupModel(
            partition_key,
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

    return


@purge_cache()
@delete_decorator(
    keys={
        "hash_key": "partition_key",
        "range_key": "wizard_group_uuid",
    },
    model_funct=get_wizard_group,
)
def delete_wizard_group(info: ResolveInfo, **kwargs: Dict[str, Any]) -> bool:

    kwargs["entity"].delete()
    return True
