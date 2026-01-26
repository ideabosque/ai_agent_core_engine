#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
AI Agent Core Engine Tests

Pytest-based test suite for AI Agent Core Engine GraphQL operations.
Refactored to follow the pattern in ai_marketing_engine (Lifecycle Flow Tests).
"""

from __future__ import print_function

__author__ = "bibow"

import json
import logging
import os
import sys
from typing import Any

import pytest
from dotenv import load_dotenv
from test_helpers import call_method, log_test_result

load_dotenv()

# Add parent directory to path to allow imports when running directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger()

from silvaengine_utility import Graphql

# Load test data from JSON file
_test_data_file = os.path.join(os.path.dirname(__file__), "test_data.json")
with open(_test_data_file, "r") as f:
    _TEST_DATA = json.load(f)

# Extract test data sets for parametrization
LLM_TEST_DATA = _TEST_DATA.get("llms", [])
AGENT_TEST_DATA = _TEST_DATA.get("agents", [])
THREAD_TEST_DATA = _TEST_DATA.get("threads", [])
RUN_TEST_DATA = _TEST_DATA.get("runs", [])
MESSAGE_TEST_DATA = _TEST_DATA.get("messages", [])
TOOL_CALL_TEST_DATA = _TEST_DATA.get("tool_calls", [])
PROMPT_TEMPLATE_TEST_DATA = _TEST_DATA.get("prompt_templates", [])
FLOW_SNIPPET_TEST_DATA = _TEST_DATA.get("flow_snippets", [])
MCP_SERVER_TEST_DATA = _TEST_DATA.get("mcp_servers", [])
UI_COMPONENT_TEST_DATA = _TEST_DATA.get("ui_components", [])
WIZARD_TEST_DATA = _TEST_DATA.get("wizards", [])
WIZARD_SCHEMA_TEST_DATA = _TEST_DATA.get("wizard_schemas", [])
WIZARD_GROUP_TEST_DATA = _TEST_DATA.get("wizard_groups", [])
WIZARD_GROUP_FILTER_TEST_DATA = _TEST_DATA.get("wizard_group_filters", [])
ELEMENT_TEST_DATA = _TEST_DATA.get("elements", [])
FINE_TUNING_MESSAGE_TEST_DATA = _TEST_DATA.get("fine_tuning_messages", [])
ASYNC_TASK_TEST_DATA = _TEST_DATA.get("async_tasks", [])


# ============================================================================
# TESTS
# ============================================================================


@pytest.mark.integration
@pytest.mark.graphql
@log_test_result
def test_graphql_ping(ai_agent_core_engine: Any, schema: Any) -> None:
    """Test GraphQL ping operation."""
    query = Graphql.generate_graphql_operation("ping", "Query", schema)
    logger.info(f"Query: {query}")
    payload = {
        "query": query,
        "variables": {},
    }
    result, error = call_method(
        ai_agent_core_engine,
        "ai_agent_core_graphql",
        payload,
        "graphql_ping",
    )
    assert error is None, f"GraphQL ping failed: {error}"
    logger.info(result)


@pytest.mark.integration
@pytest.mark.graphql
@pytest.mark.llm
@pytest.mark.parametrize("test_data", LLM_TEST_DATA)
@log_test_result
def test_llm_lifecycle_flow(
    ai_agent_core_engine: Any, schema: Any, test_data: Any
) -> None:
    """Test LLM lifecycle: Insert -> Get -> Update -> Delete."""
    # 1. Insert
    insert_query = Graphql.generate_graphql_operation(
        "insertUpdateLlm", "Mutation", schema
    )
    result, error = call_method(
        ai_agent_core_engine,
        "ai_agent_core_graphql",
        {"query": insert_query, "variables": test_data},
        "insert_llm",
    )
    assert error is None, f"Insert LLM failed: {error}"
    assert (
        result.get("data", {}).get("insertUpdateLlm", {}).get("llm")
    ), "Insert LLM failed - llm object missing in response"

    # 2. Get (Verify)
    get_query = Graphql.generate_graphql_operation("llm", "Query", schema)
    get_variables = {
        "llmProvider": test_data["llmProvider"],
        "llmName": test_data["llmName"],
    }
    result, error = call_method(
        ai_agent_core_engine,
        "ai_agent_core_graphql",
        {"query": get_query, "variables": get_variables},
        "get_llm",
    )
    assert error is None, f"Get LLM failed: {error}"
    assert result.get("data", {}).get("llm"), "LLM not found after insertion"

    # 3. Get List (Verify)
    list_query = Graphql.generate_graphql_operation("llmList", "Query", schema)
    list_variables = {"llmProvider": test_data["llmProvider"]}
    result, error = call_method(
        ai_agent_core_engine,
        "ai_agent_core_graphql",
        {"query": list_query, "variables": list_variables},
        "list_llms",
    )
    assert error is None, f"List LLMs failed: {error}"
    llm_list = result.get("data", {}).get("llmList", {}).get("llmList")
    assert llm_list and len(llm_list) > 0, "LLM list empty or missing"

    # 4. Update (if applicable, here we just re-insert with same data which acts as update)
    # For demonstration, we might change something if the API supports it, but here we just re-run insert
    result, error = call_method(
        ai_agent_core_engine,
        "ai_agent_core_graphql",
        {"query": insert_query, "variables": test_data},
        "update_llm",
    )
    assert error is None, f"Update LLM failed: {error}"

    if not int(os.getenv("full_lifecycle_flow", "0")):
        return
    # 5. Delete
    delete_query = Graphql.generate_graphql_operation("deleteLlm", "Mutation", schema)
    delete_variables = {
        "llmProvider": test_data["llmProvider"],
        "llmName": test_data["llmName"],
        "updatedBy": test_data.get("updatedBy", "test-user"),
    }
    result, error = call_method(
        ai_agent_core_engine,
        "ai_agent_core_graphql",
        {"query": delete_query, "variables": delete_variables},
        "delete_llm",
    )
    assert error is None, f"Delete LLM failed: {error}"
    assert (
        result.get("data", {}).get("deleteLlm", {}).get("ok")
    ), "Delete LLM failed - ok flag missing/false"


@pytest.mark.integration
@pytest.mark.graphql
@pytest.mark.agent
@pytest.mark.parametrize("test_data", AGENT_TEST_DATA)
@log_test_result
def test_agent_lifecycle_flow(
    ai_agent_core_engine: Any, schema: Any, test_data: Any
) -> None:
    """Test Agent lifecycle: Insert -> Get -> Delete."""
    # 1. Insert
    insert_query = Graphql.generate_graphql_operation(
        "insertUpdateAgent", "Mutation", schema
    )
    result, error = call_method(
        ai_agent_core_engine,
        "ai_agent_core_graphql",
        {"query": insert_query, "variables": test_data},
        "insert_agent",
    )
    assert error is None, f"Insert Agent failed: {error}"
    agent_data = result.get("data", {}).get("insertUpdateAgent", {}).get("agent", {})
    assert agent_data, "Agent data missing in response"

    # Capture UUIDs for subsequent steps
    agent_uuid = agent_data.get("agentUuid") or test_data.get("agentUuid")
    agent_version_uuid = agent_data.get("agentVersionUuid") or test_data.get(
        "agentVersionUuid"
    )

    # 2. Get (Verify)
    get_query = Graphql.generate_graphql_operation("agent", "Query", schema)
    get_variables = {"agentUuid": agent_uuid}
    result, error = call_method(
        ai_agent_core_engine,
        "ai_agent_core_graphql",
        {"query": get_query, "variables": get_variables},
        "get_agent",
    )
    assert error is None, f"Get Agent failed: {error}"
    assert result.get("data", {}).get("agent"), "Agent not found after insertion"

    # 3. Get List (Verify)
    list_query = Graphql.generate_graphql_operation("agentList", "Query", schema)
    list_variables = {"agentName": test_data["agentName"]}
    result, error = call_method(
        ai_agent_core_engine,
        "ai_agent_core_graphql",
        {"query": list_query, "variables": list_variables},
        "list_agents",
    )
    assert error is None, f"List Agents failed: {error}"
    agent_list = result.get("data", {}).get("agentList", {}).get("agentList")
    assert agent_list and len(agent_list) > 0, "Agent list empty or missing"

    if not int(os.getenv("full_lifecycle_flow", "0")):
        return
    # 4. Delete
    delete_query = Graphql.generate_graphql_operation("deleteAgent", "Mutation", schema)
    delete_variables = {
        "agentVersionUuid": agent_version_uuid,
        "updatedBy": test_data.get("updatedBy", "test-user"),
    }
    result, error = call_method(
        ai_agent_core_engine,
        "ai_agent_core_graphql",
        {"query": delete_query, "variables": delete_variables},
        "delete_agent",
    )
    assert error is None, f"Delete Agent failed: {error}"
    assert (
        result.get("data", {}).get("deleteAgent", {}).get("ok")
    ), "Delete Agent failed - ok flag missing/false"


@pytest.mark.integration
@pytest.mark.graphql
@pytest.mark.thread
@pytest.mark.parametrize("test_data", THREAD_TEST_DATA)
@log_test_result
def test_thread_lifecycle_flow(
    ai_agent_core_engine: Any, schema: Any, test_data: Any
) -> None:
    """Test Thread lifecycle: Insert -> Get -> Delete."""
    # 1. Insert
    insert_query = Graphql.generate_graphql_operation(
        "insertThread", "Mutation", schema
    )
    result, error = call_method(
        ai_agent_core_engine,
        "ai_agent_core_graphql",
        {"query": insert_query, "variables": test_data},
        "insert_thread",
    )
    assert error is None, f"Insert Thread failed: {error}"
    thread_data = result.get("data", {}).get("insertThread", {}).get("thread", {})
    assert thread_data, "Thread data missing in response"

    thread_uuid = thread_data.get("threadUuid") or test_data.get("threadUuid")

    # 2. Get (Verify)
    get_query = Graphql.generate_graphql_operation("thread", "Query", schema)
    get_variables = {"threadUuid": thread_uuid}
    result, error = call_method(
        ai_agent_core_engine,
        "ai_agent_core_graphql",
        {"query": get_query, "variables": get_variables},
        "get_thread",
    )
    assert error is None, f"Get Thread failed: {error}"
    assert result.get("data", {}).get("thread"), "Thread not found after insertion"

    # 3. Get List (Verify)
    list_query = Graphql.generate_graphql_operation("threadList", "Query", schema)
    list_variables = {"agentUuid": test_data.get("agentUuid")}
    result, error = call_method(
        ai_agent_core_engine,
        "ai_agent_core_graphql",
        {"query": list_query, "variables": list_variables},
        "list_threads",
    )
    assert error is None, f"List Threads failed: {error}"
    thread_list = result.get("data", {}).get("threadList", {}).get("threadList")
    assert thread_list and len(thread_list) > 0, "Thread list empty or missing"

    if not int(os.getenv("full_lifecycle_flow", "0")):
        return
    # 4. Delete
    delete_query = Graphql.generate_graphql_operation(
        "deleteThread", "Mutation", schema
    )
    delete_variables = {
        "threadUuid": thread_uuid,
        "updatedBy": test_data.get("updatedBy", "test-user"),
    }
    result, error = call_method(
        ai_agent_core_engine,
        "ai_agent_core_graphql",
        {"query": delete_query, "variables": delete_variables},
        "delete_thread",
    )
    assert error is None, f"Delete Thread failed: {error}"
    assert (
        result.get("data", {}).get("deleteThread", {}).get("ok")
    ), "Delete Thread failed - ok flag missing/false"


@pytest.mark.integration
@pytest.mark.graphql
@pytest.mark.run
@pytest.mark.parametrize("test_data", RUN_TEST_DATA)
@log_test_result
def test_run_lifecycle_flow(
    ai_agent_core_engine: Any, schema: Any, test_data: Any
) -> None:
    """Test Run lifecycle: Insert -> Get -> Delete."""
    # 1. Insert
    insert_query = Graphql.generate_graphql_operation(
        "insertUpdateRun", "Mutation", schema
    )
    result, error = call_method(
        ai_agent_core_engine,
        "ai_agent_core_graphql",
        {"query": insert_query, "variables": test_data},
        "insert_run",
    )
    assert error is None, f"Insert Run failed: {error}"
    run_data = result.get("data", {}).get("insertUpdateRun", {}).get("run", {})
    assert run_data, "Run data missing in response"

    run_uuid = run_data.get("runUuid") or test_data.get("runUuid")
    thread_uuid = test_data.get("threadUuid")

    # 2. Get (Verify)
    get_query = Graphql.generate_graphql_operation("run", "Query", schema)
    get_variables = {"threadUuid": thread_uuid, "runUuid": run_uuid}
    result, error = call_method(
        ai_agent_core_engine,
        "ai_agent_core_graphql",
        {"query": get_query, "variables": get_variables},
        "get_run",
    )
    assert error is None, f"Get Run failed: {error}"
    assert result.get("data", {}).get("run"), "Run not found after insertion"

    # 3. Get List (Verify)
    list_query = Graphql.generate_graphql_operation("runList", "Query", schema)
    list_variables = {"threadUuid": thread_uuid}
    result, error = call_method(
        ai_agent_core_engine,
        "ai_agent_core_graphql",
        {"query": list_query, "variables": list_variables},
        "list_runs",
    )
    assert error is None, f"List Runs failed: {error}"
    run_list = result.get("data", {}).get("runList", {}).get("runList")
    assert run_list and len(run_list) > 0, "Run list empty or missing"

    if not int(os.getenv("full_lifecycle_flow", "0")):
        return
    # 4. Delete
    delete_query = Graphql.generate_graphql_operation("deleteRun", "Mutation", schema)
    delete_variables = {
        "threadUuid": thread_uuid,
        "runUuid": run_uuid,
        "updatedBy": test_data.get("updatedBy", "test-user"),
    }
    result, error = call_method(
        ai_agent_core_engine,
        "ai_agent_core_graphql",
        {"query": delete_query, "variables": delete_variables},
        "delete_run",
    )
    assert error is None, f"Delete Run failed: {error}"
    assert (
        result.get("data", {}).get("deleteRun", {}).get("ok")
    ), "Delete Run failed - ok flag missing/false"


@pytest.mark.integration
@pytest.mark.graphql
@pytest.mark.message
@pytest.mark.parametrize("test_data", MESSAGE_TEST_DATA)
@log_test_result
def test_message_lifecycle_flow(
    ai_agent_core_engine: Any, schema: Any, test_data: Any
) -> None:
    """Test Message lifecycle: Insert -> Get -> Delete."""
    # 1. Insert
    insert_query = Graphql.generate_graphql_operation(
        "insertUpdateMessage", "Mutation", schema
    )
    result, error = call_method(
        ai_agent_core_engine,
        "ai_agent_core_graphql",
        {"query": insert_query, "variables": test_data},
        "insert_message",
    )
    assert error is None, f"Insert Message failed: {error}"
    message_data = (
        result.get("data", {}).get("insertUpdateMessage", {}).get("message", {})
    )
    assert message_data, "Message data missing in response"

    message_uuid = message_data.get("messageUuid") or test_data.get("messageUuid")
    message_id = message_data.get("messageId") or test_data.get("messageId")
    thread_uuid = test_data.get("threadUuid")

    # 2. Get (Verify)
    get_query = Graphql.generate_graphql_operation("message", "Query", schema)
    get_variables = {"threadUuid": thread_uuid, "messageUuid": message_uuid}
    result, error = call_method(
        ai_agent_core_engine,
        "ai_agent_core_graphql",
        {"query": get_query, "variables": get_variables},
        "get_message",
    )
    assert error is None, f"Get Message failed: {error}"
    assert result.get("data", {}).get("message"), "Message not found after insertion"

    if not int(os.getenv("full_lifecycle_flow", "0")):
        return
    # 3. Delete
    delete_query = Graphql.generate_graphql_operation(
        "deleteMessage", "Mutation", schema
    )
    delete_variables = {"threadUuid": thread_uuid, "messageUuid": message_uuid}
    result, error = call_method(
        ai_agent_core_engine,
        "ai_agent_core_graphql",
        {"query": delete_query, "variables": delete_variables},
        "delete_message",
    )
    assert error is None, f"Delete Message failed: {error}"
    assert (
        result.get("data", {}).get("deleteMessage", {}).get("ok")
    ), "Delete Message failed - ok flag missing/false"


@pytest.mark.integration
@pytest.mark.graphql
@pytest.mark.tool_call
@pytest.mark.parametrize("test_data", TOOL_CALL_TEST_DATA)
@log_test_result
def test_tool_call_lifecycle_flow(
    ai_agent_core_engine: Any, schema: Any, test_data: Any
) -> None:
    """Test Tool Call lifecycle: Insert -> Get -> Delete."""
    # 1. Insert
    insert_query = Graphql.generate_graphql_operation(
        "insertUpdateToolCall", "Mutation", schema
    )
    result, error = call_method(
        ai_agent_core_engine,
        "ai_agent_core_graphql",
        {"query": insert_query, "variables": test_data},
        "insert_tool_call",
    )
    assert error is None, f"Insert Tool Call failed: {error}"
    tool_call_data = (
        result.get("data", {}).get("insertUpdateToolCall", {}).get("toolCall", {})
    )
    assert tool_call_data, "Tool Call data missing in response"

    tool_call_uuid = tool_call_data.get("toolCallUuid") or test_data.get("toolCallUuid")
    thread_uuid = test_data.get("threadUuid")

    # 2. Get (Verify)
    get_query = Graphql.generate_graphql_operation("toolCall", "Query", schema)
    get_variables = {"threadUuid": thread_uuid, "toolCallUuid": tool_call_uuid}
    result, error = call_method(
        ai_agent_core_engine,
        "ai_agent_core_graphql",
        {"query": get_query, "variables": get_variables},
        "get_tool_call",
    )
    assert error is None, f"Get Tool Call failed: {error}"
    assert result.get("data", {}).get("toolCall"), "Tool Call not found after insertion"

    if not int(os.getenv("full_lifecycle_flow", "0")):
        return
    # 3. Delete
    delete_query = Graphql.generate_graphql_operation(
        "deleteToolCall", "Mutation", schema
    )
    delete_variables = {"threadUuid": thread_uuid, "toolCallUuid": tool_call_uuid}
    result, error = call_method(
        ai_agent_core_engine,
        "ai_agent_core_graphql",
        {"query": delete_query, "variables": delete_variables},
        "delete_tool_call",
    )
    assert error is None, f"Delete Tool Call failed: {error}"
    assert (
        result.get("data", {}).get("deleteToolCall", {}).get("ok")
    ), "Delete Tool Call failed - ok flag missing/false"


@pytest.mark.integration
@pytest.mark.graphql
@pytest.mark.parametrize("test_data", FINE_TUNING_MESSAGE_TEST_DATA)
@log_test_result
def test_fine_tuning_message_lifecycle_flow(
    ai_agent_core_engine: Any, schema: Any, test_data: Any
) -> None:
    """Test Fine Tuning Message lifecycle: Insert -> Get -> Delete."""
    # 1. Insert
    insert_query = Graphql.generate_graphql_operation(
        "insertUpdateFineTuningMessage", "Mutation", schema
    )
    result, error = call_method(
        ai_agent_core_engine,
        "ai_agent_core_graphql",
        {"query": insert_query, "variables": test_data},
        "insert_fine_tuning_message",
    )
    assert error is None, f"Insert Fine Tuning Message failed: {error}"
    ft_msg_data = (
        result.get("data", {})
        .get("insertUpdateFineTuningMessage", {})
        .get("fineTuningMessage", {})
    )
    assert ft_msg_data, "Fine Tuning Message data missing in response"

    message_uuid = ft_msg_data.get("messageUuid")
    agent_uuid = test_data.get("agentUuid")

    # 2. Get (Verify)
    get_query = Graphql.generate_graphql_operation("fineTuningMessage", "Query", schema)
    get_variables = {"agentUuid": agent_uuid, "messageUuid": message_uuid}
    result, error = call_method(
        ai_agent_core_engine,
        "ai_agent_core_graphql",
        {"query": get_query, "variables": get_variables},
        "get_fine_tuning_message",
    )
    assert error is None, f"Get Fine Tuning Message failed: {error}"
    assert result.get("data", {}).get(
        "fineTuningMessage"
    ), "Fine Tuning Message not found after insertion"

    if not int(os.getenv("full_lifecycle_flow", "0")):
        return
    # 3. Delete
    delete_query = Graphql.generate_graphql_operation(
        "deleteFineTuningMessage", "Mutation", schema
    )
    delete_variables = {"agentUuid": agent_uuid, "messageUuid": message_uuid}
    result, error = call_method(
        ai_agent_core_engine,
        "ai_agent_core_graphql",
        {"query": delete_query, "variables": delete_variables},
        "delete_fine_tuning_message",
    )
    assert error is None, f"Delete Fine Tuning Message failed: {error}"
    assert (
        result.get("data", {}).get("deleteFineTuningMessage", {}).get("ok")
    ), "Delete Fine Tuning Message failed - ok flag missing/false"


@pytest.mark.integration
@pytest.mark.graphql
@pytest.mark.parametrize("test_data", ASYNC_TASK_TEST_DATA)
@log_test_result
def test_async_task_lifecycle_flow(
    ai_agent_core_engine: Any, schema: Any, test_data: Any
) -> None:
    """Test Async Task lifecycle: Insert -> Get -> Delete."""
    # 1. Insert
    insert_query = Graphql.generate_graphql_operation(
        "insertUpdateAsyncTask", "Mutation", schema
    )
    result, error = call_method(
        ai_agent_core_engine,
        "ai_agent_core_graphql",
        {"query": insert_query, "variables": test_data},
        "insert_async_task",
    )
    assert error is None, f"Insert Async Task failed: {error}"
    async_task_data = (
        result.get("data", {}).get("insertUpdateAsyncTask", {}).get("asyncTask", {})
    )
    assert async_task_data, "Async Task data missing in response"

    async_task_uuid = async_task_data.get("asyncTaskUuid") or test_data.get(
        "asyncTaskUuid"
    )
    function_name = test_data.get("functionName")

    # 2. Get (Verify)
    get_query = Graphql.generate_graphql_operation("asyncTask", "Query", schema)
    get_variables = {"functionName": function_name, "asyncTaskUuid": async_task_uuid}
    result, error = call_method(
        ai_agent_core_engine,
        "ai_agent_core_graphql",
        {"query": get_query, "variables": get_variables},
        "get_async_task",
    )
    assert error is None, f"Get Async Task failed: {error}"
    assert result.get("data", {}).get(
        "asyncTask"
    ), "Async Task not found after insertion"

    if not int(os.getenv("full_lifecycle_flow", "0")):
        return
    # 3. Delete
    delete_query = Graphql.generate_graphql_operation(
        "deleteAsyncTask", "Mutation", schema
    )
    delete_variables = {"functionName": function_name, "asyncTaskUuid": async_task_uuid}
    result, error = call_method(
        ai_agent_core_engine,
        "ai_agent_core_graphql",
        {"query": delete_query, "variables": delete_variables},
        "delete_async_task",
    )
    assert error is None, f"Delete Async Task failed: {error}"
    assert (
        result.get("data", {}).get("deleteAsyncTask", {}).get("ok")
    ), "Delete Async Task failed - ok flag missing/false"


@pytest.mark.integration
@pytest.mark.graphql
@pytest.mark.parametrize("test_data", ELEMENT_TEST_DATA)
@log_test_result
def test_element_lifecycle_flow(
    ai_agent_core_engine: Any, schema: Any, test_data: Any
) -> None:
    """Test Element lifecycle: Insert -> Get -> Delete."""
    # 1. Insert
    insert_query = Graphql.generate_graphql_operation(
        "insertUpdateElement", "Mutation", schema
    )
    result, error = call_method(
        ai_agent_core_engine,
        "ai_agent_core_graphql",
        {"query": insert_query, "variables": test_data},
        "insert_element",
    )
    assert error is None, f"Insert Element failed: {error}"
    element_data = (
        result.get("data", {}).get("insertUpdateElement", {}).get("element", {})
    )
    assert element_data, "Element data missing in response"

    element_uuid = element_data.get("elementUuid") or test_data.get("elementUuid")

    # 2. Get (Verify)
    get_query = Graphql.generate_graphql_operation("element", "Query", schema)
    get_variables = {"elementUuid": element_uuid}
    result, error = call_method(
        ai_agent_core_engine,
        "ai_agent_core_graphql",
        {"query": get_query, "variables": get_variables},
        "get_element",
    )
    assert error is None, f"Get Element failed: {error}"
    assert result.get("data", {}).get("element"), "Element not found after insertion"

    if not int(os.getenv("full_lifecycle_flow", "0")):
        return
    # 3. Delete
    delete_query = Graphql.generate_graphql_operation(
        "deleteElement", "Mutation", schema
    )
    delete_variables = {"elementUuid": element_uuid}
    result, error = call_method(
        ai_agent_core_engine,
        "ai_agent_core_graphql",
        {"query": delete_query, "variables": delete_variables},
        "delete_element",
    )
    assert error is None, f"Delete Element failed: {error}"
    assert (
        result.get("data", {}).get("deleteElement", {}).get("ok")
    ), "Delete Element failed - ok flag missing/false"


@pytest.mark.integration
@pytest.mark.graphql
@pytest.mark.wizard
@pytest.mark.parametrize("test_data", WIZARD_TEST_DATA)
@log_test_result
def test_wizard_lifecycle_flow(
    ai_agent_core_engine: Any, schema: Any, test_data: Any
) -> None:
    """Test Wizard lifecycle: Insert -> Get -> Delete."""
    # 1. Insert
    insert_query = Graphql.generate_graphql_operation(
        "insertUpdateWizard", "Mutation", schema
    )
    result, error = call_method(
        ai_agent_core_engine,
        "ai_agent_core_graphql",
        {"query": insert_query, "variables": test_data},
        "insert_wizard",
    )
    assert error is None, f"Insert Wizard failed: {error}"
    wizard_data = result.get("data", {}).get("insertUpdateWizard", {}).get("wizard", {})
    assert wizard_data, "Wizard data missing in response"

    wizard_uuid = wizard_data.get("wizardUuid") or test_data.get("wizardUuid")

    # 2. Get (Verify)
    get_query = Graphql.generate_graphql_operation("wizard", "Query", schema)
    get_variables = {"wizardUuid": wizard_uuid}
    result, error = call_method(
        ai_agent_core_engine,
        "ai_agent_core_graphql",
        {"query": get_query, "variables": get_variables},
        "get_wizard",
    )
    assert error is None, f"Get Wizard failed: {error}"
    assert result.get("data", {}).get("wizard"), "Wizard not found after insertion"

    if not int(os.getenv("full_lifecycle_flow", "0")):
        return
    # 3. Delete
    delete_query = Graphql.generate_graphql_operation(
        "deleteWizard", "Mutation", schema
    )
    delete_variables = {"wizardUuid": wizard_uuid}
    result, error = call_method(
        ai_agent_core_engine,
        "ai_agent_core_graphql",
        {"query": delete_query, "variables": delete_variables},
        "delete_wizard",
    )
    assert error is None, f"Delete Wizard failed: {error}"
    assert (
        result.get("data", {}).get("deleteWizard", {}).get("ok")
    ), "Delete Wizard failed - ok flag missing/false"


@pytest.mark.integration
@pytest.mark.graphql
@pytest.mark.wizard
@pytest.mark.parametrize("test_data", WIZARD_SCHEMA_TEST_DATA)
@log_test_result
def test_wizard_schema_lifecycle_flow(
    ai_agent_core_engine: Any, schema: Any, test_data: Any
) -> None:
    """Test Wizard Schema lifecycle: Insert -> Get -> Delete."""
    # 1. Insert
    insert_query = Graphql.generate_graphql_operation(
        "insertUpdateWizardSchema", "Mutation", schema
    )
    result, error = call_method(
        ai_agent_core_engine,
        "ai_agent_core_graphql",
        {"query": insert_query, "variables": test_data},
        "insert_wizard_schema",
    )
    assert error is None, f"Insert Wizard Schema failed: {error}"
    schema_data = (
        result.get("data", {})
        .get("insertUpdateWizardSchema", {})
        .get("wizardSchema", {})
    )
    assert schema_data, "Wizard Schema data missing in response"

    schema_type = schema_data.get("wizardSchemaType") or test_data.get(
        "wizardSchemaType"
    )
    schema_name = schema_data.get("wizardSchemaName") or test_data.get(
        "wizardSchemaName"
    )

    # 2. Get (Verify)
    get_query = Graphql.generate_graphql_operation("wizardSchema", "Query", schema)
    get_variables = {"wizardSchemaType": schema_type, "wizardSchemaName": schema_name}
    result, error = call_method(
        ai_agent_core_engine,
        "ai_agent_core_graphql",
        {"query": get_query, "variables": get_variables},
        "get_wizard_schema",
    )
    assert error is None, f"Get Wizard Schema failed: {error}"
    assert result.get("data", {}).get(
        "wizardSchema"
    ), "Wizard Schema not found after insertion"

    if not int(os.getenv("full_lifecycle_flow", "0")):
        return
    # 3. Delete
    delete_query = Graphql.generate_graphql_operation(
        "deleteWizardSchema", "Mutation", schema
    )
    delete_variables = {
        "wizardSchemaType": schema_type,
        "wizardSchemaName": schema_name,
    }
    result, error = call_method(
        ai_agent_core_engine,
        "ai_agent_core_graphql",
        {"query": delete_query, "variables": delete_variables},
        "delete_wizard_schema",
    )
    assert error is None, f"Delete Wizard Schema failed: {error}"
    assert (
        result.get("data", {}).get("deleteWizardSchema", {}).get("ok")
    ), "Delete Wizard Schema failed - ok flag missing/false"


@pytest.mark.integration
@pytest.mark.graphql
@pytest.mark.wizard
@pytest.mark.parametrize("test_data", WIZARD_GROUP_TEST_DATA)
@log_test_result
def test_wizard_group_lifecycle_flow(
    ai_agent_core_engine: Any, schema: Any, test_data: Any
) -> None:
    """Test Wizard Group lifecycle: Insert -> Get -> Delete."""
    # 1. Insert
    insert_query = Graphql.generate_graphql_operation(
        "insertUpdateWizardGroup", "Mutation", schema
    )
    result, error = call_method(
        ai_agent_core_engine,
        "ai_agent_core_graphql",
        {"query": insert_query, "variables": test_data},
        "insert_wizard_group",
    )
    assert error is None, f"Insert Wizard Group failed: {error}"
    group_data = (
        result.get("data", {}).get("insertUpdateWizardGroup", {}).get("wizardGroup", {})
    )
    assert group_data, "Wizard Group data missing in response"

    group_uuid = group_data.get("wizardGroupUuid") or test_data.get("wizardGroupUuid")

    # 2. Get (Verify)
    get_query = Graphql.generate_graphql_operation("wizardGroup", "Query", schema)
    get_variables = {"wizardGroupUuid": group_uuid}
    result, error = call_method(
        ai_agent_core_engine,
        "ai_agent_core_graphql",
        {"query": get_query, "variables": get_variables},
        "get_wizard_group",
    )
    assert error is None, f"Get Wizard Group failed: {error}"
    assert result.get("data", {}).get(
        "wizardGroup"
    ), "Wizard Group not found after insertion"

    if not int(os.getenv("full_lifecycle_flow", "0")):
        return
    # 3. Delete
    delete_query = Graphql.generate_graphql_operation(
        "deleteWizardGroup", "Mutation", schema
    )
    delete_variables = {"wizardGroupUuid": group_uuid}
    result, error = call_method(
        ai_agent_core_engine,
        "ai_agent_core_graphql",
        {"query": delete_query, "variables": delete_variables},
        "delete_wizard_group",
    )
    assert error is None, f"Delete Wizard Group failed: {error}"
    assert (
        result.get("data", {}).get("deleteWizardGroup", {}).get("ok")
    ), "Delete Wizard Group failed - ok flag missing/false"


@pytest.mark.integration
@pytest.mark.graphql
@pytest.mark.wizard
@pytest.mark.parametrize("test_data", WIZARD_GROUP_FILTER_TEST_DATA)
@log_test_result
def test_wizard_group_filter_lifecycle_flow(
    ai_agent_core_engine: Any, schema: Any, test_data: Any
) -> None:
    """Test Wizard Group Filter lifecycle: Insert -> Get -> Delete."""
    # 1. Insert
    insert_query = Graphql.generate_graphql_operation(
        "insertUpdateWizardGroupFilter", "Mutation", schema
    )
    result, error = call_method(
        ai_agent_core_engine,
        "ai_agent_core_graphql",
        {"query": insert_query, "variables": test_data},
        "insert_wizard_group_filter",
    )
    assert error is None, f"Insert Wizard Group Filter failed: {error}"
    filter_data = (
        result.get("data", {})
        .get("insertUpdateWizardGroupFilter", {})
        .get("wizardGroupFilter", {})
    )
    assert filter_data, "Wizard Group Filter data missing in response"

    filter_uuid = filter_data.get("wizardGroupFilterUuid") or test_data.get(
        "wizardGroupFilterUuid"
    )

    # 2. Get (Verify)
    get_query = Graphql.generate_graphql_operation("wizardGroupFilter", "Query", schema)
    get_variables = {"wizardGroupFilterUuid": filter_uuid}
    result, error = call_method(
        ai_agent_core_engine,
        "ai_agent_core_graphql",
        {"query": get_query, "variables": get_variables},
        "get_wizard_group_filter",
    )
    assert error is None, f"Get Wizard Group Filter failed: {error}"
    assert result.get("data", {}).get(
        "wizardGroupFilter"
    ), "Wizard Group Filter not found after insertion"

    if not int(os.getenv("full_lifecycle_flow", "0")):
        return
    # 3. Delete
    delete_query = Graphql.generate_graphql_operation(
        "deleteWizardGroupFilter", "Mutation", schema
    )
    delete_variables = {"wizardGroupFilterUuid": filter_uuid}
    result, error = call_method(
        ai_agent_core_engine,
        "ai_agent_core_graphql",
        {"query": delete_query, "variables": delete_variables},
        "delete_wizard_group_filter",
    )
    assert error is None, f"Delete Wizard Group Filter failed: {error}"
    assert (
        result.get("data", {}).get("deleteWizardGroupFilter", {}).get("ok")
    ), "Delete Wizard Group Filter failed - ok flag missing/false"


@pytest.mark.integration
@pytest.mark.graphql
@pytest.mark.ui_component
@pytest.mark.parametrize("test_data", UI_COMPONENT_TEST_DATA)
@log_test_result
def test_ui_component_lifecycle_flow(
    ai_agent_core_engine: Any, schema: Any, test_data: Any
) -> None:
    """Test UI Component lifecycle: Insert -> Get -> Delete."""
    # 1. Insert
    insert_query = Graphql.generate_graphql_operation(
        "insertUpdateUiComponent", "Mutation", schema
    )
    result, error = call_method(
        ai_agent_core_engine,
        "ai_agent_core_graphql",
        {"query": insert_query, "variables": test_data},
        "insert_ui_component",
    )
    assert error is None, f"Insert UI Component failed: {error}"
    ui_comp_data = (
        result.get("data", {}).get("insertUpdateUiComponent", {}).get("uiComponent", {})
    )
    assert ui_comp_data, "UI Component data missing in response"

    ui_comp_uuid = ui_comp_data.get("uiComponentUuid") or test_data.get(
        "uiComponentUuid"
    )
    ui_comp_type = ui_comp_data.get("uiComponentType") or test_data.get(
        "uiComponentType"
    )

    # 2. Get (Verify)
    get_query = Graphql.generate_graphql_operation("uiComponent", "Query", schema)
    get_variables = {"uiComponentType": ui_comp_type, "uiComponentUuid": ui_comp_uuid}
    result, error = call_method(
        ai_agent_core_engine,
        "ai_agent_core_graphql",
        {"query": get_query, "variables": get_variables},
        "get_ui_component",
    )
    assert error is None, f"Get UI Component failed: {error}"
    assert result.get("data", {}).get(
        "uiComponent"
    ), "UI Component not found after insertion"

    if not int(os.getenv("full_lifecycle_flow", "0")):
        return
    # 3. Delete
    delete_query = Graphql.generate_graphql_operation(
        "deleteUiComponent", "Mutation", schema
    )
    delete_variables = {
        "uiComponentType": ui_comp_type,
        "uiComponentUuid": ui_comp_uuid,
    }
    result, error = call_method(
        ai_agent_core_engine,
        "ai_agent_core_graphql",
        {"query": delete_query, "variables": delete_variables},
        "delete_ui_component",
    )
    assert error is None, f"Delete UI Component failed: {error}"
    assert (
        result.get("data", {}).get("deleteUiComponent", {}).get("ok")
    ), "Delete UI Component failed - ok flag missing/false"


@pytest.mark.integration
@pytest.mark.graphql
@pytest.mark.mcp_server
@pytest.mark.parametrize("test_data", MCP_SERVER_TEST_DATA)
@log_test_result
def test_mcp_server_lifecycle_flow(
    ai_agent_core_engine: Any, schema: Any, test_data: Any
) -> None:
    """Test MCP Server lifecycle: Insert -> Get -> Delete."""
    # 1. Insert
    insert_query = Graphql.generate_graphql_operation(
        "insertUpdateMcpServer", "Mutation", schema
    )
    result, error = call_method(
        ai_agent_core_engine,
        "ai_agent_core_graphql",
        {"query": insert_query, "variables": test_data},
        "insert_mcp_server",
    )
    assert error is None, f"Insert MCP Server failed: {error}"
    mcp_data = (
        result.get("data", {}).get("insertUpdateMcpServer", {}).get("mcpServer", {})
    )
    assert mcp_data, "MCP Server data missing in response"

    mcp_uuid = mcp_data.get("mcpServerUuid") or test_data.get("mcpServerUuid")

    # 2. Get (Verify)
    get_query = Graphql.generate_graphql_operation("mcpServer", "Query", schema)
    get_variables = {"mcpServerUuid": mcp_uuid}
    result, error = call_method(
        ai_agent_core_engine,
        "ai_agent_core_graphql",
        {"query": get_query, "variables": get_variables},
        "get_mcp_server",
    )
    assert error is None, f"Get MCP Server failed: {error}"
    assert result.get("data", {}).get(
        "mcpServer"
    ), "MCP Server not found after insertion"

    if not int(os.getenv("full_lifecycle_flow", "0")):
        return
    # 3. Delete
    delete_query = Graphql.generate_graphql_operation(
        "deleteMcpServer", "Mutation", schema
    )
    delete_variables = {"mcpServerUuid": mcp_uuid}
    result, error = call_method(
        ai_agent_core_engine,
        "ai_agent_core_graphql",
        {"query": delete_query, "variables": delete_variables},
        "delete_mcp_server",
    )
    assert error is None, f"Delete MCP Server failed: {error}"
    assert (
        result.get("data", {}).get("deleteMcpServer", {}).get("ok")
    ), "Delete MCP Server failed - ok flag missing/false"


@pytest.mark.integration
@pytest.mark.graphql
@pytest.mark.prompt_template
@pytest.mark.parametrize("test_data", PROMPT_TEMPLATE_TEST_DATA)
@log_test_result
def test_prompt_template_lifecycle_flow(
    ai_agent_core_engine: Any, schema: Any, test_data: Any
) -> None:
    """Test Prompt Template lifecycle: Insert -> Get -> Delete."""
    # 1. Insert
    insert_query = Graphql.generate_graphql_operation(
        "insertUpdatePromptTemplate", "Mutation", schema
    )
    result, error = call_method(
        ai_agent_core_engine,
        "ai_agent_core_graphql",
        {"query": insert_query, "variables": test_data},
        "insert_prompt_template",
    )
    assert error is None, f"Insert Prompt Template failed: {error}"
    prompt_data = (
        result.get("data", {})
        .get("insertUpdatePromptTemplate", {})
        .get("promptTemplate", {})
    )
    assert prompt_data, "Prompt Template data missing in response"

    prompt_uuid = prompt_data.get("promptUuid") or test_data.get("promptUuid")
    prompt_version_uuid = prompt_data.get("promptVersionUuid") or test_data.get(
        "promptVersionUuid"
    )

    # 2. Get (Verify)
    get_query = Graphql.generate_graphql_operation("promptTemplate", "Query", schema)
    get_variables = {
        "promptUuid": prompt_uuid,
        "promptVersionUuid": prompt_version_uuid,
    }
    result, error = call_method(
        ai_agent_core_engine,
        "ai_agent_core_graphql",
        {"query": get_query, "variables": get_variables},
        "get_prompt_template",
    )
    assert error is None, f"Get Prompt Template failed: {error}"
    assert result.get("data", {}).get(
        "promptTemplate"
    ), "Prompt Template not found after insertion"

    if not int(os.getenv("full_lifecycle_flow", "0")):
        return
    # 3. Delete
    delete_query = Graphql.generate_graphql_operation(
        "deletePromptTemplate", "Mutation", schema
    )
    delete_variables = {"promptVersionUuid": prompt_version_uuid}
    result, error = call_method(
        ai_agent_core_engine,
        "ai_agent_core_graphql",
        {"query": delete_query, "variables": delete_variables},
        "delete_prompt_template",
    )
    assert error is None, f"Delete Prompt Template failed: {error}"
    assert (
        result.get("data", {}).get("deletePromptTemplate", {}).get("ok")
    ), "Delete Prompt Template failed - ok flag missing/false"


@pytest.mark.integration
@pytest.mark.graphql
@pytest.mark.flow_snippet
@pytest.mark.parametrize("test_data", FLOW_SNIPPET_TEST_DATA)
@log_test_result
def test_flow_snippet_lifecycle_flow(
    ai_agent_core_engine: Any, schema: Any, test_data: Any
) -> None:
    """Test Flow Snippet lifecycle: Insert -> Get -> Delete."""
    # 1. Insert
    insert_query = Graphql.generate_graphql_operation(
        "insertUpdateFlowSnippet", "Mutation", schema
    )
    result, error = call_method(
        ai_agent_core_engine,
        "ai_agent_core_graphql",
        {"query": insert_query, "variables": test_data},
        "insert_flow_snippet",
    )
    assert error is None, f"Insert Flow Snippet failed: {error}"
    flow_data = (
        result.get("data", {}).get("insertUpdateFlowSnippet", {}).get("flowSnippet", {})
    )
    assert flow_data, "Flow Snippet data missing in response"

    flow_uuid = flow_data.get("flowSnippetUuid") or test_data.get("flowSnippetUuid")
    flow_version_uuid = flow_data.get("flowSnippetVersionUuid") or test_data.get(
        "flowSnippetVersionUuid"
    )
    prompt_uuid = test_data.get("promptUuid")

    # 2. Get (Verify)
    get_query = Graphql.generate_graphql_operation("flowSnippet", "Query", schema)
    get_variables = {
        "flowSnippetUuid": flow_uuid,
        "flowSnippetVersionUuid": flow_version_uuid,
    }
    result, error = call_method(
        ai_agent_core_engine,
        "ai_agent_core_graphql",
        {"query": get_query, "variables": get_variables},
        "get_flow_snippet",
    )
    assert error is None, f"Get Flow Snippet failed: {error}"
    assert result.get("data", {}).get(
        "flowSnippet"
    ), "Flow Snippet not found after insertion"

    # 3. Get List (Verify)
    list_query = Graphql.generate_graphql_operation("flowSnippetList", "Query", schema)
    list_variables = {"promptUuid": prompt_uuid}
    result, error = call_method(
        ai_agent_core_engine,
        "ai_agent_core_graphql",
        {"query": list_query, "variables": list_variables},
        "list_flow_snippets",
    )
    assert error is None, f"List Flow Snippets failed: {error}"
    flow_list = result.get("data", {}).get("flowSnippetList", {}).get("flowSnippetList")
    assert flow_list and len(flow_list) > 0, "Flow Snippet list empty or missing"

    if not int(os.getenv("full_lifecycle_flow", "0")):
        return
    # 3. Delete
    delete_query = Graphql.generate_graphql_operation(
        "deleteFlowSnippet", "Mutation", schema
    )
    delete_variables = {"flowSnippetVersionUuid": flow_version_uuid}
    result, error = call_method(
        ai_agent_core_engine,
        "ai_agent_core_graphql",
        {"query": delete_query, "variables": delete_variables},
        "delete_flow_snippet",
    )
    assert error is None, f"Delete Flow Snippet failed: {error}"
    assert (
        result.get("data", {}).get("deleteFlowSnippet", {}).get("ok")
    ), "Delete Flow Snippet failed - ok flag missing/false"


if __name__ == "__main__":
    import sys

    sys.exit(pytest.main([__file__, "-v"] + sys.argv[1:]))
