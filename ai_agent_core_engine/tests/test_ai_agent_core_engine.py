#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
AI Agent Core Engine – GraphQL Integration Tests

Test structure
--------------
  Atomic tests (one operation per pytest item, across all 17 entity types)
    test_graphql_insert   – insert / upsert mutation
    test_graphql_get      – single-item query
    test_graphql_list     – list query
    test_graphql_update   – update mutation
    test_graphql_delete   – delete mutation

  Full-cycle test (all operations in order per entity type)
    test_graphql_full_cycle  – insert → update → get → list → delete

All suites are driven by test_data.json.  Set ``full_lifecycle_flow=1`` to
enable the delete step inside the full-cycle test.
"""

from __future__ import print_function

__author__ = "bibow"

import json
import logging
import os
import sys

import pytest
from dotenv import load_dotenv
from test_helpers import call_method, log_test_result

load_dotenv()
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)8s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger()

from silvaengine_utility import Graphql

# ---------------------------------------------------------------------------
# Test data
# ---------------------------------------------------------------------------

with open(os.path.join(os.path.dirname(__file__), "test_data.json")) as _f:
    _TEST_DATA = json.load(_f)

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


# ---------------------------------------------------------------------------
# GraphQL helpers
# ---------------------------------------------------------------------------


def _gql(ai_agent_core_engine, schema, op_name, op_type, variables, label):
    """Execute one GraphQL operation and return (result, error)."""
    query = Graphql.generate_graphql_operation(op_name, op_type, schema)
    return call_method(
        ai_agent_core_engine,
        "ai_agent_core_graphql",
        {"query": query, "variables": variables},
        label,
    )


def _step(op_name, op_type, label):
    """Return a pre-configured (engine, schema, variables) → (result, error) callable."""

    def _call(engine, schema, variables):
        return _gql(engine, schema, op_name, op_type, variables, label)

    return _call


def _ok(result, error, path, prefix):
    """Assert success and return the nested response value."""
    assert error is None, f"{prefix} failed: {error}"
    value = result
    for key in path:
        value = (value or {}).get(key)
    assert value, f"{prefix} – response missing at {path}"
    return value


def _deep_copy(data):
    return json.loads(json.dumps(data))


def _resolve(entity, payload, key):
    """Return server-generated value if present, else fall back to payload value."""
    return (entity or {}).get(key) or (payload or {}).get(key)


# ---------------------------------------------------------------------------
# Suite factory
# ---------------------------------------------------------------------------


def _make_suite(
    name,
    marker,
    records,
    *,
    insert,
    get,
    delete,
    context_builder,
    get_vars,
    delete_vars,
    list=None,
    list_vars=None,
    update=None,
    update_vars=None,
):
    """
    Build a suite descriptor from compact (op_name, response_path) specs.

    Each *op* argument is a 2-tuple: (GraphQL operation name, response-path tuple).
    Insert / update / delete are Mutations; get / list are Queries.
    """
    ins_op, ins_path = insert
    get_op, get_path = get
    del_op, del_path = delete

    suite = {
        "name": name,
        "marker": marker,
        "records": records,
        "insert_step": _step(ins_op, "Mutation", f"insert_{name}"),
        "insert_path": ins_path,
        "context_builder": context_builder,
        "get_step": _step(get_op, "Query", f"get_{name}"),
        "get_path": get_path,
        "get_vars": get_vars,
        "delete_step": _step(del_op, "Mutation", f"delete_{name}"),
        "delete_ok_path": del_path,
        "delete_vars": delete_vars,
    }
    if list is not None:
        lst_op, lst_path = list
        suite.update(
            {
                "list_step": _step(lst_op, "Query", f"list_{name}"),
                "list_path": lst_path,
                "list_vars": list_vars,
            }
        )
    if update is not None:
        upd_op, upd_path = update
        suite.update(
            {
                "update_step": _step(upd_op, "Mutation", f"update_{name}"),
                "update_path": upd_path,
                "update_vars": update_vars,
            }
        )
    return suite


# ---------------------------------------------------------------------------
# Suite configuration – 17 entity types
# ---------------------------------------------------------------------------


def _build_suites():
    return [
        _make_suite(
            "llm",
            pytest.mark.llm,
            LLM_TEST_DATA,
            insert=("insertUpdateLlm", ("data", "insertUpdateLlm", "llm")),
            get=("llm", ("data", "llm")),
            list=("llmList", ("data", "llmList", "llmList")),
            update=("insertUpdateLlm", ("data", "insertUpdateLlm", "llm")),
            delete=("deleteLlm", ("data", "deleteLlm", "ok")),
            context_builder=lambda p, e: {
                "llmProvider": p["llmProvider"],
                "llmName": p["llmName"],
                "llmId": _resolve(e, p, "llmId"),
            },
            get_vars=lambda s: {
                "llmProvider": s["ctx"]["llmProvider"],
                "llmName": s["ctx"]["llmName"],
            },
            list_vars=lambda s: {"llmProvider": s["ctx"]["llmProvider"]},
            update_vars=lambda s: {
                **s["payload"],
                "updatedBy": s["payload"].get("updatedBy", "test-user") + "-upd",
            },
            delete_vars=lambda s: {
                "llmProvider": s["ctx"]["llmProvider"],
                "llmName": s["ctx"]["llmName"],
                "updatedBy": s["payload"].get("updatedBy", "test-user"),
            },
        ),
        _make_suite(
            "agent",
            pytest.mark.agent,
            AGENT_TEST_DATA,
            insert=("insertUpdateAgent", ("data", "insertUpdateAgent", "agent")),
            get=("agent", ("data", "agent")),
            list=("agentList", ("data", "agentList", "agentList")),
            delete=("deleteAgent", ("data", "deleteAgent", "ok")),
            context_builder=lambda p, e: {
                "agentUuid": _resolve(e, p, "agentUuid"),
                "agentVersionUuid": _resolve(e, p, "agentVersionUuid"),
                "agentName": p["agentName"],
            },
            get_vars=lambda s: {"agentUuid": s["ctx"]["agentUuid"]},
            list_vars=lambda s: {"agentName": s["ctx"]["agentName"]},
            delete_vars=lambda s: {
                "agentVersionUuid": s["ctx"]["agentVersionUuid"],
                "updatedBy": s["payload"].get("updatedBy", "test-user"),
            },
        ),
        _make_suite(
            "thread",
            pytest.mark.thread,
            THREAD_TEST_DATA,
            insert=("insertThread", ("data", "insertThread", "thread")),
            get=("thread", ("data", "thread")),
            list=("threadList", ("data", "threadList", "threadList")),
            delete=("deleteThread", ("data", "deleteThread", "ok")),
            context_builder=lambda p, e: {
                "threadUuid": _resolve(e, p, "threadUuid"),
                "agentUuid": p.get("agentUuid"),
            },
            get_vars=lambda s: {"threadUuid": s["ctx"]["threadUuid"]},
            list_vars=lambda s: {"agentUuid": s["ctx"]["agentUuid"]},
            delete_vars=lambda s: {
                "threadUuid": s["ctx"]["threadUuid"],
                "updatedBy": s["payload"].get("updatedBy", "test-user"),
            },
        ),
        _make_suite(
            "run",
            pytest.mark.run,
            RUN_TEST_DATA,
            insert=("insertUpdateRun", ("data", "insertUpdateRun", "run")),
            get=("run", ("data", "run")),
            list=("runList", ("data", "runList", "runList")),
            delete=("deleteRun", ("data", "deleteRun", "ok")),
            context_builder=lambda p, e: {
                "runUuid": _resolve(e, p, "runUuid"),
                "threadUuid": p.get("threadUuid"),
            },
            get_vars=lambda s: {
                "threadUuid": s["ctx"]["threadUuid"],
                "runUuid": s["ctx"]["runUuid"],
            },
            list_vars=lambda s: {"threadUuid": s["ctx"]["threadUuid"]},
            delete_vars=lambda s: {
                "threadUuid": s["ctx"]["threadUuid"],
                "runUuid": s["ctx"]["runUuid"],
                "updatedBy": s["payload"].get("updatedBy", "test-user"),
            },
        ),
        _make_suite(
            "message",
            pytest.mark.message,
            MESSAGE_TEST_DATA,
            insert=("insertUpdateMessage", ("data", "insertUpdateMessage", "message")),
            get=("message", ("data", "message")),
            delete=("deleteMessage", ("data", "deleteMessage", "ok")),
            context_builder=lambda p, e: {
                "threadUuid": p.get("threadUuid"),
                "messageUuid": _resolve(e, p, "messageUuid"),
            },
            get_vars=lambda s: {
                "threadUuid": s["ctx"]["threadUuid"],
                "messageUuid": s["ctx"]["messageUuid"],
            },
            delete_vars=lambda s: {
                "threadUuid": s["ctx"]["threadUuid"],
                "messageUuid": s["ctx"]["messageUuid"],
            },
        ),
        _make_suite(
            "tool_call",
            pytest.mark.tool_call,
            TOOL_CALL_TEST_DATA,
            insert=(
                "insertUpdateToolCall",
                ("data", "insertUpdateToolCall", "toolCall"),
            ),
            get=("toolCall", ("data", "toolCall")),
            delete=("deleteToolCall", ("data", "deleteToolCall", "ok")),
            context_builder=lambda p, e: {
                "threadUuid": p.get("threadUuid"),
                "toolCallUuid": _resolve(e, p, "toolCallUuid"),
            },
            get_vars=lambda s: {
                "threadUuid": s["ctx"]["threadUuid"],
                "toolCallUuid": s["ctx"]["toolCallUuid"],
            },
            delete_vars=lambda s: {
                "threadUuid": s["ctx"]["threadUuid"],
                "toolCallUuid": s["ctx"]["toolCallUuid"],
            },
        ),
        _make_suite(
            "fine_tuning_message",
            pytest.mark.fine_tuning_message,
            FINE_TUNING_MESSAGE_TEST_DATA,
            insert=(
                "insertUpdateFineTuningMessage",
                ("data", "insertUpdateFineTuningMessage", "fineTuningMessage"),
            ),
            get=("fineTuningMessage", ("data", "fineTuningMessage")),
            delete=(
                "deleteFineTuningMessage",
                ("data", "deleteFineTuningMessage", "ok"),
            ),
            context_builder=lambda p, e: {
                "agentUuid": p.get("agentUuid"),
                "messageUuid": _resolve(e, p, "messageUuid"),
            },
            get_vars=lambda s: {
                "agentUuid": s["ctx"]["agentUuid"],
                "messageUuid": s["ctx"]["messageUuid"],
            },
            delete_vars=lambda s: {
                "agentUuid": s["ctx"]["agentUuid"],
                "messageUuid": s["ctx"]["messageUuid"],
            },
        ),
        _make_suite(
            "async_task",
            pytest.mark.async_task,
            ASYNC_TASK_TEST_DATA,
            insert=(
                "insertUpdateAsyncTask",
                ("data", "insertUpdateAsyncTask", "asyncTask"),
            ),
            get=("asyncTask", ("data", "asyncTask")),
            delete=("deleteAsyncTask", ("data", "deleteAsyncTask", "ok")),
            context_builder=lambda p, e: {
                "functionName": p.get("functionName"),
                "asyncTaskUuid": _resolve(e, p, "asyncTaskUuid"),
            },
            get_vars=lambda s: {
                "functionName": s["ctx"]["functionName"],
                "asyncTaskUuid": s["ctx"]["asyncTaskUuid"],
            },
            delete_vars=lambda s: {
                "functionName": s["ctx"]["functionName"],
                "asyncTaskUuid": s["ctx"]["asyncTaskUuid"],
            },
        ),
        _make_suite(
            "element",
            pytest.mark.element,
            ELEMENT_TEST_DATA,
            insert=("insertUpdateElement", ("data", "insertUpdateElement", "element")),
            get=("element", ("data", "element")),
            delete=("deleteElement", ("data", "deleteElement", "ok")),
            context_builder=lambda p, e: {"elementUuid": _resolve(e, p, "elementUuid")},
            get_vars=lambda s: {"elementUuid": s["ctx"]["elementUuid"]},
            delete_vars=lambda s: {"elementUuid": s["ctx"]["elementUuid"]},
        ),
        _make_suite(
            "wizard",
            pytest.mark.wizard,
            WIZARD_TEST_DATA,
            insert=("insertUpdateWizard", ("data", "insertUpdateWizard", "wizard")),
            get=("wizard", ("data", "wizard")),
            delete=("deleteWizard", ("data", "deleteWizard", "ok")),
            context_builder=lambda p, e: {"wizardUuid": _resolve(e, p, "wizardUuid")},
            get_vars=lambda s: {"wizardUuid": s["ctx"]["wizardUuid"]},
            delete_vars=lambda s: {"wizardUuid": s["ctx"]["wizardUuid"]},
        ),
        _make_suite(
            "wizard_schema",
            pytest.mark.wizard_schema,
            WIZARD_SCHEMA_TEST_DATA,
            insert=(
                "insertUpdateWizardSchema",
                ("data", "insertUpdateWizardSchema", "wizardSchema"),
            ),
            get=("wizardSchema", ("data", "wizardSchema")),
            delete=("deleteWizardSchema", ("data", "deleteWizardSchema", "ok")),
            context_builder=lambda p, e: {
                "wizardSchemaType": _resolve(e, p, "wizardSchemaType"),
                "wizardSchemaName": _resolve(e, p, "wizardSchemaName"),
            },
            get_vars=lambda s: {
                "wizardSchemaType": s["ctx"]["wizardSchemaType"],
                "wizardSchemaName": s["ctx"]["wizardSchemaName"],
            },
            delete_vars=lambda s: {
                "wizardSchemaType": s["ctx"]["wizardSchemaType"],
                "wizardSchemaName": s["ctx"]["wizardSchemaName"],
            },
        ),
        _make_suite(
            "wizard_group",
            pytest.mark.wizard_group,
            WIZARD_GROUP_TEST_DATA,
            insert=(
                "insertUpdateWizardGroup",
                ("data", "insertUpdateWizardGroup", "wizardGroup"),
            ),
            get=("wizardGroup", ("data", "wizardGroup")),
            delete=("deleteWizardGroup", ("data", "deleteWizardGroup", "ok")),
            context_builder=lambda p, e: {
                "wizardGroupUuid": _resolve(e, p, "wizardGroupUuid")
            },
            get_vars=lambda s: {"wizardGroupUuid": s["ctx"]["wizardGroupUuid"]},
            delete_vars=lambda s: {"wizardGroupUuid": s["ctx"]["wizardGroupUuid"]},
        ),
        _make_suite(
            "wizard_group_filter",
            pytest.mark.wizard_group_filter,
            WIZARD_GROUP_FILTER_TEST_DATA,
            insert=(
                "insertUpdateWizardGroupFilter",
                ("data", "insertUpdateWizardGroupFilter", "wizardGroupFilter"),
            ),
            get=("wizardGroupFilter", ("data", "wizardGroupFilter")),
            delete=(
                "deleteWizardGroupFilter",
                ("data", "deleteWizardGroupFilter", "ok"),
            ),
            context_builder=lambda p, e: {
                "wizardGroupFilterUuid": _resolve(e, p, "wizardGroupFilterUuid")
            },
            get_vars=lambda s: {
                "wizardGroupFilterUuid": s["ctx"]["wizardGroupFilterUuid"]
            },
            delete_vars=lambda s: {
                "wizardGroupFilterUuid": s["ctx"]["wizardGroupFilterUuid"]
            },
        ),
        _make_suite(
            "ui_component",
            pytest.mark.ui_component,
            UI_COMPONENT_TEST_DATA,
            insert=(
                "insertUpdateUiComponent",
                ("data", "insertUpdateUiComponent", "uiComponent"),
            ),
            get=("uiComponent", ("data", "uiComponent")),
            delete=("deleteUiComponent", ("data", "deleteUiComponent", "ok")),
            context_builder=lambda p, e: {
                "uiComponentUuid": _resolve(e, p, "uiComponentUuid"),
                "uiComponentType": _resolve(e, p, "uiComponentType"),
            },
            get_vars=lambda s: {
                "uiComponentType": s["ctx"]["uiComponentType"],
                "uiComponentUuid": s["ctx"]["uiComponentUuid"],
            },
            delete_vars=lambda s: {
                "uiComponentType": s["ctx"]["uiComponentType"],
                "uiComponentUuid": s["ctx"]["uiComponentUuid"],
            },
        ),
        _make_suite(
            "mcp_server",
            pytest.mark.mcp_server,
            MCP_SERVER_TEST_DATA,
            insert=(
                "insertUpdateMcpServer",
                ("data", "insertUpdateMcpServer", "mcpServer"),
            ),
            get=("mcpServer", ("data", "mcpServer")),
            delete=("deleteMcpServer", ("data", "deleteMcpServer", "ok")),
            context_builder=lambda p, e: {
                "mcpServerUuid": _resolve(e, p, "mcpServerUuid")
            },
            get_vars=lambda s: {"mcpServerUuid": s["ctx"]["mcpServerUuid"]},
            delete_vars=lambda s: {"mcpServerUuid": s["ctx"]["mcpServerUuid"]},
        ),
        _make_suite(
            "prompt_template",
            pytest.mark.prompt_template,
            PROMPT_TEMPLATE_TEST_DATA,
            insert=(
                "insertUpdatePromptTemplate",
                ("data", "insertUpdatePromptTemplate", "promptTemplate"),
            ),
            get=("promptTemplate", ("data", "promptTemplate")),
            delete=("deletePromptTemplate", ("data", "deletePromptTemplate", "ok")),
            context_builder=lambda p, e: {
                "promptUuid": _resolve(e, p, "promptUuid"),
                "promptVersionUuid": _resolve(e, p, "promptVersionUuid"),
            },
            get_vars=lambda s: {
                "promptUuid": s["ctx"]["promptUuid"],
                "promptVersionUuid": s["ctx"]["promptVersionUuid"],
            },
            delete_vars=lambda s: {"promptVersionUuid": s["ctx"]["promptVersionUuid"]},
        ),
        _make_suite(
            "flow_snippet",
            pytest.mark.flow_snippet,
            FLOW_SNIPPET_TEST_DATA,
            insert=(
                "insertUpdateFlowSnippet",
                ("data", "insertUpdateFlowSnippet", "flowSnippet"),
            ),
            get=("flowSnippet", ("data", "flowSnippet")),
            list=("flowSnippetList", ("data", "flowSnippetList", "flowSnippetList")),
            delete=("deleteFlowSnippet", ("data", "deleteFlowSnippet", "ok")),
            context_builder=lambda p, e: {
                "flowSnippetUuid": _resolve(e, p, "flowSnippetUuid"),
                "flowSnippetVersionUuid": _resolve(e, p, "flowSnippetVersionUuid"),
                "promptUuid": p.get("promptUuid"),
            },
            get_vars=lambda s: {
                "flowSnippetUuid": s["ctx"]["flowSnippetUuid"],
                "flowSnippetVersionUuid": s["ctx"]["flowSnippetVersionUuid"],
            },
            list_vars=lambda s: {"promptUuid": s["ctx"]["promptUuid"]},
            delete_vars=lambda s: {
                "flowSnippetVersionUuid": s["ctx"]["flowSnippetVersionUuid"]
            },
        ),
    ]


LIFECYCLE_SUITES = _build_suites()


# ---------------------------------------------------------------------------
# Parametrise: one pytest case per (suite, data-row, op)
# ---------------------------------------------------------------------------


def _entity_filter(filter_key):
    """
    Return the allowed entity-type names for a given operation, or None (= run all).

    Resolution order (first non-empty wins):
      1. <FILTER_KEY>_ENTITY_TYPES  e.g. INSERT_ENTITY_TYPES, FULL_CYCLE_ENTITY_TYPES
      2. TEST_ENTITY_TYPES          global fallback for all operations

    Example .env values:
      TEST_ENTITY_TYPES=llm,agent
      INSERT_ENTITY_TYPES=llm
      FULL_CYCLE_ENTITY_TYPES=thread
    """
    specific = os.getenv(f"{filter_key.upper()}_ENTITY_TYPES", "").strip()
    general = os.getenv("TEST_ENTITY_TYPES", "").strip()
    raw = specific or general
    if not raw:
        return None  # no filter → run all suites
    return {s.strip() for s in raw.split(",") if s.strip()}


def _cases(op_key, parametrize=True, filter_key=None):
    """
    Build parametrize list for the given operation key.

    op_key:     "insert" | "get" | "list" | "update" | "delete"
    filter_key: env-var prefix to look up allowed entity types (defaults to op_key).
                Pass "full_cycle" when building the full-cycle case list.
    """
    allowed = _entity_filter(filter_key or op_key)
    out = []
    for suite in LIFECYCLE_SUITES:
        if f"{op_key}_step" not in suite:
            continue
        if allowed is not None and suite["name"] not in allowed:
            continue
        for idx, row in enumerate(suite["records"]):
            case = {"suite": suite, "row": row}
            if parametrize:
                out.append(
                    pytest.param(
                        case,
                        id=f"{suite['name']}-{idx}",
                        marks=[suite["marker"]] if suite.get("marker") else [],
                    )
                )
            else:
                out.append(case)
    return out


INSERT_CASES     = _cases("insert")
GET_CASES        = _cases("get")
LIST_CASES       = _cases("list")
UPDATE_CASES     = _cases("update")
DELETE_CASES     = _cases("delete")
FULL_CYCLE_CASES = _cases("insert", parametrize=False, filter_key="full_cycle")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _seed(engine, schema, suite, row):
    """Insert an entity and return the (state, entity) pair."""
    payload = _deep_copy(row)
    result, error = suite["insert_step"](engine, schema, payload)
    entity = _ok(result, error, suite["insert_path"], f"Seed {suite['name']}")
    state = {
        "suite": suite,
        "payload": payload,
        "entity": entity,
        "ctx": suite["context_builder"](payload, entity),
    }
    return state


@pytest.fixture
def seeded_state(ai_agent_core_engine, schema, operation_case):
    """Insert the entity before the test and delete it on teardown."""
    suite = operation_case["suite"]
    state = _seed(ai_agent_core_engine, schema, suite, operation_case["row"])

    yield state

    if "delete_step" not in suite:
        return
    try:
        suite["delete_step"](ai_agent_core_engine, schema, suite["delete_vars"](state))
    except Exception:
        logger.warning("Cleanup failed for %s", suite["name"])


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.graphql
@log_test_result
def test_graphql_ping(ai_agent_core_engine, schema):
    """Verify the GraphQL endpoint is reachable."""
    result, error = _gql(ai_agent_core_engine, schema, "ping", "Query", {}, "ping")
    assert error is None, f"Ping failed: {error}"
    logger.info(result)


@pytest.mark.integration
@pytest.mark.graphql
@pytest.mark.parametrize("operation_case", INSERT_CASES)
@log_test_result
def test_graphql_insert(ai_agent_core_engine, schema, operation_case):
    """Insert / upsert mutation – one pytest item per entity type."""
    suite = operation_case["suite"]
    entity_type = suite["name"]
    payload = _deep_copy(operation_case["row"])
    result, error = suite["insert_step"](ai_agent_core_engine, schema, payload)
    _ok(result, error, suite["insert_path"], f"Insert {entity_type}")


@pytest.mark.integration
@pytest.mark.graphql
@pytest.mark.parametrize("operation_case", GET_CASES)
@log_test_result
def test_graphql_get(ai_agent_core_engine, schema, seeded_state, operation_case):
    """Single-item query – entity is seeded by fixture, cleaned up on teardown."""
    del operation_case  # consumed by seeded_state fixture
    suite = seeded_state["suite"]
    entity_type = suite["name"]
    result, error = suite["get_step"](
        ai_agent_core_engine, schema, suite["get_vars"](seeded_state)
    )
    _ok(result, error, suite["get_path"], f"Get {entity_type}")


@pytest.mark.integration
@pytest.mark.graphql
@pytest.mark.parametrize("operation_case", LIST_CASES)
@log_test_result
def test_graphql_list(ai_agent_core_engine, schema, seeded_state, operation_case):
    """List query – verifies at least one result is returned after an insert."""
    del operation_case
    suite = seeded_state["suite"]
    entity_type = suite["name"]
    result, error = suite["list_step"](
        ai_agent_core_engine, schema, suite["list_vars"](seeded_state)
    )
    items = _ok(result, error, suite["list_path"], f"List {entity_type}")
    assert len(items) > 0, f"List {entity_type} returned empty"


@pytest.mark.integration
@pytest.mark.graphql
@pytest.mark.parametrize("operation_case", UPDATE_CASES)
@log_test_result
def test_graphql_update(ai_agent_core_engine, schema, seeded_state, operation_case):
    """Update / upsert mutation – entity is seeded by fixture."""
    del operation_case
    suite = seeded_state["suite"]
    entity_type = suite["name"]
    result, error = suite["update_step"](
        ai_agent_core_engine, schema, suite["update_vars"](seeded_state)
    )
    _ok(result, error, suite["update_path"], f"Update {entity_type}")


@pytest.mark.integration
@pytest.mark.graphql
@pytest.mark.parametrize("operation_case", DELETE_CASES)
@log_test_result
def test_graphql_delete(ai_agent_core_engine, schema, seeded_state, operation_case):
    """Delete mutation – entity is seeded by fixture; teardown is a no-op."""
    del operation_case
    suite = seeded_state["suite"]
    entity_type = suite["name"]
    result, error = suite["delete_step"](
        ai_agent_core_engine, schema, suite["delete_vars"](seeded_state)
    )
    _ok(result, error, suite["delete_ok_path"], f"Delete {entity_type}")


@pytest.mark.integration
@pytest.mark.graphql
@pytest.mark.slow
@pytest.mark.parametrize(
    "suite_case",
    [
        pytest.param(
            c,
            id=c["suite"]["name"],
            marks=[c["suite"]["marker"]] if c["suite"].get("marker") else [],
        )
        for c in FULL_CYCLE_CASES
    ],
)
@log_test_result
def test_graphql_full_cycle(ai_agent_core_engine, schema, suite_case):
    """
    Full lifecycle per entity type: insert → update → get → list → delete.

    Set ``full_lifecycle_flow=1`` env var to enable the delete step.
    """
    suite = suite_case["suite"]
    entity_type = suite["name"]
    state = _seed(ai_agent_core_engine, schema, suite, suite_case["row"])

    # Update (if supported)
    if "update_step" in suite:
        result, error = suite["update_step"](
            ai_agent_core_engine, schema, suite["update_vars"](state)
        )
        _ok(result, error, suite["update_path"], f"Full-cycle update {entity_type}")

    # Get
    result, error = suite["get_step"](
        ai_agent_core_engine, schema, suite["get_vars"](state)
    )
    _ok(result, error, suite["get_path"], f"Full-cycle get {entity_type}")

    # List (if supported)
    if "list_step" in suite:
        result, error = suite["list_step"](
            ai_agent_core_engine, schema, suite["list_vars"](state)
        )
        items = _ok(result, error, suite["list_path"], f"Full-cycle list {entity_type}")
        assert len(items) > 0, f"Full-cycle list {entity_type} returned empty"

    # Delete (opt-in)
    if int(os.getenv("full_lifecycle_flow", "0")) and "delete_step" in suite:
        result, error = suite["delete_step"](
            ai_agent_core_engine, schema, suite["delete_vars"](state)
        )
        _ok(result, error, suite["delete_ok_path"], f"Full-cycle delete {entity_type}")


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"] + sys.argv[1:]))
