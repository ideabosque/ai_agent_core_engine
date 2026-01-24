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
from silvaengine_utility import method_cache
from tenacity import retry, stop_after_attempt, wait_exponential

from ..handlers.config import Config
from ..types.wizard_schema import WizardSchemaListType, WizardSchemaType
from ..utils.normalization import normalize_to_json

attributes_fn = lambda attributes: [
    {
        "name": attribute.get("name"),
        "attribute_type": attribute.get("attribute_type"),
        "required": attribute.get("required", False),
        "options": attribute.get("options", []),
        "pattern": attribute.get("pattern", ""),
        "col": attribute.get("col", ""),
        "label": attribute.get("label", ""),
        "group_name": attribute.get("group_name", ""),
    }
    for attribute in attributes
]

attribute_groups_fn = lambda attribute_groups: [
    {
        "name": attribute_group.get("name"),
        "label": attribute_group.get("label"),
    }
    for attribute_group in attribute_groups
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

    wizard_schema_type = UnicodeAttribute(hash_key=True)
    updated_at = UnicodeAttribute(range_key=True)


class WizardSchemaModel(BaseModel):
    class Meta(BaseModel.Meta):
        table_name = "aace-wizard_schemas"

    wizard_schema_type = UnicodeAttribute(hash_key=True)
    wizard_schema_name = UnicodeAttribute(range_key=True)
    wizard_schema_description = UnicodeAttribute(null=True)
    attributes = ListAttribute(of=MapAttribute)
    attribute_groups = ListAttribute(of=MapAttribute)
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
                    entity_keys["wizard_schema_name"] = getattr(
                        entity, "wizard_schema_name", None
                    )
                    wizard_schema_type = getattr(entity, "wizard_schema_type", None)
                else:
                    wizard_schema_type = kwargs.get("wizard_schema_type")

                # Fallback to kwargs (for creates/deletes)
                if not entity_keys.get("wizard_schema_name"):
                    entity_keys["wizard_schema_name"] = kwargs.get("wizard_schema_name")

                # Only purge if we have the required keys
                if entity_keys.get("wizard_schema_name"):
                    purge_entity_cascading_cache(
                        args[0].context.get("logger"),
                        entity_type="wizard_schema",
                        context_keys=(
                            {"wizard_schema_type": wizard_schema_type}
                            if wizard_schema_type
                            else None
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
    cache_name=Config.get_cache_name("models", "wizard_schema"),
    cache_enabled=Config.is_cache_enabled,
)
def get_wizard_schema(
    wizard_schema_type: str, wizard_schema_name: str
) -> WizardSchemaModel:
    return WizardSchemaModel.get(wizard_schema_type, wizard_schema_name)


@retry(
    reraise=True,
    wait=wait_exponential(multiplier=1, max=60),
    stop=stop_after_attempt(5),
)
def _get_wizard_schema(
    wizard_schema_type: str, wizard_schema_name: str
) -> WizardSchemaModel:
    return WizardSchemaModel.get(wizard_schema_type, wizard_schema_name)


def get_wizard_schema_count(wizard_schema_type: str, wizard_schema_name: str) -> int:
    return WizardSchemaModel.count(
        wizard_schema_type,
        WizardSchemaModel.wizard_schema_name == wizard_schema_name,
    )


def get_wizard_schema_type(
    info: ResolveInfo, wizard_schema: WizardSchemaModel
) -> WizardSchemaType:
    try:
        wizard_schema_dict = wizard_schema.__dict__["attribute_values"]
        return WizardSchemaType(**normalize_to_json(wizard_schema_dict))
    except Exception as e:
        log = traceback.format_exc()
        info.context.get("logger").exception(log)
        raise e


def resolve_wizard_schema(
    info: ResolveInfo, **kwargs: Dict[str, Any]
) -> WizardSchemaType | None:
    count = get_wizard_schema_count(
        kwargs["wizard_schema_type"], kwargs["wizard_schema_name"]
    )
    if count == 0:
        return None

    return get_wizard_schema_type(
        info,
        get_wizard_schema(kwargs["wizard_schema_type"], kwargs["wizard_schema_name"]),
    )


@monitor_decorator
@resolve_list_decorator(
    attributes_to_get=["wizard_schema_type", "wizard_schema_name", "updated_at"],
    list_type_class=WizardSchemaListType,
    type_funct=get_wizard_schema_type,
)
def resolve_wizard_schema_list(info: ResolveInfo, **kwargs: Dict[str, Any]) -> Any:
    wizard_schema_type = kwargs.get("wizard_schema_type")
    wizard_schema_name = kwargs.get("wizard_schema_name")
    updated_at_gt = kwargs.get("updated_at_gt")
    updated_at_lt = kwargs.get("updated_at_lt")

    args = []
    inquiry_funct = WizardSchemaModel.scan
    count_funct = WizardSchemaModel.count
    range_key_condition = None
    if wizard_schema_type:
        # Build range key condition for updated_at when using updated_at_index
        if updated_at_gt is not None and updated_at_lt is not None:
            range_key_condition = WizardSchemaModel.updated_at.between(
                updated_at_gt, updated_at_lt
            )
        elif updated_at_gt is not None:
            range_key_condition = WizardSchemaModel.updated_at > updated_at_gt
        elif updated_at_lt is not None:
            range_key_condition = WizardSchemaModel.updated_at < updated_at_lt

        args = [wizard_schema_type, range_key_condition]
        inquiry_funct = WizardSchemaModel.updated_at_index.query
        count_funct = WizardSchemaModel.updated_at_index.count

    the_filters = None
    if wizard_schema_name:
        the_filters &= WizardSchemaModel.wizard_schema_name == wizard_schema_name
    if the_filters is not None:
        args.append(the_filters)

    return inquiry_funct, count_funct, args


@insert_update_decorator(
    keys={
        "hash_key": "wizard_schema_type",
        "range_key": "wizard_schema_name",
    },
    range_key_required=True,
    model_funct=_get_wizard_schema,
    count_funct=get_wizard_schema_count,
    type_funct=get_wizard_schema_type,
)
@purge_cache()
def insert_update_wizard_schema(info: ResolveInfo, **kwargs: Dict[str, Any]) -> None:
    wizard_schema_type = kwargs.get("wizard_schema_type")
    wizard_schema_name = kwargs.get("wizard_schema_name")

    if kwargs.get("entity") is None:
        cols = {
            "wizard_schema_description": kwargs.get("wizard_schema_description"),
            "attributes": attributes_fn(kwargs.get("attributes", [])),
            "attribute_groups": attribute_groups_fn(kwargs.get("attribute_groups", [])),
            "updated_by": kwargs["updated_by"],
            "created_at": pendulum.now("UTC"),
            "updated_at": pendulum.now("UTC"),
        }
        WizardSchemaModel(
            wizard_schema_type,
            wizard_schema_name,
            **cols,
        ).save()
        return

    wizard_schema = kwargs.get("entity")
    actions = [
        WizardSchemaModel.updated_by.set(kwargs["updated_by"]),
        WizardSchemaModel.updated_at.set(pendulum.now("UTC")),
    ]

    field_map = {
        "attributes": WizardSchemaModel.attributes,
        "attribute_groups": WizardSchemaModel.attribute_groups,
        "wizard_schema_description": WizardSchemaModel.wizard_schema_description,
    }

    fn_map = {"attributes": attributes_fn, "attribute_groups": attribute_groups_fn}

    for key, field in field_map.items():
        if key in kwargs:
            if key in fn_map:
                actions.append(field.set(fn_map[key](kwargs.get(key, []))))
                continue

            actions.append(field.set(None if kwargs[key] == "null" else kwargs[key]))

    wizard_schema.update(actions=actions)

    return


@delete_decorator(
    keys={
        "hash_key": "wizard_schema_type",
        "range_key": "wizard_schema_name",
    },
    model_funct=get_wizard_schema,
)
@purge_cache()
def delete_wizard_schema(info: ResolveInfo, **kwargs: Dict[str, Any]) -> bool:

    kwargs["entity"].delete()
    return True
