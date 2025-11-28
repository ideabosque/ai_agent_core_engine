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
from pynamodb.attributes import UnicodeAttribute, UTCDateTimeAttribute
from pynamodb.indexes import AllProjection, LocalSecondaryIndex
from silvaengine_dynamodb_base import (
    BaseModel,
    delete_decorator,
    insert_update_decorator,
    monitor_decorator,
    resolve_list_decorator,
)
from silvaengine_utility import Utility, convert_decimal_to_number, method_cache
from tenacity import retry, stop_after_attempt, wait_exponential

from ..handlers.ai_agent_utility import convert_flow_snippet_xml
from ..handlers.config import Config
from ..types.flow_snippet import (
    FlowSnippetBaseType,
    FlowSnippetListType,
    FlowSnippetType,
)
from .utils import _update_agents_by_flow_snippet


class FlowSnippetUuidIndex(LocalSecondaryIndex):
    class Meta:
        billing_mode = "PAY_PER_REQUEST"
        # All attributes are projected
        projection = AllProjection()
        index_name = "flow_snippet_uuid-index"

    endpoint_id = UnicodeAttribute(hash_key=True)
    flow_snippet_uuid = UnicodeAttribute(range_key=True)


class PromptUuidIndex(LocalSecondaryIndex):
    class Meta:
        billing_mode = "PAY_PER_REQUEST"
        # All attributes are projected
        projection = AllProjection()
        index_name = "prompt_uuid-index"

    endpoint_id = UnicodeAttribute(hash_key=True)
    prompt_uuid = UnicodeAttribute(range_key=True)


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


class FlowSnippetModel(BaseModel):
    class Meta(BaseModel.Meta):
        table_name = "aace-flow_snippets"

    endpoint_id = UnicodeAttribute(hash_key=True)
    flow_snippet_version_uuid = UnicodeAttribute(range_key=True)
    flow_snippet_uuid = UnicodeAttribute()
    prompt_uuid = UnicodeAttribute()
    flow_name = UnicodeAttribute()
    flow_relationship = UnicodeAttribute(null=True)
    flow_context = UnicodeAttribute(null=True)
    status = UnicodeAttribute(default="active")
    updated_by = UnicodeAttribute()
    created_at = UTCDateTimeAttribute()
    updated_at = UTCDateTimeAttribute()
    flow_snippet_uuid_index = FlowSnippetUuidIndex()
    prompt_uuid_index = PromptUuidIndex()
    updated_at_index = UpdatedAtIndex()


def purge_cache():
    def actual_decorator(original_function):
        @functools.wraps(original_function)
        def wrapper_function(*args, **kwargs):
            try:
                # Use cascading cache purging for flow snippets
                from ..models.cache import purge_entity_cascading_cache

                try:
                    flow_snippet = resolve_flow_snippet(args[0], **kwargs)
                except Exception as e:
                    flow_snippet = None

                endpoint_id = args[0].context.get("endpoint_id") or kwargs.get(
                    "endpoint_id"
                )
                entity_keys = {}
                if kwargs.get("flow_snippet_version_uuid"):
                    entity_keys["flow_snippet_version_uuid"] = kwargs.get(
                        "flow_snippet_version_uuid"
                    )
                if flow_snippet:
                    entity_keys["flow_snippet_uuid"] = flow_snippet.flow_snippet_uuid

                result = purge_entity_cascading_cache(
                    args[0].context.get("logger"),
                    entity_type="flow_snippet",
                    context_keys={"endpoint_id": endpoint_id} if endpoint_id else None,
                    entity_keys=entity_keys if entity_keys else None,
                    cascade_depth=3,
                )

                # Also purge active_flow_snippet cache
                from silvaengine_utility.cache import HybridCacheEngine

                active_cache = HybridCacheEngine(
                    Config.get_cache_name("models", "active_flow_snippet")
                )
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


def create_flow_snippet_table(logger: logging.Logger) -> bool:
    """Create the FlowSnippet table if it doesn't exist."""
    if not FlowSnippetModel.exists():
        # Create with on-demand billing (PAY_PER_REQUEST)
        FlowSnippetModel.create_table(billing_mode="PAY_PER_REQUEST", wait=True)
        logger.info("The FlowSnippet table has been created.")
    return True


@retry(
    reraise=True,
    wait=wait_exponential(multiplier=1, max=60),
    stop=stop_after_attempt(5),
)
@method_cache(
    ttl=Config.get_cache_ttl(),
    cache_name=Config.get_cache_name("models", "flow_snippet"),
)
def get_flow_snippet(
    endpoint_id: str, flow_snippet_version_uuid: str
) -> FlowSnippetModel:
    return FlowSnippetModel.get(endpoint_id, flow_snippet_version_uuid)


@retry(
    reraise=True,
    wait=wait_exponential(multiplier=1, max=60),
    stop=stop_after_attempt(5),
)
@method_cache(
    ttl=Config.get_cache_ttl(),
    cache_name=Config.get_cache_name("models", "active_flow_snippet"),
)
def _get_active_flow_snippet(
    endpoint_id: str, flow_snippet_uuid: str
) -> FlowSnippetModel | None:
    try:
        results = FlowSnippetModel.flow_snippet_uuid_index.query(
            endpoint_id,
            FlowSnippetModel.flow_snippet_uuid == flow_snippet_uuid,
            filter_condition=(FlowSnippetModel.status == "active"),
            scan_index_forward=False,
            limit=1,
        )
        flow_snippet = results.next()
        return flow_snippet
    except StopIteration:
        return None


def get_flow_snippet_count(endpoint_id: str, flow_snippet_version_uuid: str) -> int:
    return FlowSnippetModel.count(
        endpoint_id,
        FlowSnippetModel.flow_snippet_version_uuid == flow_snippet_version_uuid,
    )


def get_flow_snippet_type(
    info: ResolveInfo, flow_snippet: FlowSnippetModel
) -> FlowSnippetType:
    """
    Nested resolver approach: return minimal flow snippet data.
    - Do NOT embed 'prompt_template'.
    - Keep 'prompt_uuid' as foreign key.
    - This is resolved lazily by FlowSnippetType.resolve_prompt_template.
    """
    try:
        flow_snippet_dict: Dict = flow_snippet.__dict__["attribute_values"]
        return FlowSnippetType(**Utility.json_normalize(flow_snippet_dict))
    except Exception as e:
        log = traceback.format_exc()
        info.context.get("logger").exception(log)
        raise e


def get_flow_snippet_list_type(
    info: ResolveInfo, flow_snippet: FlowSnippetModel
) -> FlowSnippetBaseType:
    """
    Nested resolver approach: return minimal flow snippet data.
    - Do NOT embed 'prompt_template'.
    - Keep 'prompt_uuid' as foreign key.
    """
    try:
        flow_snippet_dict: Dict = flow_snippet.__dict__["attribute_values"]
        # Remove detailed fields for list view
        flow_snippet_dict.pop("flow_context", None)
        flow_snippet_dict.pop("flow_relationship", None)
        return FlowSnippetBaseType(**Utility.json_normalize(flow_snippet_dict))
    except Exception as e:
        log = traceback.format_exc()
        info.context.get("logger").exception(log)
        raise e


def resolve_flow_snippet(
    info: ResolveInfo, **kwargs: Dict[str, Any]
) -> FlowSnippetType | None:
    if "flow_snippet_uuid" in kwargs:
        return get_flow_snippet_type(
            info,
            _get_active_flow_snippet(
                info.context["endpoint_id"], kwargs["flow_snippet_uuid"]
            ),
        )

    count = get_flow_snippet_count(
        info.context["endpoint_id"], kwargs["flow_snippet_version_uuid"]
    )
    if count == 0:
        return None

    return get_flow_snippet_type(
        info,
        get_flow_snippet(
            info.context["endpoint_id"], kwargs["flow_snippet_version_uuid"]
        ),
    )


@monitor_decorator
@resolve_list_decorator(
    attributes_to_get=["endpoint_id", "flow_snippet_version_uuid", "flow_snippet_uuid"],
    list_type_class=FlowSnippetListType,
    type_funct=get_flow_snippet_list_type,
)
def resolve_flow_snippet_list(info: ResolveInfo, **kwargs: Dict[str, Any]) -> Any:
    endpoint_id = info.context["endpoint_id"]
    flow_snippet_uuid = kwargs.get("flow_snippet_uuid")
    prompt_uuid = kwargs.get("prompt_uuid")
    flow_name = kwargs.get("flow_name")
    statuses = kwargs.get("statuses")
    updated_at_gt = kwargs.get("updated_at_gt")
    updated_at_lt = kwargs.get("updated_at_lt")

    args = []
    inquiry_funct = FlowSnippetModel.scan
    count_funct = FlowSnippetModel.count
    range_key_condition = None
    if endpoint_id:
        # Build range key condition for updated_at when using updated_at_index
        if updated_at_gt is not None and updated_at_lt is not None:
            range_key_condition = FlowSnippetModel.updated_at.between(
                updated_at_gt, updated_at_lt
            )
        elif updated_at_gt is not None:
            range_key_condition = FlowSnippetModel.updated_at > updated_at_gt
        elif updated_at_lt is not None:
            range_key_condition = FlowSnippetModel.updated_at < updated_at_lt

        args = [endpoint_id, range_key_condition]
        inquiry_funct = FlowSnippetModel.updated_at_index.query
        count_funct = FlowSnippetModel.updated_at_index.count

        if flow_snippet_uuid and args[1] is None:
            inquiry_funct = FlowSnippetModel.flow_snippet_uuid_index.query
            args[1] = FlowSnippetModel.flow_snippet_uuid == flow_snippet_uuid
            count_funct = FlowSnippetModel.flow_snippet_uuid_index.count

        elif prompt_uuid and args[1] is None:
            inquiry_funct = FlowSnippetModel.prompt_uuid_index.query
            args[1] = FlowSnippetModel.prompt_uuid == prompt_uuid
            count_funct = FlowSnippetModel.prompt_uuid_index.count

    the_filters = None
    if flow_snippet_uuid and range_key_condition is not None:
        the_filters &= FlowSnippetModel.flow_snippet_uuid == flow_snippet_uuid
    if prompt_uuid and range_key_condition is not None:
        the_filters &= FlowSnippetModel.prompt_uuid == prompt_uuid
    if flow_name:
        the_filters &= FlowSnippetModel.flow_name.contains(flow_name)
    if statuses:
        the_filters &= FlowSnippetModel.status.is_in(*statuses)
    if the_filters is not None:
        args.append(the_filters)

    return inquiry_funct, count_funct, args


def _inactivate_flow_snippets(
    info: ResolveInfo, endpoint_id: str, flow_snippet_uuid: str
) -> None:
    try:
        endpoint_id = endpoint_id or info.context.get("endpoint_id")
        flow_snippets = FlowSnippetModel.flow_snippet_uuid_index.query(
            endpoint_id,
            FlowSnippetModel.flow_snippet_uuid == flow_snippet_uuid,
            filter_condition=FlowSnippetModel.status == "active",
        )
        for flow_snippet in flow_snippets:
            flow_snippet.status = "inactive"
            flow_snippet.save()
        return
    except Exception as e:
        log = traceback.format_exc()
        info.context.get("logger").error(log)
        raise e


@purge_cache()
@insert_update_decorator(
    keys={
        "hash_key": "endpoint_id",
        "range_key": "flow_snippet_version_uuid",
    },
    model_funct=get_flow_snippet,
    count_funct=get_flow_snippet_count,
    type_funct=get_flow_snippet_type,
)
def insert_update_flow_snippet(info: ResolveInfo, **kwargs: Dict[str, Any]) -> Any:
    endpoint_id = kwargs.get("endpoint_id")
    flow_snippet_version_uuid = kwargs.get("flow_snippet_version_uuid")
    duplicate = kwargs.get("duplicate", False)

    if kwargs.get("entity") is None:
        cols = {
            "updated_by": kwargs["updated_by"],
            "created_at": pendulum.now("UTC"),
            "updated_at": pendulum.now("UTC"),
        }

        active_flow_snippet = None
        if "flow_snippet_uuid" in kwargs:
            active_flow_snippet = _get_active_flow_snippet(
                endpoint_id, kwargs["flow_snippet_uuid"]
            )
        if active_flow_snippet:
            excluded_fields = {
                "endpoint_id",
                "flow_snippet_version_uuid",
                "status",
                "updated_by",
                "created_at",
                "updated_at",
            }
            cols.update(
                {
                    k: v
                    for k, v in active_flow_snippet.__dict__["attribute_values"].items()
                    if k not in excluded_fields
                }
            )
            if duplicate:
                timestamp = pendulum.now("UTC").int_timestamp
                cols["flow_snippet_uuid"] = (
                    f"flow-snippet-{timestamp}-{str(uuid.uuid4())[:8]}"
                )
                cols["flow_name"] = f"{cols['flow_name']} (Copy)"
            else:
                # Deactivate previous versions before creating new one
                _inactivate_flow_snippets(
                    info, endpoint_id, kwargs["flow_snippet_uuid"]
                )
        else:
            timestamp = pendulum.now("UTC").int_timestamp
            cols["flow_snippet_uuid"] = (
                f"flow-snippet-{timestamp}-{str(uuid.uuid4())[:8]}"
            )

        for key in [
            "prompt_uuid",
            "flow_name",
            "flow_relationship",
            "flow_context",
        ]:
            if key in kwargs:
                if key == "flow_context" and Config.xml_convert:
                    cols[key] = convert_flow_snippet_xml(kwargs[key])
                else:
                    cols[key] = kwargs[key]

        FlowSnippetModel(
            endpoint_id,
            flow_snippet_version_uuid,
            **convert_decimal_to_number(cols),
        ).save()

        if active_flow_snippet is not None:
            _update_agents_by_flow_snippet(
                info,
                active_flow_snippet.flow_snippet_version_uuid,
                flow_snippet_version_uuid,
            )
        return

    flow_snippet = kwargs.get("entity")
    actions = [
        FlowSnippetModel.updated_by.set(kwargs["updated_by"]),
        FlowSnippetModel.updated_at.set(pendulum.now("UTC")),
    ]

    if "status" in kwargs and (
        kwargs["status"] == "active" and flow_snippet.status == "inactive"
    ):
        _inactivate_flow_snippets(info, endpoint_id, flow_snippet.flow_snippet_uuid)

    field_map = {
        "prompt_uuid": FlowSnippetModel.prompt_uuid,
        "flow_name": FlowSnippetModel.flow_name,
        "flow_relationship": FlowSnippetModel.flow_relationship,
        "flow_context": FlowSnippetModel.flow_context,
        "status": FlowSnippetModel.status,
    }

    for key, field in field_map.items():
        if key in kwargs:
            if key == "flow_context" and Config.xml_convert:
                actions.append(field.set(convert_flow_snippet_xml(kwargs[key])))
            else:
                actions.append(
                    field.set(None if kwargs[key] == "null" else kwargs[key])
                )

    flow_snippet.update(actions=actions)

    return


@purge_cache()
@delete_decorator(
    keys={
        "hash_key": "endpoint_id",
        "range_key": "flow_snippet_version_uuid",
    },
    model_funct=get_flow_snippet,
)
def delete_flow_snippet(info: ResolveInfo, **kwargs: Dict[str, Any]) -> bool:

    if kwargs["entity"].status == "active":
        results = FlowSnippetModel.flow_snippet_uuid_index.query(
            kwargs["entity"].endpoint_id,
            FlowSnippetModel.flow_snippet_uuid == kwargs["entity"].flow_snippet_uuid,
            filter_condition=(FlowSnippetModel.status == "inactive"),
        )
        flow_snippets = [result for result in results]
        if len(flow_snippets) > 0:
            flow_snippets = sorted(
                flow_snippets, key=lambda x: x.updated_at, reverse=True
            )
            last_updated_record = flow_snippets[0]
            last_updated_record.status = "active"
            last_updated_record.save()

    kwargs["entity"].delete()
    return True
