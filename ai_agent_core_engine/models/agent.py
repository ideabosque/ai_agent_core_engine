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
    NumberAttribute,
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
from silvaengine_utility import Serializer, convert_decimal_to_number, method_cache
from tenacity import retry, stop_after_attempt, wait_exponential

from ..handlers.config import Config
from ..types.agent import AgentListType, AgentType
from .thread import resolve_thread_list
from .utils import _get_flow_snippet, _get_prompt_template


class AgentUuidIndex(LocalSecondaryIndex):
    """
    LSI for querying agents by agent_uuid within a partition.

    MIGRATION NOTE: Updated from endpoint_id to partition_key as hash_key.
    All LSIs share the same partition_key as the main table.
    This allows efficient queries like:
        AgentModel.agent_uuid_index.query(partition_key, AgentModel.agent_uuid == uuid)
    """

    class Meta:
        billing_mode = "PAY_PER_REQUEST"
        # All attributes are projected
        projection = AllProjection()
        index_name = "agent_uuid-index"

    partition_key = UnicodeAttribute(hash_key=True)  # MIGRATED: was endpoint_id
    agent_uuid = UnicodeAttribute(range_key=True)


class UpdatedAtIndex(LocalSecondaryIndex):
    """
    LSI for querying agents by updated_at within a partition.

    MIGRATION NOTE: Updated from endpoint_id to partition_key as hash_key.
    Enables time-range queries like:
        AgentModel.updated_at_index.query(partition_key, AgentModel.updated_at > start_time)
    """

    class Meta:
        billing_mode = "PAY_PER_REQUEST"
        # All attributes are projected
        projection = AllProjection()
        index_name = "updated_at-index"

    partition_key = UnicodeAttribute(hash_key=True)  # MIGRATED: was endpoint_id
    updated_at = UnicodeAttribute(range_key=True)


class AgentModel(BaseModel):
    """
    Agent Model - Reference Implementation for partition_key Migration

    MIGRATION PATTERN:
    1. Hash key changed from endpoint_id to partition_key (composite key)
    2. Added denormalized endpoint_id and part_id fields (for reference/debugging)
    3. Updated all LSI indexes to use partition_key as hash_key
    4. partition_key assembled in main.py: f"{endpoint_id}#{part_id}"

    USAGE:
    - Direct lookup: AgentModel.get(partition_key, agent_version_uuid)
    - Query by agent_uuid: AgentModel.agent_uuid_index.query(partition_key, ...)
    - Query by time: AgentModel.updated_at_index.query(partition_key, ...)

    IMPORTANT:
    - All 3 fields (partition_key, endpoint_id, part_id) must be set on insert/update
    - Extract endpoint_id/part_id from info.context, NOT by parsing partition_key
    - This model serves as the reference for migrating 8 remaining models
    """

    class Meta(BaseModel.Meta):
        table_name = "aace-agents"

    # Primary Key (MIGRATED)
    partition_key = UnicodeAttribute(
        hash_key=True
    )  # Format: "endpoint_id#part_id" (was: endpoint_id)
    agent_version_uuid = UnicodeAttribute(range_key=True)

    # Denormalized attributes (NEW - for reference/debugging only, no indexes needed)
    endpoint_id = UnicodeAttribute()  # Platform partition (e.g., "aws-prod-us-east-1")
    part_id = UnicodeAttribute()  # Business partition (e.g., "acme-corp")

    # Other attributes
    agent_uuid = UnicodeAttribute()
    agent_name = UnicodeAttribute()
    agent_description = UnicodeAttribute(null=True)
    llm_provider = UnicodeAttribute()
    llm_name = UnicodeAttribute()
    instructions = UnicodeAttribute(null=True)
    configuration = MapAttribute()
    mcp_server_uuids = ListAttribute(null=True)
    variables = ListAttribute(null=True, of=MapAttribute)
    num_of_messages = NumberAttribute(default=10)
    tool_call_role = UnicodeAttribute(default="developer")
    flow_snippet_version_uuid = UnicodeAttribute(null=True)
    status = UnicodeAttribute(default="active")
    updated_by = UnicodeAttribute()
    created_at = UTCDateTimeAttribute()
    updated_at = UTCDateTimeAttribute()

    # Indexes (all LSI - share same partition_key)
    # MIGRATION NOTE: All LSIs updated to use partition_key instead of endpoint_id
    agent_uuid_index = AgentUuidIndex()  # Query by agent_uuid within partition
    updated_at_index = UpdatedAtIndex()  # Query by time range within partition


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
                    entity_keys["agent_version_uuid"] = getattr(
                        entity, "agent_version_uuid", None
                    )
                    entity_keys["agent_uuid"] = getattr(entity, "agent_uuid", None)

                # Fallback to kwargs (for creates/deletes)
                if not entity_keys.get("agent_version_uuid"):
                    entity_keys["agent_version_uuid"] = kwargs.get("agent_version_uuid")
                if not entity_keys.get("agent_uuid"):
                    entity_keys["agent_uuid"] = kwargs.get("agent_uuid")

                # Get partition_key from context or kwargs
                partition_key = args[0].context.get("partition_key") or kwargs.get(
                    "partition_key"
                )

                # Only purge if we have the required keys
                if entity_keys.get("agent_version_uuid"):
                    purge_entity_cascading_cache(
                        args[0].context.get("logger"),
                        entity_type="agent",
                        context_keys=(
                            {"partition_key": partition_key} if partition_key else None
                        ),
                        entity_keys=entity_keys,
                        cascade_depth=3,
                    )

                # Also purge active_agent cache
                from silvaengine_utility.cache import HybridCacheEngine

                active_cache = HybridCacheEngine(
                    Config.get_cache_name("models", "active_agent")
                )
                active_cache.clear()

                return result
            except Exception as e:
                log = traceback.format_exc()
                args[0].context.get("logger").error(log)
                raise e

        return wrapper_function

    return actual_decorator


def create_agent_table(logger: logging.Logger) -> bool:
    """Create the Agent table if it doesn't exist."""
    if not AgentModel.exists():
        # Create with on-demand billing (PAY_PER_REQUEST)
        AgentModel.create_table(billing_mode="PAY_PER_REQUEST", wait=True)
        logger.info("The Agent table has been created.")
    return True


@retry(
    reraise=True,
    wait=wait_exponential(multiplier=1, max=60),
    stop=stop_after_attempt(5),
)
@method_cache(
    ttl=Config.get_cache_ttl(), cache_name=Config.get_cache_name("models", "agent")
)
def get_agent(partition_key: str, agent_version_uuid: str) -> AgentModel:
    return AgentModel.get(partition_key, agent_version_uuid)


@retry(
    reraise=True,
    wait=wait_exponential(multiplier=1, max=60),
    stop=stop_after_attempt(5),
)
@method_cache(
    ttl=Config.get_cache_ttl(),
    cache_name=Config.get_cache_name("models", "active_agent"),
)
def _get_active_agent(partition_key: str, agent_uuid: str) -> AgentModel | None:
    try:
        results = AgentModel.agent_uuid_index.query(
            partition_key,
            AgentModel.agent_uuid == agent_uuid,
            filter_condition=(AgentModel.status == "active"),
            scan_index_forward=False,
            limit=1,
        )
        agent = results.next()

        return agent
    except StopIteration:
        return None


def get_agent_count(partition_key: str, agent_version_uuid: str) -> int:
    return AgentModel.count(
        partition_key, AgentModel.agent_version_uuid == agent_version_uuid
    )


def get_agent_type(info: ResolveInfo, agent: AgentModel) -> AgentType:
    try:
        agent_dict: Dict = agent.__dict__["attribute_values"]
        # Keep foreign keys for nested resolvers
        # No need to fetch llm, mcp_servers, or flow_snippet here
    except Exception as e:
        log = traceback.format_exc()
        info.context.get("logger").exception(log)
        raise e
    return AgentType(**Serializer.json_normalize(agent_dict))


def resolve_agent(info: ResolveInfo, **kwargs: Dict[str, Any]) -> AgentType | None:
    partition_key = info.context["partition_key"]

    if "agent_uuid" in kwargs:
        return get_agent_type(
            info, _get_active_agent(partition_key, kwargs["agent_uuid"])
        )

    count = get_agent_count(partition_key, kwargs["agent_version_uuid"])
    if count == 0:
        return None

    return get_agent_type(
        info,
        get_agent(partition_key, kwargs["agent_version_uuid"]),
    )


@monitor_decorator
@resolve_list_decorator(
    attributes_to_get=[
        "partition_key",
        "agent_version_uuid",
        "agent_uuid",
        "updated_at",
    ],
    list_type_class=AgentListType,
    type_funct=get_agent_type,
    scan_index_forward=False,
)
def resolve_agent_list(info: ResolveInfo, **kwargs: Dict[str, Any]) -> Any:
    info.context.get("logger").info(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
    info.context.get("logger").info(info.context)
    info.context.get("logger").info("<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<")
    partition_key = info.context["partition_key"]
    agent_uuid = kwargs.get("agent_uuid")
    agent_name = kwargs.get("agent_name")
    llm_provider = kwargs.get("llm_provider")
    llm_name = kwargs.get("llm_name")
    model = kwargs.get("model")
    statuses = kwargs.get("statuses")
    flow_snippet_version_uuid = kwargs.get("flow_snippet_version_uuid")
    updated_at_gt = kwargs.get("updated_at_gt")
    updated_at_lt = kwargs.get("updated_at_lt")

    args = []
    inquiry_funct = AgentModel.scan
    count_funct = AgentModel.count
    range_key_condition = None
    if partition_key:
        # Build range key condition for updated_at when using updated_at_index
        if updated_at_gt is not None and updated_at_lt is not None:
            range_key_condition = AgentModel.updated_at.between(
                updated_at_gt, updated_at_lt
            )
        elif updated_at_gt is not None:
            range_key_condition = AgentModel.updated_at > updated_at_gt
        elif updated_at_lt is not None:
            range_key_condition = AgentModel.updated_at < updated_at_lt

        args = [partition_key, range_key_condition]
        inquiry_funct = AgentModel.updated_at_index.query
        count_funct = AgentModel.updated_at_index.count

        if agent_uuid and args[1] is None:
            inquiry_funct = AgentModel.agent_uuid_index.query
            args[1] = AgentModel.agent_uuid == agent_uuid
            count_funct = AgentModel.agent_uuid_index.count

    the_filters = None  # We can add filters for the query.
    if agent_uuid and range_key_condition is not None:
        the_filters &= AgentModel.agent_uuid == agent_uuid
    if agent_name:
        the_filters &= AgentModel.agent_name.contains(agent_name)
    if llm_provider:
        the_filters &= AgentModel.llm_provider == llm_provider
    if llm_name:
        the_filters &= AgentModel.llm_name == llm_name
    if model:
        the_filters &= AgentModel.configuration["model"] == model
    if statuses:
        the_filters &= AgentModel.status.is_in(*statuses)
    if flow_snippet_version_uuid:
        the_filters &= AgentModel.flow_snippet_version_uuid == flow_snippet_version_uuid
    if the_filters is not None:
        args.append(the_filters)

    return inquiry_funct, count_funct, args


def _inactivate_agents(info: ResolveInfo, partition_key: str, agent_uuid: str) -> None:
    try:
        # Query for active agents matching the type and ID
        partition_key = partition_key or info.context.get("partition_key")
        agents = AgentModel.agent_uuid_index.query(
            partition_key,
            AgentModel.agent_uuid == agent_uuid,
            filter_condition=AgentModel.status == "active",
        )
        # Update status to inactive for each matching agent
        for agent in agents:
            agent.status = "inactive"
            agent.save()
        return
    except Exception as e:
        log = traceback.format_exc()
        info.context.get("logger").error(log)
        raise e


@insert_update_decorator(
    keys={
        "hash_key": "partition_key",
        "range_key": "agent_version_uuid",
    },
    model_funct=get_agent,
    count_funct=get_agent_count,
    type_funct=get_agent_type,
    # data_attributes_except_for_data_diff=["created_at", "updated_at"],
    # activity_history_funct=None,
)
@purge_cache()
def insert_update_agent(info: ResolveInfo, **kwargs: Dict[str, Any]) -> Any:
    partition_key = kwargs.get("partition_key")
    agent_version_uuid = kwargs.get("agent_version_uuid")
    duplicate = kwargs.get("duplicate", False)

    if kwargs.get("entity") is None:
        cols = {
            "configuration": {},
            "mcp_server_uuids": [],
            "variables": [],
            "updated_by": kwargs["updated_by"],
            "created_at": pendulum.now("UTC"),
            "updated_at": pendulum.now("UTC"),
        }

        # Handle an existing agent if an ID is provided
        active_agent = None
        if "agent_uuid" in kwargs:
            active_agent = _get_active_agent(partition_key, kwargs["agent_uuid"])
        if active_agent:
            # Copy all configuration and attributes from existing agent
            excluded_fields = {
                "partition_key",
                "endpoint_id",
                "part_id",
                "agent_version_uuid",
                "status",
                "updated_by",
                "created_at",
                "updated_at",
            }

            # Retain configuration and functions, then deactivate previous versions
            cols.update(
                {
                    k: v
                    for k, v in active_agent.__dict__["attribute_values"].items()
                    if k not in excluded_fields
                }
            )

            if duplicate:
                timestamp = pendulum.now("UTC").int_timestamp
                cols["agent_version_uuid"] = (
                    f"agent-{timestamp}-{str(uuid.uuid4())[:8]}"
                )
                cols["agent_name"] = f"{cols['agent_name']} (Copy)"
            else:
                # Deactivate previous versions before creating new one
                _inactivate_agents(info, partition_key, kwargs["agent_uuid"])
        else:
            # Generate new unique agent UUID with timestamp
            timestamp = pendulum.now("UTC").int_timestamp
            cols["agent_uuid"] = f"agent-{timestamp}-{str(uuid.uuid4())[:8]}"

        for key in [
            "agent_name",
            "agent_description",
            "llm_provider",
            "llm_name",
            "instructions",
            "configuration",
            "mcp_server_uuids",
            "variables",
            "num_of_messages",
            "tool_call_role",
            "flow_snippet_version_uuid",
        ]:
            if key in kwargs:
                cols[key] = kwargs[key]

                if key == "flow_snippet_version_uuid":
                    flow_snippet = _get_flow_snippet(partition_key, kwargs[key])
                    prmopt_template = _get_prompt_template(
                        info, flow_snippet["prompt_uuid"]
                    )

                    # replace variables
                    agent_variables = {
                        variable["name"]: variable["value"]
                        for variable in kwargs.get("variables", [])
                    }

                    replace_prmopt_template_variables = [
                        variable["name"]
                        for variable in prmopt_template.get("variables", [])
                        if variable["name"] in agent_variables
                    ]

                    has_flow_context_content = False
                    if (
                        flow_snippet["flow_context"] is not None
                        and flow_snippet["flow_context"] != ""
                    ):
                        if len(replace_prmopt_template_variables) > 0:
                            for variable in replace_prmopt_template_variables:
                                flow_snippet["flow_context"] = flow_snippet[
                                    "flow_context"
                                ].replace(
                                    f"{{{variable}}}",
                                    agent_variables[variable],
                                )
                        has_flow_context_content = True

                    cols["instructions"] = prmopt_template["template_context"].replace(
                        "{flow_snippet}", flow_snippet["flow_context"]
                    )

                    if not has_flow_context_content:
                        if len(replace_prmopt_template_variables) > 0:
                            for variable in replace_prmopt_template_variables:
                                cols["instructions"] = cols["instructions"].replace(
                                    f"{{{variable}}}",
                                    agent_variables[variable],
                                )

                    cols["mcp_server_uuids"] = [
                        mcp_server["mcp_server_uuid"]
                        for mcp_server in prmopt_template["mcp_servers"]
                        if mcp_server.get("mcp_server_uuid")
                    ]

        cols["endpoint_id"] = info.context.get("endpoint_id")  # Platform identifier
        cols["part_id"] = info.context.get("part_id")  # Business partition

        AgentModel(
            partition_key,
            agent_version_uuid,
            **convert_decimal_to_number(cols),
        ).save()
        return

    agent = kwargs.get("entity")
    actions = [
        AgentModel.updated_by.set(kwargs["updated_by"]),
        AgentModel.updated_at.set(pendulum.now("UTC")),
    ]

    if "status" in kwargs and (
        kwargs["status"] == "active" and agent.status == "inactive"
    ):
        _inactivate_agents(info, partition_key, agent.agent_uuid)

    # Map of kwargs keys to AgentModel attributes
    field_map = {
        "agent_name": AgentModel.agent_name,
        "agent_description": AgentModel.agent_description,
        "llm_provider": AgentModel.llm_provider,
        "llm_name": AgentModel.llm_name,
        "instructions": AgentModel.instructions,
        "configuration": AgentModel.configuration,
        "mcp_server_uuids": AgentModel.mcp_server_uuids,
        "variables": AgentModel.variables,
        "num_of_messages": AgentModel.num_of_messages,
        "tool_call_role": AgentModel.tool_call_role,
        "flow_snippet_version_uuid": AgentModel.flow_snippet_version_uuid,
        "status": AgentModel.status,
    }

    # Build actions dynamically based on the presence of keys in kwargs
    for key, field in field_map.items():
        if key in kwargs:  # Check if the key exists in kwargs
            actions.append(field.set(None if kwargs[key] == "null" else kwargs[key]))

    # Update the agent
    agent.update(actions=actions)

    return


@delete_decorator(
    keys={
        "hash_key": "partition_key",
        "range_key": "agent_version_uuid",
    },
    model_funct=get_agent,
)
@purge_cache()
def delete_agent(info: ResolveInfo, **kwargs: Dict[str, Any]) -> bool:
    thread_list = resolve_thread_list(
        info,
        **{
            "partition_key": kwargs["entity"].partition_key,
            "agent_uuid": kwargs["entity"].agent_version_uuid,
        },
    )
    if thread_list.total > 0:
        return False

    if kwargs["entity"].status == "active":
        results = AgentModel.agent_uuid_index.query(
            kwargs["entity"].partition_key,
            AgentModel.agent_uuid == kwargs["entity"].agent_uuid,
            filter_condition=(AgentModel.status == "inactive"),
        )
        agents = [result for result in results]
        if len(agents) > 0:
            agents = sorted(agents, key=lambda x: x.updated_at, reverse=True)
            last_updated_record = agents[0]
            last_updated_record.status = "active"
            last_updated_record.save()

    kwargs["entity"].delete()

    return True
