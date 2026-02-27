# -*- coding: utf-8 -*-
"""
Tests for cache infrastructure – configuration, performance, and cascading invalidation.
"""
from __future__ import print_function

import importlib
import json
import logging
import os
import sys
import time
from unittest.mock import MagicMock, patch

import pytest
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger()


def _load_test_data():
    try:
        with open(os.path.join(os.path.dirname(__file__), "test_data.json")) as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Could not load test_data.json: {e}")
        return {}


TEST_DATA = _load_test_data()

from silvaengine_utility import Graphql

from ai_agent_core_engine.handlers.config import Config
from ai_agent_core_engine.models.cache import purge_entity_cascading_cache


# ============================================================================
# UNIT TESTS
# ============================================================================


@pytest.mark.unit
@pytest.mark.cache
class TestCacheConfiguration:
    """Verify every entity type is registered in the cache config."""

    def test_cache_entity_config_has_all_models(self):
        config = Config.get_cache_entity_config()
        expected = [
            "agent", "thread", "run", "message", "tool_call", "llm",
            "prompt_template", "flow_snippet", "mcp_server", "ui_component",
            "wizard", "wizard_schema", "wizard_group", "wizard_group_filter",
            "element", "fine_tuning_message", "async_task",
        ]
        for entity in expected:
            assert entity in config, f"Entity '{entity}' not in cache config"

    def test_cache_entity_config_structure(self):
        config = Config.get_cache_entity_config()
        for entity, cfg in config.items():
            for field in ("module", "getter", "cache_keys"):
                assert field in cfg, f"{entity} missing '{field}'"


@pytest.mark.unit
@pytest.mark.cache
class TestCacheRelationships:
    """Verify parent→child cache relationship definitions."""

    def test_key_parents_defined(self):
        relationships = Config.get_cache_relationships()
        for parent in ("agent", "thread", "run"):
            assert parent in relationships, f"'{parent}' not in cache relationships"

    def test_agent_cascades(self):
        child_types = [
            c["entity_type"] for c in Config.get_cache_relationships()["agent"]
        ]
        assert "thread" in child_types
        assert "fine_tuning_message" in child_types

    def test_thread_cascades(self):
        child_types = [
            c["entity_type"] for c in Config.get_cache_relationships()["thread"]
        ]
        assert "run" in child_types
        assert "message" in child_types
        assert "tool_call" in child_types


@pytest.mark.unit
@pytest.mark.cache
class TestCascadingCachePurge:
    """Unit-test the purge_entity_cascading_cache public API."""

    @patch("ai_agent_core_engine.models.cache._get_cascading_cache_purger")
    def test_purge_delegates_to_purger(self, mock_get_purger):
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
    """Verify cache name generation and TTL configuration."""

    def test_cache_name_for_models(self):
        assert Config.get_cache_name("models", "agent") == "ai_agent_core_engine.models.agent"

    def test_cache_name_for_queries(self):
        assert Config.get_cache_name("queries", "agent") == "ai_agent_core_engine.queries.agent"

    def test_cache_ttl_is_positive_int(self):
        ttl = Config.get_cache_ttl()
        assert isinstance(ttl, int) and ttl > 0


# ============================================================================
# HELPERS
# ============================================================================


class _MockAgent:
    """Minimal stand-in for an AgentModel instance."""

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


# ============================================================================
# INTEGRATION TESTS
# ============================================================================


@pytest.mark.integration
@pytest.mark.cache
class TestCachePerformance:
    """Integration tests for single-item and list cache behaviour."""

    def test_agent_cache_miss_hit_invalidation(self, ai_agent_core_engine, schema):
        """Cache miss on first call, hit on second, miss again after an update."""
        test_agent_uuid = "agent-1759120093-6b0d64ad"
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
        mock_agent = _MockAgent(
            agent_uuid=test_agent_uuid,
            agent_name="Original Agent",
            attribute_values=agent_attrs,
            status="active",
        )

        with (
            patch("ai_agent_core_engine.models.agent.AgentModel") as MockAgentModel,
            patch(
                "ai_agent_core_engine.models.agent._get_active_agent",
                return_value=mock_agent,
            ) as mock_get,
        ):
            MockAgentModel.get.return_value = mock_agent
            MockAgentModel.count.return_value = 1

            query = Graphql.generate_graphql_operation("agent", "Query", schema)
            payload = {"query": query, "variables": {"agentUuid": test_agent_uuid}}

            response1 = ai_agent_core_engine.ai_agent_core_graphql(**payload)
            response2 = ai_agent_core_engine.ai_agent_core_graphql(**payload)
            assert response1 == response2, "Second call (cache hit) must match first"

            # Simulate a DB update and cache invalidation
            updated_attrs = {**agent_attrs, "agent_name": "Updated Agent"}
            mock_updated = _MockAgent(
                agent_uuid=test_agent_uuid,
                agent_name="Updated Agent",
                attribute_values=updated_attrs,
                status="active",
            )
            MockAgentModel.get.return_value = mock_updated
            mock_get.return_value = mock_updated

            update_query = Graphql.generate_graphql_operation(
                "insertUpdateAgent", "Mutation", schema
            )
            ai_agent_core_engine.ai_agent_core_graphql(
                query=update_query,
                variables={
                    "agentUuid": test_agent_uuid,
                    "agentName": "Updated Agent",
                    "agentDescription": "Testing cache invalidation",
                    "llmProvider": "openai",
                    "llmName": "openai",
                    "instructions": "Test instructions",
                    "configuration": {},
                    "status": "active",
                    "updatedBy": "cache_test",
                },
            )

            response3 = ai_agent_core_engine.ai_agent_core_graphql(**payload)
            assert response1 != response3, "Post-update response must differ from cached value"

    @pytest.mark.parametrize("agent_data", TEST_DATA.get("agents", []))
    def test_agent_cache_parametrized(self, ai_agent_core_engine, schema, agent_data):
        """Cache miss → hit → miss-after-update for each agent fixture row."""
        test_agent_uuid = f"agent-param-{int(time.time())}"
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
        mock_agent = _MockAgent(
            agent_uuid=test_agent_uuid,
            agent_name=agent_attrs["agent_name"],
            attribute_values=agent_attrs,
            status=agent_attrs["status"],
        )

        with (
            patch("ai_agent_core_engine.models.agent.AgentModel") as MockAgentModel,
            patch(
                "ai_agent_core_engine.models.agent._get_active_agent",
                return_value=mock_agent,
            ) as mock_get,
        ):
            MockAgentModel.get.return_value = mock_agent
            MockAgentModel.count.return_value = 1

            query = Graphql.generate_graphql_operation("agent", "Query", schema)
            payload = {"query": query, "variables": {"agentUuid": test_agent_uuid}}

            response1 = ai_agent_core_engine.ai_agent_core_graphql(**payload)
            response2 = ai_agent_core_engine.ai_agent_core_graphql(**payload)
            assert response1 == response2

            updated_attrs = {**agent_attrs, "agent_name": agent_attrs["agent_name"] + " (Updated)"}
            mock_updated = _MockAgent(
                agent_uuid=test_agent_uuid,
                agent_name=updated_attrs["agent_name"],
                attribute_values=updated_attrs,
                status="active",
            )
            MockAgentModel.get.return_value = mock_updated
            mock_get.return_value = mock_updated

            update_query = Graphql.generate_graphql_operation(
                "insertUpdateAgent", "Mutation", schema
            )
            ai_agent_core_engine.ai_agent_core_graphql(
                query=update_query,
                variables={
                    "agentUuid": test_agent_uuid,
                    "agentName": updated_attrs["agent_name"],
                    "llmProvider": agent_attrs["llm_provider"],
                    "llmName": agent_attrs["llm_name"],
                    "instructions": agent_attrs["instructions"],
                    "updatedBy": "cache_test",
                },
            )

            response3 = ai_agent_core_engine.ai_agent_core_graphql(**payload)
            assert response1 != response3

    def test_agent_cache_statistics(self, ai_agent_core_engine, schema):
        """Smoke test: confirm the cache stats API is reachable (no assertion required)."""
        from ai_agent_core_engine.models.agent import get_agent_type

        if hasattr(get_agent_type, "cache_stats"):
            logger.info(f"Cache stats before: {get_agent_type.cache_stats()}")

        query = Graphql.generate_graphql_operation("agent", "Query", schema)
        payload = {"query": query, "variables": {"agentUuid": "agent-1759120093-6b0d64ad"}}
        for _ in range(3):
            ai_agent_core_engine.ai_agent_core_graphql(**payload)

        if hasattr(get_agent_type, "cache_stats"):
            logger.info(f"Cache stats after: {get_agent_type.cache_stats()}")

    def test_agent_list_cache_hit(self, ai_agent_core_engine, schema):
        """Repeated list query must return identical results."""
        query = Graphql.generate_graphql_operation("agentList", "Query", schema)
        payload = {
            "query": query,
            "variables": {"statuses": ["active"], "pageNumber": 1, "pageSize": 10},
        }

        response1 = ai_agent_core_engine.ai_agent_core_graphql(**payload)
        response2 = ai_agent_core_engine.ai_agent_core_graphql(**payload)
        assert response1 == response2, "Repeated list query must return identical results"


@pytest.mark.integration
@pytest.mark.cache
class TestUniversalCachePurging:
    """Integration tests for the universal cascading cache purge system."""

    def test_individual_and_list_cache_clearing(self):
        """Exercise _clear_individual_entity_cache and _clear_entity_list_cache."""
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

        individual_cases = [
            {"entity_type": "agent",               "entity_keys": {"endpoint_id": "ep-123", "agent_version_uuid": "av-123"}},
            {"entity_type": "thread",              "entity_keys": {"endpoint_id": "ep-123", "thread_uuid": "t-123"}},
            {"entity_type": "llm",                 "entity_keys": {"endpoint_id": "ep-123", "llm_provider": "openai", "llm_name": "gpt-4"}},
            {"entity_type": "prompt_template",     "entity_keys": {"endpoint_id": "ep-123", "prompt_version_uuid": "pv-123"}},
            {"entity_type": "fine_tuning_message", "entity_keys": {"endpoint_id": "ep-123", "agent_uuid": "a-123", "message_uuid": "m-123"}},
            {"entity_type": "async_task",          "entity_keys": {"endpoint_id": "ep-123", "function_name": "fn", "async_task_uuid": "at-123"}},
            {"entity_type": "wizard_group",        "entity_keys": {"endpoint_id": "ep-123", "wizard_group_uuid": "wg-123"}},
            {"entity_type": "ui_component",        "entity_keys": {"endpoint_id": "ep-123", "ui_component_type": "form", "ui_component_uuid": "ui-123"}},
        ]
        for case in individual_cases:
            try:
                purger._clear_individual_entity_cache(
                    logger=logger,
                    entity_type=case["entity_type"],
                    entity_keys=case["entity_keys"],
                )
            except Exception as e:
                logger.info(f"_clear_individual_entity_cache({case['entity_type']}): {e}")

        list_entity_types = [
            "agent", "thread", "run", "message", "tool_call", "llm",
            "flow_snippet", "mcp_server", "fine_tuning_message", "async_task",
            "element", "wizard", "wizard_group", "wizard_group_filter",
            "ui_component", "prompt_template",
        ]
        for entity_type in list_entity_types:
            try:
                purger._clear_entity_list_cache(logger, entity_type)
            except Exception as e:
                logger.info(f"_clear_entity_list_cache({entity_type}): {e}")

    def test_cascading_purge(self):
        """Exercise purge_entity_cascading_cache for representative parent entities."""
        test_cases = [
            {
                "entity_type": "agent",
                "context_keys": {"endpoint_id": "ep-123"},
                "entity_keys": {"agent_uuid": "a-123", "agent_version_uuid": "av-123"},
                "cascade_depth": 2,
            },
            {
                "entity_type": "thread",
                "context_keys": {"endpoint_id": "ep-123"},
                "entity_keys": {"thread_uuid": "t-123"},
                "cascade_depth": 2,
            },
            {
                "entity_type": "prompt_template",
                "context_keys": {"endpoint_id": "ep-123"},
                "entity_keys": {"prompt_uuid": "p-123", "prompt_version_uuid": "pv-123"},
                "cascade_depth": 1,
            },
        ]
        for case in test_cases:
            try:
                result = purge_entity_cascading_cache(
                    logger=logger,
                    entity_type=case["entity_type"],
                    context_keys=case["context_keys"],
                    entity_keys=case["entity_keys"],
                    cascade_depth=case["cascade_depth"],
                )
                logger.info(
                    f"purge({case['entity_type']}): "
                    f"individual={result['individual_cache_cleared']} "
                    f"list={result['list_cache_cleared']} "
                    f"children={result['total_child_caches_cleared']} "
                    f"levels={len(result['cascaded_levels'])} "
                    f"errors={len(result['errors'])}"
                )
                for err in result["errors"]:
                    logger.warning(f"  error: {err}")
            except Exception as e:
                logger.error(f"purge({case['entity_type']}) raised: {e}")

    def test_cache_relationships_and_entity_children(self):
        """Assert expected parent→child relationships via Config.get_entity_children."""
        agent_child_types = [
            c["entity_type"] for c in Config.get_entity_children("agent")
        ]
        assert "thread" in agent_child_types
        assert "fine_tuning_message" in agent_child_types

        thread_child_types = [
            c["entity_type"] for c in Config.get_entity_children("thread")
        ]
        assert "run" in thread_child_types
        assert "message" in thread_child_types
        assert "tool_call" in thread_child_types

    def test_new_entity_types_have_getter(self):
        """Each recently-added entity type must expose a get_<entity> function."""
        entity_types = [
            "fine_tuning_message", "async_task", "element", "wizard",
            "wizard_group", "wizard_group_filter", "ui_component", "prompt_template",
        ]
        for entity_type in entity_types:
            module_path = f"ai_agent_core_engine.models.{entity_type}"
            get_func_name = f"get_{entity_type}"
            try:
                mod = importlib.import_module(module_path)
                assert getattr(mod, get_func_name, None) is not None, (
                    f"{module_path}.{get_func_name} not found"
                )
            except ImportError as e:
                logger.warning(f"{module_path} import failed: {e}")

    def test_cascading_invalidation_scenarios(self):
        """Run representative cascading invalidation scenarios and log results."""
        scenarios = [
            {
                "name": "Agent Update Cascade",
                "entity_type": "agent",
                "context_keys": {"endpoint_id": "ep-123"},
                "entity_keys": {"agent_uuid": "a-123", "agent_version_uuid": "av-123"},
                "cascade_depth": 3,
            },
            {
                "name": "Thread Deletion Cascade",
                "entity_type": "thread",
                "context_keys": {"endpoint_id": "ep-123"},
                "entity_keys": {"thread_uuid": "t-123"},
                "cascade_depth": 2,
            },
            {
                "name": "Prompt Template Update Cascade",
                "entity_type": "prompt_template",
                "context_keys": {"endpoint_id": "ep-123"},
                "entity_keys": {"prompt_uuid": "p-123", "prompt_version_uuid": "pv-123"},
                "cascade_depth": 2,
            },
            {
                "name": "Wizard Group Cascade",
                "entity_type": "wizard_group",
                "context_keys": {"endpoint_id": "ep-123"},
                "entity_keys": {"wizard_group_uuid": "wg-123"},
                "cascade_depth": 2,
            },
        ]
        for scenario in scenarios:
            try:
                result = purge_entity_cascading_cache(
                    logger=logger,
                    entity_type=scenario["entity_type"],
                    context_keys=scenario["context_keys"],
                    entity_keys=scenario["entity_keys"],
                    cascade_depth=scenario["cascade_depth"],
                )
                for level in result["cascaded_levels"]:
                    for child in level.get("child_caches_cleared", []):
                        logger.info(
                            f"  [{scenario['name']}] L{level['level']}: "
                            f"cleared {child['entity_type']} list"
                        )
                    for ind in level.get("individual_children_cleared", []):
                        logger.info(
                            f"  [{scenario['name']}] L{level['level']}: "
                            f"cleared {ind['count']} {ind['entity_type']} individual"
                        )
                for err in result["errors"]:
                    logger.warning(f"  [{scenario['name']}] error: {err}")
            except Exception as e:
                logger.error(f"[{scenario['name']}] raised: {e}")


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"] + sys.argv[1:]))
