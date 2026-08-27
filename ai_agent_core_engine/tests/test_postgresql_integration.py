# -*- coding: utf-8 -*-
"""PostgreSQL integration tests against a live database.

Tests CRUD operations, single-active invariant, and RLS tenant isolation.
Auto-skips when DATABASE_URL / PG_HOST is not available.
"""
from __future__ import print_function

__author__ = "bibow"

import os
import unittest
import uuid as uuidlib
from typing import Any, Dict, Optional

try:
    import sqlalchemy
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import scoped_session, sessionmaker
    HAS_SQLALCHEMY = True
    
    # Set the table prefix BEFORE any PG model imports so declared_attr
    # __tablename__ resolves correctly. This must happen at module load
    # time, before repositories or models are imported by other tests.
    from ai_agent_core_engine.models.postgresql.base import Base
    Base.table_prefix = os.getenv("PG_TABLE_PREFIX", "aace_")
except ImportError:
    HAS_SQLALCHEMY = False

PG_HOST = os.getenv("PG_HOST", "localhost")
PG_PORT = os.getenv("PG_PORT", "5432")
PG_USER = os.getenv("PG_USER_RLS", "aace_app")  # Non-superuser for RLS tests
PG_PASSWORD = os.getenv("PG_PASSWORD_RLS", "aace_app")
PG_DB = os.getenv("PG_DB", "silvaengine")
DATABASE_URL = os.getenv("DATABASE_URL")
HAS_DB = bool(DATABASE_URL or (PG_HOST and PG_PASSWORD and PG_PASSWORD != "***"))


@unittest.skipUnless(HAS_SQLALCHEMY and HAS_DB, "SQLAlchemy + live PG required")
class PostgresqlIntegrationTest(unittest.TestCase):
    """Integration tests against a live PostgreSQL database."""

    @classmethod
    def setUpClass(cls):
        from ai_agent_core_engine.handlers.config import Config
        from ai_agent_core_engine.models.postgresql.base import Base

        cls._original_backend = getattr(Config, "DB_BACKEND", "dynamodb")
        cls._original_session = getattr(Config, "db_session", None)

        # Always use the non-superuser aace_app role for RLS tests,
        # even if DATABASE_URL is set (it points to the superuser).
        url = f"postgresql+psycopg2://{PG_USER}:{PG_PASSWORD}@{PG_HOST}:{PG_PORT}/{PG_DB}"
        cls.engine = create_engine(url, pool_pre_ping=True)
        cls.db_session = scoped_session(sessionmaker(bind=cls.engine))

        Config.DB_BACKEND = "postgresql"
        Config.db_session = cls.db_session
        Config.PG_TABLE_PREFIX = os.getenv("PG_TABLE_PREFIX", "aace_")
        Base.table_prefix = Config.PG_TABLE_PREFIX

        from ai_agent_core_engine.models.postgresql import utils as pg_utils
        pg_utils._import_all_models()

    @classmethod
    def tearDownClass(cls):
        from ai_agent_core_engine.handlers.config import Config

        Config.DB_BACKEND = cls._original_backend
        Config.db_session = cls._original_session
        cls.db_session.remove()
        cls.engine.dispose()

    def setUp(self):
        from ai_agent_core_engine.models.repositories.dispatch import clear_registry
        clear_registry()

        self.pk_a = f"test_endpoint_a#{uuidlib.uuid4().hex[:8]}"
        self.pk_b = f"test_endpoint_b#{uuidlib.uuid4().hex[:8]}"

    def _set_tenant(self, partition_key: str) -> None:
        """Set RLS tenant context on the scoped session.

        Uses SET (session-level, not transaction-scoped) so the context
        persists across commits within the same session. Use _reset_session()
        to clear it.
        """
        self.db_session.execute(
            text("SET app.tenant_id = :tenant"),
            {"tenant": partition_key},
        )
        self.db_session.commit()

    def _reset_session(self) -> None:
        """Remove the scoped session (drops RLS context)."""
        self.db_session.remove()

    def test_llm_crud(self):
        """LLM is a global registry — insert, get, delete without RLS."""
        from ai_agent_core_engine.models.repositories import get_repo

        provider = f"test_provider_{uuidlib.uuid4().hex[:8]}"
        name = f"test_model_{uuidlib.uuid4().hex[:8]}"

        try:
            self._set_tenant(self.pk_a)  # RLS context needed even for global tables due to FORCE
            # Actually LLM has no RLS, so no tenant needed
            self._reset_session()

            # LLM is global — no RLS, no tenant context needed
            result = get_repo("llm").insert_update(
                None,
                llm_provider=provider,
                llm_name=name,
                module_name="openai",
                class_name="OpenAIClient",
                updated_by="test",
            )
            self.assertIsNotNone(result)
            self.assertEqual(result["llm_provider"], provider)

            data = get_repo("llm").get(llm_provider=provider, llm_name=name)
            self.assertIsNotNone(data)
            self.assertEqual(data["module_name"], "openai")

            count = get_repo("llm").count(llm_provider=provider, llm_name=name)
            self.assertEqual(count, 1)
        finally:
            try:
                get_repo("llm").delete(None, llm_provider=provider, llm_name=name)
            except Exception:
                self.db_session.rollback()
            self._reset_session()

    def test_agent_crud_with_rls(self):
        """Agent CRUD with RLS — tenant A can't see tenant B's agents."""
        from ai_agent_core_engine.models.repositories import get_repo

        agent_uuid = f"agent-{uuidlib.uuid4().hex[:12]}"
        version_uuid = f"v-{uuidlib.uuid4().hex[:12]}"

        try:
            # Insert as tenant A
            self._set_tenant(self.pk_a)
            result = get_repo("agent").insert_update(
                None,
                partition_key=self.pk_a,
                agent_version_uuid=version_uuid,
                agent_uuid=agent_uuid,
                agent_name="Test Agent A",
                llm_provider="openai",
                llm_name="gpt-4",
                updated_by="test",
                status="active",
            )
            self.assertIsNotNone(result)
            self.assertEqual(result["agent_name"], "Test Agent A")
            self._reset_session()

            # Read as tenant A — should find it
            self._set_tenant(self.pk_a)
            data = get_repo("agent").get(
                partition_key=self.pk_a,
                agent_version_uuid=version_uuid,
            )
            self.assertIsNotNone(data, "Tenant A should see its own agent")
            self._reset_session()

            # Read as tenant B — should NOT find it (RLS blocks)
            self._set_tenant(self.pk_b)
            data = get_repo("agent").get(
                partition_key=self.pk_a,
                agent_version_uuid=version_uuid,
            )
            self.assertIsNone(data, "Tenant B should NOT see tenant A's agent (RLS)")
            self._reset_session()
        finally:
            # Cleanup as tenant A (or as superuser)
            self._set_tenant(self.pk_a)
            try:
                get_repo("agent").delete(
                    None,
                    partition_key=self.pk_a,
                    agent_version_uuid=version_uuid,
                )
            except Exception:
                self.db_session.rollback()
            self._reset_session()

    def test_agent_single_active_invariant(self):
        """Only one active agent per partition_key + agent_uuid."""
        from ai_agent_core_engine.models.repositories import get_repo

        agent_uuid = f"sa-{uuidlib.uuid4().hex[:12]}"
        v1 = f"v1-{uuidlib.uuid4().hex[:12]}"
        v2 = f"v2-{uuidlib.uuid4().hex[:12]}"

        try:
            self._set_tenant(self.pk_a)

            # Insert v1 as active
            get_repo("agent").insert_update(
                None,
                partition_key=self.pk_a,
                agent_version_uuid=v1,
                agent_uuid=agent_uuid,
                agent_name="Agent V1",
                llm_provider="openai",
                llm_name="gpt-4",
                updated_by="test",
                status="active",
            )

            # Insert v2 as active — should deactivate v1
            get_repo("agent").insert_update(
                None,
                partition_key=self.pk_a,
                agent_version_uuid=v2,
                agent_uuid=agent_uuid,
                agent_name="Agent V2",
                llm_provider="openai",
                llm_name="gpt-4",
                updated_by="test",
                status="active",
            )

            # Check resolve_active returns v2
            active = get_repo("agent").resolve_active(
                self.pk_a, agent_uuid=agent_uuid
            )
            self.assertIsNotNone(active, "resolve_active should return the active agent")
            self.assertEqual(active["agent_version_uuid"], v2)
            self.assertEqual(active["status"], "active")

            # v1 should be inactive
            v1_data = get_repo("agent").get(
                partition_key=self.pk_a,
                agent_version_uuid=v1,
            )
            self.assertIsNotNone(v1_data, "v1 should still exist")
            self.assertEqual(v1_data["status"], "inactive", "v1 should be deactivated")
            self._reset_session()
        finally:
            self._set_tenant(self.pk_a)
            try:
                get_repo("agent").delete(
                    None, partition_key=self.pk_a, agent_version_uuid=v1
                )
                get_repo("agent").delete(
                    None, partition_key=self.pk_a, agent_version_uuid=v2
                )
            except Exception:
                self.db_session.rollback()
            self._reset_session()

    def test_thread_crud_with_rls(self):
        """Thread CRUD with RLS enforcement."""
        from ai_agent_core_engine.models.repositories import get_repo

        thread_uuid = f"t-{uuidlib.uuid4().hex[:12]}"

        try:
            self._set_tenant(self.pk_a)
            get_repo("thread").insert_update(
                None,
                partition_key=self.pk_a,
                thread_uuid=thread_uuid,
                agent_uuid="test-agent",
                updated_by="test",
            )

            data = get_repo("thread").get(
                partition_key=self.pk_a,
                thread_uuid=thread_uuid,
            )
            self.assertIsNotNone(data, "Tenant A should see its own thread")
            self._reset_session()

            # Tenant B can't see it
            self._set_tenant(self.pk_b)
            data = get_repo("thread").get(
                partition_key=self.pk_a,
                thread_uuid=thread_uuid,
            )
            self.assertIsNone(data, "RLS should block cross-tenant read")
            self._reset_session()
        finally:
            self._set_tenant(self.pk_a)
            try:
                get_repo("thread").delete(
                    None,
                    partition_key=self.pk_a,
                    thread_uuid=thread_uuid,
                )
            except Exception:
                self.db_session.rollback()
            self._reset_session()


if __name__ == "__main__":
    unittest.main()