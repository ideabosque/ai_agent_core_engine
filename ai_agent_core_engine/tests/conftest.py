# -*- coding: utf-8 -*-
"""
Pytest configuration and fixtures for AI Agent Core Engine tests.

This module provides shared fixtures and configuration for all test modules.
"""
from __future__ import print_function

import json
import logging
import os
import re
import sys
from typing import Any, Dict, Sequence
from unittest.mock import MagicMock

import pendulum
import pytest
from dotenv import load_dotenv
from graphene import ResolveInfo

load_dotenv()


# Setup logging
logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("test_ai_agent_core_engine")

# Make package importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
sys.path.insert(
    0,
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../../../silvaengine_dynamodb_base")
    ),
)
sys.path.insert(
    0,
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../../../silvaengine_utility")
    ),
)

from ai_agent_core_engine import AIAgentCoreEngine
from silvaengine_utility import Utility

# Test data file path
TEST_DATA_FILE = os.path.join(os.path.dirname(__file__), "test_data.json")

# Test settings
SETTING = {
    "region_name": os.getenv("region_name"),
    "aws_access_key_id": os.getenv("aws_access_key_id"),
    "aws_secret_access_key": os.getenv("aws_secret_access_key"),
    "api_id": os.getenv("api_id"),
    "api_stage": os.getenv("api_stage"),
    "funct_bucket_name": os.getenv("funct_bucket_name"),
    "funct_zip_path": os.getenv("funct_zip_path"),
    "funct_extract_path": os.getenv("funct_extract_path"),
    "task_queue_name": os.getenv("task_queue_name"),
    "functs_on_local": {
        "ai_marketing_graphql": {
            "module_name": "ai_marketing_engine",
            "class_name": "AIMarketingEngine",
        },
        "ai_agent_build_graphql_query": {
            "module_name": "ai_agent_core_engine",
            "class_name": "AIAgentCoreEngine",
        },
        "ai_agent_core_graphql": {
            "module_name": "ai_agent_core_engine",
            "class_name": "AIAgentCoreEngine",
        },
        "async_execute_ask_model": {
            "module_name": "ai_agent_core_engine",
            "class_name": "AIAgentCoreEngine",
        },
        "async_insert_update_tool_call": {
            "module_name": "ai_agent_core_engine",
            "class_name": "AIAgentCoreEngine",
        },
        "send_data_to_websocket": {
            "module_name": "ai_agent_core_engine",
            "class_name": "AIAgentCoreEngine",
        },
    },
    "xml_convert": os.getenv("xml_convert", False),
    "internal_mcp": {
        "base_url": os.getenv("mcp_server_url"),
        "bearer_token": os.getenv("bearer_token"),
        "headers": {
            "x-api-key": os.getenv("x-api-key"),
            "Content-Type": "application/json",
        },
    },
    "connection_id": os.getenv("connection_id"),
    "endpoint_id": os.getenv("endpoint_id"),
    "part_id": os.getenv("part_id"),
    "execute_mode": os.getenv("execute_mode", "local_for_all"),
    "initialize_tables": int(os.getenv("initialize_tables", "0")),
}


@pytest.fixture(scope="session")
def test_data() -> Dict[str, Any]:
    """Load test data from JSON file."""
    with open(TEST_DATA_FILE, "r") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def ai_agent_core_engine():
    """Provide an AIAgentCoreEngine instance for testing.

    This fixture is module-scoped for efficiency - the engine
    is initialized once per test module.
    """
    try:
        engine = AIAgentCoreEngine(logger, **SETTING)
        # Mark as real engine instance for validation
        setattr(engine, "__is_real__", True)
        logger.info("AIAgentCoreEngine initialized successfully")
        return engine
    except Exception as ex:
        import sys
        import traceback

        error_file = (
            r"c:\Users\bibo7\gitrepo\silvaengine\ai_agent_core_engine\error.log"
        )
        with open(error_file, "w") as f:
            traceback.print_exc(file=f)
        sys.stderr.write("Exception in fixture:\n")
        traceback.print_exc(file=sys.stderr)
        logger.exception(f"AIAgentCoreEngine initialization failed: {ex}")
        pytest.skip(f"AIAgentCoreEngine not available: {ex}")


@pytest.fixture(scope="module")
def schema(ai_agent_core_engine):
    """Fetch GraphQL schema for testing.

    Depends on ai_agent_core_engine fixture.
    """
    endpoint_id = SETTING.get("endpoint_id")

    try:
        logger.info("Fetching GraphQL schema...")

        context = {
            "endpoint_id": endpoint_id,
            "setting": SETTING,
            "logger": logger,
        }
        schema = Utility.fetch_graphql_schema(
            context,
            "ai_agent_core_graphql",
        )
        logger.info("GraphQL schema fetched successfully")
        return schema
    except Exception as ex:
        logger.warning(f"Failed to fetch GraphQL schema: {ex}")
        pytest.skip(f"GraphQL schema not available: {ex}")


@pytest.fixture(scope="function")
def mock_logger():
    """Create a mock logger for testing."""
    logger = MagicMock(spec=logging.Logger)
    return logger


@pytest.fixture(scope="function")
def mock_info(mock_logger):
    """Create a mock GraphQL ResolveInfo object."""
    info = MagicMock(spec=ResolveInfo)
    info.context = {
        "logger": mock_logger,
        "endpoint_id": "test-endpoint-001",
        "user_id": "test-user-001",
    }
    return info


@pytest.fixture(scope="function")
def endpoint_id():
    """Return test endpoint ID."""
    return "test-endpoint-001"


@pytest.fixture(scope="function")
def current_timestamp():
    """Return current UTC timestamp."""
    return pendulum.now("UTC")


# Agent fixtures
@pytest.fixture(scope="function")
def sample_agent_data(test_data, endpoint_id, current_timestamp):
    """Return sample agent data."""
    data = test_data["agents"][0].copy()
    data["endpoint_id"] = endpoint_id
    data["created_at"] = current_timestamp
    data["updated_at"] = current_timestamp
    return data


@pytest.fixture(scope="function")
def sample_agent_uuid():
    """Return sample agent UUID."""
    return "agent-1234567890-abcd1234"


@pytest.fixture(scope="function")
def sample_agent_version_uuid():
    """Return sample agent version UUID."""
    return "agent-1234567890-abcd1234-v1"


# Thread fixtures
@pytest.fixture(scope="function")
def sample_thread_data(test_data, endpoint_id, current_timestamp):
    """Return sample thread data."""
    data = test_data["threads"][0].copy()
    data["endpoint_id"] = endpoint_id
    data["created_at"] = current_timestamp
    data["updated_at"] = current_timestamp
    return data


@pytest.fixture(scope="function")
def sample_thread_uuid():
    """Return sample thread UUID."""
    return "thread-1234567890-abcd1234"


# Run fixtures
@pytest.fixture(scope="function")
def sample_run_data(test_data, sample_thread_uuid, current_timestamp):
    """Return sample run data."""
    data = test_data["runs"][0].copy()
    data["thread_uuid"] = sample_thread_uuid
    data["created_at"] = current_timestamp
    data["updated_at"] = current_timestamp
    return data


@pytest.fixture(scope="function")
def sample_run_uuid():
    """Return sample run UUID."""
    return "run-1234567890-abcd1234"


# Message fixtures
@pytest.fixture(scope="function")
def sample_message_data(
    test_data, sample_thread_uuid, sample_run_uuid, current_timestamp
):
    """Return sample message data."""
    data = test_data["messages"][0].copy()
    data["thread_uuid"] = sample_thread_uuid
    data["run_uuid"] = sample_run_uuid
    data["created_at"] = current_timestamp
    data["updated_at"] = current_timestamp
    return data


@pytest.fixture(scope="function")
def sample_message_uuid():
    """Return sample message UUID."""
    return "message-1234567890-abcd1234"


# ToolCall fixtures
@pytest.fixture(scope="function")
def sample_tool_call_data(
    test_data, sample_thread_uuid, sample_run_uuid, current_timestamp
):
    """Return sample tool call data."""
    data = test_data["tool_calls"][0].copy()
    data["thread_uuid"] = sample_thread_uuid
    data["run_uuid"] = sample_run_uuid
    data["created_at"] = current_timestamp
    data["updated_at"] = current_timestamp
    return data


@pytest.fixture(scope="function")
def sample_tool_call_uuid():
    """Return sample tool call UUID."""
    return "tool-call-1234567890-abcd1234"


# LLM fixtures
@pytest.fixture(scope="function")
def sample_llm_data(test_data, current_timestamp):
    """Return sample LLM data."""
    data = test_data["llms"][0].copy()
    data["created_at"] = current_timestamp
    data["updated_at"] = current_timestamp
    return data


# Configuration fixtures
@pytest.fixture(scope="function")
def sample_prompt_template_data(test_data, endpoint_id, current_timestamp):
    """Return sample prompt template data."""
    data = test_data["prompt_templates"][0].copy()
    data["endpoint_id"] = endpoint_id
    data["created_at"] = current_timestamp
    data["updated_at"] = current_timestamp
    return data


@pytest.fixture(scope="function")
def sample_flow_snippet_data(test_data, endpoint_id, current_timestamp):
    """Return sample flow snippet data."""
    data = test_data["flow_snippets"][0].copy()
    data["endpoint_id"] = endpoint_id
    data["created_at"] = current_timestamp
    data["updated_at"] = current_timestamp
    return data


@pytest.fixture(scope="function")
def sample_mcp_server_data(test_data, endpoint_id, current_timestamp):
    """Return sample MCP server data."""
    data = test_data["mcp_servers"][0].copy()
    data["endpoint_id"] = endpoint_id
    data["created_at"] = current_timestamp
    data["updated_at"] = current_timestamp
    return data


# ============================================================================
# CUSTOM PYTEST HOOKS
# ============================================================================

# Environment variable names for test filtering
_TEST_FUNCTION_ENV = "AI_AGENT_TEST_FUNCTION"
_TEST_MARKER_ENV = "AI_AGENT_TEST_MARKERS"


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "unit: Unit tests (no external dependencies)")
    config.addinivalue_line("markers", "integration: Integration tests (DB, API)")
    config.addinivalue_line("markers", "slow: Tests taking significant time")
    config.addinivalue_line("markers", "agent: Agent-related tests")
    config.addinivalue_line("markers", "thread: Thread/conversation tests")
    config.addinivalue_line("markers", "message: Message handling tests")
    config.addinivalue_line("markers", "run: Run tracking tests")
    config.addinivalue_line("markers", "tool_call: ToolCall functionality tests")
    config.addinivalue_line("markers", "llm: LLM provider tests")
    config.addinivalue_line("markers", "wizard: Wizard configuration tests")
    config.addinivalue_line("markers", "prompt_template: PromptTemplate tests")
    config.addinivalue_line("markers", "flow_snippet: FlowSnippet tests")
    config.addinivalue_line("markers", "mcp_server: MCPServer integration tests")
    config.addinivalue_line("markers", "cache: Cache management tests")
    config.addinivalue_line("markers", "performance: Performance/benchmarking tests")
    config.addinivalue_line("markers", "graphql: GraphQL operation tests")
    config.addinivalue_line("markers", "timeout: Test timeout configuration")


def pytest_addoption(parser: pytest.Parser) -> None:
    """Add custom command-line options for test filtering."""
    parser.addoption(
        "--test-function",
        action="store",
        default=os.getenv(_TEST_FUNCTION_ENV, "").strip(),
        help=(
            "Run only tests whose name exactly matches this string. "
            f"Defaults to the {_TEST_FUNCTION_ENV} environment variable when set."
        ),
    )
    parser.addoption(
        "--test-markers",
        action="store",
        default=os.getenv(_TEST_MARKER_ENV, "").strip(),
        help=(
            "Run only tests that include any of the specified markers "
            "(comma or space separated). "
            f"Defaults to the {_TEST_MARKER_ENV} environment variable when set."
        ),
    )


def _parse_marker_filter(raw: str) -> list[str]:
    """Parse comma/space separated marker string into list."""
    if not raw:
        return []
    parts = re.split(r"[,\s]+", raw.strip())
    return [part for part in parts if part]


def _format_filter_description(target: str, marker_filter_raw: str) -> str:
    """Build human-readable description of active filters."""
    descriptors: list[str] = []
    if target:
        descriptors.append(f"{_TEST_FUNCTION_ENV}='{target}'")
    if marker_filter_raw:
        descriptors.append(f"{_TEST_MARKER_ENV}='{marker_filter_raw}'")
    return " and ".join(descriptors) if descriptors else "no filters"


def _raise_no_matches(filters_desc: str, items: Sequence[pytest.Item]) -> None:
    """Raise informative error when no tests matched filter."""
    sample = ", ".join(sorted(item.name for item in items)[:5])
    hint = f" Available sample: {sample}" if sample else ""
    raise pytest.UsageError(f"{filters_desc} did not match any collected tests.{hint}")


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    """
    Filter collected tests based on --test-function and --test-markers options.

    This allows flexible test execution like:
        pytest --test-function test_graphql_agent
        pytest --test-markers "integration,graphql"
        AI_AGENT_TEST_FUNCTION=test_initialization pytest
    """
    target = config.getoption("--test-function")
    marker_filter_raw = config.getoption("--test-markers")
    markers = _parse_marker_filter(marker_filter_raw)

    if not target and not markers:
        return  # No filtering requested

    target_lower = target.lower()
    selected: list[pytest.Item] = []
    deselected: list[pytest.Item] = []

    for item in items:
        # Extract function name without parameters
        test_func_name = item.name.split("[")[0].lower()

        # Check if name matches (exact match)
        name_match = not target_lower or test_func_name == target_lower

        # Check if any requested marker is present
        marker_match = not markers or any(item.get_closest_marker(m) for m in markers)

        if name_match and marker_match:
            selected.append(item)
        else:
            deselected.append(item)

    if not selected:
        _raise_no_matches(_format_filter_description(target, marker_filter_raw), items)

    items[:] = selected
    config.hook.pytest_deselected(items=deselected)

    # Log filter results
    terminal = config.pluginmanager.get_plugin("terminalreporter")
    if terminal is not None:
        terminal.write_line(
            f"Filtered tests with {_format_filter_description(target, marker_filter_raw)} "
            f"({len(selected)} selected, {len(deselected)} deselected)."
        )
