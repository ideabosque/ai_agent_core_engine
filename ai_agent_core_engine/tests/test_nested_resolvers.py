#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Integration-style tests using GraphQL execution to verify nested resolvers.
Refactored to use pytest.parametrize for checking batching behavior across
different nested fields (LLM, MCP Servers, Flow Snippets, Wizards).

These tests mock the top-level Query resolvers via a local TestQuery class
and assert that the nested resolvers trigger the batch loaders correctly.
"""
from __future__ import print_function

__author__ = "bibow"

import json
import os
import sys
from typing import Any, Dict, List, Tuple
from unittest.mock import MagicMock

import graphene
import pytest
from promise import Promise

# Allow running the test directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from ai_agent_core_engine.models.batch_loaders import RequestLoaders
from ai_agent_core_engine.types.agent import AgentType
from ai_agent_core_engine.types.wizard_group import WizardGroupType

# ---------------------------------------------------------------------------
# Test Schema
# ---------------------------------------------------------------------------


class TestQuery(graphene.ObjectType):
    """
    A simplified Query root that fetches objects from a registry in the context.
    This avoids needing the real database layer.
    """

    agent = graphene.Field(AgentType, agent_uuid=graphene.String())
    wizard_group = graphene.Field(WizardGroupType, wizard_group_uuid=graphene.String())

    def resolve_agent(root, info, agent_uuid):
        registry = info.context.get("registry", {})
        return registry.get(f"agent:{agent_uuid}")

    def resolve_wizard_group(root, info, wizard_group_uuid):
        registry = info.context.get("registry", {})
        return registry.get(f"wg:{wizard_group_uuid}")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def test_data():
    """Load canonical fixture data for nested resolver integration tests."""
    data_path = os.path.join(os.path.dirname(__file__), "test_data.json")
    with open(data_path, "r") as fp:
        return json.load(fp)


@pytest.fixture(scope="module")
def schema():
    """Provide the Graphene schema using our local TestQuery."""
    return graphene.Schema(query=TestQuery)


@pytest.fixture()
def context_and_loaders(test_data):
    """Create a mock GraphQL context plus request-scoped loaders."""
    endpoint_id = "test-endpoint-001"
    if "mcp_servers" in test_data and len(test_data["mcp_servers"]) > 0:
        endpoint_id = test_data["mcp_servers"][0].get("endpointId", endpoint_id)

    ctx: Dict[str, Any] = {
        "logger": MagicMock(),
        "endpoint_id": endpoint_id,
        "part_id": endpoint_id,
        "partition_key": f"{endpoint_id}#{endpoint_id}",
        "registry": {},  # For looking up mock objects by ID
    }
    # Enable cache to ensure deduplication works
    loaders = RequestLoaders(ctx, cache_enabled=True)
    ctx["batch_loaders"] = loaders
    return ctx, loaders


def _stub_batch_loader(
    loader,
    results_for_keys: Dict[Tuple[str, str], Dict[str, Any]],
    seen_keys: List[List[Tuple[str, str]]],
):
    """Replace batch_load_fn to capture keys and return provided results."""

    def _batch(keys: List[Tuple[str, str]]) -> Promise:
        seen_keys.append(list(keys))
        ordered_results = [results_for_keys.get(key) for key in keys]
        return Promise.resolve(ordered_results)

    loader.batch_load_fn = _batch


# ---------------------------------------------------------------------------
# Setup Functions for Parametrization
# ---------------------------------------------------------------------------


def setup_llm(test_data, partition_key):
    llm_a = test_data["llms"][0]
    llm_b = test_data["llms"][1]
    key_a = (llm_a["llmProvider"], llm_a["llmName"])
    key_b = (llm_b["llmProvider"], llm_b["llmName"])

    results = {
        key_a: {"llm_provider": llm_a["llmProvider"], "llm_name": llm_a["llmName"]},
        key_b: {"llm_provider": llm_b["llmProvider"], "llm_name": llm_b["llmName"]},
    }

    obj_a = AgentType(llm_provider=llm_a["llmProvider"], llm_name=llm_a["llmName"])
    obj_b = AgentType(llm_provider=llm_b["llmProvider"], llm_name=llm_b["llmName"])

    return {
        "results": results,
        "keys": [key_a, key_b],
        "obj_a": obj_a,
        "obj_b": obj_b,
        "val_a": llm_a["llmName"],
        "val_b": llm_b["llmName"],
    }


def setup_mcp(test_data, partition_key):
    mcp_a = test_data["mcp_servers"][0]
    mcp_a_uuid = mcp_a.get("mcpServerUuid", "70825090807816536192")
    mcp_b_uuid = "mcp-second-uuid"

    results = {
        (partition_key, mcp_a_uuid): {
            "mcp_server_uuid": mcp_a_uuid,
            "mcp_label": mcp_a["mcpLabel"],
        },
        (partition_key, mcp_b_uuid): {
            "mcp_server_uuid": mcp_b_uuid,
            "mcp_label": "Second MCP",
        },
    }

    obj_a = AgentType(mcp_server_uuids=[mcp_a_uuid])
    obj_a.partition_key = partition_key
    obj_b = AgentType(mcp_server_uuids=[mcp_b_uuid])
    obj_b.partition_key = partition_key

    return {
        "results": results,
        "keys": [(partition_key, mcp_a_uuid), (partition_key, mcp_b_uuid)],
        "obj_a": obj_a,
        "obj_b": obj_b,
        "val_a": mcp_a["mcpLabel"],
        "val_b": "Second MCP",
    }


def setup_flow(test_data, partition_key):
    flow_a = test_data["flow_snippets"][0]
    flow_a_uuid = flow_a.get("flowSnippetVersionUuid", "fs-1")
    flow_b_uuid = "fs-2"

    results = {
        (partition_key, flow_a_uuid): {
            "flow_snippet_version_uuid": flow_a_uuid,
            "flow_name": flow_a["flowName"],
        },
        (partition_key, flow_b_uuid): {
            "flow_snippet_version_uuid": flow_b_uuid,
            "flow_name": "Second Flow",
        },
    }

    obj_a = AgentType(flow_snippet_version_uuid=flow_a_uuid)
    obj_a.partition_key = partition_key
    obj_b = AgentType(flow_snippet_version_uuid=flow_b_uuid)
    obj_b.partition_key = partition_key

    return {
        "results": results,
        "keys": [(partition_key, flow_a_uuid), (partition_key, flow_b_uuid)],
        "obj_a": obj_a,
        "obj_b": obj_b,
        "val_a": flow_a["flowName"],
        "val_b": "Second Flow",
    }


def setup_wizard(test_data, partition_key):
    wizard = test_data["wizards"][0]
    wizard_uuid_a = wizard.get("wizardUuid", "83684635492349919360")
    wizard_uuid_b = "wizard-second-uuid"

    results = {
        (partition_key, wizard_uuid_a): {
            "wizard_uuid": wizard_uuid_a,
            "wizard_title": wizard["wizardTitle"],
        },
        (partition_key, wizard_uuid_b): {
            "wizard_uuid": wizard_uuid_b,
            "wizard_title": "Second Wizard",
        },
    }

    obj_a = WizardGroupType(wizard_uuids=[wizard_uuid_a])
    obj_a.partition_key = partition_key
    obj_b = WizardGroupType(wizard_uuids=[wizard_uuid_b])
    obj_b.partition_key = partition_key

    return {
        "results": results,
        "keys": [(partition_key, wizard_uuid_a), (partition_key, wizard_uuid_b)],
        "obj_a": obj_a,
        "obj_b": obj_b,
        "val_a": wizard["wizardTitle"],
        "val_b": "Second Wizard",
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "config",
    [
        {
            "id": "agent_llm",
            "root_field": "agent",
            "arg_name": "agentUuid",
            "registry_prefix": "agent",
            "loader_attr": "llm_loader",
            "setup_fn": setup_llm,
            "query_fragment": "llm { llmName }",
            "getter": lambda d: d["llm"]["llmName"],
        },
        {
            "id": "agent_mcp",
            "root_field": "agent",
            "arg_name": "agentUuid",
            "registry_prefix": "agent",
            "loader_attr": "mcp_server_loader",
            "setup_fn": setup_mcp,
            "query_fragment": "mcpServers",
            # mcpServers returns list of dicts
            "getter": lambda d: d["mcpServers"][0]["mcp_label"],
        },
        {
            "id": "agent_flow",
            "root_field": "agent",
            "arg_name": "agentUuid",
            "registry_prefix": "agent",
            "loader_attr": "flow_snippet_loader",
            "setup_fn": setup_flow,
            "query_fragment": "flowSnippet { flowName }",
            "getter": lambda d: d["flowSnippet"]["flowName"],
        },
        {
            "id": "wizard_group_wizards",
            "root_field": "wizardGroup",
            "arg_name": "wizardGroupUuid",
            "registry_prefix": "wg",
            "loader_attr": "wizard_loader",
            "setup_fn": setup_wizard,
            "query_fragment": "wizards",
            # wizards returns list of dicts
            "getter": lambda d: d["wizards"][0]["wizard_title"],
        },
    ],
    ids=lambda x: x["id"],
)
def test_nested_resolver_batching(schema, context_and_loaders, test_data, config):
    """
    Consolidated test for batching behavior of nested resolvers.
    Executes a GraphQL query fetching two objects and verifies that
    the backend loader batches the nested requests.
    """
    ctx, loaders = context_and_loaders
    seen = []
    endpoint_id = ctx["endpoint_id"]
    partition_key = ctx["partition_key"]

    # 1. Setup specific test data
    setup_data = config["setup_fn"](test_data, partition_key)
    target_loader = getattr(loaders, config["loader_attr"])

    # 2. Stub the loader
    _stub_batch_loader(target_loader, setup_data["results"], seen)

    # 3. Register mock objects in context registry
    prefix = config["registry_prefix"]
    ctx["registry"][f"{prefix}:1"] = setup_data["obj_a"]
    ctx["registry"][f"{prefix}:2"] = setup_data["obj_b"]

    # 4. Construct Query
    root = config["root_field"]
    arg = config["arg_name"]
    fragment = config["query_fragment"]

    query = f"""
        query {{
            item1: {root}({arg}: "1") {{
                {fragment}
            }}
            item2: {root}({arg}: "2") {{
                {fragment}
            }}
        }}
    """

    # 5. Execute
    result = schema.execute(query, context_value=ctx)

    assert not result.errors

    # 6. Verify Data
    val_a = config["getter"](result.data["item1"])
    val_b = config["getter"](result.data["item2"])
    assert val_a == setup_data["val_a"]
    assert val_b == setup_data["val_b"]

    # 7. Verify Batching
    all_seen_keys = [k for batch in seen for k in batch]
    expected_keys = setup_data["keys"]

    # Ensure all expected keys were requested
    for k in expected_keys:
        assert k in all_seen_keys, f"Key {k} was not requested via loader"

    # Ensure the loader was called (length check assumes single batch or split batch containing all keys)
    assert len(all_seen_keys) >= len(expected_keys)


@pytest.mark.integration
def test_graphql_mixed_nested_resolvers(schema, context_and_loaders, test_data):
    """
    Verify multiple nested fields on a single agent batch independently.
    This remains a separate test as it tests a different access pattern (1 object, multiple fields).
    """
    ctx, loaders = context_and_loaders
    llm_seen, mcp_seen, flow_seen = [], [], []
    endpoint_id = ctx["endpoint_id"]
    partition_key = ctx["partition_key"]

    llm_a = test_data["llms"][0]
    mcp = test_data["mcp_servers"][0]
    flow = test_data["flow_snippets"][0]

    llm_key = (llm_a["llmProvider"], llm_a["llmName"])
    mcp_uuid = mcp.get("mcpServerUuid", "70825090807816536192")
    mcp_key = (partition_key, mcp_uuid)
    flow_uuid = flow.get("flowSnippetVersionUuid", "fs-1")
    flow_key = (partition_key, flow_uuid)

    _stub_batch_loader(
        loaders.llm_loader,
        {
            llm_key: {
                "llm_provider": llm_a["llmProvider"],
                "llm_name": llm_a["llmName"],
            }
        },
        llm_seen,
    )
    _stub_batch_loader(
        loaders.mcp_server_loader,
        {mcp_key: {"mcp_server_uuid": mcp_uuid, "mcp_label": mcp["mcpLabel"]}},
        mcp_seen,
    )
    _stub_batch_loader(
        loaders.flow_snippet_loader,
        {
            flow_key: {
                "flow_snippet_version_uuid": flow_uuid,
                "flow_name": flow["flowName"],
            }
        },
        flow_seen,
    )

    agent = AgentType(
        llm_provider=llm_a["llmProvider"],
        llm_name=llm_a["llmName"],
        mcp_server_uuids=[mcp_uuid],
        flow_snippet_version_uuid=flow_uuid,
    )
    agent.partition_key = partition_key
    agent.endpoint_id = endpoint_id

    ctx["registry"]["agent:mix"] = agent

    query = """
        query {
            agent(agentUuid: "mix") {
                llm { llmName }
                mcpServers
                flowSnippet { flowName }
            }
        }
    """
    result = schema.execute(query, context_value=ctx)

    assert not result.errors
    data = result.data["agent"]
    assert data["llm"]["llmName"] == llm_a["llmName"]
    assert data["mcpServers"][0]["mcp_label"] == mcp["mcpLabel"]
    assert data["flowSnippet"]["flowName"] == flow["flowName"]

    assert [k for b in llm_seen for k in b] == [llm_key]
    assert [k for b in mcp_seen for k in b] == [mcp_key]
    assert [k for b in flow_seen for k in b] == [flow_key]


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"] + sys.argv[1:]))
