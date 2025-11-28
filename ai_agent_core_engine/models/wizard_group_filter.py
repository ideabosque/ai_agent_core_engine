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

from ..handlers.config import Config
from ..types.wizard_group_filter import (
    WizardGroupFilterListType,
    WizardGroupFilterType,
)


class UpdatedAtIndex(LocalSecondaryIndex):
    """
    This class represents a local secondary index
    """

    class Meta:
        billing_mode = "PAY_PER_REQUEST"
        # All attributes are projected
        projection = AllProjection()
        index_name = "updated_at-index"

    endpoint_id = UnicodeAttribute(hash_key=True)
    updated_at = UnicodeAttribute(range_key=True)


class WizardGroupFilterModel(BaseModel):
    class Meta(BaseModel.Meta):
        table_name = "aace-wizard_group_filters"

    endpoint_id = UnicodeAttribute(hash_key=True)
    wizard_group_filter_uuid = UnicodeAttribute(range_key=True)
    wizard_group_filter_name = UnicodeAttribute()
    wizard_group_filter_description = UnicodeAttribute(null=True)
    region = UnicodeAttribute()
    criteria = MapAttribute()
    weight = NumberAttribute(default=0)
    wizard_group_uuid = UnicodeAttribute(null=True)
    updated_by = UnicodeAttribute()
    created_at = UTCDateTimeAttribute()
    updated_at = UTCDateTimeAttribute()
    updated_at_index = UpdatedAtIndex()


def purge_cache():
    def actual_decorator(original_function):
        @functools.wraps(original_function)
        def wrapper_function(*args, **kwargs):
            try:
                # Use cascading cache purging for wizard group filters
                from ..models.cache import purge_entity_cascading_cache

                try:
                    wizard_group_filter = resolve_wizard_group_filter(args[0], **kwargs)
                except Exception as e:
                    wizard_group_filter = None

                endpoint_id = args[0].context.get("endpoint_id") or kwargs.get(
                    "endpoint_id"
                )
                entity_keys = {}
                if kwargs.get("wizard_group_filter_uuid"):
                    entity_keys["wizard_group_filter_uuid"] = kwargs.get(
                        "wizard_group_filter_uuid"
                    )
                if wizard_group_filter and wizard_group_filter.wizard_group_uuid:
                    entity_keys["wizard_group_uuid"] = (
                        wizard_group_filter.wizard_group_uuid
                    )

                result = purge_entity_cascading_cache(
                    args[0].context.get("logger"),
                    entity_type="wizard_group_filter",
                    context_keys={"endpoint_id": endpoint_id} if endpoint_id else None,
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


def create_wizard_group_filter_table(logger: logging.Logger) -> bool:
    """Create the WizardGroupFilter table if it doesn't exist."""
    if not WizardGroupFilterModel.exists():
        # Create with on-demand billing (PAY_PER_REQUEST)
        WizardGroupFilterModel.create_table(billing_mode="PAY_PER_REQUEST", wait=True)
        logger.info("The WizardGroupFilter table has been created.")
    return True


@retry(
    reraise=True,
    wait=wait_exponential(multiplier=1, max=60),
    stop=stop_after_attempt(5),
)
@method_cache(
    ttl=Config.get_cache_ttl(),
    cache_name=Config.get_cache_name("models", "wizard_group_filter"),
)
def get_wizard_group_filter(
    endpoint_id: str, wizard_group_filter_uuid: str
) -> WizardGroupFilterModel:
    return WizardGroupFilterModel.get(endpoint_id, wizard_group_filter_uuid)


@retry(
    reraise=True,
    wait=wait_exponential(multiplier=1, max=60),
    stop=stop_after_attempt(5),
)
def _get_wizard_group_filter(
    endpoint_id: str, wizard_group_filter_uuid: str
) -> WizardGroupFilterModel:
    return WizardGroupFilterModel.get(endpoint_id, wizard_group_filter_uuid)


def get_wizard_group_filter_count(
    endpoint_id: str, wizard_group_filter_uuid: str
) -> int:
    return WizardGroupFilterModel.count(
        endpoint_id,
        WizardGroupFilterModel.wizard_group_filter_uuid == wizard_group_filter_uuid,
    )


def get_wizard_group_filter_type(
    info: ResolveInfo, wizard_group_filter: WizardGroupFilterModel
) -> WizardGroupFilterType:
    """
    Nested resolver approach: return minimal wizard group filter data.
    - Do NOT embed 'wizard_group'.
    - Keep 'wizard_group_uuid' as foreign key.
    - This is resolved lazily by WizardGroupFilterType.resolve_wizard_group.
    """
    try:
        wizard_group_filter_dict: Dict = wizard_group_filter.__dict__["attribute_values"]
        return WizardGroupFilterType(**Utility.json_normalize(wizard_group_filter_dict))
    except Exception as e:
        log = traceback.format_exc()
        info.context.get("logger").exception(log)
        raise e


def resolve_wizard_group_filter(
    info: ResolveInfo, **kwargs: Dict[str, Any]
) -> WizardGroupFilterType | None:
    count = get_wizard_group_filter_count(
        info.context["endpoint_id"], kwargs["wizard_group_filter_uuid"]
    )
    if count == 0:
        return None

    return get_wizard_group_filter_type(
        info,
        get_wizard_group_filter(
            info.context["endpoint_id"], kwargs["wizard_group_filter_uuid"]
        ),
    )


@monitor_decorator
@resolve_list_decorator(
    attributes_to_get=["endpoint_id", "wizard_group_filter_uuid", "updated_at"],
    list_type_class=WizardGroupFilterListType,
    type_funct=get_wizard_group_filter_type,
    scan_index_forward=False,
)
def resolve_wizard_group_filter_list(
    info: ResolveInfo, **kwargs: Dict[str, Any]
) -> Any:
    endpoint_id = info.context["endpoint_id"]
    wizard_group_filter_name = kwargs.get("wizard_group_filter_name")
    region = kwargs.get("region")
    wizard_group_uuid = kwargs.get("wizard_group_uuid")
    updated_at_gt = kwargs.get("updated_at_gt")
    updated_at_lt = kwargs.get("updated_at_lt")

    args = []
    inquiry_funct = WizardGroupFilterModel.scan
    count_funct = WizardGroupFilterModel.count
    range_key_condition = None
    if endpoint_id:
        # Build range key condition for updated_at when using updated_at_index
        if updated_at_gt is not None and updated_at_lt is not None:
            range_key_condition = WizardGroupFilterModel.updated_at.between(
                updated_at_gt, updated_at_lt
            )
        elif updated_at_gt is not None:
            range_key_condition = WizardGroupFilterModel.updated_at > updated_at_gt
        elif updated_at_lt is not None:
            range_key_condition = WizardGroupFilterModel.updated_at < updated_at_lt

        args = [endpoint_id, range_key_condition]
        inquiry_funct = WizardGroupFilterModel.updated_at_index.query
        count_funct = WizardGroupFilterModel.updated_at_index.count

    the_filters = None
    if wizard_group_filter_name:
        the_filters &= (
            WizardGroupFilterModel.wizard_group_filter_name == wizard_group_filter_name
        )
    if region:
        the_filters &= WizardGroupFilterModel.region == region
    if wizard_group_uuid:
        the_filters &= WizardGroupFilterModel.wizard_group_uuid == wizard_group_uuid
    if the_filters is not None:
        args.append(the_filters)

    return inquiry_funct, count_funct, args


@purge_cache()
@insert_update_decorator(
    keys={
        "hash_key": "endpoint_id",
        "range_key": "wizard_group_filter_uuid",
    },
    model_funct=_get_wizard_group_filter,
    count_funct=get_wizard_group_filter_count,
    type_funct=get_wizard_group_filter_type,
)
def insert_update_wizard_group_filter(
    info: ResolveInfo, **kwargs: Dict[str, Any]
) -> Any:

    endpoint_id = kwargs.get("endpoint_id")
    wizard_group_filter_uuid = kwargs.get("wizard_group_filter_uuid")

    if kwargs.get("entity") is None:
        cols = {
            "wizard_group_filter_name": kwargs["wizard_group_filter_name"],
            "wizard_group_filter_description": kwargs.get(
                "wizard_group_filter_description"
            ),
            "region": kwargs["region"],
            "criteria": kwargs.get("criteria", {}),
            "weight": kwargs.get("weight", 0),
            "wizard_group_uuid": kwargs.get("wizard_group_uuid"),
            "updated_by": kwargs["updated_by"],
            "created_at": pendulum.now("UTC"),
            "updated_at": pendulum.now("UTC"),
        }
        WizardGroupFilterModel(
            endpoint_id,
            wizard_group_filter_uuid,
            **cols,
        ).save()
        return

    wizard_group_filter = kwargs.get("entity")
    actions = [
        WizardGroupFilterModel.updated_by.set(kwargs["updated_by"]),
        WizardGroupFilterModel.updated_at.set(pendulum.now("UTC")),
    ]

    field_map = {
        "wizard_group_filter_name": WizardGroupFilterModel.wizard_group_filter_name,
        "wizard_group_filter_description": WizardGroupFilterModel.wizard_group_filter_description,
        "region": WizardGroupFilterModel.region,
        "criteria": WizardGroupFilterModel.criteria,
        "weight": WizardGroupFilterModel.weight,
        "wizard_group_uuid": WizardGroupFilterModel.wizard_group_uuid,
    }

    for key, field in field_map.items():
        if key in kwargs:
            actions.append(field.set(None if kwargs[key] == "null" else kwargs[key]))

    wizard_group_filter.update(actions=actions)

    return


@purge_cache()
@delete_decorator(
    keys={
        "hash_key": "endpoint_id",
        "range_key": "wizard_group_filter_uuid",
    },
    model_funct=get_wizard_group_filter,
)
def delete_wizard_group_filter(info: ResolveInfo, **kwargs: Dict[str, Any]) -> bool:

    kwargs["entity"].delete()
    return True
