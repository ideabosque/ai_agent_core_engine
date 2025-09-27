# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import logging
from typing import Any, Dict, List


# ===============================
# UNIVERSAL CASCADING CACHE PURGING
# ===============================


def purge_entity_cascading_cache(
    entity_type: str,
    endpoint_id: str = None,
    entity_keys: Dict[str, Any] = None,
    cascade_depth: int = 3,
    logger: logging.Logger = None,
) -> Dict[str, Any]:
    """
    Universal function to purge entity cache with full cascading to child entity list caches.

    Args:
        entity_type: Type of entity ("agent", "thread", "run", etc.)
        endpoint_id: The endpoint ID (if applicable)
        entity_keys: Dict containing entity identification keys
                    e.g., {"agent_uuid": "...", "agent_version_uuid": "..."}
        cascade_depth: How many levels deep to cascade (default: 3)
        logger: Optional logger

    Returns:
        Dict with comprehensive purge operation results
    """
    purge_results = {
        "entity_type": entity_type,
        "entity_keys": entity_keys,
        "individual_cache_cleared": False,
        "list_cache_cleared": False,
        "cascaded_levels": [],
        "total_child_caches_cleared": 0,
        "total_individual_children_cleared": 0,
        "errors": [],
    }

    try:
        # 1. Clear individual entity cache
        if entity_keys:
            try:
                individual_result = _clear_individual_entity_cache(
                    entity_type, endpoint_id, entity_keys, logger
                )
                purge_results["individual_cache_cleared"] = individual_result
            except Exception as e:
                purge_results["errors"].append(
                    f"Error clearing individual {entity_type} cache: {str(e)}"
                )

        # 2. Clear entity list cache
        try:
            list_result = _clear_entity_list_cache(entity_type, logger)
            purge_results["list_cache_cleared"] = list_result
        except Exception as e:
            purge_results["errors"].append(
                f"Error clearing {entity_type} list cache: {str(e)}"
            )

        # 3. Cascade through child entity caches (both list and individual)
        cascade_result = _cascade_purge_child_caches_universal(
            entity_type, endpoint_id, entity_keys, cascade_depth, logger
        )
        purge_results["cascaded_levels"] = cascade_result["cascaded_levels"]
        purge_results["total_child_caches_cleared"] = cascade_result[
            "total_caches_cleared"
        ]
        purge_results["total_individual_children_cleared"] = cascade_result[
            "total_individual_children_cleared"
        ]
        purge_results["errors"].extend(cascade_result["errors"])

    except Exception as e:
        purge_results["errors"].append(
            f"Error in purge_entity_cascading_cache: {str(e)}"
        )
        if logger:
            logger.error(f"Error in purge_entity_cascading_cache: {str(e)}")

    return purge_results


def _clear_individual_entity_cache(
    entity_type: str,
    endpoint_id: str,
    entity_keys: Dict[str, Any],
    logger: logging.Logger = None,
) -> bool:
    """
    Clear individual entity cache based on entity type.

    Args:
        entity_type: Type of entity
        endpoint_id: Endpoint ID
        entity_keys: Entity identification keys
        logger: Optional logger

    Returns:
        bool: True if cache was cleared successfully
    """
    try:
        # Dynamic import of the entity's getter function
        get_func_name = f"get_{entity_type}"
        module_path = f"ai_agent_core_engine.models.{entity_type}"
        entity_module = __import__(module_path, fromlist=[get_func_name])
        get_func = getattr(entity_module, get_func_name)

        if hasattr(get_func, "cache_delete"):
            # Build cache delete parameters based on entity type
            if entity_type == "agent":
                get_func.cache_delete(
                    endpoint_id, entity_keys.get("agent_version_uuid")
                )
            elif entity_type == "thread":
                get_func.cache_delete(endpoint_id, entity_keys.get("thread_uuid"))
            elif entity_type == "run":
                get_func.cache_delete(
                    entity_keys.get("thread_uuid"), entity_keys.get("run_uuid")
                )
            elif entity_type == "message":
                get_func.cache_delete(
                    entity_keys.get("thread_uuid"), entity_keys.get("message_uuid")
                )
            elif entity_type == "tool_call":
                get_func.cache_delete(
                    entity_keys.get("thread_uuid"), entity_keys.get("tool_call_uuid")
                )
            elif entity_type == "llm":
                get_func.cache_delete(
                    entity_keys.get("llm_provider"), entity_keys.get("llm_name")
                )
            elif entity_type == "flow_snippet":
                get_func.cache_delete(
                    endpoint_id, entity_keys.get("flow_snippet_version_uuid")
                )
            elif entity_type == "mcp_server":
                get_func.cache_delete(endpoint_id, entity_keys.get("mcp_server_uuid"))
            elif entity_type == "fine_tuning_message":
                get_func.cache_delete(
                    entity_keys.get("agent_uuid"), entity_keys.get("message_uuid")
                )
            elif entity_type == "async_task":
                get_func.cache_delete(
                    entity_keys.get("function_name"), entity_keys.get("async_task_uuid")
                )
            elif entity_type == "element":
                get_func.cache_delete(endpoint_id, entity_keys.get("element_uuid"))
            elif entity_type == "wizard":
                get_func.cache_delete(endpoint_id, entity_keys.get("wizard_uuid"))
            elif entity_type == "wizard_group":
                get_func.cache_delete(endpoint_id, entity_keys.get("wizard_group_uuid"))
            elif entity_type == "ui_component":
                get_func.cache_delete(
                    entity_keys.get("ui_component_type"),
                    entity_keys.get("ui_component_uuid"),
                )
            elif entity_type == "prompt_template":
                get_func.cache_delete(
                    endpoint_id, entity_keys.get("prompt_version_uuid")
                )
            # Add more entity types as needed

            if logger:
                logger.info(f"Cleared individual {entity_type} cache")
            return True

    except Exception as e:
        if logger:
            logger.error(f"Error clearing individual {entity_type} cache: {str(e)}")

    return False


def _clear_entity_list_cache(entity_type: str, logger: logging.Logger = None) -> bool:
    """
    Clear entity list cache.

    Args:
        entity_type: Type of entity
        logger: Optional logger

    Returns:
        bool: True if cache was cleared successfully
    """
    try:
        list_resolver_name = f"resolve_{entity_type}_list"
        module_path = f"ai_agent_core_engine.queries.{entity_type}"
        queries_module = __import__(module_path, fromlist=[list_resolver_name])
        list_resolver = getattr(queries_module, list_resolver_name)

        if hasattr(list_resolver, "cache_clear"):
            list_resolver.cache_clear()
            if logger:
                logger.info(f"Cleared {entity_type} list cache")
            return True

    except Exception as e:
        if logger:
            logger.error(f"Error clearing {entity_type} list cache: {str(e)}")

    return False


def _cascade_purge_child_caches_universal(
    parent_entity_type: str,
    endpoint_id: str = None,
    parent_entity_keys: Dict[str, Any] = None,
    cascade_depth: int = 3,
    logger: logging.Logger = None,
) -> Dict[str, Any]:
    """
    Universal internal function to handle cascading cache purging using Config relationships.
    Clears both list caches AND individual child entity caches.

    Args:
        parent_entity_type: Starting entity type for cascading
        endpoint_id: Endpoint ID for database queries
        parent_entity_keys: Keys of the parent entity (for finding children)
        cascade_depth: Maximum depth to cascade
        logger: Optional logger

    Returns:
        Dict with cascading results
    """
    cascade_results = {
        "cascaded_levels": [],
        "total_caches_cleared": 0,
        "total_individual_children_cleared": 0,
        "errors": [],
    }

    try:
        from ..handlers.config import Config

        relationships = Config.get_cache_relationships()

        # Use queue for breadth-first cascading
        entities_to_process = [(parent_entity_type, 0)]  # (entity_type, level)
        processed_entities = set()

        while entities_to_process and cascade_depth > 0:
            current_entity, current_level = entities_to_process.pop(0)

            # Avoid processing same entity multiple times
            if current_entity in processed_entities:
                continue

            processed_entities.add(current_entity)
            children = relationships.get(current_entity, [])

            if not children:
                continue

            level_results = {
                "level": current_level,
                "parent_entity": current_entity,
                "child_caches_cleared": [],
                "individual_children_cleared": [],
            }

            for child in children:
                try:
                    # 1. Clear child entity list cache
                    module_name = child["module"]
                    resolver_name = child["list_resolver"]

                    # Import the resolver function
                    module_path = f"ai_agent_core_engine.queries.{module_name}"
                    resolver_module = __import__(module_path, fromlist=[resolver_name])
                    resolver_func = getattr(resolver_module, resolver_name)

                    if hasattr(resolver_func, "cache_clear"):
                        resolver_func.cache_clear()
                        level_results["child_caches_cleared"].append(
                            {
                                "entity_type": child["entity_type"],
                                "resolver": resolver_name,
                                "dependency": child["dependency_key"],
                                "module": module_name,
                            }
                        )
                        cascade_results["total_caches_cleared"] += 1

                        if logger:
                            logger.info(
                                f"L{current_level}: Cleared {child['entity_type']} list cache (child of {current_entity})"
                            )

                    # 2. Clear individual child entity caches
                    if current_level == 0 and parent_entity_keys and endpoint_id:
                        individual_count = _clear_individual_child_entities(
                            current_entity,
                            child,
                            endpoint_id,
                            parent_entity_keys,
                            logger,
                        )
                        if individual_count > 0:
                            level_results["individual_children_cleared"].append(
                                {
                                    "entity_type": child["entity_type"],
                                    "count": individual_count,
                                    "dependency": child["dependency_key"],
                                }
                            )
                            cascade_results[
                                "total_individual_children_cleared"
                            ] += individual_count

                    # Queue child entity for next level processing
                    entities_to_process.append(
                        (child["entity_type"], current_level + 1)
                    )

                except ImportError as e:
                    cascade_results["errors"].append(
                        f"Could not import {module_name}.{resolver_name}: {str(e)}"
                    )
                except AttributeError as e:
                    cascade_results["errors"].append(
                        f"Resolver function not found: {str(e)}"
                    )
                except Exception as e:
                    cascade_results["errors"].append(
                        f"Error clearing {child['entity_type']} cache: {str(e)}"
                    )

            # Add level results if any caches were cleared
            if (
                level_results["child_caches_cleared"]
                or level_results["individual_children_cleared"]
            ):
                cascade_results["cascaded_levels"].append(level_results)

            cascade_depth -= 1

    except Exception as e:
        cascade_results["errors"].append(
            f"Error in _cascade_purge_child_caches_universal: {str(e)}"
        )
        if logger:
            logger.error(f"Error in _cascade_purge_child_caches_universal: {str(e)}")

    return cascade_results


def _clear_individual_child_entities(
    parent_entity_type: str,
    child_config: Dict[str, str],
    endpoint_id: str,
    parent_entity_keys: Dict[str, Any],
    logger: logging.Logger = None,
) -> int:
    """
    Clear individual child entity caches by querying the database for child entities.
    Generic implementation using configuration-driven approach.

    Args:
        parent_entity_type: Type of parent entity ("agent", "thread", etc.)
        child_config: Child configuration from CACHE_RELATIONSHIPS
        endpoint_id: Endpoint ID for database queries
        parent_entity_keys: Keys of the parent entity
        logger: Optional logger

    Returns:
        int: Number of individual child caches cleared
    """
    cleared_count = 0
    child_entity_type = "unknown"  # Initialize for error handling

    try:
        child_entity_type = child_config["entity_type"]
        dependency_key = child_config["dependency_key"]

        # Get the parent key value that the children depend on
        parent_key_value = parent_entity_keys.get(dependency_key)
        if not parent_key_value:
            if logger:
                logger.debug(
                    f"No parent key value found for {dependency_key} in {parent_entity_type} entity keys: {parent_entity_keys}"
                )
            return 0

        # Import the child entity model
        # Convert entity type to proper model class name (e.g., "tool_call" -> "ToolCallModel")
        model_class_name = (
            "".join(word.capitalize() for word in child_entity_type.split("_"))
            + "Model"
        )
        module_path = f"ai_agent_core_engine.models.{child_entity_type}"

        try:
            child_module = __import__(module_path, fromlist=[model_class_name])
            child_model_class = getattr(child_module, model_class_name)
        except (ImportError, AttributeError) as e:
            if logger:
                logger.warning(
                    f"Could not import {model_class_name} from {module_path} for {parent_entity_type}->{child_entity_type} relationship: {str(e)}"
                )
            return 0

        # Import the child entity getter function
        get_func_name = f"get_{child_entity_type}"
        try:
            get_func = getattr(child_module, get_func_name)
        except AttributeError as e:
            if logger:
                logger.warning(
                    f"Could not find {get_func_name} function in {module_path} for {parent_entity_type}->{child_entity_type} relationship: {str(e)}"
                )
            return 0

        if not hasattr(get_func, "cache_delete"):
            if logger:
                logger.debug(
                    f"Function {get_func_name} does not have cache_delete method for {parent_entity_type}->{child_entity_type} relationship"
                )
            return 0

        # Generic approach: try to query child entities using different strategies
        cleared_count = _query_and_clear_child_entities(
            child_model_class=child_model_class,
            child_entity_type=child_entity_type,
            dependency_key=dependency_key,
            parent_key_value=parent_key_value,
            endpoint_id=endpoint_id,
            get_func=get_func,
            parent_entity_type=parent_entity_type,
            logger=logger,
        )

    except Exception as e:
        if logger:
            logger.error(
                f"Error clearing individual {child_entity_type} caches for {parent_entity_type} parent: {str(e)}"
            )

    return cleared_count


def _query_and_clear_child_entities(
    child_model_class: Any,
    child_entity_type: str,
    dependency_key: str,
    parent_key_value: Any,
    endpoint_id: str,
    get_func: Any,
    parent_entity_type: str = "unknown",
    logger: logging.Logger = None,
) -> int:
    """
    Generic function to query and clear child entity caches based on dependency key.

    Args:
        child_model_class: The child entity model class
        child_entity_type: Type of child entity
        dependency_key: The key that links parent to children
        parent_key_value: Value of the parent key
        endpoint_id: Endpoint ID for database queries
        get_func: Cache delete function
        parent_entity_type: Type of parent entity (for logging)
        logger: Optional logger

    Returns:
        int: Number of caches cleared
    """
    cleared_count = 0

    try:
        # Strategy 1: Try using GSI index for the dependency key
        index_name = f"{dependency_key}_index"
        if hasattr(child_model_class, index_name):
            try:
                index = getattr(child_model_class, index_name)

                # Different query patterns based on entity structure
                entities = None

                # Pattern 1: For entities with endpoint_id + dependency_key (like threads with agent_uuid)
                if hasattr(child_model_class, "endpoint_id") and endpoint_id:
                    try:
                        entities = index.query(
                            endpoint_id,
                            getattr(child_model_class, dependency_key)
                            == parent_key_value,
                        )
                    except Exception as pattern_e:
                        if logger:
                            logger.debug(
                                f"Pattern 1 (endpoint_id + {dependency_key}) failed for {parent_entity_type}->{child_entity_type}: {str(pattern_e)}"
                            )

                # Pattern 2: Direct query with parent key value (like runs with thread_uuid)
                if entities is None:
                    try:
                        entities = index.query(parent_key_value)
                    except Exception as pattern_e:
                        if logger:
                            logger.debug(
                                f"Pattern 2 (direct {dependency_key}) failed for {parent_entity_type}->{child_entity_type}: {str(pattern_e)}"
                            )

                # Clear caches if we found entities
                if entities is not None:
                    cleared_count = _clear_entities_cache(
                        entities, child_entity_type, get_func, logger
                    )

                    if logger and cleared_count > 0:
                        logger.info(
                            f"Cleared {cleared_count} individual {child_entity_type} caches using {index_name} for {parent_entity_type} parent"
                        )

                    return cleared_count

            except Exception as e:
                if logger:
                    logger.warning(
                        f"Error using {index_name} for {parent_entity_type}->{child_entity_type}: {str(e)}"
                    )

        # Strategy 2: Try direct query method
        if hasattr(child_model_class, "query"):
            try:
                entities = child_model_class.query(parent_key_value)
                cleared_count = _clear_entities_cache(
                    entities, child_entity_type, get_func, logger
                )

                if logger and cleared_count > 0:
                    logger.info(
                        f"Cleared {cleared_count} individual {child_entity_type} caches using direct query for {parent_entity_type} parent"
                    )

                return cleared_count

            except Exception as e:
                if logger:
                    logger.warning(
                        f"Error using direct query for {parent_entity_type}->{child_entity_type}: {str(e)}"
                    )

        # Strategy 3: Fallback to scan (should be used cautiously)
        if logger:
            logger.warning(
                f"No suitable query method found for {parent_entity_type}->{child_entity_type} with dependency {dependency_key}"
            )

    except Exception as e:
        if logger:
            logger.error(
                f"Error in _query_and_clear_child_entities for {parent_entity_type}->{child_entity_type}: {str(e)}"
            )

    return cleared_count


def _clear_entities_cache(
    entities: Any, child_entity_type: str, get_func: Any, logger: logging.Logger = None
) -> int:
    """
    Generic function to clear cache for a collection of entities.

    Args:
        entities: Iterable of entity objects
        child_entity_type: Type of child entity
        get_func: Cache delete function
        logger: Optional logger

    Returns:
        int: Number of caches cleared
    """
    cleared_count = 0

    try:
        # Check if entities is iterable
        if entities is None:
            if logger:
                logger.debug(f"No entities found for {child_entity_type}")
            return 0

        # Handle both single entities and iterables
        if not hasattr(entities, "__iter__"):
            entities = [entities]

        for entity in entities:
            try:
                # Generic cache clearing based on entity type
                if child_entity_type == "thread":
                    get_func.cache_delete(entity.endpoint_id, entity.thread_uuid)
                elif child_entity_type == "run":
                    get_func.cache_delete(entity.thread_uuid, entity.run_uuid)
                elif child_entity_type == "message":
                    get_func.cache_delete(entity.thread_uuid, entity.message_uuid)
                elif child_entity_type == "tool_call":
                    get_func.cache_delete(entity.thread_uuid, entity.tool_call_uuid)
                elif child_entity_type == "agent":
                    get_func.cache_delete(entity.endpoint_id, entity.agent_version_uuid)
                elif child_entity_type == "llm":
                    get_func.cache_delete(entity.llm_provider, entity.llm_name)
                elif child_entity_type == "flow_snippet":
                    get_func.cache_delete(
                        entity.endpoint_id, entity.flow_snippet_version_uuid
                    )
                elif child_entity_type == "mcp_server":
                    get_func.cache_delete(entity.endpoint_id, entity.mcp_server_uuid)
                elif child_entity_type == "fine_tuning_message":
                    get_func.cache_delete(entity.agent_uuid, entity.message_uuid)
                elif child_entity_type == "async_task":
                    get_func.cache_delete(entity.function_name, entity.async_task_uuid)
                elif child_entity_type == "element":
                    get_func.cache_delete(entity.endpoint_id, entity.element_uuid)
                elif child_entity_type == "wizard":
                    get_func.cache_delete(entity.endpoint_id, entity.wizard_uuid)
                elif child_entity_type == "wizard_group":
                    get_func.cache_delete(entity.endpoint_id, entity.wizard_group_uuid)
                elif child_entity_type == "ui_component":
                    get_func.cache_delete(
                        entity.ui_component_type, entity.ui_component_uuid
                    )
                elif child_entity_type == "prompt_template":
                    get_func.cache_delete(
                        entity.endpoint_id, entity.prompt_version_uuid
                    )
                else:
                    # Generic fallback - try common patterns
                    entity_uuid_attr = f"{child_entity_type}_uuid"
                    if hasattr(entity, entity_uuid_attr):
                        entity_uuid = getattr(entity, entity_uuid_attr)

                        # Try different parameter combinations based on what the entity has
                        cache_cleared = False

                        # Pattern 1: endpoint_id + entity_uuid
                        if hasattr(entity, "endpoint_id") and not cache_cleared:
                            try:
                                get_func.cache_delete(entity.endpoint_id, entity_uuid)
                                cache_cleared = True
                            except Exception as pattern_e:
                                if logger:
                                    logger.debug(
                                        f"Cache delete pattern 1 (endpoint_id + uuid) failed for {child_entity_type}: {str(pattern_e)}"
                                    )

                        # Pattern 2: thread_uuid + entity_uuid
                        if hasattr(entity, "thread_uuid") and not cache_cleared:
                            try:
                                get_func.cache_delete(entity.thread_uuid, entity_uuid)
                                cache_cleared = True
                            except Exception as pattern_e:
                                if logger:
                                    logger.debug(
                                        f"Cache delete pattern 2 (thread_uuid + uuid) failed for {child_entity_type}: {str(pattern_e)}"
                                    )

                        # Pattern 3: agent_uuid + entity_uuid
                        if hasattr(entity, "agent_uuid") and not cache_cleared:
                            try:
                                get_func.cache_delete(entity.agent_uuid, entity_uuid)
                                cache_cleared = True
                            except Exception as pattern_e:
                                if logger:
                                    logger.debug(
                                        f"Cache delete pattern 3 (agent_uuid + uuid) failed for {child_entity_type}: {str(pattern_e)}"
                                    )

                        # Pattern 4: Just the UUID
                        if not cache_cleared:
                            try:
                                get_func.cache_delete(entity_uuid)
                                cache_cleared = True
                            except Exception as pattern_e:
                                if logger:
                                    logger.debug(
                                        f"Cache delete pattern 4 (uuid only) failed for {child_entity_type}: {str(pattern_e)}"
                                    )

                        if not cache_cleared:
                            if logger:
                                logger.warning(
                                    f"Could not determine cache delete parameters for {child_entity_type}"
                                )
                            continue  # Skip this entity

                cleared_count += 1

            except Exception as e:
                if logger:
                    logger.warning(
                        f"Error clearing cache for individual {child_entity_type}: {str(e)}"
                    )

    except Exception as e:
        if logger:
            logger.error(
                f"Error iterating through {child_entity_type} entities: {str(e)}"
            )

    return cleared_count


# ===============================
# AGENT-SPECIFIC WRAPPER FUNCTION
# ===============================


def purge_agent_cascading_cache(
    endpoint_id: str,
    agent_uuid: str = None,
    agent_version_uuid: str = None,
    cascade_depth: int = 3,
    logger: logging.Logger = None,
) -> Dict[str, Any]:
    """
    Agent-specific wrapper for the universal cache purging function.

    Args:
        endpoint_id: The endpoint ID
        agent_uuid: Agent UUID (for child cache clearing)
        agent_version_uuid: Specific agent version UUID (for individual cache clearing)
        cascade_depth: How many levels deep to cascade (default: 3)
        logger: Optional logger

    Returns:
        Dict with comprehensive purge operation results
    """
    entity_keys = {}
    if agent_uuid:
        entity_keys["agent_uuid"] = agent_uuid
    if agent_version_uuid:
        entity_keys["agent_version_uuid"] = agent_version_uuid

    # Use the universal function with agent-specific parameters
    result = purge_entity_cascading_cache(
        entity_type="agent",
        endpoint_id=endpoint_id,
        entity_keys=entity_keys if entity_keys else None,
        cascade_depth=cascade_depth,
        logger=logger,
    )

    # Transform result to match expected agent-specific format for backward compatibility
    agent_result = {
        "agent_uuid": agent_uuid,
        "agent_version_uuid": agent_version_uuid,
        "individual_agent_cache_cleared": result["individual_cache_cleared"],
        "agent_list_cache_cleared": result["list_cache_cleared"],
        "cascaded_levels": result["cascaded_levels"],
        "total_child_caches_cleared": result["total_child_caches_cleared"],
        "total_individual_children_cleared": result.get(
            "total_individual_children_cleared", 0
        ),
        "errors": result["errors"],
    }

    return agent_result


# ===============================
# ENTITY-SPECIFIC WRAPPER FUNCTIONS
# ===============================


def purge_thread_cascading_cache(
    endpoint_id: str,
    thread_uuid: str = None,
    cascade_depth: int = 3,
    logger: logging.Logger = None,
) -> Dict[str, Any]:
    """
    Thread-specific wrapper for the universal cache purging function.

    Args:
        endpoint_id: The endpoint ID
        thread_uuid: Thread UUID (for both individual and child cache clearing)
        cascade_depth: How many levels deep to cascade (default: 3)
        logger: Optional logger

    Returns:
        Dict with comprehensive purge operation results
    """
    entity_keys = {}
    if thread_uuid:
        entity_keys["thread_uuid"] = thread_uuid

    result = purge_entity_cascading_cache(
        entity_type="thread",
        endpoint_id=endpoint_id,
        entity_keys=entity_keys if entity_keys else None,
        cascade_depth=cascade_depth,
        logger=logger,
    )

    # Transform result for backward compatibility
    thread_result = {
        "thread_uuid": thread_uuid,
        "individual_thread_cache_cleared": result["individual_cache_cleared"],
        "thread_list_cache_cleared": result["list_cache_cleared"],
        "cascaded_levels": result["cascaded_levels"],
        "total_child_caches_cleared": result["total_child_caches_cleared"],
        "total_individual_children_cleared": result.get(
            "total_individual_children_cleared", 0
        ),
        "errors": result["errors"],
    }

    return thread_result


def purge_run_cascading_cache(
    thread_uuid: str,
    run_uuid: str = None,
    cascade_depth: int = 3,
    logger: logging.Logger = None,
) -> Dict[str, Any]:
    """
    Run-specific wrapper for the universal cache purging function.

    Args:
        thread_uuid: Thread UUID that the run belongs to
        run_uuid: Run UUID (for both individual and child cache clearing)
        cascade_depth: How many levels deep to cascade (default: 3)
        logger: Optional logger

    Returns:
        Dict with comprehensive purge operation results
    """
    entity_keys = {}
    if thread_uuid:
        entity_keys["thread_uuid"] = thread_uuid
    if run_uuid:
        entity_keys["run_uuid"] = run_uuid

    result = purge_entity_cascading_cache(
        entity_type="run",
        endpoint_id=None,  # Runs don't use endpoint_id directly
        entity_keys=entity_keys if entity_keys else None,
        cascade_depth=cascade_depth,
        logger=logger,
    )

    # Transform result for backward compatibility
    run_result = {
        "thread_uuid": thread_uuid,
        "run_uuid": run_uuid,
        "individual_run_cache_cleared": result["individual_cache_cleared"],
        "run_list_cache_cleared": result["list_cache_cleared"],
        "cascaded_levels": result["cascaded_levels"],
        "total_child_caches_cleared": result["total_child_caches_cleared"],
        "total_individual_children_cleared": result.get(
            "total_individual_children_cleared", 0
        ),
        "errors": result["errors"],
    }

    return run_result


def purge_llm_cascading_cache(
    llm_provider: str,
    llm_name: str = None,
    cascade_depth: int = 3,
    logger: logging.Logger = None,
) -> Dict[str, Any]:
    """
    LLM-specific wrapper for the universal cache purging function.

    Args:
        llm_provider: LLM provider name
        llm_name: LLM name (for individual cache clearing)
        cascade_depth: How many levels deep to cascade (default: 3)
        logger: Optional logger

    Returns:
        Dict with comprehensive purge operation results
    """
    entity_keys = {}
    if llm_provider:
        entity_keys["llm_provider"] = llm_provider
    if llm_name:
        entity_keys["llm_name"] = llm_name

    result = purge_entity_cascading_cache(
        entity_type="llm",
        endpoint_id=None,  # LLMs don't use endpoint_id directly
        entity_keys=entity_keys if entity_keys else None,
        cascade_depth=cascade_depth,
        logger=logger,
    )

    # Transform result for backward compatibility
    llm_result = {
        "llm_provider": llm_provider,
        "llm_name": llm_name,
        "individual_llm_cache_cleared": result["individual_cache_cleared"],
        "llm_list_cache_cleared": result["list_cache_cleared"],
        "cascaded_levels": result["cascaded_levels"],
        "total_child_caches_cleared": result["total_child_caches_cleared"],
        "total_individual_children_cleared": result.get(
            "total_individual_children_cleared", 0
        ),
        "errors": result["errors"],
    }

    return llm_result


def purge_flow_snippet_cascading_cache(
    endpoint_id: str,
    flow_snippet_version_uuid: str = None,
    flow_snippet_uuid: str = None,
    cascade_depth: int = 3,
    logger: logging.Logger = None,
) -> Dict[str, Any]:
    """
    Flow snippet-specific wrapper for the universal cache purging function.

    Args:
        endpoint_id: The endpoint ID
        flow_snippet_version_uuid: Flow snippet version UUID (for individual cache clearing)
        flow_snippet_uuid: Flow snippet UUID (for child cache clearing)
        cascade_depth: How many levels deep to cascade (default: 3)
        logger: Optional logger

    Returns:
        Dict with comprehensive purge operation results
    """
    entity_keys = {}
    if flow_snippet_version_uuid:
        entity_keys["flow_snippet_version_uuid"] = flow_snippet_version_uuid
    if flow_snippet_uuid:
        entity_keys["flow_snippet_uuid"] = flow_snippet_uuid

    result = purge_entity_cascading_cache(
        entity_type="flow_snippet",
        endpoint_id=endpoint_id,
        entity_keys=entity_keys if entity_keys else None,
        cascade_depth=cascade_depth,
        logger=logger,
    )

    # Transform result for backward compatibility
    flow_snippet_result = {
        "flow_snippet_version_uuid": flow_snippet_version_uuid,
        "flow_snippet_uuid": flow_snippet_uuid,
        "individual_flow_snippet_cache_cleared": result["individual_cache_cleared"],
        "flow_snippet_list_cache_cleared": result["list_cache_cleared"],
        "cascaded_levels": result["cascaded_levels"],
        "total_child_caches_cleared": result["total_child_caches_cleared"],
        "total_individual_children_cleared": result.get(
            "total_individual_children_cleared", 0
        ),
        "errors": result["errors"],
    }

    return flow_snippet_result


def purge_mcp_server_cascading_cache(
    endpoint_id: str,
    mcp_server_uuid: str = None,
    cascade_depth: int = 3,
    logger: logging.Logger = None,
) -> Dict[str, Any]:
    """
    MCP server-specific wrapper for the universal cache purging function.

    Args:
        endpoint_id: The endpoint ID
        mcp_server_uuid: MCP server UUID (for both individual and child cache clearing)
        cascade_depth: How many levels deep to cascade (default: 3)
        logger: Optional logger

    Returns:
        Dict with comprehensive purge operation results
    """
    entity_keys = {}
    if mcp_server_uuid:
        entity_keys["mcp_server_uuid"] = mcp_server_uuid

    result = purge_entity_cascading_cache(
        entity_type="mcp_server",
        endpoint_id=endpoint_id,
        entity_keys=entity_keys if entity_keys else None,
        cascade_depth=cascade_depth,
        logger=logger,
    )

    # Transform result for backward compatibility
    mcp_server_result = {
        "mcp_server_uuid": mcp_server_uuid,
        "individual_mcp_server_cache_cleared": result["individual_cache_cleared"],
        "mcp_server_list_cache_cleared": result["list_cache_cleared"],
        "cascaded_levels": result["cascaded_levels"],
        "total_child_caches_cleared": result["total_child_caches_cleared"],
        "total_individual_children_cleared": result.get(
            "total_individual_children_cleared", 0
        ),
        "errors": result["errors"],
    }

    return mcp_server_result


def purge_wizard_group_cascading_cache(
    endpoint_id: str,
    wizard_group_uuid: str = None,
    cascade_depth: int = 3,
    logger: logging.Logger = None,
) -> Dict[str, Any]:
    """
    Wizard group-specific wrapper for the universal cache purging function.

    Args:
        endpoint_id: The endpoint ID
        wizard_group_uuid: Wizard group UUID (for both individual and child cache clearing)
        cascade_depth: How many levels deep to cascade (default: 3)
        logger: Optional logger

    Returns:
        Dict with comprehensive purge operation results
    """
    entity_keys = {}
    if wizard_group_uuid:
        entity_keys["wizard_group_uuid"] = wizard_group_uuid

    result = purge_entity_cascading_cache(
        entity_type="wizard_group",
        endpoint_id=endpoint_id,
        entity_keys=entity_keys if entity_keys else None,
        cascade_depth=cascade_depth,
        logger=logger,
    )

    # Transform result for backward compatibility
    wizard_group_result = {
        "wizard_group_uuid": wizard_group_uuid,
        "individual_wizard_group_cache_cleared": result["individual_cache_cleared"],
        "wizard_group_list_cache_cleared": result["list_cache_cleared"],
        "cascaded_levels": result["cascaded_levels"],
        "total_child_caches_cleared": result["total_child_caches_cleared"],
        "total_individual_children_cleared": result.get(
            "total_individual_children_cleared", 0
        ),
        "errors": result["errors"],
    }

    return wizard_group_result


def purge_wizard_cascading_cache(
    endpoint_id: str,
    wizard_uuid: str = None,
    element_uuids: list = None,
    cascade_depth: int = 3,
    logger: logging.Logger = None,
) -> Dict[str, Any]:
    """
    Wizard-specific wrapper for the universal cache purging function.

    Args:
        endpoint_id: The endpoint ID
        wizard_uuid: Wizard UUID (for individual cache clearing)
        element_uuids: List of element UUIDs (for child cache clearing)
        cascade_depth: How many levels deep to cascade (default: 3)
        logger: Optional logger

    Returns:
        Dict with comprehensive purge operation results
    """
    entity_keys = {}
    if wizard_uuid:
        entity_keys["wizard_uuid"] = wizard_uuid
    if element_uuids:
        entity_keys["element_uuids"] = element_uuids

    result = purge_entity_cascading_cache(
        entity_type="wizard",
        endpoint_id=endpoint_id,
        entity_keys=entity_keys if entity_keys else None,
        cascade_depth=cascade_depth,
        logger=logger,
    )

    # Transform result for backward compatibility
    wizard_result = {
        "wizard_uuid": wizard_uuid,
        "element_uuids": element_uuids,
        "individual_wizard_cache_cleared": result["individual_cache_cleared"],
        "wizard_list_cache_cleared": result["list_cache_cleared"],
        "cascaded_levels": result["cascaded_levels"],
        "total_child_caches_cleared": result["total_child_caches_cleared"],
        "total_individual_children_cleared": result.get(
            "total_individual_children_cleared", 0
        ),
        "errors": result["errors"],
    }

    return wizard_result


def purge_prompt_template_cascading_cache(
    endpoint_id: str,
    prompt_version_uuid: str = None,
    prompt_uuid: str = None,
    cascade_depth: int = 3,
    logger: logging.Logger = None,
) -> Dict[str, Any]:
    """
    Prompt template-specific wrapper for the universal cache purging function.

    Args:
        endpoint_id: The endpoint ID
        prompt_version_uuid: Prompt version UUID (for individual cache clearing)
        prompt_uuid: Prompt UUID (for child cache clearing)
        cascade_depth: How many levels deep to cascade (default: 3)
        logger: Optional logger

    Returns:
        Dict with comprehensive purge operation results
    """
    entity_keys = {}
    if prompt_version_uuid:
        entity_keys["prompt_version_uuid"] = prompt_version_uuid
    if prompt_uuid:
        entity_keys["prompt_uuid"] = prompt_uuid

    result = purge_entity_cascading_cache(
        entity_type="prompt_template",
        endpoint_id=endpoint_id,
        entity_keys=entity_keys if entity_keys else None,
        cascade_depth=cascade_depth,
        logger=logger,
    )

    # Transform result for backward compatibility
    prompt_template_result = {
        "prompt_version_uuid": prompt_version_uuid,
        "prompt_uuid": prompt_uuid,
        "individual_prompt_template_cache_cleared": result["individual_cache_cleared"],
        "prompt_template_list_cache_cleared": result["list_cache_cleared"],
        "cascaded_levels": result["cascaded_levels"],
        "total_child_caches_cleared": result["total_child_caches_cleared"],
        "total_individual_children_cleared": result.get(
            "total_individual_children_cleared", 0
        ),
        "errors": result["errors"],
    }

    return prompt_template_result


def purge_message_cascading_cache(
    thread_uuid: str = None,
    message_uuid: str = None,
    run_uuid: str = None,
    cascade_depth: int = 3,
    logger: logging.Logger = None,
) -> Dict[str, Any]:
    """
    Message-specific wrapper for the universal cache purging function.

    Args:
        thread_uuid: Thread UUID (for identifying message context)
        message_uuid: Message UUID (for individual cache clearing)
        run_uuid: Run UUID (for additional context)
        cascade_depth: How many levels deep to cascade (default: 3)
        logger: Optional logger

    Returns:
        Dict with comprehensive purge operation results
    """
    entity_keys = {}
    if thread_uuid:
        entity_keys["thread_uuid"] = thread_uuid
    if message_uuid:
        entity_keys["message_uuid"] = message_uuid
    if run_uuid:
        entity_keys["run_uuid"] = run_uuid

    result = purge_entity_cascading_cache(
        entity_type="message",
        endpoint_id=None,  # Messages don't use endpoint_id directly
        entity_keys=entity_keys if entity_keys else None,
        cascade_depth=cascade_depth,
        logger=logger,
    )

    # Transform result for backward compatibility
    message_result = {
        "thread_uuid": thread_uuid,
        "message_uuid": message_uuid,
        "run_uuid": run_uuid,
        "individual_message_cache_cleared": result["individual_cache_cleared"],
        "message_list_cache_cleared": result["list_cache_cleared"],
        "cascaded_levels": result["cascaded_levels"],
        "total_child_caches_cleared": result["total_child_caches_cleared"],
        "total_individual_children_cleared": result.get(
            "total_individual_children_cleared", 0
        ),
        "errors": result["errors"],
    }

    return message_result


def purge_tool_call_cascading_cache(
    thread_uuid: str = None,
    tool_call_uuid: str = None,
    cascade_depth: int = 3,
    logger: logging.Logger = None,
) -> Dict[str, Any]:
    """
    Tool call-specific wrapper for the universal cache purging function.

    Args:
        thread_uuid: Thread UUID (for identifying tool call context)
        tool_call_uuid: Tool call UUID (for individual cache clearing)
        cascade_depth: How many levels deep to cascade (default: 3)
        logger: Optional logger

    Returns:
        Dict with comprehensive purge operation results
    """
    entity_keys = {}
    if thread_uuid:
        entity_keys["thread_uuid"] = thread_uuid
    if tool_call_uuid:
        entity_keys["tool_call_uuid"] = tool_call_uuid

    result = purge_entity_cascading_cache(
        entity_type="tool_call",
        endpoint_id=None,  # Tool calls don't use endpoint_id directly
        entity_keys=entity_keys if entity_keys else None,
        cascade_depth=cascade_depth,
        logger=logger,
    )

    # Transform result for backward compatibility
    tool_call_result = {
        "thread_uuid": thread_uuid,
        "tool_call_uuid": tool_call_uuid,
        "individual_tool_call_cache_cleared": result["individual_cache_cleared"],
        "tool_call_list_cache_cleared": result["list_cache_cleared"],
        "cascaded_levels": result["cascaded_levels"],
        "total_child_caches_cleared": result["total_child_caches_cleared"],
        "total_individual_children_cleared": result.get(
            "total_individual_children_cleared", 0
        ),
        "errors": result["errors"],
    }

    return tool_call_result


def purge_fine_tuning_message_cascading_cache(
    agent_uuid: str = None,
    thread_uuid: str = None,
    message_uuid: str = None,
    cascade_depth: int = 3,
    logger: logging.Logger = None,
) -> Dict[str, Any]:
    """
    Fine tuning message-specific wrapper for the universal cache purging function.

    Args:
        agent_uuid: Agent UUID (for identifying fine tuning message context)
        thread_uuid: Thread UUID (for identifying fine tuning message context)
        message_uuid: Message UUID (for individual cache clearing)
        cascade_depth: How many levels deep to cascade (default: 3)
        logger: Optional logger

    Returns:
        Dict with comprehensive purge operation results
    """
    entity_keys = {}
    if agent_uuid:
        entity_keys["agent_uuid"] = agent_uuid
    if thread_uuid:
        entity_keys["thread_uuid"] = thread_uuid
    if message_uuid:
        entity_keys["message_uuid"] = message_uuid

    result = purge_entity_cascading_cache(
        entity_type="fine_tuning_message",
        endpoint_id=None,  # Fine tuning messages don't use endpoint_id directly
        entity_keys=entity_keys if entity_keys else None,
        cascade_depth=cascade_depth,
        logger=logger,
    )

    # Transform result for backward compatibility
    fine_tuning_message_result = {
        "agent_uuid": agent_uuid,
        "thread_uuid": thread_uuid,
        "message_uuid": message_uuid,
        "individual_fine_tuning_message_cache_cleared": result[
            "individual_cache_cleared"
        ],
        "fine_tuning_message_list_cache_cleared": result["list_cache_cleared"],
        "cascaded_levels": result["cascaded_levels"],
        "total_child_caches_cleared": result["total_child_caches_cleared"],
        "total_individual_children_cleared": result.get(
            "total_individual_children_cleared", 0
        ),
        "errors": result["errors"],
    }

    return fine_tuning_message_result


def purge_element_cascading_cache(
    endpoint_id: str,
    element_uuid: str = None,
    cascade_depth: int = 3,
    logger: logging.Logger = None,
) -> Dict[str, Any]:
    """
    Element-specific wrapper for the universal cache purging function.

    Args:
        endpoint_id: The endpoint ID
        element_uuid: Element UUID (for individual cache clearing)
        cascade_depth: How many levels deep to cascade (default: 3)
        logger: Optional logger

    Returns:
        Dict with comprehensive purge operation results
    """
    entity_keys = {}
    if element_uuid:
        entity_keys["element_uuid"] = element_uuid

    result = purge_entity_cascading_cache(
        entity_type="element",
        endpoint_id=endpoint_id,
        entity_keys=entity_keys if entity_keys else None,
        cascade_depth=cascade_depth,
        logger=logger,
    )

    # Transform result for backward compatibility
    element_result = {
        "element_uuid": element_uuid,
        "individual_element_cache_cleared": result["individual_cache_cleared"],
        "element_list_cache_cleared": result["list_cache_cleared"],
        "cascaded_levels": result["cascaded_levels"],
        "total_child_caches_cleared": result["total_child_caches_cleared"],
        "total_individual_children_cleared": result.get(
            "total_individual_children_cleared", 0
        ),
        "errors": result["errors"],
    }

    return element_result


def purge_ui_component_cascading_cache(
    ui_component_type: str = None,
    ui_component_uuid: str = None,
    cascade_depth: int = 3,
    logger: logging.Logger = None,
) -> Dict[str, Any]:
    """
    UI component-specific wrapper for the universal cache purging function.

    Args:
        ui_component_type: UI component type
        ui_component_uuid: UI component UUID (for individual cache clearing)
        cascade_depth: How many levels deep to cascade (default: 3)
        logger: Optional logger

    Returns:
        Dict with comprehensive purge operation results
    """
    entity_keys = {}
    if ui_component_type:
        entity_keys["ui_component_type"] = ui_component_type
    if ui_component_uuid:
        entity_keys["ui_component_uuid"] = ui_component_uuid

    result = purge_entity_cascading_cache(
        entity_type="ui_component",
        endpoint_id=None,  # UI components don't use endpoint_id directly
        entity_keys=entity_keys if entity_keys else None,
        cascade_depth=cascade_depth,
        logger=logger,
    )

    # Transform result for backward compatibility
    ui_component_result = {
        "ui_component_type": ui_component_type,
        "ui_component_uuid": ui_component_uuid,
        "individual_ui_component_cache_cleared": result["individual_cache_cleared"],
        "ui_component_list_cache_cleared": result["list_cache_cleared"],
        "cascaded_levels": result["cascaded_levels"],
        "total_child_caches_cleared": result["total_child_caches_cleared"],
        "total_individual_children_cleared": result.get(
            "total_individual_children_cleared", 0
        ),
        "errors": result["errors"],
    }

    return ui_component_result


def purge_async_task_cascading_cache(
    function_name: str = None,
    async_task_uuid: str = None,
    cascade_depth: int = 3,
    logger: logging.Logger = None,
) -> Dict[str, Any]:
    """
    Async task-specific wrapper for the universal cache purging function.

    Args:
        function_name: Function name (for identifying async task context)
        async_task_uuid: Async task UUID (for individual cache clearing)
        cascade_depth: How many levels deep to cascade (default: 3)
        logger: Optional logger

    Returns:
        Dict with comprehensive purge operation results
    """
    entity_keys = {}
    if function_name:
        entity_keys["function_name"] = function_name
    if async_task_uuid:
        entity_keys["async_task_uuid"] = async_task_uuid

    result = purge_entity_cascading_cache(
        entity_type="async_task",
        endpoint_id=None,  # Async tasks don't use endpoint_id directly
        entity_keys=entity_keys if entity_keys else None,
        cascade_depth=cascade_depth,
        logger=logger,
    )

    # Transform result for backward compatibility
    async_task_result = {
        "function_name": function_name,
        "async_task_uuid": async_task_uuid,
        "individual_async_task_cache_cleared": result["individual_cache_cleared"],
        "async_task_list_cache_cleared": result["list_cache_cleared"],
        "cascaded_levels": result["cascaded_levels"],
        "total_child_caches_cleared": result["total_child_caches_cleared"],
        "total_individual_children_cleared": result.get(
            "total_individual_children_cleared", 0
        ),
        "errors": result["errors"],
    }

    return async_task_result