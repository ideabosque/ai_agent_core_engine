# -*- coding: utf-8 -*-
"""
Test helpers and utilities for AI Agent Core Engine tests.
"""
from __future__ import print_function

import json
import logging
import time
import uuid
from functools import wraps
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import MagicMock

import pendulum
from silvaengine_utility import Utility

logger = logging.getLogger("test_ai_agent_core_engine")


def create_mock_model(model_class, **kwargs):
    """Create a mock model instance with specified attributes."""
    mock = MagicMock(spec=model_class)
    mock.attribute_values = kwargs
    mock.__dict__["attribute_values"] = kwargs

    # Set attributes directly on mock
    for key, value in kwargs.items():
        setattr(mock, key, value)

    return mock


def assert_graphql_type_fields(graphql_type, expected_fields: List[str]):
    """Assert that a GraphQL type has all expected fields."""
    type_fields = graphql_type._meta.fields.keys()
    for field in expected_fields:
        assert (
            field in type_fields
        ), f"Field '{field}' not found in {graphql_type.__name__}"


def assert_model_data_matches(
    model, expected_data: Dict[str, Any], exclude_fields: List[str] = None
):
    """Assert that model data matches expected data."""
    exclude_fields = exclude_fields or []

    for key, expected_value in expected_data.items():
        if key in exclude_fields:
            continue

        actual_value = getattr(model, key, None)
        assert (
            actual_value == expected_value
        ), f"Field '{key}' mismatch: expected {expected_value}, got {actual_value}"


def create_timestamp(days_ago: int = 0):
    """Create a UTC timestamp for testing."""
    return pendulum.now("UTC").subtract(days=days_ago)


def create_test_context(
    endpoint_id: str = "test-endpoint-001", user_id: str = "test-user-001"
):
    """Create a test GraphQL context."""
    return {
        "endpoint_id": endpoint_id,
        "user_id": user_id,
        "logger": MagicMock(),
    }


class TestDataBuilder:
    """Builder class for creating test data with relationships."""

    def __init__(self, test_data: Dict[str, Any]):
        self.test_data = test_data
        self.created_entities = {}

    def build_agent(self, **overrides):
        """Build agent data with optional overrides."""
        data = self.test_data["agents"][0].copy()
        data.update(overrides)
        return data

    def build_thread(self, agent_uuid: str = None, **overrides):
        """Build thread data with optional agent relationship."""
        data = self.test_data["threads"][0].copy()
        if agent_uuid:
            data["agent_uuid"] = agent_uuid
        data.update(overrides)
        return data

    def build_run(self, thread_uuid: str = None, **overrides):
        """Build run data with optional thread relationship."""
        data = self.test_data["runs"][0].copy()
        if thread_uuid:
            data["thread_uuid"] = thread_uuid
        data.update(overrides)
        return data

    def build_message(self, thread_uuid: str = None, run_uuid: str = None, **overrides):
        """Build message data with optional relationships."""
        data = self.test_data["messages"][0].copy()
        if thread_uuid:
            data["thread_uuid"] = thread_uuid
        if run_uuid:
            data["run_uuid"] = run_uuid
        data.update(overrides)
        return data

    def build_tool_call(
        self, thread_uuid: str = None, run_uuid: str = None, **overrides
    ):
        """Build tool call data with optional relationships."""
        data = self.test_data["tool_calls"][0].copy()
        if thread_uuid:
            data["thread_uuid"] = thread_uuid
        if run_uuid:
            data["run_uuid"] = run_uuid
        data.update(overrides)
        return data

    def build_conversation_chain(self, endpoint_id: str = "test-endpoint-001"):
        """Build a complete conversation chain with agent, thread, run, messages, and tool calls."""
        agent_data = self.build_agent(endpoint_id=endpoint_id)
        thread_data = self.build_thread(
            endpoint_id=endpoint_id, agent_uuid=agent_data["agent_uuid"]
        )
        run_data = self.build_run(thread_uuid=thread_data["thread_uuid"])
        message_data = self.build_message(
            thread_uuid=thread_data["thread_uuid"], run_uuid=run_data["run_uuid"]
        )
        tool_call_data = self.build_tool_call(
            thread_uuid=thread_data["thread_uuid"], run_uuid=run_data["run_uuid"]
        )

        return {
            "agent": agent_data,
            "thread": thread_data,
            "run": run_data,
            "message": message_data,
            "tool_call": tool_call_data,
        }


# ============================================================================
# INTEGRATION TEST HELPERS
# ============================================================================


def call_method(
    engine: Any,
    method_name: str,
    arguments: Optional[Dict[str, Any]] = None,
    label: Optional[str] = None,
) -> Tuple[Optional[Any], Optional[Exception]]:
    """
    Invoke engine methods with consistent logging and error capture.

    Args:
        engine: Engine instance
        method_name: Name of method to call
        arguments: Method arguments
        label: Optional label for logging

    Returns:
        Tuple of (result, error) - one will be None
    """
    arguments = arguments or {}
    op = label or method_name
    cid = uuid.uuid4().hex[:8]  # Correlation ID for tracking

    logger.info(
        f"Method call: cid={cid} op={op} arguments={Utility.json_dumps(arguments)}"
    )
    t0 = time.perf_counter()

    try:
        method = getattr(engine, method_name)
    except AttributeError as exc:
        elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
        logger.info(
            f"Method response: cid={cid} op={op} elapsed_ms={elapsed_ms} "
            f"success=False error={str(exc)}"
        )
        return None, exc

    try:
        result = method(**arguments)
        if isinstance(result, str):
            try:
                result = json.loads(result)
            except ValueError:
                pass
        elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)

        logger.info(
            f"Method response: cid={cid} op={op} elapsed_ms={elapsed_ms} "
            f"success=True result={Utility.json_dumps(result)}"
        )
        return result, None
    except Exception as exc:
        elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
        logger.error(
            f"Method response: cid={cid} op={op} elapsed_ms={elapsed_ms} "
            f"success=False error={type(exc).__name__}: {str(exc)}"
        )
        return None, exc


def log_test_result(func):
    """
    Decorator to log test execution with timing.

    Usage:
        @log_test_result
        def test_something():
            pass
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        test_name = func.__name__
        logger.info(f"{'='*80}")
        logger.info(f"Starting test: {test_name}")
        logger.info(f"{'='*80}")
        t0 = time.perf_counter()

        try:
            result = func(*args, **kwargs)
            elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
            logger.info(f"{'='*80}")
            logger.info(f"Test {test_name} PASSED (elapsed: {elapsed_ms}ms)")
            logger.info(f"{'='*80}\n")
            return result
        except Exception as exc:
            elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
            logger.error(f"{'='*80}")
            logger.error(f"Test {test_name} FAILED (elapsed: {elapsed_ms}ms): {exc}")
            logger.error(f"{'='*80}\n")
            raise

    return wrapper


def validate_graphql_response(
    result: Dict[str, Any],
    expected_keys: List[str],
    operation_path: Optional[List[str]] = None,
) -> None:
    """
    Validate that GraphQL response returned expected structure.

    Args:
        result: GraphQL result dict
        expected_keys: Keys that should exist in result
        operation_path: Path to operation result (e.g., ['data', 'insertUpdateAgent', 'agent'])

    Raises:
        AssertionError: If validation fails
    """
    current = result
    path_str = "result"

    # Navigate to operation result if path provided
    if operation_path:
        for key in operation_path:
            assert key in current, f"{path_str} missing key '{key}'"
            current = current[key]
            path_str += f"['{key}']"

    # Validate expected keys exist
    for key in expected_keys:
        assert key in current, f"{path_str} missing expected key '{key}'"

    logger.info(f"Validated structure at {path_str}: {list(current.keys())}")
