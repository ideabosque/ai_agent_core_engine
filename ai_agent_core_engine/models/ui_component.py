#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import logging
import traceback
import uuid
from typing import Any, Dict

import pendulum
from graphene import ResolveInfo
from pynamodb.attributes import (
    ListAttribute,
    MapAttribute,
    UnicodeAttribute,
    UTCDateTimeAttribute,
)
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
from ..types.ui_component import UIComponentListType, UIComponentType


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


def create_ui_component_table(logger: logging.Logger) -> bool:
    """Create the UIComponent table if it doesn't exist."""
    if not UIComponentModel.exists():
        # Create with on-demand billing (PAY_PER_REQUEST)
        UIComponentModel.create_table(billing_mode="PAY_PER_REQUEST", wait=True)
        logger.info("The UIComponent table has been created.")
    return True


@retry(
    reraise=True,
    wait=wait_exponential(multiplier=1, max=60),
    stop=stop_after_attempt(5),
)
@method_cache(ttl=Config.get_cache_ttl(), cache_name=Config.get_cache_name('models', 'ui_component'))
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
    ui_component = ui_component.__dict__["attribute_values"]
    return UIComponentType(**Utility.json_normalize(ui_component))


def resolve_ui_component(
    info: ResolveInfo, **kwargs: Dict[str, Any]
) -> UIComponentType:
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
    attributes_to_get=["ui_component_type", "ui_component_uuid"],
    list_type_class=UIComponentListType,
    type_funct=get_ui_component_type,
)
def resolve_ui_component_list(info: ResolveInfo, **kwargs: Dict[str, Any]) -> Any:
    ui_component_type = kwargs.get("ui_component_type")
    tag_name = kwargs.get("tag_name")

    args = []
    inquiry_funct = UIComponentModel.scan
    count_funct = UIComponentModel.count
    if ui_component_type:
        args = [ui_component_type, None]
        inquiry_funct = UIComponentModel.query

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
def insert_update_ui_component(info: ResolveInfo, **kwargs: Dict[str, Any]) -> None:
    # Use cascading cache purging for ui components
    from ..models.cache import purge_ui_component_cascading_cache

    cache_result = purge_ui_component_cascading_cache(
        ui_component_type=kwargs.get("ui_component_type"),
        ui_component_uuid=kwargs.get("ui_component_uuid"),
        logger=info.context.get("logger"),
    )

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
def delete_ui_component(info: ResolveInfo, **kwargs: Dict[str, Any]) -> bool:
    # Use cascading cache purging for ui components
    from ..models.cache import purge_ui_component_cascading_cache

    cache_result = purge_ui_component_cascading_cache(
        ui_component_type=kwargs.get("ui_component_type"),
        ui_component_uuid=kwargs.get("ui_component_uuid"),
        logger=info.context.get("logger"),
    )

    kwargs["entity"].delete()
    return True
