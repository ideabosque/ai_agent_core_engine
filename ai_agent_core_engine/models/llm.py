#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import logging
from typing import Any, Dict

import pendulum
from graphene import ResolveInfo
from pynamodb.attributes import UnicodeAttribute, UTCDateTimeAttribute
from tenacity import retry, stop_after_attempt, wait_exponential

from silvaengine_dynamodb_base import (
    BaseModel,
    delete_decorator,
    insert_update_decorator,
    monitor_decorator,
    resolve_list_decorator,
)
from silvaengine_utility import Utility

from ..types.llm import LlmListType, LlmType


class LlmModel(BaseModel):
    class Meta(BaseModel.Meta):
        table_name = "aace-llms"

    llm_provider = UnicodeAttribute(hash_key=True)
    llm_name = UnicodeAttribute(range_key=True)
    module_name = UnicodeAttribute()
    class_name = UnicodeAttribute()
    updated_by = UnicodeAttribute()
    created_at = UTCDateTimeAttribute()
    updated_at = UTCDateTimeAttribute()


def create_llm_table(logger: logging.Logger) -> bool:
    """Create the LLM table if it doesn't exist."""
    if not LlmModel.exists():
        # Create with on-demand billing (PAY_PER_REQUEST)
        LlmModel.create_table(billing_mode="PAY_PER_REQUEST", wait=True)
        logger.info("The LLM table has been created.")
    return True


@retry(
    reraise=True,
    wait=wait_exponential(multiplier=1, max=60),
    stop=stop_after_attempt(5),
)
def get_llm(llm_provider: str, llm_name: str) -> LlmModel:
    return LlmModel.get(llm_provider, llm_name)


def get_llm_count(llm_provider: str, llm_name: str) -> int:
    return LlmModel.count(llm_provider, LlmModel.llm_name == llm_name)


def get_llm_type(info: ResolveInfo, llm: LlmModel) -> LlmType:
    llm = llm.__dict__["attribute_values"]
    return LlmType(**Utility.json_loads(Utility.json_dumps(llm)))


def resolve_llm(info: ResolveInfo, **kwargs: Dict[str, Any]) -> LlmType:
    return get_llm_type(info, get_llm(kwargs["llm_provider"], kwargs["llm_name"]))


@monitor_decorator
@resolve_list_decorator(
    attributes_to_get=["llm_provider", "llm_name"],
    list_type_class=LlmListType,
    type_funct=get_llm_type,
)
def resolve_llm_list(info: ResolveInfo, **kwargs: Dict[str, Any]) -> Any:
    llm_provider = kwargs.get("llm_provider")
    module_name = kwargs.get("module_name")
    class_name = kwargs.get("class_name")

    args = []
    inquiry_funct = LlmModel.scan
    count_funct = LlmModel.count
    if llm_provider:
        args = [llm_provider, None]
        inquiry_funct = LlmModel.query

    the_filters = None  # We can add filters for the query.
    if module_name:
        the_filters &= LlmModel.module_name == module_name
    if class_name:
        the_filters &= LlmModel.class_name == class_name
    if the_filters is not None:
        args.append(the_filters)

    return inquiry_funct, count_funct, args


@insert_update_decorator(
    keys={
        "hash_key": "llm_provider",
        "range_key": "llm_name",
    },
    range_key_required=True,
    model_funct=get_llm,
    count_funct=get_llm_count,
    type_funct=get_llm_type,
    # data_attributes_except_for_data_diff=["created_at", "updated_at"],
    # activity_history_funct=None,
)
def insert_update_llm(info: ResolveInfo, **kwargs: Dict[str, Any]) -> None:
    llm_provider = kwargs.get("llm_provider")
    llm_name = kwargs.get("llm_name")
    if kwargs.get("entity") is None:
        cols = {
            "module_name": kwargs["module_name"],
            "class_name": kwargs["class_name"],
            "updated_by": kwargs["updated_by"],
            "created_at": pendulum.now("UTC"),
            "updated_at": pendulum.now("UTC"),
        }
        LlmModel(
            llm_provider,
            llm_name,
            **cols,
        ).save()
        return

    llm = kwargs.get("entity")
    actions = [
        LlmModel.updated_by.set(kwargs["updated_by"]),
        LlmModel.updated_at.set(pendulum.now("UTC")),
    ]
    # Map of potential keys in kwargs to LlmModel attributes
    field_map = {
        "module_name": LlmModel.module_name,
        "class_name": LlmModel.class_name,
    }

    # Check if a key exists in kwargs before adding it to the update actions
    for key, field in field_map.items():
        if key in kwargs:  # Check if the key exists in kwargs
            actions.append(field.set(None if kwargs[key] == "null" else kwargs[key]))

    # Update the llm
    llm.update(actions=actions)
    return


@delete_decorator(
    keys={
        "hash_key": "llm_provider",
        "range_key": "llm_name",
    },
    model_funct=get_llm,
)
def delete_llm(info: ResolveInfo, **kwargs: Dict[str, Any]) -> bool:
    kwargs.get("entity").delete()
    return True
