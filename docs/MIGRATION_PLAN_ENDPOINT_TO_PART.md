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

**Denormalized Attributes + LSI:**
- Store `partition_key` as hash key
- Store `endpoint_id` and `part_id` as separate attributes (denormalized)
- Create Local Secondary Indexes (LSI) on `endpoint_id` and `part_id`
- Benefits: Query flexibility, strongly consistent reads, no extra write capacity

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

**After:**
```python
def get_agent(logger, partition_key: str, agent_version_uuid: str):
    agent = AgentModel.get(partition_key, agent_version_uuid)
    return agent
```

**Change:** Replace `endpoint_id` parameter with `partition_key`

**Note:** When creating new records, both `partition_key` and denormalized `endpoint_id`/`part_id` must be set:

```python
def create_agent(logger, partition_key: str, **kwargs):
    # Parse partition_key to extract components
    endpoint_id, part_id = partition_key.split('#', 1)

    agent = AgentModel()
    agent.partition_key = partition_key
    agent.endpoint_id = endpoint_id     # Denormalized
    agent.part_id = part_id             # Denormalized
    agent.agent_version_uuid = str(uuid.uuid4())
    # ... set other attributes
    agent.save()
    return agent
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
class EndpointIdIndex(LocalSecondaryIndex):
    """LSI for querying by endpoint_id within same partition."""
    class Meta:
        index_name = "endpoint_id-index"
        projection = AllProjection()

    partition_key = UnicodeAttribute(hash_key=True)
    endpoint_id = UnicodeAttribute(range_key=True)


class PartIdIndex(LocalSecondaryIndex):
    """LSI for querying by part_id within same partition."""
    class Meta:
        index_name = "part_id-index"
        projection = AllProjection()

    partition_key = UnicodeAttribute(hash_key=True)
    part_id = UnicodeAttribute(range_key=True)


class AgentModel(BaseModel):
    # Primary Key
    partition_key = UnicodeAttribute(hash_key=True)  # Format: "endpoint_id#part_id"
    agent_version_uuid = UnicodeAttribute(range_key=True)

    # Denormalized attributes for indexing
    endpoint_id = UnicodeAttribute()  # Platform partition
    part_id = UnicodeAttribute()      # Business partition

    # Other attributes
    agent_uuid = UnicodeAttribute()
    agent_name = UnicodeAttribute()
    # ... other fields

    # Indexes (all LSI - share same partition_key)
    endpoint_id_index = EndpointIdIndex()
    part_id_index = PartIdIndex()
    agent_uuid_index = AgentUuidIndex()  # Existing LSI
    updated_at_index = UpdatedAtIndex()  # Existing LSI
```

**Changes:**
- Rename hash key from `endpoint_id` to `partition_key`
- Add `endpoint_id` and `part_id` as denormalized attributes
- Add Local Secondary Indexes (LSI) for both `endpoint_id` and `part_id`
- All indexes share the same partition_key (LSI requirement)
- Keep existing LSIs for backward compatibility

**Benefits of LSI over GSI:**
- Strongly consistent reads
- No additional write capacity units required
- Automatically updated with base table writes
- Lower cost (no separate provisioning)

### 2.3 Query Patterns with LSI

**Primary Key Query (Most Efficient):**
```python
# Direct lookup with partition_key
partition_key = "aws-prod#acme-corp"
agent = AgentModel.get(partition_key, agent_version_uuid)
```

**Query by endpoint_id using LSI:**
```python
# Query all agents with specific endpoint_id within a partition
partition_key = "aws-prod#acme-corp"
agents = AgentModel.endpoint_id_index.query(
    hash_key=partition_key,
    range_key_condition=AgentModel.endpoint_id == "aws-prod"
)
```

**Query by part_id using LSI:**
```python
# Query all agents with specific part_id within a partition
partition_key = "aws-prod#acme-corp"
agents = AgentModel.part_id_index.query(
    hash_key=partition_key,
    range_key_condition=AgentModel.part_id == "acme-corp"
)
```

**Note:** LSI queries require the partition_key (hash key) to be specified. This is efficient because each partition_key already contains the endpoint_id and part_id information.

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
- Add `endpoint_id` and `part_id` as UnicodeAttribute fields
- Add `endpoint_id_index` LSI
- Add `part_id_index` LSI
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

### 5.1 Nested Resolvers

**Before:**
```python
class AgentType(graphene.ObjectType):
    def resolve_flow_snippet(self, info: ResolveInfo):
        loaders = get_loaders(info.context)
        endpoint_id = info.context.get("endpoint_id")
        
        flow_key = (endpoint_id, self.flow_snippet_version_uuid)
        return loaders.flow_snippet_loader.load(flow_key)
```

**After:**
```python
class AgentType(graphene.ObjectType):
    def resolve_flow_snippet(self, info: ResolveInfo):
        loaders = get_loaders(info.context)
        partition_key = info.context.get("partition_key")  # CHANGED
        
        flow_key = (partition_key, self.flow_snippet_version_uuid)  # CHANGED
        return loaders.flow_snippet_loader.load(flow_key)
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
# Extract both from context
endpoint_id = info.context.get("endpoint_id")
partition_key = info.context.get("partition_key")

ai_agent_handler = ai_agent_handler_class(
    info.context.get("logger"),
    agent.__dict__,
    **info.context.get("setting", {}),
)
ai_agent_handler.endpoint_id = endpoint_id        # Keep for backward compatibility
ai_agent_handler.partition_key = partition_key    # NEW: Add partition_key
ai_agent_handler.run = run.__dict__
ai_agent_handler.connection_id = connection_id
```

**Changes:** 
- Extract both `endpoint_id` and `partition_key` from context
- Set both on handler instance
- `endpoint_id` for backward compatibility and non-DB operations
- `partition_key` for database operations

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
        
        run_model = RunModel()
        run_model.partition_key = self.partition_key  # CHANGED: Use partition_key for DB
        run_model.run_uuid = run_data["run_uuid"]
        run_model.save()
        
        # endpoint_id still available if needed for logging
        self.logger.info(f"Saved run for endpoint {self.endpoint_id}")
```

**Changes:** 
- Use `self.partition_key` for database operations
- `self.endpoint_id` still available for logging, external APIs, etc.

### 7.4 Handler Usage Pattern

Handlers receive both `endpoint_id` and `partition_key`:

```python
class OpenAIHandler:
    def __init__(self, logger, agent_dict, **kwargs):
        self.logger = logger
        self.agent = agent_dict
        # Set after instantiation:
        self.endpoint_id = None      # Platform identifier (for non-DB operations)
        self.partition_key = None    # Composite key (for DB operations)
        self.run = None
        self.connection_id = None
    
    def save_to_database(self, data: dict):
        """Use partition_key for database operations."""
        model = SomeModel()
        model.partition_key = self.partition_key  # Use partition_key
        model.save()
    
    def call_external_api(self):
        """Use endpoint_id for external API calls if needed."""
        api_url = f"https://api.example.com/{self.endpoint_id}/resource"
        # ...
```

**Key Points:**
- Use `partition_key` for all database operations
- Use `endpoint_id` for external APIs, logging, or backward compatibility
- Both values available in handler

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

## 8. Migration Phases

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

---

**End of Document**
