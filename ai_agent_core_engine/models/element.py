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
    pattern = UnicodeAttribute()
    updated_by = UnicodeAttribute()
    created_at = UTCDateTimeAttribute()
    updated_at = UTCDateTimeAttribute()
    data_type_index = DataTypeIndex()
    updated_at_index = UpdatedAtIndex()


def purge_cache():
    def actual_decorator(original_function):
        @functools.wraps(original_function)
        def wrapper_function(*args, **kwargs):
            try:
                # Use cascading cache purging for elements
                from ..models.cache import purge_entity_cascading_cache

                endpoint_id = args[0].context.get("endpoint_id") or kwargs.get(
                    "endpoint_id"
                )
                entity_keys = {}
                if kwargs.get("element_uuid"):
                    entity_keys["element_uuid"] = kwargs.get("element_uuid")

                result = purge_entity_cascading_cache(
                    args[0].context.get("logger"),
                    entity_type="element",
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
@method_cache(
    ttl=Config.get_cache_ttl(), cache_name=Config.get_cache_name("models", "element")
)
def get_element(endpoint_id: str, element_uuid: str) -> ElementModel:
    return ElementModel.get(endpoint_id, element_uuid)

@retry(
    reraise=True,
    wait=wait_exponential(multiplier=1, max=60),
    stop=stop_after_attempt(5),
)
def _get_element(endpoint_id: str, element_uuid: str) -> ElementModel:
    return ElementModel.get(endpoint_id, element_uuid)

def get_element_count(endpoint_id: str, element_uuid: str) -> int:
    return ElementModel.count(endpoint_id, ElementModel.element_uuid == element_uuid)


def get_element_type(info: ResolveInfo, element: ElementModel) -> ElementType:
    element = element.__dict__["attribute_values"]
    return ElementType(**Utility.json_normalize(element))


def resolve_element(info: ResolveInfo, **kwargs: Dict[str, Any]) -> ElementType | None:
    count = get_element_count(info.context["endpoint_id"], kwargs["element_uuid"])
    if count == 0:
        return None

    return get_element_type(
        info, get_element(info.context["endpoint_id"], kwargs["element_uuid"])
    )


@monitor_decorator
@resolve_list_decorator(
    attributes_to_get=["endpoint_id", "element_uuid", "updated_at"],
    list_type_class=ElementListType,
    type_funct=get_element_type,
    scan_index_forward=False,
)
def resolve_element_list(info: ResolveInfo, **kwargs: Dict[str, Any]) -> Any:
    endpoint_id = info.context["endpoint_id"]
    data_type = kwargs.get("data_type")
    attribute_name = kwargs.get("attribute_name")
    updated_at_gt = kwargs.get("updated_at_gt")
    updated_at_lt = kwargs.get("updated_at_lt")

    args = []
    inquiry_funct = ElementModel.scan
    count_funct = ElementModel.count
    range_key_condition = None
    if endpoint_id:
        # Build range key condition for updated_at when using updated_at_index
        if updated_at_gt is not None and updated_at_lt is not None:
            range_key_condition = ElementModel.updated_at.between(
                updated_at_gt, updated_at_lt
            )
        elif updated_at_gt is not None:
            range_key_condition = ElementModel.updated_at > updated_at_gt
        elif updated_at_lt is not None:
            range_key_condition = ElementModel.updated_at < updated_at_lt

        args = [endpoint_id, range_key_condition]
        inquiry_funct = ElementModel.updated_at_index.query
        count_funct = ElementModel.updated_at_index.count

        if data_type and args[1] is None:
            inquiry_funct = ElementModel.data_type_index.query
            args[1] = ElementModel.data_type == data_type
            count_funct = ElementModel.data_type_index.count

    the_filters = None
    if data_type and range_key_condition is not None:
        the_filters &= ElementModel.data_type == data_type
    if attribute_name:
        the_filters &= ElementModel.attribute_name == attribute_name
    if the_filters is not None:
        args.append(the_filters)

    return inquiry_funct, count_funct, args


@purge_cache()
@insert_update_decorator(
    keys={
        "hash_key": "endpoint_id",
        "range_key": "element_uuid",
    },
    model_funct=_get_element,
    count_funct=get_element_count,
    type_funct=get_element_type,
)
def insert_update_element(info: ResolveInfo, **kwargs: Dict[str, Any]) -> Any:

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
            "pattern": kwargs.get("pattern", ""),
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
        "pattern": ElementModel.pattern,
    }

    for key, field in field_map.items():
        if key in kwargs:
            actions.append(field.set(None if kwargs[key] == "null" else kwargs[key]))

    element.update(actions=actions)

    return


@purge_cache()
@delete_decorator(
    keys={
        "hash_key": "endpoint_id",
        "range_key": "element_uuid",
    },
    model_funct=get_element,
)
def delete_element(info: ResolveInfo, **kwargs: Dict[str, Any]) -> bool:

    kwargs["entity"].delete()
    return True
