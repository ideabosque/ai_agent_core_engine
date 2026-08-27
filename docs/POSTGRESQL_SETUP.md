# PostgreSQL Setup Guide

> Step-by-step guide for setting up the PostgreSQL backend for `ai_agent_core_engine`.

## Prerequisites

- PostgreSQL 14+ (15 recommended)
- `uuid-ossp` extension (for UUID generation — migration `0018` creates it)
- Python 3.8+ with `pip install -e ".[postgresql]"`

## 1. Install Dependencies

```bash
cd /path/to/ai_agent_core_engine
pip install -e ".[postgresql]"
```

This installs `SQLAlchemy>=1.4`, `psycopg2-binary>=2.9`, `alembic>=1.10`.

## 2. Create the Database

```bash
psql -U postgres -c "CREATE DATABASE silvaengine;"
psql -U postgres -d silvaengine -c "CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";"
psql -U postgres -d silvaengine -c "CREATE USER silvaengine WITH PASSWORD 'silvaengine';"
psql -U postgres -d silvaengine -c "GRANT ALL PRIVILEGES ON DATABASE silvaengine TO silvaengine;"
```

## 3. Configure Environment

Create or update `.env`:

```ini
db_backend=postgresql
PG_HOST=localhost
PG_PORT=5432
PG_USER=silvaengine
PG_PASSWORD=silvaengine
PG_DB=silvaengine
PG_TABLE_PREFIX=

# AWS services are still required (Lambda, S3, SQS)
region_name=us-west-2
aws_access_key_id=YOUR_AWS_ACCESS_KEY_ID
aws_secret_access_key=YOUR_AWS_SECRET_ACCESS_KEY

# Engine identity
endpoint_id=YOUR_ENDPOINT_ID
part_id=YOUR_PART_ID

# Set to 1 on first run to create tables
initialize_tables=0
```

Alternatively, use `DATABASE_URL`:

```ini
DATABASE_URL=postgresql+psycopg2://silvaengine:silvaengine@localhost:5432/silvaengine
```

## 4. Run Migrations

```bash
export DATABASE_URL=postgresql+psycopg2://silvaengine:silvaengine@localhost:5432/silvaengine
export PG_TABLE_PREFIX=

alembic -c migration/alembic.ini upgrade head
```

This creates all 17 entity tables + indexes + partial unique indexes + RLS policies.

Migration order:
1. `0001`–`0003`: Global registries (llms, wizard_schemas, ui_components)
2. `0004`–`0017`: Tenant-scoped tables (agents, threads, runs, messages, etc.)
3. `0018`: RLS policies on all 14 partition-keyed tables

## 5. Verify RLS

After migrations, verify RLS is enabled:

```sql
-- Check RLS is enabled
SELECT relname, relrowsecurity 
FROM pg_class 
WHERE relname IN ('agents', 'threads', 'runs', 'messages')
ORDER BY relname;

-- Check policies
SELECT tablename, policyname, cmd, qual 
FROM pg_policies 
WHERE schemaname = 'public'
ORDER BY tablename;
```

## 6. Test Tenant Isolation

```sql
-- As a superuser, insert data for two tenants
SET app.tenant_id = 'tenantA#part1';
INSERT INTO agents (partition_key, agent_version_uuid, agent_uuid, agent_name, llm_provider, llm_name, updated_by)
VALUES ('tenantA#part1', 'v1', 'a1', 'Agent A', 'openai', 'gpt-4', 'test');

SET app.tenant_id = 'tenantB#part1';
INSERT INTO agents (partition_key, agent_version_uuid, agent_uuid, agent_name, llm_provider, llm_name, updated_by)
VALUES ('tenantB#part1', 'v1', 'b1', 'Agent B', 'openai', 'gpt-4', 'test');

-- Tenant A can only see their rows
SET app.tenant_id = 'tenantA#part1';
SELECT count(*) FROM agents;  -- Returns 1

-- Tenant B can only see their rows
SET app.tenant_id = 'tenantB#part1';
SELECT count(*) FROM agents;  -- Returns 1

-- Without tenant context, no rows visible (RLS blocks)
RESET app.tenant_id;
SELECT count(*) FROM agents;  -- Returns 0 (or error if setting is required)
```

## 7. Start the Engine

```bash
# Start the SilvaEngine gateway (which loads AACE)
python -m silvaengine_gateway
```

The gateway will call `Config.initialize()` which reads `db_backend=postgresql`, builds the SQLAlchemy `scoped_session`, and the dispatch boundary routes all persistence through PG repos.

## Troubleshooting

### `ImportError: SQLAlchemy is required for PostgreSQL backend`

Install the optional dependency: `pip install -e ".[postgresql]"`

### `relation "agents" does not exist`

Run migrations first: `alembic -c migration/alembic.ini upgrade head`

### `permission denied for table agents`

Grant privileges: `GRANT ALL ON ALL TABLES IN SCHEMA public TO silvaengine;`

### `unrecognized configuration parameter "app.tenant_id"`

The `app.tenant_id` custom GUC is set per-session by `main.py::_set_rls_context()`. If you're running queries manually, use `SET LOCAL app.tenant_id = 'your#partition';` first.

### `RLS policy violation: tenant mismatch`

The `partition_key` in the row doesn't match `app.tenant_id`. Ensure `partition_key` is set correctly as `{endpoint_id}#{part_id}`.