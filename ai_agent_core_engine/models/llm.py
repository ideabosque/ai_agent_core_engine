#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import functools
import traceback
from typing import Any, Dict

import pendulum
from graphene import ResolveInfo
from pynamodb.attributes import MapAttribute, UnicodeAttribute, UTCDateTimeAttribute
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
from ..types.llm import LlmListType, LlmType
from .agent import resolve_agent_list


class UpdatedAtIndex(LocalSecondaryIndex):
    """
    This class represents a local secondary index
    """

    class Meta:
        billing_mode = "PAY_PER_REQUEST"
        # All attributes are projected
        projection = AllProjection()
        index_name = "updated_at-index"

    llm_provider = UnicodeAttribute(hash_key=True)
    updated_at = UnicodeAttribute(range_key=True)


class LlmModel(BaseModel):
    class Meta(BaseModel.Meta):
        table_name = "aace-llms"

    llm_provider = UnicodeAttribute(hash_key=True)
    llm_name = UnicodeAttribute(range_key=True)
    module_name = UnicodeAttribute()
    class_name = UnicodeAttribute()
    configuration_schema = MapAttribute()
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
                    entity_keys["llm_provider"] = getattr(entity, "llm_provider", None)
                    entity_keys["llm_name"] = getattr(entity, "llm_name", None)

                # Fallback to kwargs (for creates/deletes)
                if not entity_keys.get("llm_provider"):
                    entity_keys["llm_provider"] = kwargs.get("llm_provider")
                if not entity_keys.get("llm_name"):
                    entity_keys["llm_name"] = kwargs.get("llm_name")

                # Only purge if we have the required keys
                if entity_keys.get("llm_provider") and entity_keys.get("llm_name"):
                    purge_entity_cascading_cache(
                        args[0].context.get("logger"),
                        entity_type="llm",
                        context_keys=None,  # LLMs don't use partition_key
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
    cache_name=Config.get_cache_name("models", "llm"),
    cache_enabled=Config.is_cache_enabled,
)
def get_llm(llm_provider: str, llm_name: str) -> LlmModel:
    return LlmModel.get(llm_provider, llm_name)


def get_llm_count(llm_provider: str, llm_name: str) -> int:
    return LlmModel.count(llm_provider, LlmModel.llm_name == llm_name)


def get_llm_type(info: ResolveInfo, llm: LlmModel) -> LlmType:
    llm = llm.__dict__["attribute_values"]
    return LlmType(**Serializer.json_normalize(llm))


def resolve_llm(info: ResolveInfo, **kwargs: Dict[str, Any]) -> LlmType | None:
    count = get_llm_count(kwargs["llm_provider"], kwargs["llm_name"])
    if count == 0:
        return None

    return get_llm_type(info, get_llm(kwargs["llm_provider"], kwargs["llm_name"]))


@monitor_decorator
@resolve_list_decorator(
    attributes_to_get=["llm_provider", "llm_name", "updated_at"],
    list_type_class=LlmListType,
    type_funct=get_llm_type,
)
def resolve_llm_list(info: ResolveInfo, **kwargs: Dict[str, Any]) -> Any:
    llm_provider = kwargs.get("llm_provider")
    module_name = kwargs.get("module_name")
    class_name = kwargs.get("class_name")
    updated_at_gt = kwargs.get("updated_at_gt")
    updated_at_lt = kwargs.get("updated_at_lt")

    args = []
    inquiry_funct = LlmModel.scan
    count_funct = LlmModel.count
    range_key_condition = None
    if llm_provider:
        # Build range key condition for updated_at when using updated_at_index
        if updated_at_gt is not None and updated_at_lt is not None:
            range_key_condition = LlmModel.updated_at.between(
                updated_at_gt, updated_at_lt
            )
        elif updated_at_gt is not None:
            range_key_condition = LlmModel.updated_at > updated_at_gt
        elif updated_at_lt is not None:
            range_key_condition = LlmModel.updated_at < updated_at_lt

        args = [llm_provider, range_key_condition]
        inquiry_funct = LlmModel.updated_at_index.query
        count_funct = LlmModel.updated_at_index.count

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
@purge_cache()
def insert_update_llm(info: ResolveInfo, **kwargs: Dict[str, Any]) -> Any:

    llm_provider = kwargs.get("llm_provider")
    llm_name = kwargs.get("llm_name")
    if kwargs.get("entity") is None:
        cols = {
            "module_name": kwargs["module_name"],
            "class_name": kwargs["class_name"],
            "configuration_schema": kwargs.get("configuration_schema", {}),
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
        "configuration_schema": LlmModel.configuration_schema,
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
@purge_cache()
def delete_llm(info: ResolveInfo, **kwargs: Dict[str, Any]) -> bool:

    agent_list = resolve_agent_list(
        info,
        **{
            "llm_provider": kwargs["entity"].llm_provider,
            "llm_name": kwargs["entity"].llm_name,
        },
    )
    if agent_list.total > 0:
        return False

    kwargs["entity"].delete()
    return True
