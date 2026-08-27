# Dual-Backend Configuration

> How to select and configure the persistence backend for `ai_agent_core_engine`.

## Backend Selection

The backend is selected at deployment time via the `db_backend` setting (env var `db_backend`).

| Value | Description |
| --- | --- |
| `dynamodb` (default) | PynamoDB models via `silvaengine_dynamodb_base`. AWS credentials required. |
| `postgresql` | SQLAlchemy models with RLS tenant isolation. PG connection required. |

Set in `.env`:

```ini
db_backend=dynamodb      # or postgresql
```

## Environment Variables

### Common (both backends)

```ini
region_name=us-west-2
aws_access_key_id=YOUR_AWS_ACCESS_KEY_ID
aws_secret_access_key=YOUR_AWS_SECRET_ACCESS_KEY
api_id=YOUR_API_GATEWAY_ID
api_stage=beta
endpoint_id=YOUR_ENDPOINT_ID
part_id=YOUR_PART_ID
initialize_tables=0
cache_enabled=0
```

> **AWS services in PG mode:** AACE uses Lambda (async task dispatch), S3 (file upload/download), and SQS (task queues). These are initialized unconditionally in both modes. AWS credentials must be present even when `db_backend=postgresql`.

### DynamoDB-specific

No additional vars — DynamoDB uses the AWS credentials above.

### PostgreSQL-specific

```ini
# DATABASE_URL takes precedence over PG_* if set
# DATABASE_URL=postgresql+psycopg2://silvaengine:silvaengine@localhost:5432/silvaengine
PG_HOST=localhost
PG_PORT=5432
PG_USER=silvaengine
PG_PASSWORD=silvaengine
PG_DB=silvaengine
PG_TABLE_PREFIX=
```

| Variable | Setting key | Description |
| --- | --- | --- |
| `DATABASE_URL` | (overrides all) | Full SQLAlchemy connection URL |
| `PG_HOST` | `db_host` | PostgreSQL host |
| `PG_PORT` | `db_port` | PostgreSQL port (default 5432) |
| `PG_USER` | `db_user` | Database user |
| `PG_PASSWORD` | `db_password` | Database password (URL-encoded by Config) |
| `PG_DB` | `db_schema` | Database name |
| `PG_TABLE_PREFIX` | `pg_table_prefix` | Prefix for all table/index names (e.g. `aace_`) |

## Table Prefix

`PG_TABLE_PREFIX` prefixes all PostgreSQL table and index names. This allows multiple SilvaEngine modules to share one PostgreSQL database without table name collisions.

Example: `PG_TABLE_PREFIX=aace_` → tables become `aace_agents`, `aace_threads`, etc.

The prefix is applied via `declared_attr __tablename__` + `prefixed_table()` in `models/postgresql/base.py`. It must be set before model modules are imported — `Config._initialize_db_session` handles this.

## RLS (Row-Level Security)

AACE is the first SilvaEngine module to use PostgreSQL RLS for multi-tenant isolation.

**Mechanism:**
- 14 tables with a `partition_key` column have RLS enabled
- A `tenant_isolation` policy on each table enforces: `USING (partition_key = current_setting('app.tenant_id', true))`
- `main.py::_set_rls_context(partition_key)` executes `SET LOCAL app.tenant_id = :tenant` before each request
- `main.py::_clear_rls_context()` calls `session.remove()` after each request

**RLS-enabled tables (14):**
`agents`, `threads`, `elements`, `wizards`, `wizard_groups`, `wizard_group_filters`, `mcp_servers`, `flow_snippets`, `prompt_templates`, `runs`, `messages`, `tool_calls`, `async_tasks`, `fine_tuning_messages`

**Non-RLS tables (3 global registries):**
`llms`, `wizard_schemas`, `ui_components` — shared across all tenants, no RLS.

## Cache Configuration

Cache config is backend-aware:

| Backend | `CACHE_ENTITY_CONFIG` | `CACHE_RELATIONSHIPS` |
| --- | --- | --- |
| DynamoDB | 15 entities with `@method_cache` | 9 entity → children mappings |
| PostgreSQL | Empty `{}` (PG repos don't use `@method_cache`) | Empty `{}` |

PG repos still call `purge_entity_cascading_cache` after commits for parity, but the PG cache maps are intentionally empty so the purge is a no-op.

## Install Dependencies

```bash
# DynamoDB only (default)
pip install -e .

# With PostgreSQL support
pip install -e ".[postgresql]"
```

The `[postgresql]` extra adds: `SQLAlchemy>=1.4`, `psycopg2-binary>=2.9`, `alembic>=1.10`.

DynamoDB-only installs never import SQLAlchemy — all PG imports are lazy.

## Alembic Migrations

```bash
# Set DATABASE_URL or PG_* env vars
export db_backend=postgresql
export PG_HOST=localhost
export PG_PORT=5432
export PG_USER=silvaengine
export PG_PASSWORD=silvaengine
export PG_DB=silvaengine
export PG_TABLE_PREFIX=

# Run migrations
alembic -c migration/alembic.ini upgrade head

# Rollback last migration
alembic -c migration/alembic.ini downgrade -1
```

18 migrations: `0001`–`0017` create entity tables, `0018` enables RLS policies.

## Switching Backends

Switching is deployment-time only — no runtime switching. To switch:

1. Set `db_backend` in `.env`
2. If switching to `postgresql`: install `[postgresql]` extra, run Alembic migrations
3. If switching to `dynamodb`: ensure AWS credentials are set, set `initialize_tables=1` on first run
4. Restart the gateway/daemon

No data migration is provided — both backends start empty.