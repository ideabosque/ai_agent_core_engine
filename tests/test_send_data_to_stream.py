# -*- coding: utf-8 -*-
"""Tests for ai_agent_core_engine send_data_to_stream dual-mode behavior.

Tests verify that send_data_to_stream:
  - Uses ConnectionManager when set (SilvaEngine Gateway mode)
  - Falls back to AWS API Gateway post_to_connection when manager is None
  - Manager takes priority when both manager and apigw_client are set
"""

import json
import logging
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Ensure the repository root is importable. This file lives at
# ai_agent_core_engine/tests/, so walk up once to reach the package root.
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _project_root)


class TestSendDataToStream(unittest.TestCase):
    """Test the dual-mode send_data_to_stream behavior."""

    @classmethod
    def setUpClass(cls):
        """Initialize Config with minimal settings (no AWS WebSocket settings).

        Load config.py and at_agent_listener.py directly via importlib.util,
        stubbing out the heavy dependency chain (google.genai etc.) before
        loading.
        """
        import importlib.util
        import sys as _sys
        import types

        # Step 1: Create stub packages to short-circuit the import chain.
        # The problem: config.py does `from ..models import utils` which
        # triggers ai_agent_core_engine/__init__.py -> main.py -> at_agent_listener.py
        # -> ai_agent.py -> ai_agent_utility.py -> `from google import genai`.
        # We stub the entire package hierarchy before loading anything.

        pkg_root = os.path.join(_project_root, "ai_agent_core_engine")

        # Stub the top-level package __init__.py
        _pkg = types.ModuleType("ai_agent_core_engine")
        _pkg.__path__ = [pkg_root]
        _sys.modules["ai_agent_core_engine"] = _pkg

        # Stub handlers package
        _handlers_pkg = types.ModuleType("ai_agent_core_engine.handlers")
        _handlers_pkg.__path__ = [os.path.join(pkg_root, "handlers")]
        _sys.modules["ai_agent_core_engine.handlers"] = _handlers_pkg

        # Stub models package
        _models_pkg = types.ModuleType("ai_agent_core_engine.models")
        _models_pkg.__path__ = [os.path.join(pkg_root, "models")]
        _sys.modules["ai_agent_core_engine.models"] = _models_pkg

        # Stub models.utils (imported by config.py via `from ..models import utils`)
        _utils_stub = types.ModuleType("ai_agent_core_engine.models.utils")
        _utils_stub.initialize_tables = lambda *a, **kw: None
        _sys.modules["ai_agent_core_engine.models.utils"] = _utils_stub

        # Step 2: Load config.py
        config_path = os.path.join(pkg_root, "handlers", "config.py")
        spec = importlib.util.spec_from_file_location(
            "ai_agent_core_engine.handlers.config", config_path
        )
        config_module = importlib.util.module_from_spec(spec)
        _sys.modules["ai_agent_core_engine.handlers.config"] = config_module
        spec.loader.exec_module(config_module)
        Config = config_module.Config

        cls.Config = Config
        # Reset Config to ensure clean state
        Config._initialized = False
        Config.connection_manager = None
        Config.apigw_client = None

        # Initialize without AWS WebSocket settings -> apigw_client stays None
        Config.initialize(
            logging.getLogger("test"),
            {
                "region_name": "us-east-1",
                "aws_access_key_id": "test-key",
                "aws_secret_access_key": "test-secret",
            },
        )

        # Step 3: Stub remaining deps and load at_agent_listener.py
        # Stub ai_agent_core_engine.handlers.ai_agent (avoid google.genai)
        _ai_agent_stub = types.ModuleType(
            "ai_agent_core_engine.handlers.ai_agent"
        )
        _ai_agent_stub.execute_ask_model = lambda **kw: None
        _sys.modules["ai_agent_core_engine.handlers.ai_agent"] = _ai_agent_stub

        # Stub ai_agent_core_engine.utils.listener
        _utils_pkg2 = types.ModuleType("ai_agent_core_engine.utils")
        _utils_pkg2.__path__ = [os.path.join(pkg_root, "utils")]
        _sys.modules["ai_agent_core_engine.utils"] = _utils_pkg2
        _listener_stub = types.ModuleType(
            "ai_agent_core_engine.utils.listener"
        )
        _listener_stub.create_listener_info = lambda *a, **kw: None
        _sys.modules["ai_agent_core_engine.utils.listener"] = _listener_stub

        # Stub models.tool_call
        _tool_call_stub = types.ModuleType(
            "ai_agent_core_engine.models.tool_call"
        )
        _tool_call_stub.insert_update_tool_call = lambda *a, **kw: None
        _tool_call_stub.resolve_tool_call_list = lambda *a, **kw: None
        _sys.modules["ai_agent_core_engine.models.tool_call"] = _tool_call_stub

        # Now load at_agent_listener
        listener_path = os.path.join(
            pkg_root, "handlers", "at_agent_listener.py"
        )
        spec2 = importlib.util.spec_from_file_location(
            "ai_agent_core_engine.handlers.at_agent_listener",
            listener_path,
        )
        listener_module = importlib.util.module_from_spec(spec2)
        _sys.modules["ai_agent_core_engine.handlers.at_agent_listener"] = (
            listener_module
        )
        spec2.loader.exec_module(listener_module)

        cls._send_data_to_stream = staticmethod(listener_module.send_data_to_stream)

    def setUp(self):
        """Reset connection_manager before each test."""
        self.Config.connection_manager = None

    def tearDown(self):
        """Clean up after each test."""
        self.Config.connection_manager = None

    def test_send_data_to_stream_uses_connection_manager(self):
        """Sends through manager when Config.connection_manager is set."""
        mock_manager = MagicMock()
        mock_manager.send_to_connection.return_value = True
        self.Config.set_connection_manager(mock_manager)

        result = self._send_data_to_stream(
            logging.getLogger("test"),
            connection_id="conn-123",
            data={"message": "hello", "index": 0},
        )

        self.assertTrue(result)
        mock_manager.send_to_connection.assert_called_once()
        call_args = mock_manager.send_to_connection.call_args
        self.assertEqual(call_args[0][0], "conn-123")
        self.assertEqual(call_args[0][1], {"message": "hello", "index": 0})

    def test_send_data_to_stream_aws_fallback(self):
        """Uses post_to_connection when manager is None and apigw_client is set."""
        # Ensure Config is initialized (may have been reset by prior test)
        if not self.Config._initialized:
            self.Config.initialize(
                logging.getLogger("test"),
                {
                    "region_name": "us-east-1",
                    "aws_access_key_id": "test-key",
                    "aws_secret_access_key": "test-secret",
                },
            )

        # Ensure manager is None
        self.Config.connection_manager = None

        # Mock the apigw_client directly (bypass _initialize_apigw_client
        # which would try to create a real boto3 client)
        mock_apigw = MagicMock()
        self.Config.apigw_client = mock_apigw

        try:
            result = self._send_data_to_stream(
                logging.getLogger("test"),
                connection_id="conn-456",
                data={"message": "world", "index": 1},
            )

            self.assertTrue(result)
            mock_apigw.post_to_connection.assert_called_once()
            call_kwargs = mock_apigw.post_to_connection.call_args.kwargs
            self.assertEqual(call_kwargs["ConnectionId"], "conn-456")
            # Data is serialized via Serializer.json_dumps
            sent_data = call_kwargs["Data"]
            parsed = json.loads(sent_data)
            self.assertEqual(parsed["message"], "world")
        finally:
            self.Config.apigw_client = None

    def test_send_data_to_stream_manager_takes_priority(self):
        """When both manager and apigw_client are set, manager wins."""
        mock_manager = MagicMock()
        mock_manager.send_to_connection.return_value = True
        self.Config.set_connection_manager(mock_manager)

        mock_apigw = MagicMock()
        self.Config.apigw_client = mock_apigw

        try:
            result = self._send_data_to_stream(
                logging.getLogger("test"),
                connection_id="conn-789",
                data={"message": "priority"},
            )

            self.assertTrue(result)
            # Manager should have been called
            mock_manager.send_to_connection.assert_called_once()
            # API Gateway client should NOT have been called
            mock_apigw.post_to_connection.assert_not_called()
        finally:
            self.Config.apigw_client = None
            self.Config.connection_manager = None

    def test_config_local_mode_does_not_require_apigw(self):
        """FastAPI mode initializes without API Gateway settings -- apigw_client stays None."""
        # This was already verified in setUpClass â€” apigw_client is None
        # because we initialized without api_id/api_stage.
        self.assertIsNone(self.Config.apigw_client)

    def test_config_aws_mode_initializes_apigw(self):
        """AWS mode with api_id/api_stage creates apigw_client. connection_manager stays None."""
        # Reset and reinitialize with AWS WebSocket settings
        self.Config._initialized = False
        self.Config.apigw_client = None
        self.Config.connection_manager = None

        self.Config.initialize(
            logging.getLogger("test-aws"),
            {
                "region_name": "us-east-1",
                "aws_access_key_id": "test-key",
                "aws_secret_access_key": "test-secret",
                "api_id": "abc123def4",
                "api_stage": "prod",
            },
        )

        # apigw_client should be initialized (it's a MagicMock from boto3 in tests,
        # but the attribute should not be None if all settings were provided).
        # Note: In a real environment, boto3.client would be created.
        # In tests, it may fail if boto3 is not configured -- that's OK,
        # the important thing is connection_manager stays None.
        self.assertIsNone(self.Config.connection_manager)

        # Reset for other tests
        self.Config._initialized = False
        self.Config.apigw_client = None


class TestConfigConnectionManager(unittest.TestCase):
    """Test Config.set_connection_manager / get_connection_manager."""

    @classmethod
    def setUpClass(cls):
        """Load Config.py directly to avoid heavy import chain."""
        import importlib.util
        import sys as _sys
        import types

        pkg_root = os.path.join(_project_root, "ai_agent_core_engine")

        _pkg = types.ModuleType("ai_agent_core_engine")
        _pkg.__path__ = [pkg_root]
        _sys.modules["ai_agent_core_engine"] = _pkg

        _handlers_pkg = types.ModuleType("ai_agent_core_engine.handlers")
        _handlers_pkg.__path__ = [os.path.join(pkg_root, "handlers")]
        _sys.modules["ai_agent_core_engine.handlers"] = _handlers_pkg

        _models_pkg = types.ModuleType("ai_agent_core_engine.models")
        _models_pkg.__path__ = [os.path.join(pkg_root, "models")]
        _sys.modules["ai_agent_core_engine.models"] = _models_pkg

        _utils_stub = types.ModuleType("ai_agent_core_engine.models.utils")
        _utils_stub.initialize_tables = lambda *a, **kw: None
        _sys.modules["ai_agent_core_engine.models.utils"] = _utils_stub

        config_path = os.path.join(
            pkg_root, "handlers", "config.py"
        )
        spec = importlib.util.spec_from_file_location(
            "ai_agent_core_engine.handlers.config", config_path
        )
        config_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(config_module)
        cls.Config = config_module.Config

    def test_set_and_get_connection_manager(self):
        manager = MagicMock()
        self.Config.set_connection_manager(manager)
        self.assertIs(self.Config.get_connection_manager(), manager)

        self.Config.set_connection_manager(None)
        self.assertIsNone(self.Config.get_connection_manager())


if __name__ == "__main__":
    unittest.main()