# -*- coding: utf-8 -*-
"""Alembic migration environment for ai_agent_core_engine PostgreSQL backend.

URL resolution priority:
    1. ``DATABASE_URL`` environment variable
    2. ``Config`` setting (when already initialized at runtime)
    3. ``sqlalchemy.url`` in ``alembic.ini`` (fallback)

Table-prefix resolution priority:
    1. ``PG_TABLE_PREFIX`` environment variable
    2. ``Config.PG_TABLE_PREFIX``
    3. ``""`` (empty prefix)

All PostgreSQL model modules are imported so that ``Base.metadata`` is
populated before autogenerate runs.
"""
from __future__ import print_function

__author__ = "bibow"

import importlib
import logging
import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# --- Project path setup ------------------------------------------------------
# Ensure the repository root is on sys.path so that
# ``ai_agent_core_engine`` is importable from the alembic env.
_this_dir = os.path.dirname(os.path.abspath(__file__))
_repo_root = os.path.dirname(os.path.dirname(_this_dir))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

_logger = logging.getLogger(__name__)

# --- URL resolution -----------------------------------------------------------
# Priority: DATABASE_URL env > Config setting > alembic.ini fallback
database_url = os.environ.get("DATABASE_URL")
if database_url:
    config.set_main_option("sqlalchemy.url", database_url)
else:
    try:
        from ai_agent_core_engine.handlers.config import Config

        setting = Config.get_setting()
        if setting and setting.get("db_host"):
            from urllib.parse import quote_plus

            password = quote_plus(setting["db_password"])
            db_url = (
                f"postgresql+psycopg2://{setting['db_user']}:{password}"
                f"@{setting['db_host']}:{setting['db_port']}/{setting['db_schema']}"
            )
            config.set_main_option("sqlalchemy.url", db_url)
    except Exception:
        # Config not initialized — rely on alembic.ini sqlalchemy.url
        _logger.debug("Config not available; falling back to alembic.ini URL.")

# --- Table prefix ------------------------------------------------------------
# Priority: PG_TABLE_PREFIX env > Config.PG_TABLE_PREFIX
pg_table_prefix = os.environ.get("PG_TABLE_PREFIX")
if not pg_table_prefix:
    try:
        from ai_agent_core_engine.handlers.config import Config

        pg_table_prefix = Config.PG_TABLE_PREFIX
    except Exception:
        pg_table_prefix = ""

# Import Base and set the prefix BEFORE importing any models.
from ai_agent_core_engine.models.postgresql.base import Base

Base.table_prefix = pg_table_prefix or ""

# --- Import all models so Base.metadata is populated -------------------------

_MODEL_MODULES = [
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
]


def _import_all_models() -> None:
    """Import every PostgreSQL model module to register with Base.metadata."""
    for mod_name in _MODEL_MODULES:
        try:
            importlib.import_module(
                f"ai_agent_core_engine.models.postgresql.{mod_name}"
            )
        except ImportError as exc:
            _logger.debug("PostgreSQL model not yet available: %s (%s)", mod_name, exc)


_import_all_models()

target_metadata = Base.metadata


# --- Offline / online migration runners ---------------------------------------

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (emit SQL to stdout)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (connected to the database)."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()