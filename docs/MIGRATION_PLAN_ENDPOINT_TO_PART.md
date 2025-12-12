# Migration Plan: endpoint_id → partition_key (Minimal Changes Approach)

> **Migration Status**: Planning Phase
> **Last Updated**: 2025-12-11
> **Target Completion**: TBD
> **Risk Level**: Medium (Controlled Breaking Change)

---

## Executive Summary

### What's Changing?

Migrate from single `endpoint_id` to composite `partition_key` pattern:

**Current State:**
```
endpoint_id = "acme-corp-prod"  (dual purpose)
```

**Target State:**
```
endpoint_id = "aws-prod-us-east-1"  (platform)
part_id = "acme-corp"               (business)
partition_key = "aws-prod-us-east-1#acme-corp"  (composite, assembled in main.py)
```

### Key Principles

**Single Point of Assembly:**
- `partition_key` is assembled **ONCE** in `main.py` (`ai_agent_core_graphql` function)
- Format: `"{endpoint_id}#{part_id}"`
- Passed to all downstream code via context

**Denormalized Attributes:**
- Store `partition_key` as hash key
- Store `endpoint_id` and `part_id` as separate attributes (denormalized)
- No additional indexes needed for endpoint_id/part_id
- Benefits: Simple schema, no extra index maintenance

**Minimal Code Changes:**
- `/models`: Change function signatures from `endpoint_id` to `partition_key`
- `/queries`: Extract `partition_key` from context instead of `endpoint_id`
- `/mutations`: Extract `partition_key` from context instead of `endpoint_id`
- `/types`: Extract `partition_key` from context instead of `endpoint_id`
- No new utility modules needed

**Backward Compatibility:**
- If `part_id` not provided, defaults to `endpoint_id`
- Fallback logic during transition period

---

## 1. Main Entry Point Changes

### 1.1 main.py - Partition Key Assembly

**File:** `ai_agent_core_engine/main.py`

```python
class AIAgentCoreEngine(Graphql):
    def ai_agent_core_graphql(self, **params: Dict[str, Any]) -> Any:
        ## Test the waters before diving in!
        ##<--Testing Data-->##
        if params.get("connection_id") is None:
            params["connection_id"] = self.setting.get("connection_id")
        if params.get("endpoint_id") is None:
            params["endpoint_id"] = self.setting.get("endpoint_id")
        ##<--Testing Data-->##
        
        # NEW: Extract part_id and assemble partition_key
        endpoint_id = params.get("endpoint_id")
        part_id = params.get("part_id")  # From JWT, header, or request body
        
        # Backward compatibility: if part_id not provided, use endpoint_id
        if not part_id:
            part_id = endpoint_id
        
        # Assemble composite partition_key ONCE here
        partition_key = f"{endpoint_id}#{part_id}"
        params["partition_key"] = partition_key  # Add to params
        
        schema = Schema(
            query=Query,
            mutation=Mutations,
            types=type_class(),
        )
        return self.execute(schema, **params)  # partition_key passed to context
```

**Changes:**
- Extract `part_id` from params
- Assemble `partition_key = f"{endpoint_id}#{part_id}"`
- Add `partition_key` to params
- Pass to `self.execute()`

---

## 2. Model Changes

### 2.1 Function Signature Changes

**Before:**
```python
def get_agent(logger, endpoint_id: str, agent_version_uuid: str):
    agent = AgentModel.get(endpoint_id, agent_version_uuid)
    return agent
```

**After (Actual Implementation):**
```python
@method_cache(
    ttl=Config.get_cache_ttl(), cache_name=Config.get_cache_name("models", "agent")
)
def get_agent(partition_key: str, agent_version_uuid: str) -> AgentModel:
    return AgentModel.get(partition_key, agent_version_uuid)
```

**Change:** Replace `endpoint_id` parameter with `partition_key`

**Note:** When creating new records, extract `endpoint_id` and `part_id` from context:

```python
@insert_update_decorator(
    keys={
        "hash_key": "partition_key",
        "range_key": "agent_version_uuid",
    },
    model_funct=get_agent,
    count_funct=get_agent_count,
    type_funct=get_agent_type,
)
def insert_update_agent(info: ResolveInfo, **kwargs) -> Any:
    partition_key = kwargs.get("partition_key")
    agent_version_uuid = kwargs.get("agent_version_uuid")
    
    if kwargs.get("entity") is None:
        cols = {
            "configuration": {},
            "mcp_server_uuids": [],
            "variables": [],
            "updated_by": kwargs["updated_by"],
            "created_at": pendulum.now("UTC"),
            "updated_at": pendulum.now("UTC"),
        }
        
        # ... populate cols with other fields ...
        
        # CRITICAL: Extract denormalized fields from context
        cols["endpoint_id"] = info.context.get("endpoint_id")
        cols["part_id"] = info.context.get("part_id")
        
        AgentModel(
            partition_key,
            agent_version_uuid,
            **convert_decimal_to_number(cols),
        ).save()
        return
```

### 2.2 Model Schema Changes

**Before:**
```python
class AgentModel(BaseModel):
    endpoint_id = UnicodeAttribute(hash_key=True)
    agent_version_uuid = UnicodeAttribute(range_key=True)
```

**After:**
```python
class AgentModel(BaseModel):
    # Primary Key
    partition_key = UnicodeAttribute(hash_key=True)  # Format: "endpoint_id#part_id"
    agent_version_uuid = UnicodeAttribute(range_key=True)

    # Denormalized attributes (for reference/debugging only)
    endpoint_id = UnicodeAttribute()  # Platform partition
    part_id = UnicodeAttribute()      # Business partition

    # Other attributes
    agent_uuid = UnicodeAttribute()
    agent_name = UnicodeAttribute()
    # ... other fields

    # Indexes (all LSI - share same partition_key)
    agent_uuid_index = AgentUuidIndex()  # Existing LSI
    updated_at_index = UpdatedAtIndex()  # Existing LSI
```

**Changes:**
- Rename hash key from `endpoint_id` to `partition_key`
- Add `endpoint_id` and `part_id` as denormalized attributes (for reference only)
- Keep existing LSIs (agent_uuid_index, updated_at_index)
- Update existing LSI classes to use `partition_key` as hash_key

### 2.3 Query Patterns

**Primary Key Query (Most Efficient):**
```python
# Direct lookup with partition_key
partition_key = "aws-prod#acme-corp"
agent = AgentModel.get(partition_key, agent_version_uuid)
```

**Query by agent_uuid using existing LSI:**
```python
# Query all agents with specific agent_uuid within a partition
partition_key = "aws-prod#acme-corp"
agents = AgentModel.agent_uuid_index.query(
    partition_key,
    AgentModel.agent_uuid == agent_uuid
)
```

**Query by updated_at using existing LSI:**
```python
# Query agents by time range within a partition
partition_key = "aws-prod#acme-corp"
agents = AgentModel.updated_at_index.query(
    partition_key,
    AgentModel.updated_at > start_time
)
```

### 2.4 Models Requiring Schema Updates

Apply the same pattern (partition_key + denormalized endpoint_id/part_id + LSIs) to these 9 models:

1. **AgentModel** - `aace-agents`
2. **ThreadModel** - `aace-threads`
3. **PromptTemplateModel** - `aace-prompt_templates`
4. **FlowSnippetModel** - `aace-flow_snippets`
5. **MCPServerModel** - `aace-mcp_servers`
6. **ElementModel** - `aace-elements`
7. **WizardModel** - `aace-wizards`
8. **WizardGroupModel** - `aace-wizard_groups`
9. **WizardGroupFilterModel** - `aace-wizard_group_filters`

**For each model:**
- Change hash key from `endpoint_id` to `partition_key`
- Add `endpoint_id` and `part_id` as UnicodeAttribute fields (denormalized)
- Update existing LSI classes to use `partition_key` as hash_key
- Update create/update functions to populate all three fields

---

## 3. Query Changes (Minimal)

### 3.1 Extract partition_key from Context

**Before:**
```python
def resolve_agent(info: ResolveInfo, **kwargs):
    logger = info.context.get("logger")
    endpoint_id = info.context.get("endpoint_id")
    agent_version_uuid = kwargs.get("agent_version_uuid")
    
    agent = get_agent(logger, endpoint_id, agent_version_uuid)
    return AgentType(**agent.attribute_values) if agent else None
```

**After:**
```python
def resolve_agent(info: ResolveInfo, **kwargs):
    logger = info.context.get("logger")
    partition_key = info.context.get("partition_key")  # CHANGED
    agent_version_uuid = kwargs.get("agent_version_uuid")
    
    agent = get_agent(logger, partition_key, agent_version_uuid)  # CHANGED
    return AgentType(**agent.attribute_values) if agent else None
```

**Change:** Replace `endpoint_id` with `partition_key` from context

---

## 4. Mutation Changes (Minimal)

### 4.1 Extract partition_key from Context

**Before:**
```python
def resolve_insert_update_agent(info: ResolveInfo, **kwargs):
    logger = info.context.get("logger")
    endpoint_id = info.context.get("endpoint_id")
    
    agent = create_agent(logger, endpoint_id, **kwargs)
    return AgentType(**agent.attribute_values)
```

**After:**
```python
def resolve_insert_update_agent(info: ResolveInfo, **kwargs):
    logger = info.context.get("logger")
    partition_key = info.context.get("partition_key")  # CHANGED
    
    agent = create_agent(logger, partition_key, **kwargs)  # CHANGED
    return AgentType(**agent.attribute_values)
```

**Change:** Replace `endpoint_id` with `partition_key` from context

---

## 5. Type Changes (Minimal)

### 5.1 Update TypeBase Schema

**Before:**
```python
class AgentTypeBase(ObjectType):
    endpoint_id = String()
    agent_version_uuid = String()
    agent_uuid = String()
    # ... other fields
```

**After (Actual Implementation):**
```python
class AgentTypeBase(ObjectType):
    # Primary Key
    partition_key = String()  # Composite: "endpoint_id#part_id"
    agent_version_uuid = String()

    # Denormalized attributes
    endpoint_id = String()  # Platform partition
    part_id = String()      # Business partition

    # Agent identifiers
    agent_uuid = String()
    agent_name = String()
    # ... other fields
```

### 5.2 Nested Resolvers

**Before:**
```python
class AgentType(AgentTypeBase):
    def resolve_flow_snippet(parent, info):
        loaders = get_loaders(info.context)
        endpoint_id = info.context.get("endpoint_id")
        
        flow_key = (endpoint_id, parent.flow_snippet_version_uuid)
        return loaders.flow_snippet_loader.load(flow_key)
```

**After (Actual Implementation):**
```python
class AgentType(AgentTypeBase):
    def resolve_flow_snippet(parent, info):
        """Resolve nested FlowSnippet for this agent using DataLoader."""
        from ..models.batch_loaders import get_loaders

        # Check if already embedded
        existing = getattr(parent, "flow_snippet", None)
        if isinstance(existing, dict):
            return [normalize_to_json(flow_snippet_dict) for flow_snippet_dict in existing]

        # Fetch flow snippet if version UUID exists
        partition_key = info.context.get("partition_key")  # CHANGED
        flow_snippet_version_uuid = getattr(parent, "flow_snippet_version_uuid", None)
        if not partition_key or not flow_snippet_version_uuid:
            return None

        loaders = get_loaders(info.context)
        return loaders.flow_snippet_loader.load(
            (partition_key, flow_snippet_version_uuid)  # CHANGED
        ).then(
            lambda flow_snippet_dict: (
                normalize_to_json(flow_snippet_dict) if flow_snippet_dict else None
            )
        )
```

**Change:** Replace `endpoint_id` with `partition_key` from context

---

## 6. Batch Loader Changes (Minimal)

### 6.1 Loader Key Format

**Before:**
```python
class AgentLoader(SafeDataLoader):
    def batch_load_fn(self, keys: List[Tuple[str, str]]):
        # keys = [(endpoint_id, agent_version_uuid), ...]
        for endpoint_id, agent_version_uuid in keys:
            agent = AgentModel.get(endpoint_id, agent_version_uuid)
```

**After:**
```python
class AgentLoader(SafeDataLoader):
    def batch_load_fn(self, keys: List[Tuple[str, str]]):
        # keys = [(partition_key, agent_version_uuid), ...]
        for partition_key, agent_version_uuid in keys:
            agent = AgentModel.get(partition_key, agent_version_uuid)
```

**Change:** Replace `endpoint_id` with `partition_key` in key tuples

---

## 7. Handler Class Attribute Updates

### 7.1 Overview

AI Agent handlers in `../ai_agent_handler/` use partition information for database operations during agent execution.

### 7.2 Handler Instantiation Changes

**Location:** `ai_agent_core_engine/handlers/ai_agent.py`

**Before:**
```python
ai_agent_handler = ai_agent_handler_class(
    info.context.get("logger"),
    agent.__dict__,
    **info.context.get("setting", {}),
)
ai_agent_handler.endpoint_id = endpoint_id
ai_agent_handler.run = run.__dict__
ai_agent_handler.connection_id = connection_id
```

**After:**
```python
# Extract both endpoint_id and part_id from context
endpoint_id = info.context.get("endpoint_id")
part_id = info.context.get("part_id")  # NEW

ai_agent_handler = ai_agent_handler_class(
    info.context.get("logger"),
    agent.__dict__,
    **info.context.get("setting", {}),
)
ai_agent_handler.endpoint_id = endpoint_id  # Platform identifier
ai_agent_handler.part_id = part_id          # NEW: Business partition
ai_agent_handler.run = run.__dict__
ai_agent_handler.connection_id = connection_id
```

**Changes:**
- Extract both `endpoint_id` and `part_id` from context
- Set both on handler instance
- Handlers will construct `partition_key` internally when needed for DB operations

### 7.3 Handler Database Operations

**Before:**
```python
# Inside handler class (e.g., OpenAIHandler, GeminiHandler, AnthropicHandler)
class OpenAIHandler:
    def save_run_data(self, run_data: dict):
        from ..models.run import RunModel
        
        run_model = RunModel()
        run_model.endpoint_id = self.endpoint_id  # OLD
        run_model.run_uuid = run_data["run_uuid"]
        run_model.save()
```

**After:**
```python
# Inside handler class
class OpenAIHandler:
    def save_run_data(self, run_data: dict):
        from ..models.run import RunModel

        # Construct partition_key from endpoint_id and part_id
        partition_key = f"{self.endpoint_id}#{self.part_id}"

        run_model = RunModel()
        run_model.partition_key = partition_key       # Composite key for DB
        run_model.endpoint_id = self.endpoint_id      # Denormalized
        run_model.part_id = self.part_id              # Denormalized
        run_model.run_uuid = run_data["run_uuid"]
        run_model.save()

        # endpoint_id still available for logging
        self.logger.info(f"Saved run for endpoint {self.endpoint_id}")
```

**Changes:**
- Construct `partition_key` from `self.endpoint_id` and `self.part_id`
- Set all three fields: `partition_key`, `endpoint_id`, `part_id`
- `endpoint_id` available for logging, external APIs, etc.

### 7.4 Handler Usage Pattern

Handlers receive both `endpoint_id` and `part_id`:

```python
class OpenAIHandler:
    def __init__(self, logger, agent_dict, **kwargs):
        self.logger = logger
        self.agent = agent_dict
        # Set after instantiation:
        self.endpoint_id = None  # Platform identifier
        self.part_id = None      # Business partition
        self.run = None
        self.connection_id = None

    def _make_partition_key(self) -> str:
        """Helper to construct partition_key from components."""
        return f"{self.endpoint_id}#{self.part_id}"

    def save_to_database(self, data: dict):
        """Save data to database with all required fields."""
        partition_key = self._make_partition_key()

        model = SomeModel()
        model.partition_key = partition_key       # Composite key
        model.endpoint_id = self.endpoint_id      # Denormalized
        model.part_id = self.part_id              # Denormalized
        # ... set other fields
        model.save()

    def call_external_api(self):
        """Use endpoint_id for external API calls if needed."""
        api_url = f"https://api.example.com/{self.endpoint_id}/resource"
        # ...
```

**Key Points:**
- Handlers store `endpoint_id` and `part_id` separately
- Construct `partition_key` when needed for DB operations using helper method
- Set all three fields (`partition_key`, `endpoint_id`, `part_id`) when saving to DB
- Use `endpoint_id` for external APIs, logging, or backward compatibility

### 7.5 Files to Update

**Handler Files (in `../ai_agent_handler/`):**
- OpenAIHandler
- GeminiHandler
- AnthropicHandler
- ClaudeHandler
- OllamaHandler
- Any custom handlers

**Integration Points (in `ai_agent_core_engine/handlers/`):**
- `ai_agent.py` - Handler instantiation (4 locations)
- `ai_agent_utility.py` - Helper functions

### 7.6 Config.get_internal_mcp Updates

**File:** `ai_agent_core_engine/handlers/config.py`

**Before:**
```python
@classmethod
def get_internal_mcp(cls, endpoint_id: str) -> Dict[str, Any] | None:
    if cls.internal_mcp is None:
        return cls.internal_mcp
    internal_mcp = cls.internal_mcp.copy()
    internal_mcp["base_url"] = internal_mcp["base_url"].format(endpoint_id=endpoint_id)
    return internal_mcp
```

**After:**
```python
@classmethod
def get_internal_mcp(cls, endpoint_id: str, part_id: str = None) -> Dict[str, Any] | None:
    if cls.internal_mcp is None:
        return cls.internal_mcp
    internal_mcp = cls.internal_mcp.copy()
    internal_mcp["base_url"] = internal_mcp["base_url"].format(endpoint_id=endpoint_id)
    if part_id and "headers" in internal_mcp:
        internal_mcp["headers"]["X-Part-ID"] = part_id
    return internal_mcp
```

**Usage:**
```python
# Before
internal_mcp = Config.get_internal_mcp(endpoint_id)

# After
endpoint_id = info.context.get("endpoint_id")
part_id = info.context.get("part_id")
internal_mcp = Config.get_internal_mcp(endpoint_id, part_id)
```

**Changes:**
- Add optional `part_id` parameter
- Pass `part_id` to internal MCP server via custom header `X-Part-ID`
- Backward compatible (part_id is optional)

---

## 8. Agent Model Reference Implementation

> **Status**: ✅ COMPLETED
> **Purpose**: Reference implementation for migrating remaining 8 models

### What Was Changed

1. ✅ **Main Entry Point** - main.py (partition_key assembly)
2. ✅ **Model Schema** - agent.py (LSI indexes, denormalized fields)
3. ✅ **CRUD Functions** - agent.py (signature changes)
4. ✅ **Type Resolvers** - types/agent.py (nested resolvers)
5. ✅ **Batch Loaders** - batch_loaders/agent_loader.py (key format)
6. ✅ **Handler Integration** - handlers/ai_agent.py
7. ✅ **Config Updates** - handlers/config.py

### Step-by-Step Implementation Guide

#### Step 1: Update Existing LSI Classes

Change hash_key from `endpoint_id` to `partition_key`:

```python
class AgentUuidIndex(LocalSecondaryIndex):
    partition_key = UnicodeAttribute(hash_key=True)  # Changed
    agent_uuid = UnicodeAttribute(range_key=True)
```

#### Step 2: Update Model Schema

```python
class AgentModel(BaseModel):
    # Primary Key
    partition_key = UnicodeAttribute(hash_key=True)
    agent_version_uuid = UnicodeAttribute(range_key=True)

    # Denormalized attributes (for reference only)
    endpoint_id = UnicodeAttribute()
    part_id = UnicodeAttribute()

    # Other attributes...

    # Indexes (existing LSIs updated to use partition_key)
    agent_uuid_index = AgentUuidIndex()
    updated_at_index = UpdatedAtIndex()
```

#### Step 3: Update CRUD Functions

**get_* functions:**
```python
def get_agent(partition_key: str, agent_version_uuid: str) -> AgentModel:
    return AgentModel.get(partition_key, agent_version_uuid)
```

**resolve_* functions:**
```python
def resolve_agent(info: ResolveInfo, **kwargs) -> AgentType | None:
    partition_key = info.context["partition_key"]
    # Use partition_key for all queries
```

**insert_update_* functions:**
```python
@insert_update_decorator(
    keys={"hash_key": "partition_key", "range_key": "agent_version_uuid"},
    ...
)
def insert_update_agent(info: ResolveInfo, **kwargs) -> Any:
    # Extract denormalized fields from context
    cols["endpoint_id"] = info.context.get("endpoint_id")
    cols["part_id"] = info.context.get("part_id")
    
    AgentModel(partition_key, agent_version_uuid, **cols).save()
```

#### Step 4: Update TypeBase Schema

```python
class AgentTypeBase(ObjectType):
    partition_key = String()
    agent_version_uuid = String()
    endpoint_id = String()
    part_id = String()
    # ... other fields
```

#### Step 5: Update Nested Resolvers

```python
def resolve_mcp_servers(parent, info):
    partition_key = info.context.get("partition_key")
    loaders = get_loaders(info.context)
    promises = [
        loaders.mcp_server_loader.load((partition_key, mcp_uuid))
        for mcp_uuid in mcp_server_uuids
    ]
    return Promise.all(promises).then(filter_results)
```

#### Step 6: Update Batch Loaders

```python
class AgentLoader(SafeDataLoader):
    def batch_load_fn(self, keys: List[Key]) -> Promise:
        for partition_key, agent_uuid in uncached_keys:
            results = AgentModel.agent_uuid_index.query(
                partition_key,
                AgentModel.agent_uuid == agent_uuid,
            )
```

### Checklist for Each Model

- [ ] Update existing LSIs to use partition_key hash key
- [ ] Update Model schema (partition_key, denormalized fields, indexes)
- [ ] Update get_* functions signature
- [ ] Update get_*_count functions signature
- [ ] Update resolve_* functions to extract partition_key from context
- [ ] Update resolve_*_list functions to use partition_key
- [ ] Update insert_update_* decorator and denormalized fields
- [ ] Update delete_* decorator
- [ ] Update TypeBase to include partition_key and part_id fields
- [ ] Update Type nested resolvers
- [ ] Update batch loader key format

### Common Pitfalls

❌ **DON'T**: Parse partition_key to extract endpoint_id/part_id
✅ **DO**: Extract from info.context

❌ **DON'T**: Forget to update excluded_fields in insert_update
✅ **DO**: Add partition_key, endpoint_id, part_id to excluded_fields

❌ **DON'T**: Change queries/mutations files
✅ **DO**: Let decorators handle context extraction

---

## 9. Migration Phases

### Phase 1: Code Changes (Week 1-2)
- [ ] Update `main.py` to assemble `partition_key`
- [ ] Update model schemas (hash key rename)
- [ ] Update model functions (signature changes)
- [ ] Update queries (context extraction)
- [ ] Update mutations (context extraction)
- [ ] Update types (nested resolvers)
- [ ] Update batch loaders (key format)

### Phase 2: Data Migration (Week 3-4)
- [ ] Create migration script
- [ ] Backfill `partition_key` for existing records
- [ ] Validate data integrity

### Phase 3: Testing (Week 5-6)
- [ ] Unit tests
- [ ] Integration tests
- [ ] Load tests

### Phase 4: Deployment (Week 7-8)
- [ ] Deploy to dev
- [ ] Deploy to staging
- [ ] Deploy to production (staged)

---

## 8. File Change Summary

### Files Requiring Changes

**Main Entry Point (1 file):**
- `main.py` - Add partition_key assembly

**Models (9 files):**
- `agent.py` - Change signatures
- `thread.py` - Change signatures
- `prompt_template.py` - Change signatures
- `flow_snippet.py` - Change signatures
- `mcp_server.py` - Change signatures
- `element.py` - Change signatures
- `wizard.py` - Change signatures
- `wizard_group.py` - Change signatures
- `wizard_group_filter.py` - Change signatures

**Queries (9 files):**
- All query resolvers - Extract `partition_key` from context

**Mutations (9 files):**
- All mutation resolvers - Extract `partition_key` from context

**Types (9 files):**
- All type resolvers - Extract `partition_key` from context

**Batch Loaders (9 files):**
- All loaders - Update key format

**Handlers (in `../ai_agent_handler/`):**
- OpenAIHandler
- GeminiHandler
- AnthropicHandler
- ClaudeHandler
- OllamaHandler

**Handler Integration (2 files):**
- `handlers/ai_agent.py` - Handler instantiation
- `handlers/ai_agent_utility.py` - Helper functions

**Total: ~53 files**

---

## 10. Testing Strategy

### Unit Tests
```python
def test_partition_key_assembly():
    engine = AIAgentCoreEngine(logger, **settings)
    params = {"endpoint_id": "aws-prod", "part_id": "acme-corp"}
    
    # Mock execute to capture params
    with patch.object(engine, 'execute') as mock_execute:
        engine.ai_agent_core_graphql(**params)
        
        # Verify partition_key was assembled
        call_args = mock_execute.call_args
        assert call_args[1]["partition_key"] == "aws-prod#acme-corp"
```

### Integration Tests
```python
def test_agent_crud_with_partition_key():
    partition_key = "aws-prod#acme-corp"
    
    # Create
    agent = create_agent(logger, partition_key, agent_uuid="test-agent")
    assert agent.partition_key == partition_key
    
    # Read
    fetched = get_agent(logger, partition_key, agent.agent_version_uuid)
    assert fetched.agent_uuid == "test-agent"
```

---

## 11. Rollback Plan

### Immediate Rollback
1. Revert code deployment
2. Monitor metrics
3. Notify stakeholders

### Data Rollback
1. Restore from backup if needed
2. Re-run validation scripts

---

## Document Version

| Version | Date | Changes |
|---------|------|---------|
| 2.0 | 2025-12-11 | Minimal changes approach with partition_key assembly in main.py |
| 2.1 | 2025-12-11 | Added denormalized endpoint_id/part_id attributes with LSI indexes for better query flexibility |
| 2.2 | 2025-12-11 | Updated handler pattern to use endpoint_id and part_id separately, constructing partition_key internally for DB operations |

---

**End of Document**
