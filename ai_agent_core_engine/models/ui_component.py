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
from ..types.ui_component import UIComponentListType, UIComponentType
from ..utils.normalization import normalize_to_json


class UpdatedAtIndex(LocalSecondaryIndex):
    """
    This class represents a local secondary index
    """

    class Meta:
        billing_mode = "PAY_PER_REQUEST"
        # All attributes are projected
        projection = AllProjection()
        index_name = "updated_at-index"

    ui_component_type = UnicodeAttribute(hash_key=True)
    updated_at = UnicodeAttribute(range_key=True)


class UIComponentModel(BaseModel):
    class Meta(BaseModel.Meta):
        table_name = "aace-ui_components"

    ui_component_type = UnicodeAttribute(hash_key=True)
    ui_component_uuid = UnicodeAttribute(range_key=True)
    tag_name = UnicodeAttribute()
    parameters = ListAttribute(of=MapAttribute)
    wait_for = UnicodeAttribute(null=True)
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
                    entity_keys["ui_component_type"] = getattr(
                        entity, "ui_component_type", None
                    )
                    entity_keys["ui_component_uuid"] = getattr(
                        entity, "ui_component_uuid", None
                    )

                # Fallback to kwargs (for creates/deletes)
                if not entity_keys.get("ui_component_type"):
                    entity_keys["ui_component_type"] = kwargs.get("ui_component_type")
                if not entity_keys.get("ui_component_uuid"):
                    entity_keys["ui_component_uuid"] = kwargs.get("ui_component_uuid")

                # Only purge if we have the required keys
                if entity_keys.get("ui_component_type") and entity_keys.get(
                    "ui_component_uuid"
                ):
                    purge_entity_cascading_cache(
                        args[0].context.get("logger"),
                        entity_type="ui_component",
                        context_keys=None,  # UI components don't use partition_key
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
    cache_name=Config.get_cache_name("models", "ui_component"),
    cache_enabled=Config.is_cache_enabled,
)
def get_ui_component(
    ui_component_type: str, ui_component_uuid: str
) -> UIComponentModel:
    return UIComponentModel.get(ui_component_type, ui_component_uuid)


def get_ui_component_count(ui_component_type: str, ui_component_uuid: str) -> int:
    return UIComponentModel.count(
        ui_component_type, UIComponentModel.ui_component_uuid == ui_component_uuid
    )


def get_ui_component_type(
    info: ResolveInfo, ui_component: UIComponentModel
) -> UIComponentType:
    _ = info  # Keep for signature compatibility with decorators
    ui_component_dict = ui_component.__dict__["attribute_values"].copy()
    return UIComponentType(**normalize_to_json(ui_component_dict))


def resolve_ui_component(
    info: ResolveInfo, **kwargs: Dict[str, Any]
) -> UIComponentType | None:
    count = get_ui_component_count(
        kwargs["ui_component_type"], kwargs["ui_component_uuid"]
    )
    if count == 0:
        return None

    return get_ui_component_type(
        info, get_ui_component(kwargs["ui_component_type"], kwargs["ui_component_uuid"])
    )


@monitor_decorator
@resolve_list_decorator(
    attributes_to_get=["ui_component_type", "ui_component_uuid", "updated_at"],
    list_type_class=UIComponentListType,
    type_funct=get_ui_component_type,
)
def resolve_ui_component_list(info: ResolveInfo, **kwargs: Dict[str, Any]) -> Any:
    ui_component_type = kwargs.get("ui_component_type")
    tag_name = kwargs.get("tag_name")
    updated_at_gt = kwargs.get("updated_at_gt")
    updated_at_lt = kwargs.get("updated_at_lt")

    args = []
    inquiry_funct = UIComponentModel.scan
    count_funct = UIComponentModel.count
    range_key_condition = None
    if ui_component_type:
        # Build range key condition for updated_at when using updated_at_index
        if updated_at_gt is not None and updated_at_lt is not None:
            range_key_condition = UIComponentModel.updated_at.between(
                updated_at_gt, updated_at_lt
            )
        elif updated_at_gt is not None:
            range_key_condition = UIComponentModel.updated_at > updated_at_gt
        elif updated_at_lt is not None:
            range_key_condition = UIComponentModel.updated_at < updated_at_lt

        args = [ui_component_type, range_key_condition]
        inquiry_funct = UIComponentModel.updated_at_index.query
        count_funct = UIComponentModel.updated_at_index.count

    the_filters = None
    if tag_name:
        the_filters &= UIComponentModel.tag_name == tag_name
    if the_filters is not None:
        args.append(the_filters)

    return inquiry_funct, count_funct, args


@insert_update_decorator(
    keys={
        "hash_key": "ui_component_type",
        "range_key": "ui_component_uuid",
    },
    model_funct=get_ui_component,
    count_funct=get_ui_component_count,
    type_funct=get_ui_component_type,
)
@purge_cache()
def insert_update_ui_component(info: ResolveInfo, **kwargs: Dict[str, Any]) -> Any:

    ui_component_type = kwargs.get("ui_component_type")
    ui_component_uuid = kwargs.get("ui_component_uuid")

    if kwargs.get("entity") is None:
        cols = {
            "tag_name": kwargs["tag_name"],
            "parameters": kwargs.get("parameters", []),
            "wait_for": kwargs.get("wait_for"),
            "updated_by": kwargs["updated_by"],
            "created_at": pendulum.now("UTC"),
            "updated_at": pendulum.now("UTC"),
        }
        UIComponentModel(
            ui_component_type,
            ui_component_uuid,
            **cols,
        ).save()
        return

    ui_component = kwargs.get("entity")
    actions = [
        UIComponentModel.updated_by.set(kwargs["updated_by"]),
        UIComponentModel.updated_at.set(pendulum.now("UTC")),
    ]

    field_map = {
        "tag_name": UIComponentModel.tag_name,
        "parameters": UIComponentModel.parameters,
        "wait_for": UIComponentModel.wait_for,
    }

    for key, field in field_map.items():
        if key in kwargs:
            actions.append(field.set(None if kwargs[key] == "null" else kwargs[key]))

    ui_component.update(actions=actions)

    return


@delete_decorator(
    keys={
        "hash_key": "ui_component_type",
        "range_key": "ui_component_uuid",
    },
    model_funct=get_ui_component,
)
@purge_cache()
def delete_ui_component(info: ResolveInfo, **kwargs: Dict[str, Any]) -> bool:

    kwargs["entity"].delete()
    return True
