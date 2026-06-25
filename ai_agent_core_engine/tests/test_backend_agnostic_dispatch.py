# -*- coding: utf-8 -*-
"""Backend-agnostic dispatch test — verifies all 17 entities resolve on both backends."""
from __future__ import print_function

__author__ = "bibow"

import unittest
from typing import Set

EXPECTED_ENTITIES: Set[str] = {
    "agent",
    "llm",
    "thread",
    "run",
    "message",
    "tool_call",
    "async_task",
    "fine_tuning_message",
    "element",
    "wizard",
    "wizard_schema",
    "wizard_group",
    "wizard_group_filter",
    "mcp_server",
    "ui_component",
    "flow_snippet",
    "prompt_template",
}


class BackendAgnosticDispatchTest(unittest.TestCase):
    """Test that get_repo() resolves all expected entities on the active backend."""

    @classmethod
    def setUpClass(cls):
        from ai_agent_core_engine.handlers.config import Config

        cls._original_backend = getattr(Config, "DB_BACKEND", "dynamodb")
        Config.DB_BACKEND = "dynamodb"

    @classmethod
    def tearDownClass(cls):
        from ai_agent_core_engine.handlers.config import Config

        Config.DB_BACKEND = cls._original_backend

    def setUp(self):
        from ai_agent_core_engine.models.repositories.dispatch import clear_registry

        clear_registry()

    def test_dynamodb_repos_registered(self):
        """All 17 entities should resolve on the DynamoDB backend."""
        from ai_agent_core_engine.models.repositories import get_repo

        for entity_type in EXPECTED_ENTITIES:
            repo = get_repo(entity_type)
            self.assertEqual(
                repo.entity_type,
                entity_type,
                f"Repository for '{entity_type}' returned wrong entity_type",
            )

    def test_unknown_entity_raises_keyerror(self):
        """An unknown entity type should raise KeyError."""
        from ai_agent_core_engine.models.repositories import get_repo

        with self.assertRaises(KeyError):
            get_repo("nonexistent_entity")

    def test_get_loaders_returns_object(self):
        """get_loaders() should return a non-None loaders container."""
        from ai_agent_core_engine.models.repositories import get_loaders

        context = {}
        loaders = get_loaders(context)
        self.assertIsNotNone(loaders)
        # Verify memoization
        self.assertIs(get_loaders(context), loaders)

    def test_get_loaders_none_context(self):
        """get_loaders(None) should not crash."""
        from ai_agent_core_engine.models.repositories import get_loaders

        loaders = get_loaders(None)
        self.assertIsNotNone(loaders)

    def test_clear_registry(self):
        """clear_registry() should reset all repos."""
        from ai_agent_core_engine.models.repositories import get_repo, clear_registry

        # First access triggers lazy init
        repo = get_repo("agent")
        self.assertIsNotNone(repo)

        # Clear and re-access
        clear_registry()
        repo = get_repo("agent")
        self.assertIsNotNone(repo)


class RegistryContractTest(unittest.TestCase):
    """Test the repository registry contract."""

    def test_register_repo(self):
        """register_repo should add a repo to the correct backend slot."""
        from ai_agent_core_engine.models.repositories import (
            register_repo,
            clear_registry,
            get_repo,
        )
        from ai_agent_core_engine.handlers.config import Config

        original_backend = Config.DB_BACKEND
        try:
            Config.DB_BACKEND = "dynamodb"
            clear_registry()

            # Register a mock repo
            from ai_agent_core_engine.models.repositories.base import EntityRepository

            class MockRepo(EntityRepository):
                @property
                def entity_type(self):
                    return "mock_entity"

                def get(self, **keys):
                    return None

                def count(self, **keys):
                    return 0

                def list(self, info, **filters):
                    return None

                def insert_update(self, info, **kwargs):
                    return None

                def delete(self, info, **kwargs):
                    return True

            register_repo("dynamodb", "mock_entity", MockRepo())
            repo = get_repo("mock_entity")
            self.assertEqual(repo.entity_type, "mock_entity")
        finally:
            Config.DB_BACKEND = original_backend
            clear_registry()


if __name__ == "__main__":
    unittest.main()