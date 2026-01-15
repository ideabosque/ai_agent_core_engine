#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import functools
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
from silvaengine_dynamodb_base import (
    BaseModel,
    delete_decorator,
    insert_update_decorator,
    monitor_decorator,
    resolve_list_decorator,
)
from silvaengine_utility import Serializer, method_cache
from tenacity import retry, stop_after_attempt, wait_exponential

from ..handlers.config import Config
from ..types.wizard import WizardListType, WizardType

wizard_attributes_fn = lambda wizard_attributes: [
    {
        "name": wizard_attribute["name"],
        "value": wizard_attribute["value"],
    }
    for wizard_attribute in wizard_attributes
]

wizard_elements_fn = lambda wizard_elements: [
    {
        "element_uuid": wizard_element["element_uuid"],
        "required": wizard_element.get("required", False),
        "placeholder": wizard_element.get("placeholder"),
    }
    for wizard_element in wizard_elements
]


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


class WizardModel(BaseModel):
    class Meta(BaseModel.Meta):
        table_name = "aace-wizards"

    partition_key = UnicodeAttribute(hash_key=True)
    wizard_uuid = UnicodeAttribute(range_key=True)
    endpoint_id = UnicodeAttribute()
    part_id = UnicodeAttribute()
    wizard_title = UnicodeAttribute()
    wizard_description = UnicodeAttribute(null=True)
    wizard_type = UnicodeAttribute()
    wizard_schema_type = UnicodeAttribute()
    wizard_schema_name = UnicodeAttribute()
    wizard_attributes = ListAttribute(of=MapAttribute)
    wizard_elements = ListAttribute(of=MapAttribute)
    priority = NumberAttribute(default=0)
    updated_by = UnicodeAttribute()
    created_at = UTCDateTimeAttribute()
    updated_at = UTCDateTimeAttribute()
    updated_at_index = UpdatedAtIndex()


def purge_cache():
    def actual_decorator(original_function):
        @functools.wraps(original_function)
        def wrapper_function(*args, **kwargs):
            try:
                # Execute original function first
                result = original_function(*args, **kwargs)

                # Then purge cache after successful operation
                from ..models.cache import purge_entity_cascading_cache

                # Get entity keys from kwargs or entity parameter
                entity_keys = {}

                # Try to get from entity parameter first (for updates)
                entity = kwargs.get("entity")
                if entity:
                    entity_keys["wizard_uuid"] = getattr(entity, "wizard_uuid", None)
                    entity_keys["wizard_schema_type"] = getattr(
                        entity, "wizard_schema_type", None
                    )
                    entity_keys["wizard_schema_name"] = getattr(
                        entity, "wizard_schema_name", None
                    )
                    wizard_elements = getattr(entity, "wizard_elements", None)
                    if wizard_elements:
                        entity_keys["element_uuids"] = [
                            wizard_element["element_uuid"]
                            for wizard_element in wizard_elements
                        ]

                # Fallback to kwargs (for creates/deletes)
                if not entity_keys.get("wizard_uuid"):
                    entity_keys["wizard_uuid"] = kwargs.get("wizard_uuid")

                # Get partition_key from context or kwargs
                partition_key = args[0].context.get("partition_key") or kwargs.get(
                    "partition_key"
                )

                # Only purge if we have the required keys
                if entity_keys.get("wizard_uuid"):
                    purge_entity_cascading_cache(
                        args[0].context.get("logger"),
                        entity_type="wizard",
                        context_keys=(
                            {"partition_key": partition_key} if partition_key else None
                        ),
                        entity_keys=entity_keys,
                        cascade_depth=3,
                    )

                return result
            except Exception as e:
                log = traceback.format_exc()
                args[0].context.get("logger").error(log)
                raise e

        return wrapper_function

    return actual_decorator


@retry(
    reraise=True,
    wait=wait_exponential(multiplier=1, max=60),
    stop=stop_after_attempt(5),
)
@method_cache(
    ttl=Config.get_cache_ttl(),
    cache_name=Config.get_cache_name("models", "wizard"),
    cache_enabled=Config.is_cache_enabled,
)
def get_wizard(partition_key: str, wizard_uuid: str) -> WizardModel:
    return WizardModel.get(partition_key, wizard_uuid)


@retry(
    reraise=True,
    wait=wait_exponential(multiplier=1, max=60),
    stop=stop_after_attempt(5),
)
def _get_wizard(partition_key: str, wizard_uuid: str) -> WizardModel:
    return WizardModel.get(partition_key, wizard_uuid)


def get_wizard_count(partition_key: str, wizard_uuid: str) -> int:
    return WizardModel.count(partition_key, WizardModel.wizard_uuid == wizard_uuid)


def get_wizard_type(info: ResolveInfo, wizard: WizardModel) -> WizardType:
    """
    Nested resolver approach: return minimal wizard data.
    - Do NOT embed 'wizard_schema', 'wizard_elements'.
    - Keep foreign keys 'wizard_schema_type', 'wizard_schema_name'.
    - Store raw element references as 'wizard_element_refs'.
    - These are resolved lazily by WizardType.resolve_wizard_schema, resolve_wizard_elements.
    """
    try:
        wizard_dict: Dict = wizard.__dict__["attribute_values"]

        # Keep the raw element references for nested resolvers
        wizard_dict["wizard_element_refs"] = wizard.wizard_elements

        return WizardType(**Serializer.json_normalize(wizard_dict))
    except Exception as e:
        log = traceback.format_exc()
        info.context.get("logger").exception(log)
        raise e


def resolve_wizard(info: ResolveInfo, **kwargs: Dict[str, Any]) -> WizardType | None:
    count = get_wizard_count(info.context["partition_key"], kwargs["wizard_uuid"])
    if count == 0:
        return None

    return get_wizard_type(
        info, get_wizard(info.context["partition_key"], kwargs["wizard_uuid"])
    )


@monitor_decorator
@resolve_list_decorator(
    attributes_to_get=["partition_key", "wizard_uuid", "updated_at"],
    list_type_class=WizardListType,
    type_funct=get_wizard_type,
    scan_index_forward=False,
)
def resolve_wizard_list(info: ResolveInfo, **kwargs: Dict[str, Any]) -> Any:
    partition_key = info.context["partition_key"]
    wizard_type = kwargs.get("wizard_type")
    wizard_title = kwargs.get("wizard_title")
    updated_at_gt = kwargs.get("updated_at_gt")
    updated_at_lt = kwargs.get("updated_at_lt")

    args = []
    inquiry_funct = WizardModel.scan
    count_funct = WizardModel.count
    range_key_condition = None
    if partition_key:
        # Build range key condition for updated_at when using updated_at_index
        if updated_at_gt is not None and updated_at_lt is not None:
            range_key_condition = WizardModel.updated_at.between(
                updated_at_gt, updated_at_lt
            )
        elif updated_at_gt is not None:
            range_key_condition = WizardModel.updated_at > updated_at_gt
        elif updated_at_lt is not None:
            range_key_condition = WizardModel.updated_at < updated_at_lt

        args = [partition_key, range_key_condition]
        inquiry_funct = WizardModel.updated_at_index.query
        count_funct = WizardModel.updated_at_index.count

    the_filters = None
    if wizard_type:
        the_filters &= WizardModel.wizard_type == wizard_type
    if wizard_title:
        the_filters &= WizardModel.wizard_title == wizard_title
    if the_filters is not None:
        args.append(the_filters)

    return inquiry_funct, count_funct, args


@insert_update_decorator(
    keys={
        "hash_key": "partition_key",
        "range_key": "wizard_uuid",
    },
    model_funct=_get_wizard,
    count_funct=get_wizard_count,
    type_funct=get_wizard_type,
)
@purge_cache()
def insert_update_wizard(info: ResolveInfo, **kwargs: Dict[str, Any]) -> Any:
    partition_key = kwargs.get("partition_key")
    wizard_uuid = kwargs.get("wizard_uuid")

    if kwargs.get("entity") is None:
        cols = {
            "wizard_title": kwargs["wizard_title"],
            "wizard_description": kwargs.get("wizard_description"),
            "wizard_type": kwargs["wizard_type"],
            "wizard_schema_type": kwargs["wizard_schema_type"],
            "wizard_schema_name": kwargs["wizard_schema_name"],
            "wizard_attributes": wizard_attributes_fn(
                kwargs.get("wizard_attributes", [])
            ),
            "wizard_elements": wizard_elements_fn(kwargs.get("wizard_elements", [])),
            "priority": kwargs.get("priority", 0),
            "updated_by": kwargs["updated_by"],
            "created_at": pendulum.now("UTC"),
            "updated_at": pendulum.now("UTC"),
        }
        cols["endpoint_id"] = info.context.get("endpoint_id")
        cols["part_id"] = info.context.get("part_id")
        WizardModel(
            partition_key,
            wizard_uuid,
            **cols,
        ).save()
        return

    wizard = kwargs.get("entity")
    actions = [
        WizardModel.updated_by.set(kwargs["updated_by"]),
        WizardModel.updated_at.set(pendulum.now("UTC")),
    ]

    field_map = {
        "wizard_title": WizardModel.wizard_title,
        "wizard_description": WizardModel.wizard_description,
        "wizard_type": WizardModel.wizard_type,
        "wizard_schema_type": WizardModel.wizard_schema_type,
        "wizard_schema_name": WizardModel.wizard_schema_name,
        "wizard_attributes": WizardModel.wizard_attributes,
        "wizard_elements": WizardModel.wizard_elements,
        "priority": WizardModel.priority,
    }

    fn_map = {
        "wizard_attributes": wizard_attributes_fn,
        "wizard_elements": wizard_elements_fn,
    }

    for key, field in field_map.items():
        if key in kwargs:
            if key in fn_map:
                actions.append(field.set(fn_map[key](kwargs.get(key, []))))
                continue

            actions.append(field.set(None if kwargs[key] == "null" else kwargs[key]))

    wizard.update(actions=actions)

    return


@delete_decorator(
    keys={
        "hash_key": "partition_key",
        "range_key": "wizard_uuid",
    },
    model_funct=get_wizard,
)
@purge_cache()
def delete_wizard(info: ResolveInfo, **kwargs: Dict[str, Any]) -> bool:

    kwargs["entity"].delete()
    return True
