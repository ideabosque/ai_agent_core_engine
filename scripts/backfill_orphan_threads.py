#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Backfill missing ``<prefix>threads`` rows for orphaned thread_uuids.

Context
-------
Before the gateway streaming path was fixed to pre-create the thread
(``dispatch_ask_model._precreate_thread``), runs/messages/tool_calls were
written against thread_uuids whose thread row was never inserted. This script
recreates those thread rows so joins from threads no longer lose history.

Limitations (important)
-----------------------
* ``agent_uuid`` is NOT NULL on the threads table but is NOT stored on any child
  table (runs/messages/tool_calls) and is not recoverable from async_tasks, so
  it CANNOT be derived. You must supply it via ``--agent-uuid`` (or the
  BACKFILL_AGENT_UUID env var). Every backfilled thread is attributed to that
  value — pick a real agent_uuid for the partition, or a clearly-labelled
  sentinel (e.g. ``backfilled-unknown``).
* Orphans whose child rows all have a NULL ``partition_key`` cannot be
  backfilled (partition_key is part of the PK) and are reported+skipped.

Usage
-----
    # dry run (default): shows counts + a sample, writes nothing
    python scripts/backfill_orphan_threads.py --agent-uuid <agent_uuid>

    # apply
    python scripts/backfill_orphan_threads.py --agent-uuid <agent_uuid> --commit

Connection comes from env (PG_HOST/PG_PORT/PG_USER/PG_PASSWORD/PG_DB,
PG_TABLE_PREFIX). A .env is loaded if present.
"""
from __future__ import print_function

__author__ = "bibow"

import argparse
import os
import sys

try:
    from dotenv import load_dotenv

    # Load a .env if one sits next to the repo/tests; harmless if absent.
    for _cand in (
        os.path.join(os.path.dirname(__file__), "..", "ai_agent_core_engine", "tests", ".env"),
        os.path.join(os.getcwd(), ".env"),
    ):
        if os.path.isfile(_cand):
            load_dotenv(_cand)
            break
except ImportError:
    pass

import psycopg2


def _conn():
    return psycopg2.connect(
        host=os.getenv("PG_HOST", "localhost"),
        port=os.getenv("PG_PORT", "5432"),
        dbname=os.getenv("PG_DB", "silvaengine"),
        user=os.getenv("PG_USER", "silvaengine"),
        password=os.getenv("PG_PASSWORD", "silvaengine"),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill orphaned thread rows.")
    parser.add_argument(
        "--agent-uuid",
        default=os.getenv("BACKFILL_AGENT_UUID"),
        help="agent_uuid to attribute recovered threads to (required to commit).",
    )
    parser.add_argument(
        "--commit",
        action="store_true",
        help="Apply the backfill. Without this flag the script is a dry run.",
    )
    args = parser.parse_args()

    prefix = os.getenv("PG_TABLE_PREFIX", "aace_")
    threads = f"{prefix}threads"

    # Derived orphan set: one row per orphaned thread_uuid with the best
    # non-null partition_key and earliest created_at across all child tables.
    orphans_cte = f"""
    WITH child AS (
        SELECT thread_uuid, partition_key, created_at FROM {prefix}runs
        UNION ALL
        SELECT thread_uuid, partition_key, created_at FROM {prefix}messages
        UNION ALL
        SELECT thread_uuid, partition_key, created_at FROM {prefix}tool_calls
    ),
    orphan AS (
        SELECT
            c.thread_uuid,
            max(c.partition_key) FILTER (WHERE c.partition_key IS NOT NULL) AS partition_key,
            min(c.created_at) AS created_at
        FROM child c
        LEFT JOIN {threads} t ON t.thread_uuid = c.thread_uuid
        WHERE t.thread_uuid IS NULL
        GROUP BY c.thread_uuid
    )
    """

    conn = _conn()
    conn.autocommit = False
    cur = conn.cursor()

    # Report scope.
    cur.execute(orphans_cte + """
        SELECT
            count(*) FILTER (WHERE partition_key IS NOT NULL) AS recoverable,
            count(*) FILTER (WHERE partition_key IS NULL)     AS no_partition
        FROM orphan
    """)
    recoverable, no_partition = cur.fetchone()
    print(f"Orphaned thread_uuids: recoverable={recoverable}  "
          f"unrecoverable(no partition_key)={no_partition}")

    if recoverable == 0:
        print("Nothing to backfill.")
        conn.close()
        return 0

    # Sample.
    cur.execute(orphans_cte + """
        SELECT thread_uuid, partition_key, created_at
        FROM orphan WHERE partition_key IS NOT NULL
        ORDER BY created_at DESC LIMIT 5
    """)
    print("Sample recoverable orphans (newest first):")
    for r in cur.fetchall():
        print(f"  {r[0]}  {r[1]}  {r[2]}")

    if not args.commit:
        print("\nDRY RUN - no rows written. Re-run with --agent-uuid <id> --commit "
              "to apply.")
        conn.close()
        return 0

    if not args.agent_uuid:
        print("\nERROR: --agent-uuid (or BACKFILL_AGENT_UUID) is required to commit; "
              "agent_uuid cannot be derived from the data.", file=sys.stderr)
        conn.close()
        return 2

    # Insert. endpoint_id/part_id are split from partition_key ("endpoint#part").
    cur.execute(orphans_cte + f"""
        INSERT INTO {threads}
            (partition_key, thread_uuid, endpoint_id, part_id, agent_uuid, created_at)
        SELECT
            partition_key,
            thread_uuid,
            split_part(partition_key, '#', 1),
            split_part(partition_key, '#', 2),
            %s,
            created_at
        FROM orphan
        WHERE partition_key IS NOT NULL
        ON CONFLICT DO NOTHING
    """, (args.agent_uuid,))
    inserted = cur.rowcount
    conn.commit()
    print(f"\nBackfilled {inserted} thread row(s) with agent_uuid={args.agent_uuid!r}. "
          f"Skipped {no_partition} orphan(s) with no partition_key.")
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
