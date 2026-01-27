#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import functools
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
from ..types.prompt_template import PromptTemplateListType, PromptTemplateType
from ..utils.normalization import normalize_to_json


class PromptUuidIndex(LocalSecondaryIndex):
    """
    This class represents a local secondary index
    """

    class Meta:
        billing_mode = "PAY_PER_REQUEST"
        # All attributes are projected
        projection = AllProjection()
        index_name = "prompt_uuid-index"

    partition_key = UnicodeAttribute(hash_key=True)
    prompt_uuid = UnicodeAttribute(range_key=True)


class PromptTypeIndex(LocalSecondaryIndex):
    """
    This class represents a local secondary index
    """

    class Meta:
        billing_mode = "PAY_PER_REQUEST"
        # All attributes are projected
        projection = AllProjection()
        index_name = "prompt_type-index"

    partition_key = UnicodeAttribute(hash_key=True)
    prompt_type = UnicodeAttribute(range_key=True)


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


class PromptTemplateModel(BaseModel):
    class Meta(BaseModel.Meta):
        table_name = "aace-prompt_templates"

    partition_key = UnicodeAttribute(hash_key=True)
    prompt_version_uuid = UnicodeAttribute(range_key=True)
    endpoint_id = UnicodeAttribute()
    part_id = UnicodeAttribute()
    prompt_uuid = UnicodeAttribute()
    prompt_type = UnicodeAttribute()
    prompt_name = UnicodeAttribute()
    prompt_description = UnicodeAttribute(null=True)
    template_context = UnicodeAttribute()
    variables = ListAttribute(of=MapAttribute)
    mcp_servers = ListAttribute(of=MapAttribute)
    ui_components = ListAttribute(of=MapAttribute)
    status = UnicodeAttribute(default="active")
    updated_by = UnicodeAttribute()
    created_at = UTCDateTimeAttribute()
    updated_at = UTCDateTimeAttribute()
    prompt_uuid_index = PromptUuidIndex()
    prompt_type_index = PromptTypeIndex()
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
                    entity_keys["prompt_version_uuid"] = getattr(
                        entity, "prompt_version_uuid", None
                    )
                    entity_keys["prompt_uuid"] = getattr(entity, "prompt_uuid", None)

                # Fallback to kwargs (for creates/deletes)
                if not entity_keys.get("prompt_version_uuid"):
                    entity_keys["prompt_version_uuid"] = kwargs.get(
                        "prompt_version_uuid"
                    )
                if not entity_keys.get("prompt_uuid"):
                    entity_keys["prompt_uuid"] = kwargs.get("prompt_uuid")

                # Get partition_key from context or kwargs
                partition_key = args[0].context.get("partition_key") or kwargs.get(
                    "partition_key"
                )

                # Only purge if we have the required keys
                if entity_keys.get("prompt_version_uuid"):
                    purge_entity_cascading_cache(
                        args[0].context.get("logger"),
                        entity_type="prompt_template",
                        context_keys=(
                            {"partition_key": partition_key} if partition_key else None
                        ),
                        entity_keys=entity_keys,
                        cascade_depth=3,
                    )

                # Also purge active_prompt_template cache
                from silvaengine_utility.cache import HybridCacheEngine

                active_cache = HybridCacheEngine(
                    Config.get_cache_name("models", "active_prompt_template")
                )
                active_cache.clear()

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
    cache_name=Config.get_cache_name("models", "prompt_template"),
    cache_enabled=Config.is_cache_enabled,
)
def get_prompt_template(
    partition_key: str, prompt_version_uuid: str
) -> PromptTemplateModel:
    return PromptTemplateModel.get(partition_key, prompt_version_uuid)


@retry(
    reraise=True,
    wait=wait_exponential(multiplier=1, max=60),
    stop=stop_after_attempt(5),
)
@method_cache(
    ttl=Config.get_cache_ttl(),
    cache_name=Config.get_cache_name("models", "active_prompt_template"),
    cache_enabled=Config.is_cache_enabled,
)
def _get_active_prompt_template(
    partition_key: str, prompt_uuid: str
) -> PromptTemplateModel | None:
    try:
        results = PromptTemplateModel.prompt_uuid_index.query(
            partition_key,
            PromptTemplateModel.prompt_uuid == prompt_uuid,
            filter_condition=(PromptTemplateModel.status == "active"),
            scan_index_forward=False,
            limit=1,
        )
        prompt_template = results.next()
        return prompt_template
    except StopIteration:
        return None


def get_prompt_template_count(partition_key: str, prompt_version_uuid: str) -> int:
    return PromptTemplateModel.count(
        partition_key, PromptTemplateModel.prompt_version_uuid == prompt_version_uuid
    )


def get_prompt_template_type(
    info: ResolveInfo, prompt_template: PromptTemplateModel
) -> PromptTemplateType:
    _ = info  # Keep for signature compatibility with decorators
    prompt_template_dict = prompt_template.__dict__["attribute_values"].copy()
    return PromptTemplateType(**normalize_to_json(prompt_template_dict))


def resolve_prompt_template(
    info: ResolveInfo, **kwargs: Dict[str, Any]
) -> PromptTemplateType | None:
    if "prompt_uuid" in kwargs:
        return get_prompt_template_type(
            info,
            _get_active_prompt_template(
                info.context["partition_key"], kwargs["prompt_uuid"]
            ),
        )

    count = get_prompt_template_count(
        info.context["partition_key"], kwargs["prompt_version_uuid"]
    )
    if count == 0:
        return None

    return get_prompt_template_type(
        info,
        get_prompt_template(
            info.context["partition_key"], kwargs["prompt_version_uuid"]
        ),
    )


@monitor_decorator
@resolve_list_decorator(
    attributes_to_get=[
        "partition_key",
        "prompt_version_uuid",
        "prompt_uuid",
        "updated_at",
    ],
    list_type_class=PromptTemplateListType,
    type_funct=get_prompt_template_type,
)
def resolve_prompt_template_list(info: ResolveInfo, **kwargs: Dict[str, Any]) -> Any:
    partition_key = info.context["partition_key"]
    prompt_uuid = kwargs.get("prompt_uuid")
    prompt_type = kwargs.get("prompt_type")
    prompt_name = kwargs.get("prompt_name")
    statuses = kwargs.get("statuses")
    updated_at_gt = kwargs.get("updated_at_gt")
    updated_at_lt = kwargs.get("updated_at_lt")

    args = []
    inquiry_funct = PromptTemplateModel.scan
    count_funct = PromptTemplateModel.count
    range_key_condition = None
    if partition_key:
        # Build range key condition for updated_at when using updated_at_index
        if updated_at_gt is not None and updated_at_lt is not None:
            range_key_condition = PromptTemplateModel.updated_at.between(
                updated_at_gt, updated_at_lt
            )
        elif updated_at_gt is not None:
            range_key_condition = PromptTemplateModel.updated_at > updated_at_gt
        elif updated_at_lt is not None:
            range_key_condition = PromptTemplateModel.updated_at < updated_at_lt

        args = [partition_key, range_key_condition]
        inquiry_funct = PromptTemplateModel.updated_at_index.query
        count_funct = PromptTemplateModel.updated_at_index.count

        if prompt_uuid and args[1] is None:
            inquiry_funct = PromptTemplateModel.prompt_uuid_index.query
            args[1] = PromptTemplateModel.prompt_uuid == prompt_uuid
            count_funct = PromptTemplateModel.prompt_uuid_index.count
        elif prompt_type and args[1] is None:
            inquiry_funct = PromptTemplateModel.prompt_type_index.query
            args[1] = PromptTemplateModel.prompt_type == prompt_type
            count_funct = PromptTemplateModel.prompt_type_index.count

    the_filters = None
    if prompt_uuid and range_key_condition is not None:
        the_filters &= PromptTemplateModel.prompt_uuid == prompt_uuid
    if prompt_type and range_key_condition is not None:
        the_filters &= PromptTemplateModel.prompt_type == prompt_type
    if prompt_name:
        the_filters &= PromptTemplateModel.prompt_name.contains(prompt_name)
    if statuses:
        the_filters &= PromptTemplateModel.status.is_in(*statuses)
    if the_filters is not None:
        args.append(the_filters)

    return inquiry_funct, count_funct, args


def _inactivate_prompt_templates(
    info: ResolveInfo, partition_key: str, prompt_uuid: str
) -> None:
    try:
        partition_key = partition_key or info.context.get("partition_key")
        prompt_templates = PromptTemplateModel.prompt_uuid_index.query(
            partition_key,
            PromptTemplateModel.prompt_uuid == prompt_uuid,
            filter_condition=PromptTemplateModel.status == "active",
        )
        for prompt_template in prompt_templates:
            prompt_template.status = "inactive"
            prompt_template.save()
        return
    except Exception as e:
        log = traceback.format_exc()
        info.context.get("logger").error(log)
        raise e


@insert_update_decorator(
    keys={
        "hash_key": "partition_key",
        "range_key": "prompt_version_uuid",
    },
    model_funct=get_prompt_template,
    count_funct=get_prompt_template_count,
    type_funct=get_prompt_template_type,
)
@purge_cache()
def insert_update_prompt_template(info: ResolveInfo, **kwargs: Dict[str, Any]) -> Any:
    partition_key = kwargs.get("partition_key")
    prompt_version_uuid = kwargs.get("prompt_version_uuid")
    duplicate = kwargs.get("duplicate", False)

    if kwargs.get("entity") is None:
        cols = {
            "variables": [],
            "mcp_servers": [],
            "ui_components": [],
            "updated_by": kwargs["updated_by"],
            "created_at": pendulum.now("UTC"),
            "updated_at": pendulum.now("UTC"),
        }

        active_prompt_template = None
        if "prompt_uuid" in kwargs:
            active_prompt_template = _get_active_prompt_template(
                partition_key, kwargs["prompt_uuid"]
            )
        if active_prompt_template:
            excluded_fields = {
                "partition_key",
                "endpoint_id",
                "part_id",
                "prompt_version_uuid",
                "status",
                "updated_by",
                "created_at",
                "updated_at",
            }
            cols.update(
                {
                    k: v
                    for k, v in active_prompt_template.__dict__[
                        "attribute_values"
                    ].items()
                    if k not in excluded_fields
                }
            )
            if duplicate:
                timestamp = pendulum.now("UTC").int_timestamp
                cols["prompt_uuid"] = f"prompt-{timestamp}-{str(uuid.uuid4())[:8]}"
                cols["prompt_name"] = f"{cols['prompt_name']} (Copy)"
            else:
                # Deactivate previous versions before creating new one
                _inactivate_prompt_templates(info, partition_key, kwargs["prompt_uuid"])
        else:
            timestamp = pendulum.now("UTC").int_timestamp
            cols["prompt_uuid"] = f"prompt-{timestamp}-{str(uuid.uuid4())[:8]}"

        for key in [
            "prompt_type",
            "prompt_name",
            "prompt_description",
            "template_context",
            "variables",
            "mcp_servers",
            "ui_components",
        ]:
            if key in kwargs:
                cols[key] = kwargs[key]

        cols["endpoint_id"] = info.context.get("endpoint_id")
        cols["part_id"] = info.context.get("part_id")

        PromptTemplateModel(
            partition_key,
            prompt_version_uuid,
            **cols,
        ).save()
        return

    prompt_template = kwargs.get("entity")
    actions = [
        PromptTemplateModel.updated_by.set(kwargs["updated_by"]),
        PromptTemplateModel.updated_at.set(pendulum.now("UTC")),
    ]

    if "status" in kwargs and (
        kwargs["status"] == "active" and prompt_template.status == "inactive"
    ):
        _inactivate_prompt_templates(info, partition_key, prompt_template.prompt_uuid)

    field_map = {
        "prompt_type": PromptTemplateModel.prompt_type,
        "prompt_name": PromptTemplateModel.prompt_name,
        "prompt_description": PromptTemplateModel.prompt_description,
        "template_context": PromptTemplateModel.template_context,
        "variables": PromptTemplateModel.variables,
        "mcp_servers": PromptTemplateModel.mcp_servers,
        "ui_components": PromptTemplateModel.ui_components,
        "status": PromptTemplateModel.status,
    }

    for key, field in field_map.items():
        if key in kwargs:
            actions.append(field.set(None if kwargs[key] == "null" else kwargs[key]))

    prompt_template.update(actions=actions)

    return


@delete_decorator(
    keys={
        "hash_key": "partition_key",
        "range_key": "prompt_version_uuid",
    },
    model_funct=get_prompt_template,
)
@purge_cache()
def delete_prompt_template(info: ResolveInfo, **kwargs: Dict[str, Any]) -> bool:
    if kwargs["entity"].status == "active":
        results = PromptTemplateModel.prompt_uuid_index.query(
            kwargs["entity"].partition_key,
            PromptTemplateModel.prompt_uuid == kwargs["entity"].prompt_uuid,
            filter_condition=(PromptTemplateModel.status == "inactive"),
        )
        prompt_templates = [result for result in results]
        if len(prompt_templates) > 0:
            prompt_templates = sorted(
                prompt_templates, key=lambda x: x.updated_at, reverse=True
            )
            last_updated_record = prompt_templates[0]
            last_updated_record.status = "active"
            last_updated_record.save()

    kwargs["entity"].delete()
    return True
