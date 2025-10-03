#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import logging
import uuid
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

from ..handlers.config import Config
from ..types.element import ElementListType, ElementType


class DataTypeIndex(LocalSecondaryIndex):
    """
    This class represents a local secondary index
    """

    class Meta:
        billing_mode = "PAY_PER_REQUEST"
        # All attributes are projected
        projection = AllProjection()
        index_name = "data_type-index"

    endpoint_id = UnicodeAttribute(hash_key=True)
    data_type = UnicodeAttribute(range_key=True)


class ElementModel(BaseModel):
    class Meta(BaseModel.Meta):
        table_name = "aace-elements"

    endpoint_id = UnicodeAttribute(hash_key=True)
    element_uuid = UnicodeAttribute(range_key=True)
    data_type = UnicodeAttribute()
    element_title = UnicodeAttribute()
    priority = NumberAttribute(default=0)
    attribute_name = UnicodeAttribute()
    attribute_type = UnicodeAttribute()
    option_values = ListAttribute(of=MapAttribute)
    conditions = ListAttribute(of=MapAttribute)
    updated_by = UnicodeAttribute()
    created_at = UTCDateTimeAttribute()
    updated_at = UTCDateTimeAttribute()
    data_type_index = DataTypeIndex()


def create_element_table(logger: logging.Logger) -> bool:
    """Create the Element table if it doesn't exist."""
    if not ElementModel.exists():
        # Create with on-demand billing (PAY_PER_REQUEST)
        ElementModel.create_table(billing_mode="PAY_PER_REQUEST", wait=True)
        logger.info("The Element table has been created.")
    return True


@retry(
    reraise=True,
    wait=wait_exponential(multiplier=1, max=60),
    stop=stop_after_attempt(5),
)
@method_cache(ttl=Config.get_cache_ttl(), cache_name=Config.get_cache_name('models', 'element'))
def get_element(endpoint_id: str, element_uuid: str) -> ElementModel:
    return ElementModel.get(endpoint_id, element_uuid)


def get_element_count(endpoint_id: str, element_uuid: str) -> int:
    return ElementModel.count(endpoint_id, ElementModel.element_uuid == element_uuid)


def get_element_type(info: ResolveInfo, element: ElementModel) -> ElementType:
    element = element.__dict__["attribute_values"]
    return ElementType(**Utility.json_normalize(element))


def resolve_element(info: ResolveInfo, **kwargs: Dict[str, Any]) -> ElementType:
    count = get_element_count(info.context["endpoint_id"], kwargs["element_uuid"])
    if count == 0:
        return None

    return get_element_type(
        info, get_element(info.context["endpoint_id"], kwargs["element_uuid"])
    )


@monitor_decorator
@resolve_list_decorator(
    attributes_to_get=["endpoint_id", "element_uuid"],
    list_type_class=ElementListType,
    type_funct=get_element_type,
)
def resolve_element_list(info: ResolveInfo, **kwargs: Dict[str, Any]) -> Any:
    endpoint_id = info.context["endpoint_id"]
    data_type = kwargs.get("data_type")
    attribute_name = kwargs.get("attribute_name")

    args = []
    inquiry_funct = ElementModel.scan
    count_funct = ElementModel.count
    if endpoint_id:
        args = [endpoint_id, None]
        inquiry_funct = ElementModel.query
        if data_type:
            inquiry_funct = ElementModel.data_type_index.query
            args[1] = ElementModel.data_type == data_type
            count_funct = ElementModel.data_type_index.count

    the_filters = None
    if data_type:
        the_filters &= ElementModel.data_type == data_type
    if attribute_name:
        the_filters &= ElementModel.attribute_name == attribute_name
    if the_filters is not None:
        args.append(the_filters)

    return inquiry_funct, count_funct, args


@insert_update_decorator(
    keys={
        "hash_key": "endpoint_id",
        "range_key": "element_uuid",
    },
    model_funct=get_element,
    count_funct=get_element_count,
    type_funct=get_element_type,
)
def insert_update_element(info: ResolveInfo, **kwargs: Dict[str, Any]) -> None:
    # Use cascading cache purging for elements
    from ..models.cache import purge_element_cascading_cache

    cache_result = purge_element_cascading_cache(
        endpoint_id=kwargs.get("endpoint_id"),
        element_uuid=kwargs.get("element_uuid"),
        logger=info.context.get("logger"),
    )

    endpoint_id = kwargs.get("endpoint_id")
    element_uuid = kwargs.get("element_uuid")

    if kwargs.get("entity") is None:
        cols = {
            "data_type": kwargs["data_type"],
            "element_title": kwargs["element_title"],
            "priority": kwargs.get("priority", 0),
            "attribute_name": kwargs["attribute_name"],
            "attribute_type": kwargs["attribute_type"],
            "option_values": kwargs.get("option_values", []),
            "conditions": kwargs.get("conditions", []),
            "updated_by": kwargs["updated_by"],
            "created_at": pendulum.now("UTC"),
            "updated_at": pendulum.now("UTC"),
        }
        ElementModel(
            endpoint_id,
            element_uuid,
            **cols,
        ).save()
        return

    element = kwargs.get("entity")
    actions = [
        ElementModel.updated_by.set(kwargs["updated_by"]),
        ElementModel.updated_at.set(pendulum.now("UTC")),
    ]

    field_map = {
        "data_type": ElementModel.data_type,
        "element_title": ElementModel.element_title,
        "priority": ElementModel.priority,
        "attribute_name": ElementModel.attribute_name,
        "attribute_type": ElementModel.attribute_type,
        "option_values": ElementModel.option_values,
        "conditions": ElementModel.conditions,
    }

    for key, field in field_map.items():
        if key in kwargs:
            actions.append(field.set(None if kwargs[key] == "null" else kwargs[key]))

    element.update(actions=actions)


    return


@delete_decorator(
    keys={
        "hash_key": "endpoint_id",
        "range_key": "element_uuid",
    },
    model_funct=get_element,
)
def delete_element(info: ResolveInfo, **kwargs: Dict[str, Any]) -> bool:
    # Use cascading cache purging for elements
    from ..models.cache import purge_element_cascading_cache

    cache_result = purge_element_cascading_cache(
        endpoint_id=kwargs.get("endpoint_id"),
        element_uuid=kwargs.get("element_uuid"),
        logger=info.context.get("logger"),
    )

    kwargs["entity"].delete()
    return True
