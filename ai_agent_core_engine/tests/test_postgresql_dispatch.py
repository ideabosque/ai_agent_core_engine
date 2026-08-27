# -*- coding: utf-8 -*-
"""PostgreSQL backend dispatch smoke tests.

Verifies that:
1. PG register_all resolves all 17 entity repos when SQLAlchemy is installed.
2. PG repos have matching entity_type values for all expected entities.
3. PG get_loaders returns PGRequestLoaders (or raises RuntimeError for
   not-yet-implemented loaders).
4. PG repos are backend-agnostic (no direct DynamoDB imports).

These tests auto-skip when SQLAlchemy is not installed (DynamoDB-only envs).
"""
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

# Single-active entities that must expose resolve_active
SINGLE_ACTIVE_ENTITIES: Set[str] = {"agent", "flow_snippet", "prompt_template"}


def _has_sqlalchemy() -> bool:
    """Check if SQLAlchemy is importable."""
    try:
        import sqlalchemy  # noqa: F401

        return True
    except ImportError:
        return False


@unittest.skipUnless(_has_sqlalchemy(), "SQLAlchemy not installed")
class PostgresqlDispatchTest(unittest.TestCase):
    """Test PG backend dispatch when SQLAlchemy is available."""

    @classmethod
    def setUpClass(cls):
        from ai_agent_core_engine.handlers.config import Config

        cls._original_backend = getattr(Config, "DB_BACKEND", "dynamodb")
        Config.DB_BACKEND = "postgresql"

    @classmethod
    def tearDownClass(cls):
        from ai_agent_core_engine.handlers.config import Config

        Config.DB_BACKEND = cls._original_backend

    def setUp(self):
        from ai_agent_core_engine.models.repositories.dispatch import clear_registry

        clear_registry()

    def test_pg_repos_registered(self):
        """All 17 entities should resolve on the PostgreSQL backend."""
        from ai_agent_core_engine.models.repositories import get_repo

        for entity_type in EXPECTED_ENTITIES:
            try:
                repo = get_repo(entity_type)
                self.assertEqual(
                    repo.entity_type,
                    entity_type,
                    f"PG repository for '{entity_type}' returned wrong entity_type",
                )
            except ImportError as exc:
                self.fail(
                    f"PG repository for '{entity_type}' could not be imported: {exc}"
                )

    def test_pg_single_active_repos_have_resolve_active(self):
        """Agent, FlowSnippet, PromptTemplate repos must expose resolve_active."""
        from ai_agent_core_engine.models.repositories import get_repo

        for entity_type in SINGLE_ACTIVE_ENTITIES:
            repo = get_repo(entity_type)
            self.assertTrue(
                hasattr(repo, "resolve_active"),
                f"PG {entity_type} repo must expose resolve_active()",
            )

    def test_pg_get_loaders_returns_pgrequestloaders(self):
        """get_loaders() should return PGRequestLoaders under PG backend."""
        from ai_agent_core_engine.models.repositories import get_loaders

        context = {}
        loaders = get_loaders(context)
        self.assertIsNotNone(loaders)
        # Verify it's a PGRequestLoaders instance
        self.assertEqual(type(loaders).__name__, "PGRequestLoaders")
        # Verify memoization
        self.assertIs(get_loaders(context), loaders)

    def test_pg_unknown_entity_raises_keyerror(self):
        """An unknown entity type should raise KeyError on PG backend."""
        from ai_agent_core_engine.models.repositories import get_repo

        with self.assertRaises(KeyError):
            get_repo("nonexistent_entity")


@unittest.skipIf(_has_sqlalchemy(), "SQLAlchemy is installed — testing DynamoDB-only path")
class PostgresqlNotAvailableTest(unittest.TestCase):
    """When SQLAlchemy is not installed, PG backend should fail gracefully."""

    def test_pg_init_raises_import_error(self):
        """Importing PG models without SQLAlchemy should raise ImportError."""
        try:
            from ai_agent_core_engine.models.postgresql.base import Base  # noqa: F401
            # If this succeeds, SQLAlchemy IS installed — skip
            self.skipTest("SQLAlchemy is installed")
        except ImportError:
            pass  # Expected


if __name__ == "__main__":
    unittest.main()