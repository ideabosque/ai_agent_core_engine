#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Migrate data from DynamoDB to PostgreSQL for all 17 AACE entities.

Uses raw SQL INSERT ... ON CONFLICT DO NOTHING for maximum compatibility.
Idempotent: re-running won't duplicate rows.
"""
from __future__ import print_function

__author__ = "bibow"

import os
import sys
import time
import json
import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SILVA_ROOT = os.path.dirname(_REPO_ROOT)
for p in [
    _REPO_ROOT,
    _SILVA_ROOT,
    os.path.join(_SILVA_ROOT, "silvaengine_dynamodb_base"),
    os.path.join(_SILVA_ROOT, "silvaengine_utility"),
    os.path.join(_SILVA_ROOT, "silvaengine_constants"),
]:
    if os.path.isdir(p) and p not in sys.path:
        sys.path.insert(0, p)

from dotenv import load_dotenv
load_dotenv(os.path.join(_REPO_ROOT, "ai_agent_core_engine", "tests", ".env"))

import psycopg2
from psycopg2.extras import Json

# --- DynamoDB setup ---
from silvaengine_dynamodb_base import BaseModel

BaseModel.Meta.region = os.getenv("region_name")
BaseModel.Meta.aws_access_key_id = os.getenv("aws_access_key_id")
BaseModel.Meta.aws_secret_access_key = os.getenv("aws_secret_access_key")

PARTITION_KEY = f"{os.getenv('endpoint_id')}#{os.getenv('part_id')}"
PG_PREFIX = os.getenv("PG_TABLE_PREFIX", "aace_")

# --- PostgreSQL setup ---
PG_HOST = os.getenv("PG_HOST", "localhost")
PG_PORT = os.getenv("PG_PORT", "5432")
PG_USER = os.getenv("PG_USER", "silvaengine")
PG_PASSWORD = os.getenv("PG_PASSWORD", "silvaengine")
PG_DB = os.getenv("PG_DB", "silvaengine")

pg_conn = psycopg2.connect(
    host=PG_HOST, port=PG_PORT, user=PG_USER, password=PG_PASSWORD, dbname=PG_DB
)
pg_conn.autocommit = False


def to_pg_value(val: Any) -> Any:
    """Convert a PynamoDB attribute value to a PostgreSQL-compatible value."""
    import json

    if val is None:
        return None
    if isinstance(val, bool):
        return val
    if isinstance(val, (int, float, str)):
        return val
    if isinstance(val, Decimal):
        return float(val)
    if isinstance(val, (datetime.datetime, datetime.date)):
        return val
    if isinstance(val, dict):
        # PynamoDB MapAttribute
        if hasattr(val, "attribute_values"):
            return json.loads(json.dumps(
                {k: to_pg_value(v) for k, v in val.attribute_values.items()},
                default=str
            ))
        return json.loads(json.dumps(
            {k: to_pg_value(v) for k, v in val.items()},
            default=str
        ))
    if isinstance(val, (list, tuple)):
        result = []
        for item in val:
            if hasattr(item, "attribute_values"):
                result.append({k: to_pg_value(v) for k, v in item.attribute_values.items()})
            else:
                result.append(to_pg_value(item))
        return json.loads(json.dumps(result, default=str))
    # PynamoDB attribute object with attribute_values
    if hasattr(val, "attribute_values"):
        return json.loads(json.dumps(
            {k: to_pg_value(v) for k, v in val.attribute_values.items()},
            default=str
        ))
    return str(val)


def model_to_dict(model) -> Dict[str, Any]:
    """Convert a PynamoDB model instance to a dict of PG-compatible values."""
    if model is None:
        return {}
    result = {}
    for attr_name in model.get_attributes().keys():
        val = getattr(model, attr_name, None)
        result[attr_name] = to_pg_value(val)
    return result


def get_pg_columns(table_name: str) -> List[str]:
    """Get the list of column names for a PG table."""
    full_table = f"{PG_PREFIX}{table_name}"
    cur = pg_conn.cursor()
    cur.execute(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_schema='public' AND table_name=%s ORDER BY ordinal_position",
        (full_table,),
    )
    cols = [r[0] for r in cur.fetchall()]
    cur.close()
    return cols


def get_pg_pk_columns(table_name: str) -> List[str]:
    """Get the PK column names for a PG table."""
    full_table = f"{PG_PREFIX}{table_name}"
    cur = pg_conn.cursor()
    cur.execute(
        "SELECT a.attname FROM pg_index i "
        "JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey) "
        "WHERE i.indrelid = %s::regclass AND i.indisprimary",
        (full_table,),
    )
    cols = [r[0] for r in cur.fetchall()]
    cur.close()
    return cols


def insert_row(table_name: str, row: Dict[str, Any]) -> bool:
    """Insert a row into PG using ON CONFLICT DO NOTHING."""
    full_table = f"{PG_PREFIX}{table_name}"
    pg_cols = get_pg_columns(table_name)

    # Only keep keys that are actual PG columns and have non-None values
    clean = {}
    for k, v in row.items():
        if k in pg_cols and v is not None:
            clean[k] = v

    if not clean:
        return False

    col_names = list(clean.keys())
    placeholders = [f"%({c})s" for c in col_names]

    # Wrap dict/list values with Json adapter for psycopg2
    from psycopg2.extras import Json as PsycopgJson
    params = {}
    for k, v in clean.items():
        if isinstance(v, (dict, list)):
            params[k] = PsycopgJson(v)
        else:
            params[k] = v

    sql = (
        f"INSERT INTO {full_table} ({', '.join(col_names)}) "
        f"VALUES ({', '.join(placeholders)}) "
        f"ON CONFLICT DO NOTHING"
    )

    cur = pg_conn.cursor()
    try:
        cur.execute(sql, params)
        pg_conn.commit()
        return cur.rowcount > 0
    except Exception as e:
        pg_conn.rollback()
        if "violates not-null" in str(e) or "duplicate key" in str(e):
            # Skip rows that can't be inserted
            pass
        else:
            print(f"    ERROR: {str(e)[:120]}")
        return False
    finally:
        cur.close()


def scan_all(model_class, partition_key: Optional[str] = None) -> List:
    """Scan/query all items from a DynamoDB table."""
    items = []
    if partition_key:
        try:
            for item in model_class.query(partition_key, consistent_read=False):
                items.append(item)
        except Exception as e:
            print(f"  Query error: {str(e)[:80]}")
    else:
        try:
            for item in model_class.scan(consistent_read=False):
                items.append(item)
        except Exception as e:
            print(f"  Scan error: {str(e)[:80]}")
    return items


# --- Entity definitions ---
# (entity_name, module_path, class_name, table_name, use_partition_key)
ENTITIES = [
    ("llm", "ai_agent_core_engine.models.dynamodb.llm", "LlmModel", "llms", False),
    ("wizard_schema", "ai_agent_core_engine.models.dynamodb.wizard_schema", "WizardSchemaModel", "wizard_schemas", False),
    ("ui_component", "ai_agent_core_engine.models.dynamodb.ui_component", "UIComponentModel", "ui_components", False),
    ("agent", "ai_agent_core_engine.models.dynamodb.agent", "AgentModel", "agents", True),
    ("thread", "ai_agent_core_engine.models.dynamodb.thread", "ThreadModel", "threads", True),
    ("element", "ai_agent_core_engine.models.dynamodb.element", "ElementModel", "elements", True),
    ("wizard", "ai_agent_core_engine.models.dynamodb.wizard", "WizardModel", "wizards", True),
    ("wizard_group", "ai_agent_core_engine.models.dynamodb.wizard_group", "WizardGroupModel", "wizard_groups", True),
    ("wizard_group_filter", "ai_agent_core_engine.models.dynamodb.wizard_group_filter", "WizardGroupFilterModel", "wizard_group_filters", True),
    ("mcp_server", "ai_agent_core_engine.models.dynamodb.mcp_server", "MCPServerModel", "mcp_servers", True),
    ("flow_snippet", "ai_agent_core_engine.models.dynamodb.flow_snippet", "FlowSnippetModel", "flow_snippets", True),
    ("prompt_template", "ai_agent_core_engine.models.dynamodb.prompt_template", "PromptTemplateModel", "prompt_templates", True),
    ("async_task", "ai_agent_core_engine.models.dynamodb.async_task", "AsyncTaskModel", "async_tasks", False),
    ("run", "ai_agent_core_engine.models.dynamodb.run", "RunModel", "runs", False),
    ("message", "ai_agent_core_engine.models.dynamodb.message", "MessageModel", "messages", False),
    ("tool_call", "ai_agent_core_engine.models.dynamodb.tool_call", "ToolCallModel", "tool_calls", False),
    ("fine_tuning_message", "ai_agent_core_engine.models.dynamodb.fine_tuning_message", "FineTuningMessageModel", "fine_tuning_messages", False),
]


def migrate_entity(entity_name, module_path, class_name, table_name, use_pk):
    import importlib

    mod = importlib.import_module(module_path)
    model_class = getattr(mod, class_name)

    print(f"\n--- {entity_name} ---")
    pk = PARTITION_KEY if use_pk else None
    items = scan_all(model_class, pk)
    print(f"  DynamoDB: {len(items)} rows")

    if not items:
        return 0

    inserted = 0
    for item in items:
        row = model_to_dict(item)
        if insert_row(table_name, row):
            inserted += 1

    # Verify
    cur = pg_conn.cursor()
    cur.execute(f"SELECT count(*) FROM {PG_PREFIX}{table_name}")
    pg_count = cur.fetchone()[0]
    cur.close()
    print(f"  PostgreSQL: {pg_count} rows (inserted {inserted})")
    return inserted


def main():
    print("=" * 60)
    print("DynamoDB → PostgreSQL Migration")
    print("=" * 60)
    print(f"Partition: {PARTITION_KEY}")
    print(f"Prefix: {PG_PREFIX}")

    # Disable RLS for the migration connection (silvaengine is superuser)
    cur = pg_conn.cursor()
    cur.execute("SET app.tenant_id = %s", (PARTITION_KEY,))
    pg_conn.commit()
    cur.close()

    total = 0
    start = time.time()

    for entity_name, module_path, class_name, table_name, use_pk in ENTITIES:
        try:
            count = migrate_entity(entity_name, module_path, class_name, table_name, use_pk)
            total += count
        except Exception as e:
            print(f"\n  FATAL: {e}")
            import traceback
            traceback.print_exc()

    elapsed = time.time() - start
    print(f"\n{'=' * 60}")
    print(f"Complete: {total} rows in {elapsed:.1f}s")
    print(f"{'=' * 60}")

    # Final counts
    print("\nFinal counts:")
    for entity_name, _, _, table_name, _ in ENTITIES:
        cur = pg_conn.cursor()
        cur.execute(f"SELECT count(*) FROM {PG_PREFIX}{table_name}")
        print(f"  {entity_name}: {cur.fetchone()[0]}")
        cur.close()

    pg_conn.close()


if __name__ == "__main__":
    main()