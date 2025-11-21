#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import functools
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
from ..types.prompt_template import PromptTemplateListType, PromptTemplateType
from .utils import _get_mcp_servers, _get_ui_components


class PromptUuidIndex(LocalSecondaryIndex):
    """
    This class represents a local secondary index
    """

    class Meta:
        billing_mode = "PAY_PER_REQUEST"
        # All attributes are projected
        projection = AllProjection()
        index_name = "prompt_uuid-index"

    endpoint_id = UnicodeAttribute(hash_key=True)
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

    endpoint_id = UnicodeAttribute(hash_key=True)
    prompt_type = UnicodeAttribute(range_key=True)


class PromptTemplateModel(BaseModel):
    class Meta(BaseModel.Meta):
        table_name = "aace-prompt_templates"

    endpoint_id = UnicodeAttribute(hash_key=True)
    prompt_version_uuid = UnicodeAttribute(range_key=True)
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


def purge_cache():
    def actual_decorator(original_function):
        @functools.wraps(original_function)
        def wrapper_function(*args, **kwargs):
            try:
                # Use cascading cache purging for prompt templates
                from ..models.cache import purge_entity_cascading_cache

                try:
                    prompt_template = resolve_prompt_template(args[0], **kwargs)
                except Exception:
                    prompt_template = None

                endpoint_id = args[0].context.get("endpoint_id") or kwargs.get(
                    "endpoint_id"
                )
                entity_keys = {}
                if kwargs.get("prompt_version_uuid"):
                    entity_keys["prompt_version_uuid"] = kwargs.get(
                        "prompt_version_uuid"
                    )
                if prompt_template:
                    entity_keys["prompt_uuid"] = prompt_template.prompt_uuid

                result = purge_entity_cascading_cache(
                    args[0].context.get("logger"),
                    entity_type="prompt_template",
                    context_keys={"endpoint_id": endpoint_id} if endpoint_id else None,
                    entity_keys=entity_keys if entity_keys else None,
                    cascade_depth=3,
                )
                
                # Also purge active_prompt_template cache
                from silvaengine_utility.cache import HybridCacheEngine
                active_cache = HybridCacheEngine(Config.get_cache_name("models", "active_prompt_template"))
                active_cache.clear()

                ## Original function.
                result = original_function(*args, **kwargs)

                return result
            except Exception as e:
                log = traceback.format_exc()
                args[0].context.get("logger").error(log)
                raise e

        return wrapper_function

    return actual_decorator


def create_prompt_template_table(logger: logging.Logger) -> bool:
    """Create the PromptTemplate table if it doesn't exist."""
    if not PromptTemplateModel.exists():
        # Create with on-demand billing (PAY_PER_REQUEST)
        PromptTemplateModel.create_table(billing_mode="PAY_PER_REQUEST", wait=True)
        logger.info("The PromptTemplate table has been created.")
    return True


@retry(
    reraise=True,
    wait=wait_exponential(multiplier=1, max=60),
    stop=stop_after_attempt(5),
)
@method_cache(
    ttl=Config.get_cache_ttl(),
    cache_name=Config.get_cache_name("models", "prompt_template"),
)
def get_prompt_template(
    endpoint_id: str, prompt_version_uuid: str
) -> PromptTemplateModel:
    return PromptTemplateModel.get(endpoint_id, prompt_version_uuid)


@retry(
    reraise=True,
    wait=wait_exponential(multiplier=1, max=60),
    stop=stop_after_attempt(5),
)
@method_cache(
    ttl=Config.get_cache_ttl(),
    cache_name=Config.get_cache_name("models", "active_prompt_template"),
)
def _get_active_prompt_template(
    endpoint_id: str, prompt_uuid: str
) -> PromptTemplateModel | None:
    try:
        results = PromptTemplateModel.prompt_uuid_index.query(
            endpoint_id,
            PromptTemplateModel.prompt_uuid == prompt_uuid,
            filter_condition=(PromptTemplateModel.status == "active"),
            scan_index_forward=False,
            limit=1,
        )
        prompt_template = results.next()
        return prompt_template
    except StopIteration:
        return None


def get_prompt_template_count(endpoint_id: str, prompt_version_uuid: str) -> int:
    return PromptTemplateModel.count(
        endpoint_id, PromptTemplateModel.prompt_version_uuid == prompt_version_uuid
    )


def get_prompt_template_type(
    info: ResolveInfo, prompt_template: PromptTemplateModel
) -> PromptTemplateType:
    try:
        mcp_servers = _get_mcp_servers(info, prompt_template.mcp_servers)
        ui_components = _get_ui_components(info, prompt_template.ui_components)

        prompt_template = prompt_template.__dict__["attribute_values"]
        prompt_template["mcp_servers"] = mcp_servers
        prompt_template["ui_components"] = ui_components
        return PromptTemplateType(**Utility.json_normalize(prompt_template))
    except Exception as e:
        log = traceback.format_exc()
        info.context.get("logger").exception(log)
        raise e

def get_prompt_template_list_type(
    info: ResolveInfo, prompt_template: PromptTemplateModel
) -> PromptTemplateType:
    try:
        prompt_template = prompt_template.__dict__["attribute_values"]
        return PromptTemplateType(**Utility.json_normalize(prompt_template))
    except Exception as e:
        log = traceback.format_exc()
        info.context.get("logger").exception(log)
        raise e

def resolve_prompt_template(
    info: ResolveInfo, **kwargs: Dict[str, Any]
) -> PromptTemplateType | None:
    if "prompt_uuid" in kwargs:
        return get_prompt_template_type(
            info,
            _get_active_prompt_template(
                info.context["endpoint_id"], kwargs["prompt_uuid"]
            ),
        )

    count = get_prompt_template_count(
        info.context["endpoint_id"], kwargs["prompt_version_uuid"]
    )
    if count == 0:
        return None

    return get_prompt_template_type(
        info,
        get_prompt_template(info.context["endpoint_id"], kwargs["prompt_version_uuid"]),
    )


@monitor_decorator
@resolve_list_decorator(
    attributes_to_get=["endpoint_id", "prompt_version_uuid", "prompt_uuid"],
    list_type_class=PromptTemplateListType,
    type_funct=get_prompt_template_list_type,
)
def resolve_prompt_template_list(info: ResolveInfo, **kwargs: Dict[str, Any]) -> Any:
    endpoint_id = info.context["endpoint_id"]
    prompt_uuid = kwargs.get("prompt_uuid")
    prompt_type = kwargs.get("prompt_type")
    prompt_name = kwargs.get("prompt_name")
    statuses = kwargs.get("statuses")

    args = []
    inquiry_funct = PromptTemplateModel.scan
    count_funct = PromptTemplateModel.count
    if endpoint_id:
        args = [endpoint_id, None]
        inquiry_funct = PromptTemplateModel.query
        if prompt_uuid:
            inquiry_funct = PromptTemplateModel.prompt_uuid_index.query
            args[1] = PromptTemplateModel.prompt_uuid == prompt_uuid
            count_funct = PromptTemplateModel.prompt_uuid_index.count
        elif prompt_type:
            inquiry_funct = PromptTemplateModel.prompt_type_index.query
            args[1] = PromptTemplateModel.prompt_type == prompt_type
            count_funct = PromptTemplateModel.prompt_type_index.count

    the_filters = None
    if prompt_name:
        the_filters &= PromptTemplateModel.prompt_name.contains(prompt_name)
    if statuses:
        the_filters &= PromptTemplateModel.status.is_in(*statuses)
    if the_filters is not None:
        args.append(the_filters)

    return inquiry_funct, count_funct, args


def _inactivate_prompt_templates(
    info: ResolveInfo, endpoint_id: str, prompt_uuid: str
) -> None:
    try:
        endpoint_id = endpoint_id or info.context.get("endpoint_id")
        prompt_templates = PromptTemplateModel.prompt_uuid_index.query(
            endpoint_id,
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


@purge_cache()
@insert_update_decorator(
    keys={
        "hash_key": "endpoint_id",
        "range_key": "prompt_version_uuid",
    },
    model_funct=get_prompt_template,
    count_funct=get_prompt_template_count,
    type_funct=get_prompt_template_type,
)
def insert_update_prompt_template(info: ResolveInfo, **kwargs: Dict[str, Any]) -> Any:
    endpoint_id = kwargs.get("endpoint_id")
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
                endpoint_id, kwargs["prompt_uuid"]
            )
        if active_prompt_template:
            excluded_fields = {
                "endpoint_id",
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
                _inactivate_prompt_templates(info, endpoint_id, kwargs["prompt_uuid"])
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

        PromptTemplateModel(
            endpoint_id,
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
        _inactivate_prompt_templates(info, endpoint_id, prompt_template.prompt_uuid)

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


@purge_cache()
@delete_decorator(
    keys={
        "hash_key": "endpoint_id",
        "range_key": "prompt_version_uuid",
    },
    model_funct=get_prompt_template,
)
def delete_prompt_template(info: ResolveInfo, **kwargs: Dict[str, Any]) -> bool:
    if kwargs["entity"].status == "active":
        results = PromptTemplateModel.prompt_uuid_index.query(
            kwargs["entity"].endpoint_id,
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
