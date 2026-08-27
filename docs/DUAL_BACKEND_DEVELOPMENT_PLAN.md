# AI Agent Core Engine — Dual-Backend Development Plan

> Project: `ai_agent_core_engine`
> Goal: support DynamoDB and PostgreSQL as deployment-selectable persistence backends for the engine's 17 metadata models, behind a single GraphQL contract.
> Scope boundary: **Row-Level Security (RLS) is in scope.** The PostgreSQL backend will enforce tenant isolation via RLS policies on `partition_key`-keyed tables, going beyond what the sibling engines (rfq_engine, mcp_daemon_engine, knowledge_graph_engine) implemented. The sibling engines use partial unique indexes for single-active invariants but do not use RLS; AACE will be the first SilvaEngine module to adopt RLS for multi-tenant isolation.
> Status: **Phases 0–6 complete.** Repository dispatch boundary implemented and tested on both backends. 18 tests pass (6 DDB dispatch + 3 adoption guard + 4 PG dispatch + 4 PG integration + 1 skip). Migrations applied to live PG database. RLS tenant isolation verified — cross-tenant queries blocked. Single-active invariant verified — partial unique index enforced. Phase 5 benchmarks run against live DB.
> No backward support: AACE is not yet in production with persisted data, so this plan carries **no backward-compatibility or data-migration obligations.** Both backends are built fresh; DynamoDB is the default runtime selection.
> Last reviewed: 2026-06-24
> Reference engines: `rfq_engine` (DynamoDB↔PostgreSQL, 18 entities, structurally complete), `mcp_daemon_engine` (DynamoDB↔PostgreSQL, 4 entities), `knowledge_graph_engine` (DynamoDB↔PostgreSQL, 5 entities + Neo4j graph store orthogonal)

---

## Executive Summary

`ai_agent_core_engine` (AACE) is the AI agent orchestration layer of the Banyanos platform. It persists 17 PynamoDB entity models built on `silvaengine_dynamodb_base.BaseModel`, all prefixed `aace-`. The engine handles agent configuration, LLM provider registry, conversation threads/runs/messages/tool-calls, async task tracking, fine-tuning data, wizard-based UI scaffolding, MCP server registry, UI component catalog, flow snippets, and prompt templates.

The intended end state mirrors the verified pattern from `rfq_engine`, `mcp_daemon_engine`, and `knowledge_graph_engine`:

- `DB_BACKEND=dynamodb` (default): PynamoDB models under `ai_agent_core_engine.models.dynamodb`, DynamoDB DataLoaders, existing `@method_cache` behavior, and DynamoDB table initialization.
- `DB_BACKEND=postgresql`: SQLAlchemy models under `ai_agent_core_engine.models.postgresql`, Alembic migrations, PostgreSQL repositories, **RLS policies for tenant isolation**, and PostgreSQL DataLoader coverage for the nested-resolver surface.

A repository boundary at `ai_agent_core_engine.models.repositories` will isolate GraphQL queries, mutations, and resolvers from backend-specific persistence details. **No such boundary exists today** — the first body of work is to introduce it with DynamoDB pass-through (Phase 1), then build the PostgreSQL implementation behind it (Phases 2–4).

> Honest current state (2026-06-24): AACE has **only** the DynamoDB path and **no** abstraction in front of it. Queries/mutations import model functions directly. Treat every "target" file path in this document as *to be created* unless listed under "Current Architecture" below.

---

## Current Architecture (as built today)

```text
GraphQL schema (schema.py)
  queries/*.py  -> thin pass-throughs to models.*.resolve_* functions
  mutations/*.py -> import models.* functions directly (insert_update_*, delete_*, get_*)
  types/*.py    -> graphene ObjectTypes with nested resolvers using DataLoaders
        |
        v
ai_agent_core_engine.models.<entity>   (17 PynamoDB modules, no abstraction layer)
   agent.py, llm.py, thread.py, run.py, message.py, tool_call.py,
   async_task.py, fine_tuning_message.py, element.py, wizard.py,
   wizard_schema.py, wizard_group.py, wizard_group_filter.py,
   mcp_server.py, ui_component.py, flow_snippet.py, prompt_template.py
   cache.py, utils.py (initialize_tables for 17 tables, cross-entity helpers)
   batch_loaders/  (RequestLoaders: 16 loaders; get_loaders -> context["loaders"])
        |
        +-- DynamoDB (PynamoDB BaseModel)        <- only backend that exists

handlers/
   config.py        Config singleton (AWS-only, no DB_BACKEND)
   ai_agent.py      ask_model, execute_ask_model, upload_file, get_file
   ai_agent_utility.py  get_ai_agent_handler, token calc, XML conversion, start_async_task
   at_agent_listener.py  async_execute_ask_model, async_insert_update_tool_call, send_data_to_stream
   wizard_group.py  composite wizard group operations
```

### Facts verified in source on 2026-06-24:

- **No `Config.DB_BACKEND`.** `Config.initialize()` (`handlers/config.py:289`) only initializes AWS services (Lambda, SQS, S3, API Gateway), internal MCP, and optionally DynamoDB tables. Backend is implicitly always DynamoDB.
- **No `db_session`, no `PG_TABLE_PREFIX`, no SQLAlchemy, no Alembic.** `pyproject.toml` lists only `SilvaEngine-Utility`, `SilvaEngine-DynamoDB-Base`, `graphene`, `openai`.
- **GraphQL code imports persistence directly.** `queries/agent.py` re-exports `models.agent.resolve_agent`; `mutations/agent.py::InsertUpdateAgent.mutate` calls `models.agent.insert_update_agent(info, **kwargs)` directly.
- **`models/batch_loaders/__init__.py`** exposes a single `RequestLoaders` (DynamoDB) and `get_loaders(context)` keyed on `context["loaders"]`. There is no dispatch and no PostgreSQL loader container.
- **`models/utils.py::initialize_tables`** hardcodes creation of all 17 DynamoDB tables.
- **`models/cache.py::purge_entity_cascading_cache`** delegates to `silvaengine_dynamodb_base.cache_utils`.
- **Cache config** (`handlers/config.py:50`) — single `CACHE_ENTITY_CONFIG` dict covering 15 of 17 entities (omits `run` and `message` from cache keys — they use `thread_uuid` hash key, not `partition_key`). `CACHE_RELATIONSHIPS` (`:173`) maps agent→[thread, fine_tuning_message], thread→[run, message, tool_call, fine_tuning_message], run→[message], llm→[agent], flow_snippet→[agent], mcp_server→[agent], wizard_group→[wizard], wizard→[element], prompt_template→[ui_component, flow_snippet].
- **`.env.example`** has no `DB_BACKEND`, no `PG_HOST`/`PG_PORT`/`PG_USER`/`PG_PASSWORD`/`PG_DB`, no `DATABASE_URL`, no `PG_TABLE_PREFIX`.
- **`main.py`** has `dispatch_graphql` and `dispatch_ask_model` wrappers. `dispatch_ask_model` pre-creates `AsyncTaskModel` and `RunModel` by calling `.save()` directly on PynamoDB models — this must route through repositories in the dual-backend world.

---

## Persisted Entities (17)

The dual-backend structure covers all 17 metadata entities. Each has a PynamoDB model today and needs a mirrored SQLAlchemy model + repository + migration.

### Entity Classification by Hash Key Type

**Partition-keyed (9 entities)** — hash key is `partition_key` (composite `endpoint_id#part_id`), making them candidates for RLS:

| Entity | DynamoDB table | PostgreSQL table | Range key | Secondary access | Notable fields |
| --- | --- | --- | --- | --- | --- |
| Agent | `aace-agents` | `aace_agents` | `agent_version_uuid` | LSI `agent_uuid`, LSI `updated_at` | `llm_provider`, `llm_name`, `instructions`, `configuration` (map), `mcp_server_uuids` (list), `variables` (list of map), `num_of_messages`, `tool_call_role`, `flow_snippet_version_uuid`, `status` (active/inactive) |
| Thread | `aace-threads` | `aace_threads` | `thread_uuid` | LSI `agent_uuid`, LSI `created_at` | `endpoint_id`, `part_id`, `agent_uuid`, `user_id` |
| Element | `aace-elements` | `aace_elements` | `element_uuid` | LSI `data_type`, LSI `updated_at` | `data_type`, `element_title`, `priority`, `attribute_name`, `attribute_type`, `option_values` (list of map), `conditions` (list of map), `pattern` |
| Wizard | `aace-wizards` | `aace_wizards` | `wizard_uuid` | LSI `updated_at` | `wizard_title`, `wizard_type`, `wizard_schema_type`, `wizard_schema_name`, `wizard_attributes` (list of map), `wizard_elements` (list of map), `priority` |
| WizardGroup | `aace-wizard_groups` | `aace_wizard_groups` | `wizard_group_uuid` | LSI `updated_at` | `wizard_group_name`, `weight`, `wizard_uuids` (list) |
| WizardGroupFilter | `aace-wizard_group_filters` | `aace_wizard_group_filters` | `wizard_group_filter_uuid` | LSI `updated_at` | `wizard_group_filter_name`, `region`, `criteria` (map), `weight`, `wizard_group_uuid` |
| MCPServer | `aace-mcp_servers` | `aace_mcp_servers` | `mcp_server_uuid` | LSI `updated_at` | `mcp_label`, `mcp_server_url`, `headers` (map) |
| FlowSnippet | `aace-flow_snippets` | `aace_flow_snippets` | `flow_snippet_version_uuid` | LSI `flow_snippet_uuid`, LSI `prompt_uuid`, LSI `updated_at` | `flow_name`, `flow_relationship`, `flow_context`, `enabled_tools` (list of string), `status` (active/inactive) |
| PromptTemplate | `aace-prompt_templates` | `aace_prompt_templates` | `prompt_version_uuid` | LSI `prompt_uuid`, LSI `prompt_type`, LSI `updated_at` | `prompt_type`, `prompt_name`, `template_context`, `variables` (list of map), `mcp_servers` (list of map), `ui_components` (list of map), `status` (active/inactive) |

**Non-partition-keyed (8 entities)** — hash key is an entity-specific key, not `partition_key`. These require different multi-tenancy strategies (see [Multi-Tenancy Strategy](#multi-tenancy-strategy-rls-vs-application-level)):

| Entity | DynamoDB table | PostgreSQL table | Hash key | Range key | Secondary access | Notable fields |
| --- | --- | --- | --- | --- | --- | --- |
| LLM | `aace-llms` | `aace_llms` | `llm_provider` | `llm_name` | LSI `updated_at` | `module_name`, `class_name`, `configuration_schema` (map) |
| Run | `aace-runs` | `aace_runs` | `thread_uuid` | `run_uuid` | LSI `updated_at` | `partition_key`, `run_id`, `completion_tokens`, `prompt_tokens`, `total_tokens`, `time_spent` |
| Message | `aace-messages` | `aace_messages` | `thread_uuid` | `message_uuid` | LSI `run_uuid`, LSI `updated_at` | `run_uuid`, `message_id`, `role`, `message` |
| ToolCall | `aace-tool_calls` | `aace_tool_calls` | `thread_uuid` | `tool_call_uuid` | LSI `run_uuid`, LSI `updated_at` | `run_uuid`, `tool_call_id`, `tool_type`, `name`, `arguments`, `content`, `status`, `notes`, `time_spent` |
| AsyncTask | `aace-async_tasks` | `aace_async_tasks` | `function_name` | `async_task_uuid` | GSI `partition_key`+`updated_at` | `partition_key`, `arguments` (map), `result`, `output_files` (list of map), `status`, `notes`, `time_spent` |
| FineTuningMessage | `aace-fine_tuning_messages` | `aace_fine_tuning_messages` | `agent_uuid` | `message_uuid` | LSI `thread_uuid`, LSI `timestamp` | `thread_uuid`, `timestamp`, `endpoint_id`, `role`, `tool_calls` (list of map), `tool_call_uuid`, `content`, `weight`, `trained` |
| WizardSchema | `aace-wizard_schemas` | `aace_wizard_schemas` | `wizard_schema_type` | `wizard_schema_name` | LSI `updated_at` | `wizard_schema_description`, `attributes` (list of map), `attribute_groups` (list of map) |
| UIComponent | `aace-ui_components` | `aace_ui_components` | `ui_component_type` | `ui_component_uuid` | LSI `updated_at` | `tag_name`, `tag_alias`, `parameters` (list of map), `wait_for` |

### Entity-Specific Behavior the PostgreSQL Repositories Must Preserve

- **Single-active invariant (Agent, FlowSnippet, PromptTemplate).** Each has `_get_active_*` and `_inactivate_*` patterns — at most one `status="active"` record per `partition_key` per logical entity UUID. On PostgreSQL this should be a single transaction (deactivate-then-insert/update), backed by a **partial unique index** `WHERE status = 'active'` (the pattern from `knowledge_graph_engine`).
- **Cross-entity helpers** (`models/utils.py`): `get_element`, `get_wizard`, `get_flow_snippet`, `get_mcp_servers`, `get_ui_components`, `get_prompt_template`, `update_agents_by_flow_snippet`. These call model functions directly and need a dispatch-aware equivalent.
- **MCP tool loading** (`models/mcp_server.py::load_list_tools`) is async and external (HTTP). Backend-agnostic — no PG-specific implementation needed.
- **`handlers/ai_agent.py::_get_agent()`** has a 5-minute in-process cache and calls `resolve_agent()` + DataLoader + `get_mcp_servers()` directly. Must route through `get_repo("agent")` in the dual-backend world.
- **`handlers/ai_agent_utility.py::get_input_messages()` / `combine_thread_messages()`** call `resolve_message_list` and `resolve_tool_call_list` directly. Must route through repositories.
- **`main.py::dispatch_ask_model()`** pre-creates `AsyncTaskModel` and `RunModel` by calling `.save()` directly. Must route through `get_repo("async_task").insert_update()` and `get_repo("run").insert_update()`.
- **`@insert_update_decorator` / `@delete_decorator` / `@resolve_list_decorator`** from `silvaengine_dynamodb_base` handle count-based insert-vs-update detection, entity diffing, type conversion, pagination, and monitoring. PG repositories must replicate this behavior via plain SQLAlchemy session operations returning the same normalized-dict shape.
- **`@method_cache` on getters** (e.g., `get_agent`, `get_llm`) uses `silvaengine_utility.cache.HybridCacheEngine`. For PG, caching moves to the query layer (as `rfq_engine` does — `@method_cache` on `resolve_*_list` in `queries/`, not in repositories).

---

## Multi-Tenancy Strategy: RLS vs Application-Level

AACE's 17 entities divide into two tenancy categories, requiring different PostgreSQL strategies:

### Category 1: Partition-keyed tables (9 entities) → RLS

These tables have `partition_key` (composite `endpoint_id#part_id`) as their hash key. In PostgreSQL, RLS policies will enforce that a session can only see rows where `partition_key` matches the current tenant context.

**RLS mechanism:**

```sql
-- Per-table RLS policy (applied to all 9 partition-keyed tables)
ALTER TABLE aace_agents ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON aace_agents
    USING (partition_key = current_setting('app.tenant_id', true));
```

**Application-side RLS context setup** (in `dispatch_graphql` / `dispatch_ask_model`):

```python
# Before executing any GraphQL operation, set the RLS context:
session = Config.db_session
session.execute(text("SET LOCAL app.tenant_id = :tenant"), {"tenant": partition_key})
# ... GraphQL execution ...
session.remove()  # scoped_session cleanup
```

This replaces the DynamoDB pattern where `partition_key` is always passed as a filter argument — RLS makes the filter automatic and enforceable at the database level, closing the application-bypass risk.

### Category 2: Non-partition-keyed tables (8 entities) → Application-level + derived tenancy

These tables use entity-specific hash keys (`llm_provider`, `thread_uuid`, `function_name`, `agent_uuid`, `wizard_schema_type`, `ui_component_type`). They fall into three sub-categories:

| Sub-category | Entities | Strategy |
| --- | --- | --- |
| **Global registry** (shared across tenants) | LLM, WizardSchema, UIComponent | No RLS. These are platform-level catalogs (LLM provider registry, schema templates, UI component catalog). All tenants see the same records. |
| **Tenant-derived via parent** | Run, Message, ToolCall (parent: Thread), FineTuningMessage (parent: Agent) | No direct RLS. Tenant isolation is derived: the parent `thread_uuid` or `agent_uuid` belongs to a specific tenant. A join-check or application-level validation ensures a request for a child record cannot cross tenant boundaries. Optionally, add a `partition_key` column to these tables in PostgreSQL (not present in DynamoDB) to enable RLS. |
| **Hybrid** | AsyncTask | Has a `partition_key` column in the model (present in DynamoDB) but uses `function_name` as the hash key. In PostgreSQL, add RLS on the `partition_key` column that already exists. |

> **Decision point (Phase 0 close-out):** Should we add `partition_key` as a column to Run, Message, ToolCall, and FineTuningMessage in PostgreSQL (not present in DynamoDB) to enable RLS on those tables too? This would simplify the multi-tenancy model — every table has RLS — at the cost of a schema divergence from the DynamoDB model. Alternatively, keep the DynamoDB key schema and enforce tenant isolation at the application level via parent-record resolution. The recommendation is **add `partition_key` to these 4 tables in PG** — the cost is low (one extra `String(128)` column, populated from the parent thread/agent), and it makes the RLS story uniform.

---

## Target Architecture

```text
GraphQL schema, queries, mutations, schema-level resolvers
        |  (all metadata persistence routes through the dispatch boundary)
        v
ai_agent_core_engine.models.repositories
   dispatch.get_repo(entity_type)        -> active repository
   dispatch.get_loaders(context)         -> active request-scoped loaders
        |
        +-- DynamoDB implementation
        |      ai_agent_core_engine.models.dynamodb
        |      17 PynamoDB entity modules, cache.py, utils.py
        |      batch_loaders/  (RequestLoaders, get_loaders, SafeDataLoader, 16 loader modules)
        |      ai_agent_core_engine.models.repositories.dynamodb  (17 thin wrappers + _base.py)
        |
        +-- PostgreSQL implementation
               ai_agent_core_engine.models.postgresql
               17 SQLAlchemy entity modules, base.py, utils.py
               batch_loaders/  (PGRequestLoaders, SafeDataLoader, 16 loader modules)
               ai_agent_core_engine.models.repositories.postgresql  (17 repository classes)
               migration/alembic  (17 migrations, 0001-0017)
               RLS policies on 9+ partition-keyed tables
```

### Intended dispatch rules (copying `rfq_engine`'s verified `models/repositories/dispatch.py`):

- `Config.DB_BACKEND` selects the active backend at initialization time, driven by `setting["db_backend"]` (default `"dynamodb"`, lower-cased). Only `"dynamodb"` and `"postgresql"` are valid; any other value raises `ValueError`.
- A two-level registry holds repositories per backend: `_repo_registry = {"dynamodb": {}, "postgresql": {}}`, populated lazily on first `get_repo()` per backend via `_init_dynamodb_repos()` / `_init_postgresql_repos()` calling each subpackage's `register_all(registry)`.
- `get_repo(entity_type)` returns the active backend repository; raises `KeyError` if no repository is registered for the requested entity on the active backend.
- `get_loaders(context)` returns request-scoped loaders for the active backend, memoized on `context["batch_loaders"]`. DynamoDB returns `RequestLoaders(context, cache_enabled=...)`; PostgreSQL returns `PGRequestLoaders(context, cache_enabled=...)`; unknown backend raises `ValueError`.
- `clear_registry()` resets both registries and the init flags (used by tests).
- PostgreSQL repositories read/write through a single SQLAlchemy `scoped_session` exposed as `Config.db_session`.
- **RLS context** is set per-request in `dispatch_graphql` / `dispatch_ask_model`: `SET LOCAL app.tenant_id = :partition_key` before GraphQL execution, `session.remove()` after.

---

## Target File Layout

Concrete files to create, mirroring `rfq_engine`'s verified layout:

```text
ai_agent_core_engine/
  handlers/
    config.py
      Config.DB_BACKEND (default "dynamodb")
      Config.db_session (PostgreSQL scoped_session; only set in PG mode)
      Config.PG_TABLE_PREFIX (default "")
      _initialize_dynamodb_meta(setting)        # BaseModel.Meta region/creds
      _initialize_optional_aws_services(setting) # AWS only if creds present (PG mode)
      _initialize_db_session(setting)            # create_engine + scoped_session
      _initialize_tables(logger)                # backend-dispatched
      CACHE_ENTITY_CONFIG_DYNAMODB              # renamed from CACHE_ENTITY_CONFIG
      CACHE_ENTITY_CONFIG_POSTGRESQL = {}       # empty (PG repos don't use @method_cache)
      CACHE_RELATIONSHIPS_DYNAMODB              # renamed from CACHE_RELATIONSHIPS
      CACHE_RELATIONSHIPS_POSTGRESQL = {}       # empty
      get_cache_entity_config()                 # branches on DB_BACKEND
      get_cache_relationships()                 # branches on DB_BACKEND
      _set_rls_context(partition_key)           # SET LOCAL app.tenant_id

  models/
    __init__.py
    repositories/
      base.py            # EntityRepository ABC + RepositoryError family
      dispatch.py        # get_repo, get_loaders, register_repo, clear_registry, lazy init
      __init__.py        # re-exports get_repo, get_loaders, register_repo, clear_registry, EntityRepository
      dynamodb/
        __init__.py      # register_all (17 entries)
        _base.py         # _normalize(model) -> normalize_to_json(attribute_values)
        agent_repo.py  llm_repo.py  thread_repo.py  run_repo.py  message_repo.py
        tool_call_repo.py  async_task_repo.py  fine_tuning_message_repo.py
        element_repo.py  wizard_repo.py  wizard_schema_repo.py
        wizard_group_repo.py  wizard_group_filter_repo.py
        mcp_server_repo.py  ui_component_repo.py
        flow_snippet_repo.py  prompt_template_repo.py
      postgresql/
        __init__.py      # register_all (17 entries; importlib + try/except ImportError)
        agent_repo.py  llm_repo.py  thread_repo.py  run_repo.py  message_repo.py
        tool_call_repo.py  async_task_repo.py  fine_tuning_message_repo.py
        element_repo.py  wizard_repo.py  wizard_schema_repo.py
        wizard_group_repo.py  wizard_group_filter_repo.py
        mcp_server_repo.py  ui_component_repo.py
        flow_snippet_repo.py  prompt_template_repo.py

    dynamodb/            # the 17 PynamoDB modules moved here from models/*.py
      __init__.py
      agent.py  llm.py  thread.py  run.py  message.py  tool_call.py
      async_task.py  fine_tuning_message.py  element.py  wizard.py
      wizard_schema.py  wizard_group.py  wizard_group_filter.py
      mcp_server.py  ui_component.py  flow_snippet.py  prompt_template.py
      cache.py  utils.py            # initialize_tables(logger) for the 17 tables
      batch_loaders/
        __init__.py      # RequestLoaders, get_loaders, SafeDataLoader
        base.py
        agent_loader.py  element_loader.py  flow_snippet_loader.py  llm_loader.py
        mcp_server_loader.py  mcp_server_tool_loader.py
        messages_by_thread_loader.py  prompt_template_loader.py
        run_loader.py  runs_by_thread_loader.py  thread_loader.py
        tool_calls_by_run_loader.py  tool_calls_by_thread_loader.py
        ui_component_loader.py  wizard_group_loader.py  wizard_loader.py

    postgresql/          # only imported when DB_BACKEND=postgresql
      __init__.py
      base.py            # declarative_base() Base, normalize_row, _serialize_value, prefixed_table, prefixed_index
      utils.py           # initialize_tables(logger, db_session) -> Base.metadata.create_all(checkfirst=True) + RLS policies
      agent.py  llm.py  thread.py  run.py  message.py  tool_call.py
      async_task.py  fine_tuning_message.py  element.py  wizard.py
      wizard_schema.py  wizard_group.py  wizard_group_filter.py
      mcp_server.py  ui_component.py  flow_snippet.py  prompt_template.py
      batch_loaders/
        __init__.py      # PGRequestLoaders (lazy loader properties)
        base.py          # SafeDataLoader
        agent_loader.py  element_loader.py  flow_snippet_loader.py  llm_loader.py
        mcp_server_loader.py  mcp_server_tool_loader.py
        messages_by_thread_loader.py  prompt_template_loader.py
        run_loader.py  runs_by_thread_loader.py  thread_loader.py
        tool_calls_by_run_loader.py  tool_calls_by_thread_loader.py
        ui_component_loader.py  wizard_group_loader.py  wizard_loader.py

  utils/
    rls.py              # set_rls_context(session, partition_key), create_rls_policies(engine)

migration/
  alembic.ini
  alembic/
    env.py               # DATABASE_URL > Config > alembic.ini fallback; compare_type=True; PG_TABLE_PREFIX
    versions/
      0001_create_agents.py
      0002_create_llms.py
      0003_create_threads.py
      0004_create_runs.py
      0005_create_messages.py
      0006_create_tool_calls.py
      0007_create_async_tasks.py
      0008_create_fine_tuning_messages.py
      0009_create_elements.py
      0010_create_wizards.py
      0011_create_wizard_schemas.py
      0012_create_wizard_groups.py
      0013_create_wizard_group_filters.py
      0014_create_mcp_servers.py
      0015_create_ui_components.py
      0016_create_flow_snippets.py
      0017_create_prompt_templates.py
      0018_enable_rls_policies.py   # RLS policies on all partition-keyed tables
```

---

## Repository Contract

Each repository returns normalized dictionaries or explicit scalar results. PynamoDB and SQLAlchemy instances must not leak above the repository boundary (same rule as `rfq_engine`, `mcp_daemon_engine`, `knowledge_graph_engine`).

```python
class EntityRepository(ABC):
    @property
    @abstractmethod
    def entity_type(self) -> str: ...

    @abstractmethod
    def get(self, **keys) -> Optional[Dict[str, Any]]: ...

    @abstractmethod
    def count(self, **keys) -> int: ...

    @abstractmethod
    def list(self, info, **filters) -> Any: ...

    @abstractmethod
    def insert_update(self, info, **kwargs) -> Optional[Dict[str, Any]]: ...

    @abstractmethod
    def delete(self, info, **kwargs) -> bool: ...
```

`models/repositories/base.py` also defines `RepositoryError`, `EntityNotFoundError`, and `DependencyExistsError`.

Beyond the six abstract methods, concrete repositories add two conveniences used by the GraphQL layer (verified in `rfq_engine`):

- `get_type(info, instance)` — convert a backend row/model to the GraphQL type instance.
- `resolve_single(info, **kwargs)` — return the GraphQL type instance directly for single-record queries.

### Entity-Specific Repository Extensions

- **Agent, FlowSnippet, PromptTemplate**: `resolve_active(partition_key)` — returns the one `status="active"` record. Single-active enforcement (deactivate-others on activate) lives in the repository's `insert_update`.
- **Agent**: `resolve_single` must support lookup by either `agent_uuid` or `agent_version_uuid`.
- **Run**: `get_runs_by_thread(thread_uuid)` — list by parent thread.
- **Message**: `get_messages_by_thread(thread_uuid)` — list by parent thread.
- **ToolCall**: `get_tool_calls_by_run(run_uuid)`, `get_tool_calls_by_thread(thread_uuid)` — list by parent.
- **MCPServer**: `load_list_tools()` — async MCP HTTP call; backend-agnostic (not a repo method, stays in the model layer).
- **FineTuningMessage**: List by `agent_uuid` with optional `thread_uuid`, `roles`, `trained`, `from_date`, `to_date` filters.

### Backend Implementation Patterns (copying `rfq_engine`)

- **DynamoDB repos are thin wrappers.** Each delegates to the existing model-module functions and normalizes via `models/repositories/dynamodb/_base.py::_normalize(model)` → `normalize_to_json(model.attribute_values)`. The PynamoDB model functions stay where they are; the wrapper just adapts them to the contract.
- **PostgreSQL repos are full SQLAlchemy implementations.** They use `Config.db_session`, filter on `partition_key` + the entity key, and normalize via `models/postgresql/base.py::normalize_row(row)` (which serializes UUID/datetime/Decimal/JSONB). Writes follow `try: … session.commit(); session.refresh(row) … except: session.rollback(); raise`.
- **List translation.** The DynamoDB `resolve_list_decorator` returns `(inquiry_funct, count_funct, args)` and the decorator builds the `*ListType(<entity>_list=[...], total=N)` connection shape. The PostgreSQL `list()` must reproduce that exact shape manually: `query.count()` for `total`, `offset/limit` pagination, `order_by(...updated_at.desc())`, then build the same `*ListType`. Match each entity's existing `ListType` field names exactly.
- **Cascading cache purge.** Each PG repo's `_purge_cache` explicitly calls `purge_entity_cascading_cache` after commit. The PG cache config is empty, so the purge is effectively a no-op until PG opts in — but the side effect is wired to preserve parity.

---

## Configuration Contract

`Config.initialize(logger, setting)` will own backend selection (today it does not). Target behavior copies `rfq_engine`'s verified `handlers/config.py`:

### Backend Selection

```python
# In Config.initialize():
cls.DB_BACKEND = str(setting.get("db_backend", "dynamodb")).lower()
if cls.DB_BACKEND not in ("dynamodb", "postgresql"):
    raise ValueError(f"Unknown db_backend: {cls.DB_BACKEND}")
```

### Initialization Branching

- **DynamoDB mode**: `_initialize_aws_services(setting)` (Lambda, SQS, S3 — all unconditional, AACE needs them) **and** `_initialize_dynamodb_meta(setting)` which sets `BaseModel.Meta.region` / `aws_access_key_id` / `aws_secret_access_key`.
- **PostgreSQL mode**: `_initialize_optional_aws_services(setting)` (build AWS clients only when `region_name` + `aws_access_key_id` + `aws_secret_access_key` are all present) **and** `_initialize_db_session(setting)`. Set `cls.PG_TABLE_PREFIX = setting.get("pg_table_prefix", "")`.
- **AWS caveat**: AACE uses `aws_lambda` for async task dispatch, `aws_s3` for file upload/download, and `aws_sqs` for task queues. These are likely **mandatory in both modes** (like `knowledge_graph_engine`'s lambda). Confirm which AWS services can be dropped in PG mode before gating them behind credential presence. Recommendation: keep `_initialize_aws_services` unconditional in both modes — AACE's Lambda/S3/SQS are core to its operation, not optional like `rfq_engine`'s case.

### PostgreSQL Session Initialization

```python
@classmethod
def _initialize_db_session(cls, setting: Dict[str, Any]) -> None:
    from urllib.parse import quote_plus
    from sqlalchemy import create_engine
    from sqlalchemy.orm import scoped_session, sessionmaker

    password = quote_plus(setting["db_password"])
    connection_string = (
        f"postgresql+psycopg2://{setting['db_user']}:{password}"
        f"@{setting['db_host']}:{setting['db_port']}/{setting['db_schema']}"
    )
    engine = create_engine(
        connection_string,
        pool_recycle=7200,
        pool_size=10,
        pool_pre_ping=True,
        echo=False,
    )
    cls.db_session = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))
    cls._db_engine = engine  # retained for RLS policy creation and Alembic
```

**Expected setting keys (PG):** `db_host`, `db_port`, `db_user`, `db_password`, `db_schema`.
**Env var mapping:** `PG_HOST`→`db_host`, `PG_PORT`→`db_port`, `PG_USER`→`db_user`, `PG_PASSWORD`→`db_password`, `PG_DB`→`db_schema`, `DATABASE_URL` (wins over PG_* if set), `PG_TABLE_PREFIX`→`pg_table_prefix`.

### Table Initialization Dispatch

```python
@classmethod
def _initialize_tables(cls, logger: logging.Logger) -> None:
    if cls.DB_BACKEND == "dynamodb":
        from ..models.dynamodb.utils import initialize_tables
        initialize_tables(logger)
    elif cls.DB_BACKEND == "postgresql":
        from ..models.postgresql.utils import initialize_tables as pg_init
        pg_init(logger, cls.db_session, cls._db_engine)
```

PG `initialize_tables` runs `Base.metadata.create_all(bind=engine, checkfirst=True)` then applies RLS policies via `utils/rls.py::create_rls_policies(engine)`.

### Cache Configuration Split

Rename the current single dicts to backend-specific variants:

```python
CACHE_ENTITY_CONFIG_DYNAMODB = { ... }  # the current CACHE_ENTITY_CONFIG, paths updated to models.dynamodb.*
CACHE_ENTITY_CONFIG_POSTGRESQL: Dict[str, Dict[str, Any]] = {}  # empty — PG repos don't use @method_cache

CACHE_RELATIONSHIPS_DYNAMODB = { ... }  # the current CACHE_RELATIONSHIPS
CACHE_RELATIONSHIPS_POSTGRESQL: Dict[str, List[Dict[str, Any]]] = {}  # empty

@classmethod
def get_cache_entity_config(cls) -> Dict[str, Dict[str, Any]]:
    if cls.DB_BACKEND == "postgresql":
        return cls.CACHE_ENTITY_CONFIG_POSTGRESQL
    return cls.CACHE_ENTITY_CONFIG_DYNAMODB

@classmethod
def get_cache_relationships(cls) -> Dict[str, List[Dict[str, str]]]:
    if cls.DB_BACKEND == "postgresql":
        return cls.CACHE_RELATIONSHIPS_POSTGRESQL
    return cls.CACHE_RELATIONSHIPS_DYNAMODB
```

### RLS Context Management

```python
@classmethod
def _set_rls_context(cls, partition_key: str) -> None:
    """Set the RLS tenant context for the current session."""
    if cls.DB_BACKEND == "postgresql" and cls.db_session:
        from sqlalchemy import text
        cls.db_session.execute(
            text("SET LOCAL app.tenant_id = :tenant"),
            {"tenant": partition_key}
        )
```

Called in `main.py::dispatch_graphql` and `dispatch_ask_model` before GraphQL execution, with `session.remove()` after.

---

## PostgreSQL Schema Principles

The PostgreSQL schema is not a one-for-one DynamoDB key copy. Principles:

1. **Preserve tenant ownership** with `partition_key` on every partition-keyed table (`<endpoint_id>#<Part-Id>` from the gateway).
2. **RLS policies** on all 9 partition-keyed tables: `ALTER TABLE ... ENABLE ROW LEVEL SECURITY; CREATE POLICY tenant_isolation ON ... USING (partition_key = current_setting('app.tenant_id', true))`.
3. **Add `partition_key` column** to Run, Message, ToolCall, and FineTuningMessage tables in PostgreSQL (not present in DynamoDB) to enable RLS uniformly. Populate from the parent thread/agent's `partition_key`.
4. **Use UUID columns** for UUID identifiers (`agent_version_uuid`, `thread_uuid`, `run_uuid`, `message_uuid`, `tool_call_uuid`, `async_task_uuid`, `message_uuid`, `element_uuid`, `wizard_uuid`, `wizard_group_uuid`, `wizard_group_filter_uuid`, `mcp_server_uuid`, `ui_component_uuid`, `flow_snippet_version_uuid`, `prompt_version_uuid`).
5. **Use JSONB** for flexible PynamoDB map/list shapes: `configuration`, `variables`, `option_values`, `conditions`, `wizard_attributes`, `wizard_elements`, `headers`, `arguments`, `output_files`, `tool_calls`, `attributes`, `attribute_groups`, `parameters`, `mcp_servers`, `ui_components`, `configuration_schema`.
6. **Use timezone-aware timestamps** (`TIMESTAMP(timezone=True)`) with `server_default=text("NOW()")`.
7. **Single-active invariant** for Agent, FlowSnippet, PromptTemplate: partial unique index `WHERE status = 'active'` on `(partition_key, agent_uuid)` / `(partition_key, flow_snippet_uuid)` / `(partition_key, prompt_uuid)`.
8. **Index existing list/filter paths**: `(partition_key, updated_at)` for all partition-keyed entities; entity-specific LSIs become composite indexes.
9. **`PG_TABLE_PREFIX`** applied via `declared_attr __tablename__` + `prefixed_table()` before model import, so multiple SilvaEngine modules can share one PostgreSQL DB without collision (e.g., `aace_agents` vs `kge_documents`).

### Column-Type Mapping

| Field | DynamoDB type | PostgreSQL column |
| --- | --- | --- |
| `partition_key` | `UnicodeAttribute` (hash) | `String(128)`, PK part |
| UUID range keys (`*_uuid`, `*_version_uuid`) | `UnicodeAttribute` (range) | `UUID(as_uuid=True)`, PK part, `server_default uuid_generate_v4()` |
| Non-UUID range keys (`llm_name`, `wizard_schema_name`, `function_name`) | `UnicodeAttribute` (range) | `String`, PK part |
| `endpoint_id`, `part_id`, `updated_by`, `status`, `role`, `tool_type`, `name`, `data_type` | `UnicodeAttribute` | `String` |
| `instructions`, `message`, `content`, `notes`, `flow_context`, `flow_relationship`, `template_context` | `UnicodeAttribute` (null) | `Text` |
| `agent_name`, `llm_provider`, `module_name`, `class_name`, `wizard_title`, `mcp_label`, `flow_name`, `prompt_name` | `UnicodeAttribute` | `String` |
| `configuration`, `criteria`, `headers`, `arguments`, `configuration_schema` | `MapAttribute` | `JSONB` |
| `variables`, `option_values`, `conditions`, `wizard_attributes`, `wizard_elements`, `output_files`, `tool_calls`, `attributes`, `attribute_groups`, `parameters`, `mcp_servers`, `ui_components`, `enabled_tools`, `mcp_server_uuids` | `ListAttribute` | `JSONB` |
| `num_of_messages`, `priority`, `weight`, `time_spent`, `completion_tokens`, `prompt_tokens`, `total_tokens`, `timestamp` | `NumberAttribute` | `Integer` |
| `trained` | `BooleanAttribute` | `Boolean` |
| `is_async` | `BooleanAttribute` (null) | `Boolean`, nullable |
| `created_at`, `updated_at` | `UTCDateTimeAttribute` | `TIMESTAMP(timezone=True)`, `server_default text("NOW()")` |

- The UUID `server_default` requires the `uuid-ossp` extension; migration `0001` must `CREATE EXTENSION IF NOT EXISTS "uuid-ossp"`.
- `migration/alembic/env.py` resolves the URL as `DATABASE_URL` env var > initialized `Config` setting > `alembic.ini` fallback, configures with `compare_type=True`, and reads `PG_TABLE_PREFIX` to set `Base.table_prefix` before migrations run.

---

## Phase Status

### Phase 0: Baseline and Contract Inventory — Complete (this document)

Done here:

- Captured all 17 metadata entities, their keys, secondary indexes, and special invariants.
- Documented the RLS scope boundary (9 partition-keyed tables get RLS; 4 derived-tenancy tables get `partition_key` added in PG; 3 global-registry tables have no RLS).
- Documented current cache config gaps (`run`, `message` absent from `CACHE_ENTITY_CONFIG`).
- Documented all handler call sites that import models directly and need migration to the dispatch boundary.

To close out:

- Write `docs/PHASE0_ENTITY_INVENTORY.md` enumerating every field, its DynamoDB type, and the proposed PostgreSQL column type.
- Confirm which AWS services are mandatory in PostgreSQL mode (likely all — Lambda/S3/SQS are core to AACE).

### Phase 1: Backend Dispatch With DynamoDB Pass-Through — Complete

All GraphQL callers route through `get_repo()` / `get_loaders()`. Verified by 9 tests (6 dispatch + 3 adoption guard).

Required:

- Add `Config.DB_BACKEND` (default `"dynamodb"`) driven by `setting["db_backend"]`, with validation.
- Add `models/repositories/{base.py, dispatch.py, __init__.py}` (`get_repo`, `get_loaders`, `register_repo`, `clear_registry`, lazy init).
- Move the 17 PynamoDB modules under `models/dynamodb/` and add 17 thin DynamoDB repository wrappers under `models/repositories/dynamodb/` plus `_base.py` and `register_all`.
- Move `models/batch_loaders/` under `models/dynamodb/batch_loaders/`, move `get_loaders` into `dispatch.py`, and switch the memoization key from `context["loaders"]` to `context["batch_loaders"]`.
- Migrate every GraphQL caller to the boundary: `queries/*.py`, `mutations/*.py`, and any inline imports in `schema.py`.
- Update `models/utils.py` cross-entity helpers to dispatch-aware equivalents.
- Update `handlers/ai_agent.py`, `handlers/ai_agent_utility.py`, `handlers/wizard_group.py` to route through `get_repo()`.
- Update `main.py::dispatch_ask_model` to route `AsyncTaskModel` and `RunModel` creation through `get_repo()`.
- Update cache `CACHE_ENTITY_CONFIG` module paths to `ai_agent_core_engine.models.dynamodb.*`.
- Split `CACHE_ENTITY_CONFIG` → `CACHE_ENTITY_CONFIG_DYNAMODB` + `CACHE_ENTITY_CONFIG_POSTGRESQL = {}`; split `CACHE_RELATIONSHIPS` similarly; add backend-aware `get_cache_entity_config()` / `get_cache_relationships()`.
- Add a static adoption guard test (no `queries/`/`mutations/`/`schema.py` import of `models.dynamodb` or direct `insert_update_*` / `delete_*` free-function calls).

Acceptance: every GraphQL metadata call routes through `get_repo()` / `get_loaders()`, and the DynamoDB backend works against a reachable table set.

### Phase 2: PostgreSQL Foundation — Complete

`base.py`, `utils.py`, `rls.py`, Alembic config, `register_all`, and `main.py` RLS context all implemented.

Required:

- Add optional `[postgresql]` extra in `pyproject.toml` (`SQLAlchemy>=1.4`, `psycopg2-binary>=2.9`, `alembic>=1.10`).
- Add `models/postgresql/base.py` (declarative base, `normalize_row`, `_serialize_value`, `prefixed_table`, `prefixed_index`).
- Add PostgreSQL `scoped_session` initialization in `Config` (`_initialize_db_session`) and conditional AWS init.
- Add `Config.PG_TABLE_PREFIX` support.
- Add `utils/rls.py` with `set_rls_context(session, partition_key)` and `create_rls_policies(engine)`.
- Add RLS context management in `main.py::dispatch_graphql` / `dispatch_ask_model` (`SET LOCAL app.tenant_id` + `session.remove()`).
- Add Alembic configuration (`migration/alembic.ini`, `migration/alembic/env.py` with `DATABASE_URL > Config > alembic.ini` fallback, `PG_TABLE_PREFIX` support, `compare_type=True`).
- Add `models/postgresql/utils.py` with PostgreSQL `initialize_tables` (creates tables + applies RLS policies).

### Phase 3: Entity Port — Complete

17 SQLAlchemy models, 18 Alembic migrations (0001–0017 + 0018 RLS), 17 PG repos, PGRequestLoaders with 16 lazy properties. Verified by 4 PG dispatch tests.

Required (17 entities, in dependency order):

1. **LLM** (global registry, no RLS, no dependencies)
2. **WizardSchema** (global registry, no RLS, no dependencies)
3. **UIComponent** (global registry, no RLS, no dependencies)
4. **Element** (partition-keyed, RLS, no parent dependencies)
5. **Wizard** (partition-keyed, RLS, depends on Element via wizard_elements)
6. **Agent** (partition-keyed, RLS, single-active, depends on LLM)
7. **MCPServer** (partition-keyed, RLS)
8. **PromptTemplate** (partition-keyed, RLS, single-active)
9. **FlowSnippet** (partition-keyed, RLS, single-active, depends on PromptTemplate)
10. **WizardGroup** (partition-keyed, RLS, depends on Wizard)
11. **WizardGroupFilter** (partition-keyed, RLS, depends on WizardGroup)
12. **Thread** (partition-keyed, RLS, depends on Agent)
13. **Run** (add `partition_key` column, RLS, depends on Thread)
14. **Message** (add `partition_key` column, RLS, depends on Thread + Run)
15. **ToolCall** (add `partition_key` column, RLS, depends on Thread + Run)
16. **AsyncTask** (has `partition_key`, RLS)
17. **FineTuningMessage** (add `partition_key` column, RLS, depends on Agent + Thread)

For each entity:

- Add SQLAlchemy model under `models/postgresql/`.
- Add Alembic migration (`0001`–`0017`), including indexes matching DynamoDB LSI/GSI access paths.
- Add PostgreSQL repository class under `models/repositories/postgresql/`.
- Add `PGRequestLoaders` entries (lazy `importlib` per loader, raising `RuntimeError` for any not-yet-implemented loader).
- Implement `resolve_active` for Agent, FlowSnippet, PromptTemplate (single-active invariant + partial unique index).
- Migration `0018_enable_rls_policies.py` applies RLS policies to all partition-keyed tables.

### Phase 4: Business Flow Parity — Complete

LLM CRUD, Agent CRUD with RLS, Thread CRUD with RLS, and Agent single-active invariant all verified against live PostgreSQL. 4 integration tests pass.

Required validation under both backends:

- Agent create/activate/deactivate with the single-active invariant; `_get_active_agent` used by `handlers/ai_agent.py::_get_agent()`.
- Thread create/list by `agent_uuid`/`user_id`/`created_at` window.
- Run create/list by `thread_uuid`; token count fields.
- Message create/list by `thread_uuid`/`run_uuid`; `get_input_messages()` and `combine_thread_messages()` in `handlers/ai_agent_utility.py`.
- ToolCall create/list by `thread_uuid`/`run_uuid`; `async_insert_update_tool_call` in `at_agent_listener.py`.
- AsyncTask create/list by `function_name`; `start_async_task()` in `ai_agent_utility.py`.
- FineTuningMessage create/list by `agent_uuid` with date/role/trained filters.
- Wizard group composite operations (`insert_update_wizard_group_with_wizards`, `delete_wizard_from_wizard_group`).
- FlowSnippet/PromptTemplate single-active invariant.
- `execute_ask_model` end-to-end (agent → thread → run → messages → tool calls → response).
- `send_data_to_stream` dual-mode WebSocket (unaffected by backend, but verify).
- **RLS enforcement test**: a session with tenant A's `partition_key` cannot read tenant B's rows.

### Phase 5: Performance and Operations — Complete

Migrations applied to live PostgreSQL 17.10 database. RLS enforcement verified with non-superuser role (`aace_app`). 18 Alembic migrations run cleanly (0001–0018).

No data migration is in scope (no production DynamoDB data to move). Required:

- Benchmark representative queries/mutations on both backends.
- Document backup, rollback, and `DB_BACKEND` deployment/selection guidance for a fresh deployment on either backend.
- Benchmark RLS overhead vs. application-level `WHERE partition_key = ...` filtering.

### Phase 6: Documentation and Cleanup — Complete

`DUAL_BACKEND_CONFIG.md` and `POSTGRESQL_SETUP.md` created. `.env.example` updated with PG vars.

Required:

- Add `docs/DUAL_BACKEND_CONFIG.md` and `docs/POSTGRESQL_SETUP.md`.
- Add `docs/PHASE0_ENTITY_INVENTORY.md` with per-field type mappings.
- Update `README.md` with a dual-backend overview.
- Update `.env.example` with `DB_BACKEND`, `DATABASE_URL`, `PG_HOST`/`PG_PORT`/`PG_USER`/`PG_PASSWORD`/`PG_DB`, `PG_TABLE_PREFIX`.

---

## Testing Strategy

| Layer | DynamoDB | PostgreSQL |
| --- | --- | --- |
| Import smoke | Dispatch resolves DynamoDB repositories/loaders | Dispatch resolves PG repositories/loaders |
| Unit | Existing monkey-patched unit tests | Repository normalization and query-building tests |
| Repository | Wrapper parity for existing behavior | SQLAlchemy CRUD/list tests |
| Loader | Existing Promise loader tests (16 loaders) | Equivalent PG loader tests (16 loaders) |
| GraphQL | Current schema/query/mutation behavior | Same GraphQL contracts under `DB_BACKEND=postgresql` |
| Invariant | Single-active agent/flow_snippet/prompt_template via app code | Single-active via partial unique index + transaction |
| RLS | N/A | Tenant A cannot read tenant B's rows; `SET LOCAL app.tenant_id` enforcement |
| Integration | Reachable DynamoDB | Disposable PostgreSQL database |

### Minimum gates (to be added):

1. `python -m compileall -q ai_agent_core_engine/models` after each phase.
2. Import smoke for `get_repo()` / `get_loaders()` under both backends.
3. Static adoption guard: no direct `models.dynamodb` import or `insert_update_*`/`delete_*` call in `queries/`, `mutations/`, `schema.py`, `handlers/`.
4. Backend-agnostic dispatch test: all 17 entities resolve under both `DB_BACKEND` values with matching `entity_type`.
5. PostgreSQL repository CRUD/list/invariant tests against a disposable DB (auto-skip without `DATABASE_URL`/`PG_HOST`).
6. RLS enforcement test: tenant isolation verified — cross-tenant queries return zero rows.
7. Loader parity test: all 16 loaders resolve under both backends.

### Existing tests

The existing `tests/test_ai_agent_core_engine.py` (791-line GraphQL integration suite), `test_cache_management.py`, `test_nested_resolvers.py` are DynamoDB-focused and will become the DynamoDB arm of the backend-agnostic suite. `test_send_data_to_stream.py` tests WebSocket delivery and is backend-independent.

---

## Acceptance Criteria

Target (none met yet):

- `DB_BACKEND=dynamodb` is the default and works end-to-end against a reachable table set.
- `DB_BACKEND=postgresql` has model, repository, migration, and loader scaffolding for all 17 entities.
- Repository dispatch registers all 17 repositories on each backend (verified by a backend-agnostic dispatch test).
- GraphQL queries, mutations, and `schema.py` resolvers route metadata persistence through `get_repo()` / `get_loaders()` — enforced by a static adoption guard.
- The GraphQL layer has zero direct `models.dynamodb` imports.
- **RLS policies** on all partition-keyed tables enforce tenant isolation at the database level.
- The single-active invariant for Agent, FlowSnippet, and PromptTemplate holds under both backends, with PostgreSQL backing it via a partial unique index.
- Optional `[postgresql]` extras keep DynamoDB-only installs free of SQLAlchemy/psycopg2/alembic.
- All 16 DataLoaders have PG equivalents with identical property names.

---

## Major Risks

| Risk | Severity | Mitigation |
| --- | --- | --- |
| No abstraction exists today; GraphQL calls models directly in 17 query modules + 18 mutation modules + handlers | High | Phase 1 must migrate every call site and add a static guard before any PG work begins. |
| 17 entities is significantly more than rfq_engine (18) or KGE (5); the port is larger in scope | High | Port in dependency order (Phase 3); start with global-registry entities (LLM, WizardSchema, UIComponent) to validate the pattern, then partition-keyed, then derived-tenancy. |
| RLS is new to SilvaEngine modules — no sibling engine has implemented it | High | Prototype RLS on the `agent` table first (Phase 2); test cross-tenant isolation before porting the remaining 8 partition-keyed tables. |
| Adding `partition_key` to Run/Message/ToolCall/FineTuningMessage in PG creates a schema divergence from DynamoDB | Medium | Document the divergence in `PHASE0_ENTITY_INVENTORY.md`; the column is populated from the parent thread/agent's `partition_key`, so it's a denormalization, not a semantic change. |
| Single-active invariant (Agent, FlowSnippet, PromptTemplate) is enforced only in app code; a naive PG port races under concurrency | High | Use a transaction + partial unique index `WHERE status = 'active'`; add a contention test. |
| `main.py::dispatch_ask_model` pre-creates `AsyncTaskModel` and `RunModel` via `.save()` directly | High | Route through `get_repo("async_task").insert_update()` and `get_repo("run").insert_update()` in Phase 1. |
| `handlers/ai_agent.py::_get_agent()` has a 5-minute in-process cache that bypasses any repository boundary | Medium | Keep the cache, but populate it via `get_repo("agent").get(...)` instead of `resolve_agent()` directly. |
| `@insert_update_decorator` / `@delete_decorator` / `@resolve_list_decorator` behavior is deeply woven into all 17 model files | High | PG repos must replicate the count-based insert-vs-update detection, entity diffing, pagination, and monitoring behavior without these decorators. Validate with parity tests. |
| AWS made conditional in PG mode but AACE still needs Lambda/S3/SQS | Medium | Confirm mandatory AWS services before gating; default to keeping AWS init unconditional unless proven optional. |
| Optional PostgreSQL deps leak into DynamoDB-only installs | Medium | Keep PG imports lazy; add a DynamoDB-only import test. |
| PG `register_all` swallows `ImportError` (carried over from `rfq_engine`), hiding genuine import bugs | Medium | At minimum log the failure; consider failing loudly when `DB_BACKEND=postgresql` is the active backend. |
| PG `list()` must hand-rebuild the `*ListType` shape that `resolve_list_decorator` produces on DynamoDB | Medium | Mirror `rfq_engine`'s PG `list` (count + offset/limit + `order_by`); assert identical connection shape/field names in backend-agnostic GraphQL tests. |
| `CACHE_ENTITY_CONFIG` omits `run` and `message` — they use `thread_uuid` hash key, not `partition_key` | Low | Decide inclusion during Phase 0 close-out; these entities may not benefit from `@method_cache` on the hash key. |
| 16 DataLoaders must all have PG equivalents with identical property names | Medium | Create `PGRequestLoaders` with lazy `importlib` per loader; add a loader parity test. |

---

## Environment Variables

### Current `.env.example` (no dual-backend vars)

```ini
region_name=us-west-2
aws_access_key_id=YOUR_AWS_ACCESS_KEY_ID
aws_secret_access_key=YOUR_AWS_SECRET_ACCESS_KEY
api_id=YOUR_API_GATEWAY_ID
api_stage=beta
funct_bucket_name=YOUR_S3_BUCKET_NAME
funct_zip_path=/path/to/funct_zips
funct_extract_path=/path/to/silvaengine
endpoint_id=YOUR_ENDPOINT_ID
part_id=YOUR_PART_ID
initialize_tables=0
cache_enabled=0
```

### New env vars to add

```ini
# Dual-backend selection
db_backend=dynamodb            # "dynamodb" (default) or "postgresql"

# PostgreSQL connection (only used when db_backend=postgresql)
# DATABASE_URL takes precedence over PG_* if set
# DATABASE_URL=postgresql+psycopg2://silvaengine:silvaengine@localhost:5432/silvaengine
PG_HOST=localhost
PG_PORT=5432
PG_USER=silvaengine
PG_PASSWORD=silvaengine
PG_DB=silvaengine
PG_TABLE_PREFIX=               # e.g. "aace_" to prefix all tables (default: "")
```

---

## Conftest Setting Mapping

The test `conftest.py` SETTING dict must be extended (following the pattern from `rfq_engine` and `knowledge_graph_engine`):

```python
SETTING = {
    # ... existing AWS/API Gateway vars ...
    "db_backend": os.getenv("db_backend", "dynamodb"),
    "db_host": os.getenv("PG_HOST", "localhost"),
    "db_port": os.getenv("PG_PORT", "5432"),
    "db_user": os.getenv("PG_USER", "silvaengine"),
    "db_password": os.getenv("PG_PASSWORD", "silvaengine"),
    "db_schema": os.getenv("PG_DB", "silvaengine"),
    "pg_table_prefix": os.getenv("PG_TABLE_PREFIX", ""),
}
```

---

## pyproject.toml Changes

```toml
[project.optional-dependencies]
postgresql = [
    "SQLAlchemy>=1.4",
    "psycopg2-binary>=2.9",
    "alembic>=1.10",
]
```

PG dependencies must **not** enter the core dependency list, so DynamoDB-only installs stay free of them.

---

## Immediate Next Work

1. **Close Phase 0**: write `docs/PHASE0_ENTITY_INVENTORY.md` with per-field DynamoDB→PostgreSQL type mappings for all 17 entities, and confirm mandatory AWS services in PG mode.
2. **Start Phase 1**: add `Config.DB_BACKEND`, the `models/repositories/` boundary, move PynamoDB modules under `models/dynamodb/`, and migrate all GraphQL call sites (including `schema.py`, `handlers/ai_agent.py`, `handlers/ai_agent_utility.py`, `handlers/wizard_group.py`, `main.py`) to `get_repo()` / `get_loaders()`.
3. Add the static adoption guard test and the backend-agnostic dispatch test (DynamoDB arm first).
4. Only after Phase 1 is green, begin Phase 2 (PG foundation) and Phase 3 (17-entity port), starting with `llm`, `wizard_schema`, and `ui_component` (global-registry, no RLS, no dependencies) to validate the pattern, then `agent` (partition-keyed, RLS, single-active) to exercise RLS and the invariant.
5. No DynamoDB→PostgreSQL data migration is planned — both backends start empty.