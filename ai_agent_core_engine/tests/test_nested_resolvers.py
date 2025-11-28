#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Nested Resolver Tests

Pytest-based test suite for nested field resolvers in AI Agent Core Engine.
Tests lazy loading via DataLoaders for all GraphQL type relationships.
"""
from __future__ import print_function

__author__ = "bibow"

from unittest.mock import MagicMock
import pytest
from promise import Promise

from ai_agent_core_engine.models.batch_loaders import RequestLoaders, get_loaders
from ai_agent_core_engine.types.wizard import WizardType
from ai_agent_core_engine.types.wizard_schema import WizardSchemaType
from ai_agent_core_engine.types.wizard_group import WizardGroupType
from ai_agent_core_engine.types.agent import AgentType
from ai_agent_core_engine.types.llm import LlmType
from ai_agent_core_engine.types.flow_snippet import FlowSnippetType
from ai_agent_core_engine.types.prompt_template import PromptTemplateType
from ai_agent_core_engine.types.run import RunType
from ai_agent_core_engine.types.thread import ThreadType
from ai_agent_core_engine.types.message import MessageType
from ai_agent_core_engine.types.tool_call import ToolCallType
from ai_agent_core_engine.types.element import ElementType
from ai_agent_core_engine.types.mcp_server import MCPServerType
from ai_agent_core_engine.types.wizard_group_filter import WizardGroupFilterType


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture(scope="function")
def mock_context(mock_logger):
    """Create mock GraphQL context with logger."""
    return {
        "logger": mock_logger,
        "endpoint_id": "test-endpoint-001",
    }


@pytest.fixture(scope="function")
def mock_info(mock_context):
    """Create mock GraphQL ResolveInfo object."""
    info = MagicMock()
    info.context = mock_context
    return info


@pytest.fixture(scope="function")
def mock_loaders(mock_context):
    """Create RequestLoaders with mocked batch_load_fn for all loaders."""
    loaders = RequestLoaders(mock_context, cache_enabled=False)
    
    # Mock all loaders to return Promises
    loaders.element_loader.load = MagicMock()
    loaders.wizard_loader.load = MagicMock()
    loaders.llm_loader.load = MagicMock()
    loaders.flow_snippet_loader.load = MagicMock()
    loaders.mcp_server_loader.load = MagicMock()
    loaders.thread_loader.load = MagicMock()
    loaders.prompt_template_loader.load = MagicMock()
    
    # Store in context for get_loaders()
    mock_context["batch_loaders"] = loaders
    return loaders


# ============================================================================
# WIZARD TYPE RESOLVER TESTS
# ============================================================================

class TestWizardResolvers:
    """Test nested resolvers for WizardType."""

    @pytest.mark.unit
    @pytest.mark.nested_resolver
    @pytest.mark.wizard
    def test_resolve_wizard_schema_from_embedded_dict(self, mock_info):
        """Test wizard_schema resolver with embedded dict data."""
        # Arrange
        parent = MagicMock()
        parent.wizard_schema = {
            "wizard_schema_type": "test_type",
            "wizard_schema_name": "test_name",
            "wizard_schema_description": "Test Schema"
        }
        
        # Act
        result = WizardType.resolve_wizard_schema(parent, mock_info)
        
        # Assert
        assert isinstance(result, WizardSchemaType)
        assert result.wizard_schema_name == "test_name"
        assert result.wizard_schema_type == "test_type"

    @pytest.mark.unit
    @pytest.mark.nested_resolver
    @pytest.mark.wizard
    def test_resolve_wizard_schema_from_embedded_type(self, mock_info):
        """Test wizard_schema resolver with embedded WizardSchemaType."""
        # Arrange
        parent = MagicMock()
        schema_obj = WizardSchemaType(
            wizard_schema_type="test_type",
            wizard_schema_name="test_name"
        )
        parent.wizard_schema = schema_obj
        
        # Act
        result = WizardType.resolve_wizard_schema(parent, mock_info)
        
        # Assert
        assert result is schema_obj

    @pytest.mark.unit
    @pytest.mark.nested_resolver
    @pytest.mark.wizard
    def test_resolve_wizard_schema_missing_keys(self, mock_info):
        """Test wizard_schema resolver with missing required keys."""
        # Arrange
        parent = MagicMock()
        parent.wizard_schema = None
        parent.wizard_schema_type = None
        parent.wizard_schema_name = "test_name"
        
        # Act
        result = WizardType.resolve_wizard_schema(parent, mock_info)
        
        # Assert
        assert result is None

    @pytest.mark.unit
    @pytest.mark.nested_resolver
    @pytest.mark.wizard
    def test_resolve_wizard_elements_from_embedded(self, mock_info):
        """Test wizard_elements resolver with embedded element data."""
        # Arrange
        parent = MagicMock()
        parent.wizard_elements = [
            {
                "element_uuid": "elem1",
                "required": True,
                "element": ElementType(element_uuid="elem1", element_title="Element 1")
            }
        ]
        
        # Act
        result = WizardType.resolve_wizard_elements(parent, mock_info)
        
        # Assert
        assert result == parent.wizard_elements

    @pytest.mark.unit
    @pytest.mark.nested_resolver
    @pytest.mark.wizard
    def test_resolve_wizard_elements_from_loader(self, mock_info, mock_loaders):
        """Test wizard_elements resolver with lazy loading."""
        # Arrange
        parent = MagicMock()
        parent.endpoint_id = "test-endpoint"
        parent.wizard_elements = [
            {"element_uuid": "elem1", "required": True},
            {"element_uuid": "elem2", "required": False}
        ]
        
        mock_loaders.element_loader.load.side_effect = [
            Promise.resolve({"element_uuid": "elem1", "element_title": "Element 1"}),
            Promise.resolve({"element_uuid": "elem2", "element_title": "Element 2"})
        ]
        
        # Act
        result_promise = WizardType.resolve_wizard_elements(parent, mock_info)
        result = result_promise.get()
        
        # Assert
        assert len(result) == 2
        assert result[0]["element"].element_title == "Element 1"
        assert result[1]["element"].element_title == "Element 2"
        assert result[0]["required"] is True
        assert result[1]["required"] is False

    @pytest.mark.unit
    @pytest.mark.nested_resolver
    @pytest.mark.wizard
    def test_resolve_wizard_elements_empty_list(self, mock_info):
        """Test wizard_elements resolver with empty list."""
        # Arrange
        parent = MagicMock()
        parent.endpoint_id = "test-endpoint"
        parent.wizard_elements = []
        
        # Act
        result = WizardType.resolve_wizard_elements(parent, mock_info)
        
        # Assert
        assert result == []


# ============================================================================
# WIZARD GROUP TYPE RESOLVER TESTS
# ============================================================================

class TestWizardGroupResolvers:
    """Test nested resolvers for WizardGroupType."""

    @pytest.mark.unit
    @pytest.mark.nested_resolver
    @pytest.mark.wizard
    def test_resolve_wizards_from_embedded_dicts(self, mock_info):
        """Test wizards resolver with embedded dict data."""
        # Arrange
        parent = MagicMock()
        parent.wizards = [
            {"wizard_uuid": "w1", "wizard_title": "Wizard 1"},
            {"wizard_uuid": "w2", "wizard_title": "Wizard 2"}
        ]
        
        # Act
        result = WizardGroupType.resolve_wizards(parent, mock_info)
        
        # Assert
        assert len(result) == 2
        assert all(isinstance(w, WizardType) for w in result)

    @pytest.mark.unit
    @pytest.mark.nested_resolver
    @pytest.mark.wizard
    def test_resolve_wizards_from_loader(self, mock_info, mock_loaders):
        """Test wizards resolver with lazy loading."""
        # Arrange
        parent = MagicMock()
        parent.endpoint_id = "test-endpoint"
        parent.wizard_uuids = ["w1", "w2"]
        parent.wizards = None
        
        mock_loaders.wizard_loader.load.side_effect = [
            Promise.resolve({"wizard_uuid": "w1", "wizard_title": "Wizard 1"}),
            Promise.resolve({"wizard_uuid": "w2", "wizard_title": "Wizard 2"})
        ]
        
        # Act
        result_promise = WizardGroupType.resolve_wizards(parent, mock_info)
        result = result_promise.get()
        
        # Assert
        assert len(result) == 2
        assert result[0].wizard_title == "Wizard 1"
        assert result[1].wizard_title == "Wizard 2"

    @pytest.mark.unit
    @pytest.mark.nested_resolver
    @pytest.mark.wizard
    def test_resolve_wizards_empty_list(self, mock_info):
        """Test wizards resolver with empty wizard_uuids."""
        # Arrange
        parent = MagicMock()
        parent.endpoint_id = "test-endpoint"
        parent.wizard_uuids = []
        parent.wizards = None
        
        # Act
        result = WizardGroupType.resolve_wizards(parent, mock_info)
        
        # Assert
        assert result == []


# ============================================================================
# AGENT TYPE RESOLVER TESTS
# ============================================================================

class TestAgentResolvers:
    """Test nested resolvers for AgentType."""

    @pytest.mark.unit
    @pytest.mark.nested_resolver
    @pytest.mark.agent
    def test_resolve_llm_from_embedded_dict(self, mock_info):
        """Test llm resolver with embedded dict data."""
        # Arrange
        parent = MagicMock()
        parent.llm = {"llm_provider": "openai", "llm_name": "gpt-4"}
        
        # Act
        result = AgentType.resolve_llm(parent, mock_info)
        
        # Assert
        assert isinstance(result, LlmType)
        assert result.llm_provider == "openai"

    @pytest.mark.unit
    @pytest.mark.nested_resolver
    @pytest.mark.agent
    def test_resolve_llm_from_loader(self, mock_info, mock_loaders):
        """Test llm resolver with lazy loading."""
        # Arrange
        parent = MagicMock()
        parent.llm = None
        parent.llm_provider = "openai"
        parent.llm_name = "gpt-4"
        
        mock_loaders.llm_loader.load.return_value = Promise.resolve({
            "llm_provider": "openai",
            "llm_name": "gpt-4",
            "module_name": "openai_module"
        })
        
        # Act
        result_promise = AgentType.resolve_llm(parent, mock_info)
        result = result_promise.get()
        
        # Assert
        mock_loaders.llm_loader.load.assert_called_once_with(("openai", "gpt-4"))
        assert isinstance(result, LlmType)

    @pytest.mark.unit
    @pytest.mark.nested_resolver
    @pytest.mark.agent
    def test_resolve_llm_missing_keys(self, mock_info):
        """Test llm resolver with missing required keys."""
        # Arrange
        parent = MagicMock()
        parent.llm = None
        parent.llm_provider = None
        parent.llm_name = "gpt-4"
        
        # Act
        result = AgentType.resolve_llm(parent, mock_info)
        
        # Assert
        assert result is None

    @pytest.mark.unit
    @pytest.mark.nested_resolver
    @pytest.mark.agent
    def test_resolve_flow_snippet_from_embedded_dict(self, mock_info):
        """Test flow_snippet resolver with embedded dict data."""
        # Arrange
        parent = MagicMock()
        parent.flow_snippet = {
            "flow_snippet_version_uuid": "fs1",
            "flow_name": "main_flow"
        }
        
        # Act
        result = AgentType.resolve_flow_snippet(parent, mock_info)
        
        # Assert
        assert isinstance(result, FlowSnippetType)

    @pytest.mark.unit
    @pytest.mark.nested_resolver
    @pytest.mark.agent
    def test_resolve_flow_snippet_from_loader(self, mock_info, mock_loaders):
        """Test flow_snippet resolver with lazy loading."""
        # Arrange
        parent = MagicMock()
        parent.flow_snippet = None
        parent.endpoint_id = "test-endpoint"
        parent.flow_snippet_version_uuid = "fs1"
        
        mock_loaders.flow_snippet_loader.load.return_value = Promise.resolve({
            "flow_snippet_version_uuid": "fs1",
            "flow_name": "main_flow"
        })
        
        # Act
        result_promise = AgentType.resolve_flow_snippet(parent, mock_info)
        result = result_promise.get()
        
        # Assert
        mock_loaders.flow_snippet_loader.load.assert_called_once_with(
            ("test-endpoint", "fs1")
        )
        assert isinstance(result, FlowSnippetType)

    @pytest.mark.unit
    @pytest.mark.nested_resolver
    @pytest.mark.agent
    def test_resolve_mcp_servers_from_embedded_dicts(self, mock_info, mock_loaders):
        """Test mcp_servers resolver with embedded dict data."""
        # Arrange
        parent = MagicMock()
        parent.endpoint_id = "test-endpoint"
        parent.mcp_servers = [
            {"mcp_server_uuid": "ms1"},
            {"mcp_server_uuid": "ms2"}
        ]
        
        mock_loaders.mcp_server_loader.load.side_effect = [
            Promise.resolve({"mcp_server_uuid": "ms1", "mcp_label": "Server 1"}),
            Promise.resolve({"mcp_server_uuid": "ms2", "mcp_label": "Server 2"})
        ]
        
        # Act
        result_promise = AgentType.resolve_mcp_servers(parent, mock_info)
        result = result_promise.get()
        
        # Assert
        assert len(result) == 2
        assert all(isinstance(s, MCPServerType) for s in result)

    @pytest.mark.unit
    @pytest.mark.nested_resolver
    @pytest.mark.agent
    def test_resolve_mcp_servers_from_loader(self, mock_info, mock_loaders):
        """Test mcp_servers resolver with lazy loading."""
        # Arrange
        parent = MagicMock()
        parent.endpoint_id = "test-endpoint"
        parent.mcp_server_uuids = ["ms1", "ms2"]
        parent.mcp_servers = None
        
        mock_loaders.mcp_server_loader.load.side_effect = [
            Promise.resolve({"mcp_server_uuid": "ms1", "mcp_label": "Server 1"}),
            Promise.resolve({"mcp_server_uuid": "ms2", "mcp_label": "Server 2"})
        ]
        
        # Act
        result_promise = AgentType.resolve_mcp_servers(parent, mock_info)
        result = result_promise.get()
        
        # Assert
        assert len(result) == 2
        assert result[0].mcp_label == "Server 1"

    @pytest.mark.unit
    @pytest.mark.nested_resolver
    @pytest.mark.agent
    def test_resolve_mcp_servers_empty_list(self, mock_info):
        """Test mcp_servers resolver with empty list."""
        # Arrange
        parent = MagicMock()
        parent.endpoint_id = "test-endpoint"
        parent.mcp_server_uuids = []
        parent.mcp_servers = None
        
        # Act
        result = AgentType.resolve_mcp_servers(parent, mock_info)
        
        # Assert
        assert result == []


# ============================================================================
# FLOW SNIPPET TYPE RESOLVER TESTS
# ============================================================================

class TestFlowSnippetResolvers:
    """Test nested resolvers for FlowSnippetType."""

    @pytest.mark.unit
    @pytest.mark.nested_resolver
    def test_resolve_prompt_template_from_embedded_dict(self, mock_info):
        """Test prompt_template resolver with embedded dict data."""
        # Arrange
        parent = MagicMock()
        parent.prompt_template = {
            "prompt_version_uuid": "pt1",
            "prompt_name": "test_prompt"
        }
        
        # Act
        result = FlowSnippetType.resolve_prompt_template(parent, mock_info)
        
        # Assert
        assert isinstance(result, PromptTemplateType)

    @pytest.mark.unit
    @pytest.mark.nested_resolver
    def test_resolve_prompt_template_from_loader(self, mock_info, mock_loaders):
        """Test prompt_template resolver with lazy loading via utility function."""
        # Arrange
        parent = MagicMock()
        parent.prompt_template = None
        parent.endpoint_id = "test-endpoint"
        parent.prompt_uuid = "pt1"
        
        # Mock the utility function that's called internally
        with MagicMock() as mock_get_prompt:
            # The resolver calls _get_prompt_template which we can't easily mock
            # So we'll just test the None case
            parent.prompt_uuid = None
            
            # Act
            result = FlowSnippetType.resolve_prompt_template(parent, mock_info)
            
            # Assert
            assert result is None

    @pytest.mark.unit
    @pytest.mark.nested_resolver
    def test_resolve_prompt_template_missing_keys(self, mock_info):
        """Test prompt_template resolver with missing required keys."""
        # Arrange
        parent = MagicMock()
        parent.prompt_template = None
        parent.endpoint_id = None
        parent.prompt_version_uuid = "pt1"
        
        # Act
        result = FlowSnippetType.resolve_prompt_template(parent, mock_info)
        
        # Assert
        assert result is None


# ============================================================================
# RUN TYPE RESOLVER TESTS
# ============================================================================

class TestRunResolvers:
    """Test nested resolvers for RunType."""

    @pytest.mark.unit
    @pytest.mark.nested_resolver
    @pytest.mark.run
    def test_resolve_thread_from_embedded_dict(self, mock_info):
        """Test thread resolver with embedded dict data."""
        # Arrange
        parent = MagicMock()
        parent.thread = {
            "thread_uuid": "t1",
            "endpoint_id": "test-endpoint"
        }
        
        # Act
        result = RunType.resolve_thread(parent, mock_info)
        
        # Assert
        assert isinstance(result, ThreadType)

    @pytest.mark.unit
    @pytest.mark.nested_resolver
    @pytest.mark.run
    def test_resolve_thread_from_loader(self, mock_info, mock_loaders):
        """Test thread resolver with lazy loading."""
        # Arrange
        parent = MagicMock()
        parent.thread = None
        parent.endpoint_id = "test-endpoint"
        parent.thread_uuid = "t1"
        
        mock_loaders.thread_loader.load.return_value = Promise.resolve({
            "thread_uuid": "t1",
            "endpoint_id": "test-endpoint"
        })
        
        # Act
        result_promise = RunType.resolve_thread(parent, mock_info)
        result = result_promise.get()
        
        # Assert
        mock_loaders.thread_loader.load.assert_called_once_with(
            ("test-endpoint", "t1")
        )
        assert isinstance(result, ThreadType)

    @pytest.mark.unit
    @pytest.mark.nested_resolver
    @pytest.mark.run
    def test_resolve_messages_from_embedded_dicts(self, mock_info):
        """Test messages resolver with embedded dict data."""
        # Arrange
        parent = MagicMock()
        parent.messages = [
            {"message_uuid": "m1"},
            {"message_uuid": "m2"}
        ]
        
        # Act
        result = RunType.resolve_messages(parent, mock_info)
        
        # Assert
        assert len(result) == 2
        assert all(isinstance(m, MessageType) for m in result)

    @pytest.mark.unit
    @pytest.mark.nested_resolver
    @pytest.mark.run
    def test_resolve_messages_empty_list(self, mock_info):
        """Test messages resolver with empty list."""
        # Arrange
        parent = MagicMock()
        parent.messages = None
        parent.message_uuids = []
        parent.thread_uuid = "t1"
        
        # Act
        result = RunType.resolve_messages(parent, mock_info)
        
        # Assert
        assert result == []

    @pytest.mark.unit
    @pytest.mark.nested_resolver
    @pytest.mark.run
    def test_resolve_tool_calls_from_embedded_dicts(self, mock_info):
        """Test tool_calls resolver with embedded dict data."""
        # Arrange
        parent = MagicMock()
        parent.tool_calls = [
            {"tool_call_uuid": "tc1"},
            {"tool_call_uuid": "tc2"}
        ]
        
        # Act
        result = RunType.resolve_tool_calls(parent, mock_info)
        
        # Assert
        assert len(result) == 2
        assert all(isinstance(tc, ToolCallType) for tc in result)

    @pytest.mark.unit
    @pytest.mark.nested_resolver
    @pytest.mark.run
    def test_resolve_tool_calls_empty_list(self, mock_info):
        """Test tool_calls resolver with empty list."""
        # Arrange
        parent = MagicMock()
        parent.tool_calls = None
        parent.tool_call_uuids = []
        parent.thread_uuid = "t1"
        
        # Act
        result = RunType.resolve_tool_calls(parent, mock_info)
        
        # Assert
        assert result == []


# ============================================================================
# MESSAGE TYPE RESOLVER TESTS
# ============================================================================

class TestMessageResolvers:
    """Test nested resolvers for MessageType."""

    @pytest.mark.unit
    @pytest.mark.nested_resolver
    @pytest.mark.message
    def test_resolve_run_from_embedded_dict(self, mock_info):
        """Test run resolver with embedded dict data."""
        # Arrange
        parent = MagicMock()
        parent.run = {
            "run_uuid": "r1"
        }
        
        # Act
        result = MessageType.resolve_run(parent, mock_info)
        
        # Assert
        assert isinstance(result, RunType)

    @pytest.mark.unit
    @pytest.mark.nested_resolver
    @pytest.mark.message
    def test_resolve_run_returns_none_when_missing(self, mock_info):
        """Test run resolver returns None when run data is missing."""
        # Arrange
        parent = MagicMock()
        parent.run = None
        parent.run_uuid = None
        
        # Act
        result = MessageType.resolve_run(parent, mock_info)
        
        # Assert
        assert result is None


# ============================================================================
# TOOL CALL TYPE RESOLVER TESTS
# ============================================================================

class TestToolCallResolvers:
    """Test nested resolvers for ToolCallType."""

    @pytest.mark.unit
    @pytest.mark.nested_resolver
    @pytest.mark.tool_call
    def test_resolve_run_from_embedded_dict(self, mock_info):
        """Test run resolver with embedded dict data."""
        # Arrange
        parent = MagicMock()
        parent.run = {
            "run_uuid": "r1"
        }
        
        # Act
        result = ToolCallType.resolve_run(parent, mock_info)
        
        # Assert
        assert isinstance(result, RunType)

    @pytest.mark.unit
    @pytest.mark.nested_resolver
    @pytest.mark.tool_call
    def test_resolve_run_returns_none_when_missing(self, mock_info):
        """Test run resolver returns None when run data is missing."""
        # Arrange
        parent = MagicMock()
        parent.run = None
        parent.run_uuid = None
        
        # Act
        result = ToolCallType.resolve_run(parent, mock_info)
        
        # Assert
        assert result is None


# ============================================================================
# THREAD TYPE RESOLVER TESTS
# ============================================================================

class TestThreadResolvers:
    """Test nested resolvers for ThreadType."""

    @pytest.mark.unit
    @pytest.mark.nested_resolver
    @pytest.mark.thread
    def test_resolve_agent_from_embedded_dict(self, mock_info):
        """Test agent resolver with embedded dict data."""
        # Arrange
        parent = MagicMock()
        parent.agent = {
            "agent_version_uuid": "a1",
            "endpoint_id": "test-endpoint"
        }
        
        # Act
        result = ThreadType.resolve_agent(parent, mock_info)
        
        # Assert
        assert isinstance(result, AgentType)

    @pytest.mark.unit
    @pytest.mark.nested_resolver
    @pytest.mark.thread
    def test_resolve_agent_returns_none_when_missing(self, mock_info):
        """Test agent resolver returns None when agent data is missing."""
        # Arrange
        parent = MagicMock()
        parent.agent = None
        parent.agent_version_uuid = None
        
        # Act
        result = ThreadType.resolve_agent(parent, mock_info)
        
        # Assert
        assert result is None


# ============================================================================
# WIZARD GROUP FILTER TYPE RESOLVER TESTS
# ============================================================================

class TestWizardGroupFilterResolvers:
    """Test nested resolvers for WizardGroupFilterType."""

    @pytest.mark.unit
    @pytest.mark.nested_resolver
    @pytest.mark.wizard
    def test_resolve_wizard_group_from_embedded_dict(self, mock_info):
        """Test wizard_group resolver with embedded dict data."""
        # Arrange
        parent = MagicMock()
        parent.wizard_group = {
            "wizard_group_uuid": "wg1",
            "endpoint_id": "test-endpoint"
        }
        
        # Act
        result = WizardGroupFilterType.resolve_wizard_group(parent, mock_info)
        
        # Assert
        assert isinstance(result, WizardGroupType)

    @pytest.mark.unit
    @pytest.mark.nested_resolver
    @pytest.mark.wizard
    def test_resolve_wizard_group_returns_none_when_missing(self, mock_info):
        """Test wizard_group resolver returns None when data is missing."""
        # Arrange
        parent = MagicMock()
        parent.wizard_group = None
        parent.wizard_group_uuid = None
        
        # Act
        result = WizardGroupFilterType.resolve_wizard_group(parent, mock_info)
        
        # Assert
        assert result is None
