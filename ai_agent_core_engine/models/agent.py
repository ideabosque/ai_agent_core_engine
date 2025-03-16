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
from pynamodb.attributes import MapAttribute, UnicodeAttribute, UTCDateTimeAttribute
from pynamodb.indexes import AllProjection, LocalSecondaryIndex
from tenacity import retry, stop_after_attempt, wait_exponential

from silvaengine_dynamodb_base import (
    BaseModel,
    delete_decorator,
    insert_update_decorator,
    monitor_decorator,
    resolve_list_decorator,
)
from silvaengine_utility import Utility

from ..types.agent import AgentListType, AgentType
from .utils import _get_llm


class AgentUuidIndex(LocalSecondaryIndex):
    """
    This class represents a local secondary index
    """

    class Meta:
        billing_mode = "PAY_PER_REQUEST"
        # All attributes are projected
        projection = AllProjection()
        index_name = "agent_uuid-index"

    endpoint_id = UnicodeAttribute(hash_key=True)
    agent_uuid = UnicodeAttribute(range_key=True)


class AgentModel(BaseModel):
    class Meta(BaseModel.Meta):
        table_name = "aace-agents"

    endpoint_id = UnicodeAttribute(hash_key=True)
    agent_version_uuid = UnicodeAttribute(range_key=True)
    agent_uuid = UnicodeAttribute()
    agent_name = UnicodeAttribute()
    agent_description = UnicodeAttribute(null=True)
    llm_provider = UnicodeAttribute()
    llm_name = UnicodeAttribute()
    llm_configuration = MapAttribute(default={})
    instructions = UnicodeAttribute(null=True)
    configuration = MapAttribute(default={})
    function_configuration = MapAttribute(default={})
    functions = MapAttribute(default={})
    status = UnicodeAttribute(default="active")
    updated_by = UnicodeAttribute()
    created_at = UTCDateTimeAttribute()
    updated_at = UTCDateTimeAttribute()
    agent_uuid_index = AgentUuidIndex()


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
def get_agent(endpoint_id: str, agent_version_uuid: str) -> AgentModel:
    return AgentModel.get(endpoint_id, agent_version_uuid)


@retry(
    reraise=True,
    wait=wait_exponential(multiplier=1, max=60),
    stop=stop_after_attempt(5),
)
def _get_active_agent(endpoint_id: str, agent_uuid: str) -> AgentModel:
    try:
        results = AgentModel.agent_uuid_index.query(
            endpoint_id,
            AgentModel.agent_uuid == agent_uuid,
            filter_condition=(AgentModel.status == "active"),
            scan_index_forward=False,
            limit=1,
        )
        agent = results.next()

        return agent
    except StopIteration:
        return None


def get_agent_count(endpoint_id: str, agent_version_uuid: str) -> int:
    return AgentModel.count(
        endpoint_id, AgentModel.agent_version_uuid == agent_version_uuid
    )


def get_agent_type(info: ResolveInfo, agent: AgentModel) -> AgentType:
    try:
        llm = _get_llm(agent.llm_provider, agent.llm_name)
    except Exception as e:
        log = traceback.format_exc()
        info.context.get("logger").exception(log)
        raise e
    agent = agent.__dict__["attribute_values"]
    agent["llm"] = llm
    agent.pop("llm_provider")
    agent.pop("llm_name")
    return AgentType(**Utility.json_loads(Utility.json_dumps(agent)))


def resolve_agent(info: ResolveInfo, **kwargs: Dict[str, Any]) -> AgentType:
    if "agent_uuid" in kwargs:
        return get_agent_type(
            info, _get_active_agent(info.context["endpoint_id"], kwargs["agent_uuid"])
        )

    return get_agent_type(
        info,
        get_agent(info.context["endpoint_id"], kwargs["agent_version_uuid"]),
    )


@monitor_decorator
@resolve_list_decorator(
    attributes_to_get=["endpoint_id", "agent_version_uuid", "agent_uuid"],
    list_type_class=AgentListType,
    type_funct=get_agent_type,
)
def resolve_agent_list(info: ResolveInfo, **kwargs: Dict[str, Any]) -> Any:
    endpoint_id = info.context["endpoint_id"]
    agent_uuid = kwargs.get("agent_uuid")
    agent_name = kwargs.get("agent_name")
    llm_provider = kwargs.get("llm_provider")
    llm_name = kwargs.get("llm_name")
    model = kwargs.get("model")
    statuses = kwargs.get("statuses")

    args = []
    inquiry_funct = AgentModel.scan
    count_funct = AgentModel.count
    if endpoint_id:
        args = [endpoint_id, None]
        inquiry_funct = AgentModel.query
        if agent_uuid:
            inquiry_funct = AgentModel.agent_uuid_index.query
            args[1] = AgentModel.agent_uuid == agent_uuid
            count_funct = AgentModel.agent_uuid_index.count

    the_filters = None  # We can add filters for the query.
    if agent_name:
        the_filters &= AgentModel.agent_name.contains(agent_name)
    if llm_provider:
        the_filters &= AgentModel.llm_provider == llm_provider
    if llm_name:
        the_filters &= AgentModel.llm_name == llm_name
    if model:
        the_filters &= AgentModel.llm_configuration["model"] == model
    if statuses:
        the_filters &= AgentModel.status.is_in(*statuses)
    if the_filters is not None:
        args.append(the_filters)

    return inquiry_funct, count_funct, args


def _inactivate_agents(info: ResolveInfo, endpoint_id: str, agent_uuid: str) -> None:
    try:
        # Query for active agents matching the type and ID
        agents = AgentModel.agent_uuid_index.query(
            endpoint_id,
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
        "hash_key": "endpoint_id",
        "range_key": "agent_version_uuid",
    },
    model_funct=get_agent,
    count_funct=get_agent_count,
    type_funct=get_agent_type,
    # data_attributes_except_for_data_diff=["created_at", "updated_at"],
    # activity_history_funct=None,
)
def insert_update_agent(info: ResolveInfo, **kwargs: Dict[str, Any]) -> None:
    endpoint_id = kwargs.get("endpoint_id")
    agent_version_uuid = kwargs.get("agent_version_uuid")
    if kwargs.get("entity") is None:
        cols = {
            "updated_by": kwargs["updated_by"],
            "created_at": pendulum.now("UTC"),
            "updated_at": pendulum.now("UTC"),
        }

        # Handle an existing agent if an ID is provided
        active_agent = None
        if "agent_uuid" in kwargs:
            active_agent = _get_active_agent(endpoint_id, kwargs["agent_uuid"])
        if active_agent:
            # Copy all configuration and attributes from existing agent
            excluded_fields = {
                "endpoint_id",
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

            # Deactivate previous versions before creating new one
            _inactivate_agents(info, endpoint_id, kwargs["agent_uuid"])
        else:
            # Generate new unique agent UUID with timestamp
            timestamp = pendulum.now("UTC").int_timestamp
            cols["agent_uuid"] = f"agent-{timestamp}-{str(uuid.uuid4())[:8]}"

        for key in [
            "agent_name",
            "agent_description",
            "llm_provider",
            "llm_name",
            "llm_configuration",
            "instructions",
            "configuration",
            "function_configuration",
            "functions",
        ]:
            if key in kwargs:
                cols[key] = kwargs[key]

        AgentModel(
            endpoint_id,
            agent_version_uuid,
            **cols,
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
        _inactivate_agents(info, endpoint_id, agent.agent_uuid)

    # Map of kwargs keys to AgentModel attributes
    field_map = {
        "agent_name": AgentModel.agent_name,
        "agent_description": AgentModel.agent_description,
        "llm_provider": AgentModel.llm_provider,
        "llm_name": AgentModel.llm_name,
        "llm_configuration": AgentModel.llm_configuration,
        "instructions": AgentModel.instructions,
        "configuration": AgentModel.configuration,
        "function_configuration": AgentModel.function_configuration,
        "functions": AgentModel.functions,
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
        "hash_key": "endpoint_id",
        "range_key": "agent_version_uuid",
    },
    model_funct=get_agent,
)
def delete_agent(info: ResolveInfo, **kwargs: Dict[str, Any]) -> bool:
    if kwargs["entity"].status == "active":
        results = AgentModel.agent_uuid_index.query(
            kwargs["entity"].endpoint_id,
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
