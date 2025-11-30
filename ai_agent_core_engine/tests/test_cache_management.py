# -*- coding: utf-8 -*-
"""
Tests for cache management infrastructure and performance.

This module contains comprehensive tests for:
- Cache performance and optimization
- Cache statistics and monitoring
- Universal cache purging system
- Cascading cache invalidation
- Cache relationships configuration
- Entity-specific cache support
"""
from __future__ import print_function

import json
import logging
import os
import sys
import time
from unittest.mock import MagicMock, patch

import pytest
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path to allow imports when running directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# Setup logging
logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger()

def load_test_data():
    try:
        data_path = os.path.join(os.path.dirname(__file__), "test_data.json")
        with open(data_path, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Could not load test_data.json: {e}")
        return {}

TEST_DATA = load_test_data()

from graphene import Schema
from silvaengine_utility import Utility

from ai_agent_core_engine import AIAgentCoreEngine
from ai_agent_core_engine.handlers.config import Config
from ai_agent_core_engine.models.cache import purge_entity_cascading_cache
from ai_agent_core_engine.schema import Mutations, Query, type_class

# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture(scope="class")
def cache_integration_setup():
    """Set up test environment with AIAgentCoreEngine for integration tests."""
    setting = {
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
            "ai_agent_core_graphql": {
                "module_name": "ai_agent_core_engine",
                "class_name": "AIAgentCoreEngine",
            },
            "async_execute_ask_model": {
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
        "execute_mode": os.getenv("execute_mode"),
        "initialize_tables": int(os.getenv("initialize_tables", "0")),
    }

    ai_agent_core_engine = AIAgentCoreEngine(logger, **setting)
    endpoint_id = setting.get("endpoint_id")
    schema_object = Schema(query=Query, mutation=Mutations, types=type_class())
    schema = schema_object.introspect()["__schema"]

    return {
        "ai_agent_core_engine": ai_agent_core_engine,
        "schema": schema,
        "setting": setting,
    }


# ============================================================================
# UNIT TESTS
# ============================================================================


@pytest.mark.unit
@pytest.mark.cache
class TestCacheConfiguration:
    """Test cache configuration."""

    def test_cache_entity_config_has_all_models(self):
        """Test that cache configuration includes all 17 models."""
        config = Config.get_cache_entity_config()

        expected_entities = [
            "agent",
            "thread",
            "run",
            "message",
            "tool_call",
            "llm",
            "prompt_template",
            "flow_snippet",
            "mcp_server",
            "ui_component",
            "wizard",
            "wizard_schema",
            "wizard_group",
            "wizard_group_filter",
            "element",
            "fine_tuning_message",
            "async_task",
        ]

        for entity in expected_entities:
            assert entity in config, f"Entity '{entity}' not in cache config"

    def test_cache_entity_config_structure(self):
        """Test that each cache entity config has required fields."""
        config = Config.get_cache_entity_config()

        for entity, entity_config in config.items():
            assert "module" in entity_config, f"{entity} missing 'module'"
            assert "getter" in entity_config, f"{entity} missing 'getter'"
            assert "cache_keys" in entity_config, f"{entity} missing 'cache_keys'"


@pytest.mark.unit
@pytest.mark.cache
class TestCacheRelationships:
    """Test cache relationship configuration."""

    def test_cache_relationships_defined(self):
        """Test that cache relationships are defined for key entities."""
        relationships = Config.get_cache_relationships()

        # Key entities that should have child relationships
        assert "agent" in relationships
        assert "thread" in relationships
        assert "run" in relationships

    def test_agent_cache_relationships(self):
        """Test agent cache relationships."""
        relationships = Config.get_cache_relationships()
        agent_children = relationships["agent"]

        # Agent should cascade to threads and fine_tuning_messages
        child_types = [child["entity_type"] for child in agent_children]
        assert "thread" in child_types
        assert "fine_tuning_message" in child_types

    def test_thread_cache_relationships(self):
        """Test thread cache relationships."""
        relationships = Config.get_cache_relationships()
        thread_children = relationships["thread"]

        # Thread should cascade to runs, messages, tool_calls
        child_types = [child["entity_type"] for child in thread_children]
        assert "run" in child_types
        assert "message" in child_types
        assert "tool_call" in child_types


@pytest.mark.unit
@pytest.mark.cache
class TestCascadingCachePurge:
    """Test cascading cache purge functionality."""

    @patch("ai_agent_core_engine.models.cache._get_cascading_cache_purger")
    def test_purge_entity_cascading_cache_calls_purger(self, mock_get_purger):
        """Test that purge_entity_cascading_cache calls the purger correctly."""
        mock_purger = MagicMock()
        mock_get_purger.return_value = mock_purger
        mock_logger = MagicMock()

        purge_entity_cascading_cache(
            logger=mock_logger,
            entity_type="agent",
            context_keys={"endpoint_id": "test-endpoint-001"},
            entity_keys={"agent_uuid": "agent-123"},
            cascade_depth=3,
        )

        mock_purger.purge_entity_cascading_cache.assert_called_once_with(
            mock_logger,
            "agent",
            context_keys={"endpoint_id": "test-endpoint-001"},
            entity_keys={"agent_uuid": "agent-123"},
            cascade_depth=3,
        )


@pytest.mark.unit
@pytest.mark.cache
class TestCacheNames:
    """Test cache naming conventions."""

    def test_get_cache_name_for_models(self):
        """Test cache name generation for models."""
        cache_name = Config.get_cache_name("models", "agent")
        assert cache_name == "ai_agent_core_engine.models.agent"

    def test_get_cache_name_for_queries(self):
        """Test cache name generation for queries."""
        cache_name = Config.get_cache_name("queries", "agent")
        assert cache_name == "ai_agent_core_engine.queries.agent"

    def test_cache_ttl_is_configured(self):
        """Test that cache TTL is configured."""
        ttl = Config.get_cache_ttl()
        assert isinstance(ttl, int)
        assert ttl > 0


# ============================================================================
# INTEGRATION TESTS
# ============================================================================


@pytest.mark.integration
@pytest.mark.cache
# @pytest.mark.skip(reason="demonstrating skipping")
# Helper class for mock agent instance
class MockAgentInstance:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
        self.attribute_values = kwargs.get("attribute_values", {})

    def update(self, actions=None):
        pass

    def save(self):
        pass

    def delete(self):
        pass


class TestCachePerformance:
    """Integration tests for cache performance."""

    def test_agent_cache_performance(self, cache_integration_setup):
        """Test agent cache functionality for performance improvements."""
        ai_agent_core_engine = cache_integration_setup["ai_agent_core_engine"]
        schema = cache_integration_setup["schema"]

        logger.info("Testing agent cache performance...")

        # Test data
        test_agent_uuid = "agent-1759120093-6b0d64ad"

        # Mock AgentModel to return data without hitting DB
        with patch("ai_agent_core_engine.models.agent.AgentModel") as MockAgentModel:
            # Setup mock agent instance
            agent_attrs = {
                "agent_uuid": test_agent_uuid,
                "agent_name": "Original Agent",
                "agent_description": "Original Description",
                "llm_provider": "openai",
                "llm_name": "gpt-4",
                "instructions": "Original instructions",
                "configuration": {},
                "mcp_server_uuids": [],
                "variables": [],
                "updated_by": "test",
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
                "status": "active",
                "endpoint_id": "test_endpoint",
                "agent_version_uuid": "v1",
            }

            mock_agent = MockAgentInstance(
                agent_uuid=test_agent_uuid,
                agent_name="Original Agent",
                attribute_values=agent_attrs,
                status="active"
            )

            # Setup AgentModel.get to return our mock agent
            MockAgentModel.get.return_value = mock_agent
            MockAgentModel.count.return_value = 1

            # Mock get_active_agent to avoid complex query logic
            with patch(
                "ai_agent_core_engine.models.agent._get_active_agent",
                return_value=mock_agent,
            ) as mock_get_active_agent:

                # Query for agent (this should cache the result)
                query = Utility.generate_graphql_operation("agent", "Query", schema)
                payload = {
                    "query": query,
                    "variables": {
                        "agentUuid": test_agent_uuid,
                    },
                }

                # First call - should hit database (mock) and cache the result
                logger.info("First agent query (cache miss expected)...")
                start_time = time.time()
                response1 = ai_agent_core_engine.ai_agent_core_graphql(**payload)
                first_call_time = time.time() - start_time
                logger.info(f"First call completed in {first_call_time:.4f} seconds")

                # Second call - should hit cache (faster)
                logger.info("Second agent query (cache hit expected)...")
                start_time = time.time()
                response2 = ai_agent_core_engine.ai_agent_core_graphql(**payload)
                second_call_time = time.time() - start_time
                logger.info(f"Second call completed in {second_call_time:.4f} seconds")

                # Verify responses are identical
                assert (
                    response1 == response2
                ), "Cached and non-cached responses should be identical"

                # Update the mock agent for the next call to simulate DB update
                updated_attrs = agent_attrs.copy()
                updated_attrs["agent_name"] = "Updated Agent"

                mock_agent_updated = MockAgentInstance(
                    agent_uuid=test_agent_uuid,
                    agent_name="Updated Agent",
                    attribute_values=updated_attrs,
                    status="active"
                )

                # Change what AgentModel.get returns
                MockAgentModel.get.return_value = mock_agent_updated
                mock_get_active_agent.return_value = mock_agent_updated

                # Test cache invalidation by updating the agent
                logger.info("Testing cache invalidation...")
                update_query = Utility.generate_graphql_operation(
                    "insertUpdateAgent", "Mutation", schema
                )
                update_payload = {
                    "query": update_query,
                    "variables": {
                        "agentUuid": test_agent_uuid,
                        "agentName": "Updated Agent",
                        "agentDescription": "Testing cache invalidation",
                        "llmProvider": "openai",
                        "llmName": "openai",
                        "instructions": "Test instructions for cache invalidation",
                        "configuration": {},
                        "status": "active",
                        "updatedBy": "cache_test",
                    },
                }

                # Mock saving/updating to avoid DB errors
                # We don't need logic here, just need it to not crash and to trigger cache purge decorator
                update_response = ai_agent_core_engine.ai_agent_core_graphql(
                    **update_payload
                )
                logger.info("Agent updated - cache should be invalidated")

                # Query again - should hit database (mock) again since cache was cleared
                logger.info("Third agent query after update (cache miss expected)...")
                start_time = time.time()
                response3 = ai_agent_core_engine.ai_agent_core_graphql(**payload)
                third_call_time = time.time() - start_time
                logger.info(f"Third call completed in {third_call_time:.4f} seconds")

                # The updated response should be different from the original
                assert (
                    response1 != response3
                ), "Response after update should be different"

        logger.info("Cache performance test completed successfully!")

    @pytest.mark.parametrize("agent_data", TEST_DATA.get("agents", []))
    def test_agent_cache_performance_parametrized(
        self, cache_integration_setup, agent_data
    ):
        """Test agent cache performance with parametrized data."""
        ai_agent_core_engine = cache_integration_setup["ai_agent_core_engine"]
        schema = cache_integration_setup["schema"]

        logger.info(f"Testing cache for agent: {agent_data.get('agentName')}")

        test_agent_uuid = "agent-param-" + str(time.time())

        # Map camelCase from JSON to snake_case for internal model
        agent_attrs = {
            "agent_uuid": test_agent_uuid,
            "agent_name": agent_data.get("agentName"),
            "agent_description": agent_data.get("agentDescription"),
            "llm_provider": agent_data.get("llmProvider"),
            "llm_name": agent_data.get("llmName"),
            "instructions": agent_data.get("instructions"),
            "configuration": agent_data.get("configuration", {}),
            "mcp_server_uuids": agent_data.get("mcpServerUuids", []),
            "variables": agent_data.get("variables", []),
            "num_of_messages": agent_data.get("numOfMessages"),
            "tool_call_role": agent_data.get("toolCallRole"),
            "status": agent_data.get("status"),
            "updated_by": agent_data.get("updatedBy"),
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
            "endpoint_id": "test_endpoint",
            "agent_version_uuid": "v1",
        }

        # Mock AgentModel
        with patch("ai_agent_core_engine.models.agent.AgentModel") as MockAgentModel:
            mock_agent = MockAgentInstance(
                agent_uuid=test_agent_uuid,
                agent_name=agent_attrs["agent_name"],
                attribute_values=agent_attrs,
                status=agent_attrs["status"],
            )

            MockAgentModel.get.return_value = mock_agent
            MockAgentModel.count.return_value = 1

            with patch(
                "ai_agent_core_engine.models.agent._get_active_agent",
                return_value=mock_agent,
            ) as mock_get_active_agent:

                # Query
                query = Utility.generate_graphql_operation("agent", "Query", schema)
                payload = {
                    "query": query,
                    "variables": {
                        "agentUuid": test_agent_uuid,
                    },
                }

                # First call (Cache Miss)
                logger.info("First query (cache miss expected)...")
                start_time = time.time()
                response1 = ai_agent_core_engine.ai_agent_core_graphql(**payload)
                logger.info(f"First call: {time.time() - start_time:.4f}s")

                # Second call (Cache Hit)
                logger.info("Second query (cache hit expected)...")
                start_time = time.time()
                response2 = ai_agent_core_engine.ai_agent_core_graphql(**payload)
                logger.info(f"Second call: {time.time() - start_time:.4f}s")

                assert response1 == response2

                # Update
                updated_attrs = agent_attrs.copy()
                updated_attrs["agent_name"] = agent_attrs["agent_name"] + " (Updated)"
                mock_agent_updated = MockAgentInstance(
                    agent_uuid=test_agent_uuid,
                    agent_name=updated_attrs["agent_name"],
                    attribute_values=updated_attrs,
                    status="active",
                )

                MockAgentModel.get.return_value = mock_agent_updated
                mock_get_active_agent.return_value = mock_agent_updated

                update_query = Utility.generate_graphql_operation(
                    "insertUpdateAgent", "Mutation", schema
                )
                update_payload = {
                    "query": update_query,
                    "variables": {
                        "agentUuid": test_agent_uuid,
                        "agentName": updated_attrs["agent_name"],
                        "llmProvider": agent_attrs["llm_provider"],
                        "llmName": agent_attrs["llm_name"],
                        "instructions": agent_attrs["instructions"],
                        "updatedBy": "cache_test",
                    },
                }

                ai_agent_core_engine.ai_agent_core_graphql(**update_payload)
                logger.info("Agent updated")

                # Third call (Cache Miss)
                logger.info("Third query (cache miss expected)...")
                start_time = time.time()
                response3 = ai_agent_core_engine.ai_agent_core_graphql(**payload)
                logger.info(f"Third call: {time.time() - start_time:.4f}s")

                assert response1 != response3

    def test_agent_cache_statistics(self, cache_integration_setup):
        """Test cache statistics and monitoring."""
        ai_agent_core_engine = cache_integration_setup["ai_agent_core_engine"]
        schema = cache_integration_setup["schema"]

        logger.info("Testing agent cache statistics...")

        # Import the cache function to access stats
        from ai_agent_core_engine.models.agent import get_agent_type

        # Check if cache stats are available
        if hasattr(get_agent_type, "cache_stats"):
            initial_stats = get_agent_type.cache_stats()
            logger.info(f"Initial cache stats: {initial_stats}")
        else:
            logger.info("Cache stats method not available")

        # Perform some agent queries to generate cache activity
        test_agent_uuid = "agent-1759120093-6b0d64ad"
        query = Utility.generate_graphql_operation("agent", "Query", schema)
        payload = {
            "query": query,
            "variables": {
                "agentUuid": test_agent_uuid,
            },
        }

        # Make multiple queries
        for i in range(3):
            logger.info(f"Cache test query #{i + 1}")
            response = ai_agent_core_engine.ai_agent_core_graphql(**payload)

        # Check final stats
        if hasattr(get_agent_type, "cache_stats"):
            final_stats = get_agent_type.cache_stats()
            logger.info(f"Final cache stats: {final_stats}")

        logger.info("Cache statistics test completed!")

    def test_agent_list_cache_performance(self, cache_integration_setup):
        """Test agent list cache functionality for performance improvements."""
        ai_agent_core_engine = cache_integration_setup["ai_agent_core_engine"]
        schema = cache_integration_setup["schema"]

        logger.info("Testing agent list cache performance...")

        # Query for agent list (this should cache the result)
        query = Utility.generate_graphql_operation("agentList", "Query", schema)
        payload = {
            "query": query,
            "variables": {
                "statuses": ["active"],
                "pageNumber": 1,
                "pageSize": 10,
            },
        }

        # First call - should hit database and cache the result
        logger.info("First agent list query (cache miss expected)...")
        start_time = time.time()
        response1 = ai_agent_core_engine.ai_agent_core_graphql(**payload)
        first_call_time = time.time() - start_time
        logger.info(f"First call completed in {first_call_time:.4f} seconds")

        # Second call - should hit cache (faster)
        logger.info("Second agent list query (cache hit expected)...")
        start_time = time.time()
        response2 = ai_agent_core_engine.ai_agent_core_graphql(**payload)
        second_call_time = time.time() - start_time
        logger.info(f"Second call completed in {second_call_time:.4f} seconds")

        # Verify responses are identical
        assert (
            response1 == response2
        ), "Cached and non-cached responses should be identical"

        # Verify cache improved performance (second call should be faster)
        if second_call_time < first_call_time:
            logger.info(
                f"Performance improvement: {((first_call_time - second_call_time) / first_call_time * 100):.1f}%"
            )
        else:
            logger.info(
                "Cache performance: Second call was not faster, cache might not be working for agent lists"
            )

        # Test cache invalidation by creating a new agent
        logger.info("Testing cache invalidation with new agent...")
        create_query = Utility.generate_graphql_operation(
            "insertUpdateAgent", "Mutation", schema
        )
        create_payload = {
            "query": create_query,
            "variables": {
                "agentName": f"Cache Test Agent List - {int(time.time())}",
                "agentDescription": "Testing cache invalidation for agent list",
                "llmProvider": "openai",
                "llmName": "openai",
                "instructions": "Test instructions for cache invalidation",
                "configuration": {},
                "status": "active",
                "updatedBy": "cache_test",
            },
        }

        # Create new agent (this should invalidate related caches)
        create_response = ai_agent_core_engine.ai_agent_core_graphql(**create_payload)
        logger.info("New agent created - related caches should be invalidated")

        # Query agent list again
        logger.info("Third agent list query after creating new agent...")
        start_time = time.time()
        response3 = ai_agent_core_engine.ai_agent_core_graphql(**payload)
        third_call_time = time.time() - start_time
        logger.info(f"Third call completed in {third_call_time:.4f} seconds")

        logger.info("Agent list cache performance test completed!")


@pytest.mark.integration
@pytest.mark.cache
# @pytest.mark.skip(reason="demonstrating skipping")
class TestUniversalCachePurging:
    """Integration tests for universal cache purging system."""

    def test_universal_cache_purging_system(self, cache_integration_setup):
        """Test the universal cache purging system with cascading functionality."""
        logger.info("Testing universal cache purging system...")

        # Import the universal cache purging functions
        from silvaengine_dynamodb_base.cache_utils import (
            CacheConfigResolvers,
            CascadingCachePurger,
        )

        purger = CascadingCachePurger(
            CacheConfigResolvers(
                get_cache_entity_config=Config.get_cache_entity_config,
                get_cache_relationships=Config.get_cache_relationships,
                queries_module_base="ai_agent_core_engine.queries",
            )
        )

        # Test clearing individual entity cache for different entity types
        logger.info("Testing individual entity cache clearing...")

        test_cases = [
            {
                "entity_type": "agent",
                "endpoint_id": "test_endpoint_123",
                "entity_keys": {"agent_version_uuid": "test_agent_version_123"},
            },
            {
                "entity_type": "thread",
                "endpoint_id": "test_endpoint_123",
                "entity_keys": {"thread_uuid": "test_thread_123"},
            },
            {
                "entity_type": "llm",
                "endpoint_id": "test_endpoint_123",
                "entity_keys": {"llm_provider": "openai", "llm_name": "gpt-4"},
            },
            {
                "entity_type": "prompt_template",
                "endpoint_id": "test_endpoint_123",
                "entity_keys": {"prompt_version_uuid": "test_prompt_version_123"},
            },
            {
                "entity_type": "fine_tuning_message",
                "endpoint_id": "test_endpoint_123",
                "entity_keys": {
                    "agent_uuid": "test_agent_123",
                    "message_uuid": "test_message_123",
                },
            },
            {
                "entity_type": "async_task",
                "endpoint_id": "test_endpoint_123",
                "entity_keys": {
                    "function_name": "test_function",
                    "async_task_uuid": "test_task_123",
                },
            },
            {
                "entity_type": "wizard_group",
                "endpoint_id": "test_endpoint_123",
                "entity_keys": {"wizard_group_uuid": "test_wizard_group_123"},
            },
            {
                "entity_type": "ui_component",
                "endpoint_id": "test_endpoint_123",
                "entity_keys": {
                    "ui_component_type": "form",
                    "ui_component_uuid": "test_ui_123",
                },
            },
        ]

        for test_case in test_cases:
            try:
                # Build entity_keys that include the context
                merged_keys = dict(test_case["entity_keys"])
                if test_case["endpoint_id"]:
                    merged_keys["endpoint_id"] = test_case["endpoint_id"]

                result = purger._clear_individual_entity_cache(
                    logger=logger,
                    entity_type=test_case["entity_type"],
                    entity_keys=merged_keys,
                )
                logger.info(
                    f"Individual cache clear for {test_case['entity_type']}: {'Success' if result else 'Failed/Not Available'}"
                )
            except Exception as e:
                logger.info(
                    f"Individual cache clear for {test_case['entity_type']} failed: {str(e)}"
                )

        # Test entity list cache clearing
        logger.info("Testing entity list cache clearing...")

        entity_types = [
            "agent",
            "thread",
            "run",
            "message",
            "tool_call",
            "llm",
            "flow_snippet",
            "mcp_server",
            "fine_tuning_message",
            "async_task",
            "element",
            "wizard",
            "wizard_group",
            "wizard_group_filter",
            "ui_component",
            "prompt_template",
        ]

        for entity_type in entity_types:
            try:
                result = purger._clear_entity_list_cache(logger, entity_type)
                logger.info(
                    f"List cache clear for {entity_type}: {'Success' if result else 'Failed/Not Available'}"
                )
            except Exception as e:
                logger.info(f"List cache clear for {entity_type} failed: {str(e)}")

        # Test universal cache purging with cascading
        logger.info("Testing universal cache purging with cascading...")

        purge_test_cases = [
            {
                "entity_type": "agent",
                "endpoint_id": "test_endpoint_123",
                "entity_keys": {
                    "agent_uuid": "test_agent_123",
                    "agent_version_uuid": "test_agent_version_123",
                },
                "cascade_depth": 2,
            },
            {
                "entity_type": "thread",
                "endpoint_id": "test_endpoint_123",
                "entity_keys": {"thread_uuid": "test_thread_123"},
                "cascade_depth": 2,
            },
            {
                "entity_type": "prompt_template",
                "endpoint_id": "test_endpoint_123",
                "entity_keys": {
                    "prompt_uuid": "test_prompt_123",
                    "prompt_version_uuid": "test_prompt_version_123",
                },
                "cascade_depth": 1,
            },
        ]

        for test_case in purge_test_cases:
            try:
                context_keys = (
                    {"endpoint_id": test_case["endpoint_id"]}
                    if test_case["endpoint_id"]
                    else None
                )
                result = purge_entity_cascading_cache(
                    logger=logger,
                    entity_type=test_case["entity_type"],
                    context_keys=context_keys,
                    entity_keys=test_case["entity_keys"],
                    cascade_depth=test_case["cascade_depth"],
                )

                logger.info(f"Universal purge for {test_case['entity_type']}:")
                logger.info(
                    f"  - Individual cache cleared: {result['individual_cache_cleared']}"
                )
                logger.info(f"  - List cache cleared: {result['list_cache_cleared']}")
                logger.info(
                    f"  - Child caches cleared: {result['total_child_caches_cleared']}"
                )
                logger.info(
                    f"  - Individual children cleared: {result['total_individual_children_cleared']}"
                )
                logger.info(f"  - Cascaded levels: {len(result['cascaded_levels'])}")
                logger.info(f"  - Errors: {len(result['errors'])}")

                if result["errors"]:
                    for error in result["errors"]:
                        logger.warning(f"    Error: {error}")

            except Exception as e:
                logger.error(
                    f"Universal purge for {test_case['entity_type']} failed: {str(e)}"
                )

        logger.info("Universal cache purging system test completed!")

    def test_cache_relationships_configuration(self, cache_integration_setup):
        """Test the cache relationships configuration system."""
        logger.info("Testing cache relationships configuration...")

        # Test getting cache relationships
        try:
            relationships = Config.get_cache_relationships()
            logger.info(
                f"Cache relationships loaded: {len(relationships)} parent entities"
            )

            # Test that all expected parent entities are present
            expected_parents = [
                "agent",
                "thread",
                "run",
                "llm",
                "flow_snippet",
                "mcp_server",
                "wizard_group",
                "wizard",
                "prompt_template",
            ]

            for parent in expected_parents:
                if parent in relationships:
                    children = relationships[parent]
                    logger.info(f"  {parent}: {len(children)} child relationship(s)")
                    for child in children:
                        logger.info(
                            f"    -> {child['entity_type']} (via {child['dependency_key']})"
                        )
                else:
                    logger.warning(f"  {parent}: No relationships configured")

            # Test getting children for specific entities
            agent_children = Config.get_entity_children("agent")
            logger.info(f"Agent has {len(agent_children)} direct child types")

            thread_children = Config.get_entity_children("thread")
            logger.info(f"Thread has {len(thread_children)} direct child types")

            # Verify expected relationships
            agent_child_types = [child["entity_type"] for child in agent_children]
            assert "thread" in agent_child_types, "Agent should have thread as child"
            assert (
                "fine_tuning_message" in agent_child_types
            ), "Agent should have fine_tuning_message as child"

            thread_child_types = [child["entity_type"] for child in thread_children]
            assert "run" in thread_child_types, "Thread should have run as child"
            assert (
                "message" in thread_child_types
            ), "Thread should have message as child"
            assert (
                "tool_call" in thread_child_types
            ), "Thread should have tool_call as child"

        except Exception as e:
            logger.error(f"Cache relationships configuration test failed: {str(e)}")
            raise

        logger.info("Cache relationships configuration test completed!")

    def test_new_entity_types_cache_support(self, cache_integration_setup):
        """Test cache support for newly added entity types."""
        logger.info("Testing cache support for new entity types...")

        # Test entity types that were recently added to the cache system
        new_entity_types = [
            "fine_tuning_message",
            "async_task",
            "element",
            "wizard",
            "wizard_group",
            "wizard_group_filter",
            "ui_component",
            "prompt_template",
        ]

        for entity_type in new_entity_types:
            logger.info(f"Testing {entity_type} cache support...")

            try:
                # Test that we can import the entity module
                from ai_agent_core_engine.models import utils

                module_name = f".{entity_type}"
                get_func_name = f"get_{entity_type}"

                try:
                    entity_module = __import__(
                        f"ai_agent_core_engine.models{module_name}",
                        fromlist=[get_func_name],
                    )
                    get_func = getattr(entity_module, get_func_name, None)

                    if get_func:
                        logger.info(f"  ✓ {entity_type} getter function found")

                        # Check if cache methods are available
                        has_cache_delete = hasattr(get_func, "cache_delete")
                        logger.info(
                            f"  {'✓' if has_cache_delete else '✗'} {entity_type} cache_delete available"
                        )

                    else:
                        logger.warning(f"  ✗ {entity_type} getter function not found")

                except ImportError as e:
                    logger.warning(f"  ✗ {entity_type} module import failed: {str(e)}")

            except Exception as e:
                logger.error(f"  ✗ {entity_type} test failed: {str(e)}")

        logger.info("New entity types cache support test completed!")

    def test_cascading_cache_invalidation_simulation(self, cache_integration_setup):
        """Simulate cascading cache invalidation scenarios."""
        logger.info("Testing cascading cache invalidation simulation...")

        # Simulate different cascading scenarios
        test_scenarios = [
            {
                "name": "Agent Update Cascade",
                "parent_entity_type": "agent",
                "endpoint_id": "test_endpoint_123",
                "parent_entity_keys": {
                    "agent_uuid": "test_agent_123",
                    "agent_version_uuid": "test_agent_version_123",
                },
                "cascade_depth": 3,
                "expected_children": ["thread", "fine_tuning_message"],
            },
            {
                "name": "Thread Deletion Cascade",
                "parent_entity_type": "thread",
                "endpoint_id": "test_endpoint_123",
                "parent_entity_keys": {"thread_uuid": "test_thread_123"},
                "cascade_depth": 2,
                "expected_children": [
                    "run",
                    "message",
                    "tool_call",
                    "fine_tuning_message",
                ],
            },
            {
                "name": "Prompt Template Update Cascade",
                "parent_entity_type": "prompt_template",
                "endpoint_id": "test_endpoint_123",
                "parent_entity_keys": {
                    "prompt_uuid": "test_prompt_123",
                    "prompt_version_uuid": "test_prompt_version_123",
                },
                "cascade_depth": 2,
                "expected_children": ["ui_component", "flow_snippet"],
            },
            {
                "name": "Wizard Group Cascade",
                "parent_entity_type": "wizard_group",
                "endpoint_id": "test_endpoint_123",
                "parent_entity_keys": {"wizard_group_uuid": "test_wizard_group_123"},
                "cascade_depth": 2,
                "expected_children": ["wizard"],
            },
        ]

        for scenario in test_scenarios:
            logger.info(f"Running scenario: {scenario['name']}")

            try:
                context_keys = (
                    {"endpoint_id": scenario["endpoint_id"]}
                    if scenario["endpoint_id"]
                    else None
                )
                result = purge_entity_cascading_cache(
                    logger=logger,
                    entity_type=scenario["parent_entity_type"],
                    context_keys=context_keys,
                    entity_keys=scenario["parent_entity_keys"],
                    cascade_depth=scenario["cascade_depth"],
                )

                logger.info(f"  Results for {scenario['name']}:")
                logger.info(f"    - Cascaded levels: {len(result['cascaded_levels'])}")
                logger.info(
                    f"    - Total child caches cleared: {result['total_child_caches_cleared']}"
                )
                logger.info(
                    f"    - Total individual children cleared: {result['total_individual_children_cleared']}"
                )
                logger.info(
                    f"    - Individual cache cleared: {result.get('individual_cache_cleared', False)}"
                )
                logger.info(
                    f"    - List cache cleared: {result.get('list_cache_cleared', False)}"
                )
                logger.info(f"    - Errors: {len(result['errors'])}")

                # Log details of each cascaded level
                for i, level in enumerate(result["cascaded_levels"]):
                    logger.info(
                        f"    Level {level['level']} (parent: {level['parent_entity']}):"
                    )
                    for child_cache in level.get("child_caches_cleared", []):
                        logger.info(
                            f"      - Cleared {child_cache['entity_type']} list cache"
                        )
                    for individual_child in level.get(
                        "individual_children_cleared", []
                    ):
                        logger.info(
                            f"      - Cleared {individual_child['count']} individual {individual_child['entity_type']} caches"
                        )

                # Log any errors
                for error in result["errors"]:
                    logger.warning(f"    Error: {error}")

            except Exception as e:
                logger.error(f"Scenario {scenario['name']} failed: {str(e)}")

        logger.info("Cascading cache invalidation simulation completed!")


if __name__ == "__main__":
    import sys

    sys.exit(pytest.main([__file__, "-v"] + sys.argv[1:]))
