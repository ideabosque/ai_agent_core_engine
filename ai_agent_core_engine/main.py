#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function

__author__ = "bibow"

import logging
import uuid
from typing import Any, Dict, List, Optional

import pendulum
from graphene import Schema
from silvaengine_utility import Graphql

from .handlers import ai_agent_listener
from .handlers.ai_agent_utility import generate_async_task_uuid
from .handlers.config import Config
from .schema import Mutations, Query, type_class


# Hook function applied to deployment
def deploy() -> List:
    return [
        {
            "service": "AI Assistant",
            "class": "AIAgentCoreEngine",
            "functions": {
                "ai_agent_core_graphql": {
                    "is_static": False,
                    "label": "AI Agent Core GraphQL",
                    "query": [
                        {"action": "ping", "label": "Ping"},
                        {
                            "action": "llm",
                            "label": "View LLM",
                        },
                        {
                            "action": "llmList",
                            "label": "View LLM List",
                        },
                        {
                            "action": "agent",
                            "label": "View Agent",
                        },
                        {
                            "action": "agentList",
                            "label": "View Agent List",
                        },
                        {
                            "action": "thread",
                            "label": "View Thread",
                        },
                        {
                            "action": "threadList",
                            "label": "View Thread List",
                        },
                        {
                            "action": "run",
                            "label": "View Run",
                        },
                        {
                            "action": "runList",
                            "label": "View Run List",
                        },
                        {
                            "action": "toolCall",
                            "label": "View Tool Call",
                        },
                        {
                            "action": "toolCallList",
                            "label": "View Tool Call List",
                        },
                        {
                            "action": "asyncTask",
                            "label": "View Async Task",
                        },
                        {
                            "action": "asyncTaskList",
                            "label": "View Async Task List",
                        },
                        {
                            "action": "fineTuningMessage",
                            "label": "View Fine Tuning Message",
                        },
                        {
                            "action": "fineTuningMessageList",
                            "label": "View Fine Tuning Message List",
                        },
                        {
                            "action": "promptTemplate",
                            "label": "View Prompt Template",
                        },
                        {
                            "action": "promptTemplateList",
                            "label": "List Prompt Template",
                        },
                        {
                            "action": "askModel",
                            "label": "Ask Model",
                        },
                    ],
                    "mutation": [
                        {
                            "action": "insertUpdateLlm",
                            "label": "Create Update LLM",
                        },
                        {
                            "action": "deleteLlm",
                            "label": "Delete LLM",
                        },
                        {
                            "action": "insertUpdateAgent",
                            "label": "Create Update Agent",
                        },
                        {
                            "action": "deleteAgent",
                            "label": "Delete Agent",
                        },
                        {
                            "action": "insertUpdateThread",
                            "label": "Create Update Thread",
                        },
                        {
                            "action": "deleteThread",
                            "label": "Delete Thread",
                        },
                        {
                            "action": "insertUpdateRun",
                            "label": "Create Update Run",
                        },
                        {
                            "action": "deleteRun",
                            "label": "Delete Run",
                        },
                        {
                            "action": "insertUpdateToolCall",
                            "label": "Create Update Tool Call",
                        },
                        {
                            "action": "deleteToolCall",
                            "label": "Delete Tool Call",
                        },
                        {
                            "action": "insertUpdateAsyncTask",
                            "label": "Create Update Async Task",
                        },
                        {
                            "action": "deleteAsyncTask",
                            "label": "Delete Async Task",
                        },
                        {
                            "action": "insertUpdateFineTuningMessage",
                            "label": "Create Update Fine Tuning Message",
                        },
                        {
                            "action": "deleteFineTuningMessage",
                            "label": "Delete Fine Tuning Message",
                        },
                        {
                            "action": "insertUpdateWizardGroupWithWizards",
                            "label": "Insert Update Wizard Group With Wizards",
                        },
                        {
                            "action": "deleteWizardFromWizardGroup",
                            "label": "Delete Wizard From WizardGroup",
                        },
                    ],
                    "type": "RequestResponse",
                    "support_methods": ["POST"],
                    "is_auth_required": False,
                    "is_graphql": True,
                    "settings": "beta_core_ai_agent",
                    "disabled_in_resources": True,  # Ignore adding to resource list.
                },
                "ai_agent_build_graphql_query": {
                    "is_static": False,
                    "label": "Send Data To WebSocket",
                    "type": "RequestResponse",
                    "support_methods": ["POST"],
                    "is_auth_required": False,
                    "is_graphql": False,
                    "settings": "beta_core_ai_agent",
                    "disabled_in_resources": True,  # Ignore adding to resource list.
                },
                "ask_model": {
                    "is_static": False,
                    "label": "Dispatch Ask Model",
                    "type": "RequestResponse",
                    "support_methods": ["POST"],
                    "is_auth_required": False,
                    "is_graphql": False,
                    "settings": "beta_core_ai_agent",
                    "disabled_in_resources": True,  # Ignore adding to resource list.
                },
                "async_execute_ask_model": {
                    "is_static": False,
                    "label": "Async Execute Ask Model",
                    "type": "Event",
                    "support_methods": ["POST"],
                    "is_auth_required": False,
                    "is_graphql": False,
                    "settings": "beta_core_ai_agent",
                    "disabled_in_resources": True,  # Ignore adding to resource list.
                },
                "async_insert_update_tool_call": {
                    "is_static": False,
                    "label": "Async Insert Update Tool Call",
                    "type": "Event",
                    "support_methods": ["POST"],
                    "is_auth_required": False,
                    "is_graphql": False,
                    "settings": "beta_core_ai_agent",
                    "disabled_in_resources": True,  # Ignore adding to resource list.
                },
                "send_data_to_stream": {
                    "is_static": False,
                    "label": "Send Data To WebSocket",
                    "type": "Event",
                    "support_methods": ["POST"],
                    "is_auth_required": False,
                    "is_graphql": False,
                    "settings": "beta_core_ai_agent",
                    "disabled_in_resources": True,  # Ignore adding to resource list.
                },
            },
        }
    ]


class AIAgentCoreEngine(Graphql):
    def __init__(self, logger: logging.Logger, **setting: Dict[str, Any]) -> None:
        """
        Initialize the AIAgentCoreEngine with the provided logger and settings.

        Args:
            logger (logging.Logger): The logger instance to be used for logging.
            **setting (Dict[str, Any]): A dictionary of settings required to initialize the engine.
        """
        Graphql.__init__(self, logger, **setting)

        # Backend initialization (DynamoDB Meta or PG session) is handled
        # by Config.initialize() based on the db_backend setting.
        Config.initialize(logger, setting)

        # Pre-warm agent cache in a background thread to avoid ~3s MCP
        # tool-loading latency on the first WebSocket request.
        # Supports PREWARM_AGENT_UUIDS env var (comma-separated); if not set,
        # all active agents for the endpoint_id/part_id are auto-discovered.
        self._prewarm_agent_cache(logger, setting)

    def ai_agent_build_graphql_query(self, **params: Dict[str, Any]):
        """
        Build a GraphQL query based on the provided parameters.

        Args:
            params (Dict[str, Any]): A dictionary of parameters required to build the GraphQL query.

        Returns:
            Dict[str, Any]: A dictionary containing the operation name, operation type, and the generated GraphQL query.
        """
        try:
            self._apply_partition_defaults(params)

            context = {
                "endpoint_id": params.get("endpoint_id"),
                "setting": self.setting,
                "logger": self.logger,
            }
            schema = Config.fetch_graphql_schema(
                context,
                params.get("function_name"),
            )

            return Graphql.success_response(
                data={
                    "operation_name": params.get("operation_name"),
                    "operation_type": params.get("operation_type"),
                    "query": Graphql.generate_graphql_operation(
                        params.get("operation_name"),
                        params.get("operation_type"),
                        schema,
                    ),
                }
            )
        except Exception as e:
            return Graphql.error_response(errors=str(e), status_code=500)

    def _apply_partition_defaults(self, params: Dict[str, Any]) -> None:
        """
        Apply default partition values if not provided in params.

        Args:
            params (Dict[str, Any]): A dictionary of parameters required to build the GraphQL query.
        """
        endpoint_id = params.get("endpoint_id", self.setting.get("endpoint_id"))
        part_id = params.get("metadata", {}).get(
            "part_id",
            params.get("part_id", self.setting.get("part_id")),
        )

        if params.get("context") is None:
            params["context"] = {}

        if "endpoint_id" not in params["context"]:
            params["context"]["endpoint_id"] = endpoint_id
        if "part_id" not in params["context"]:
            params["context"]["part_id"] = part_id
        if "connection_id" not in params:
            params["connection_id"] = self.setting.get("connection_id")

        if "partition_key" not in params["context"]:
            # Validate endpoint_id and part_id before creating partition_key
            if not endpoint_id or not part_id:
                self.logger.error(
                    f"Missing endpoint_id or part_id: endpoint_id={endpoint_id}, part_id={part_id}"
                )
                raise ValueError(
                    "Both 'endpoint_id' and 'part_id' are required to generate 'partition_key'."
                )
            else:
                params["context"]["partition_key"] = f"{endpoint_id}#{part_id}"

    def _prewarm_agent_cache(
        self, logger: logging.Logger, setting: Dict[str, Any]
    ) -> None:
        """Pre-warm _get_agent cache in a background daemon thread.

        Loads agent config + LLM config + MCP tools for each agent so the
        first WebSocket request doesn't pay ~3s cold-start latency.
        """
        import os as _os
        import threading as _threading

        def _prewarm():
            try:
                from .handlers.ai_agent import _get_agent
                from .utils.listener import create_listener_info
                from .models.repositories import get_repo

                _endpoint = setting.get("endpoint_id", "")
                _part = setting.get("part_id", "")
                _partition_key = f"{_endpoint}#{_part}" if _endpoint and _part else ""
                if not _partition_key:
                    logger.debug("Pre-warm skipped: no endpoint_id/part_id in setting.")
                    return

                _info = create_listener_info(
                    logger,
                    "ask_model",
                    setting,
                    endpoint_id=_endpoint,
                    part_id=_part,
                    partition_key=_partition_key,
                )

                # Build the list of agent UUIDs to pre-warm.
                # 1. Explicit list via PREWARM_AGENT_UUIDS env var (comma-separated)
                # 2. If not set, discover all active agents for this partition
                _explicit = _os.environ.get("PREWARM_AGENT_UUIDS", "").strip()
                _agent_uuids = []
                if _explicit:
                    _agent_uuids = [
                        u.strip() for u in _explicit.split(",") if u.strip()
                    ]

                if not _agent_uuids:
                    _agent_list = get_repo("agent").list(
                        _info, limit=100, page_number=1
                    )
                    _agent_uuids = [a.agent_uuid for a in _agent_list.agent_list]

                if not _agent_uuids:
                    logger.info("No agents found to pre-warm.")
                    return

                logger.info(f"Pre-warming {len(_agent_uuids)} agent(s): {_agent_uuids}")
                for _uuid in _agent_uuids:
                    try:
                        _get_agent(_info, _uuid)
                        logger.info(f"Pre-warmed agent cache for {_uuid}")
                    except Exception as e:
                        logger.warning(f"Pre-warm failed for agent {_uuid}: {e}")
            except Exception as e:
                logger.debug(f"Agent cache pre-warm skipped: {e}")

        _threading.Thread(target=_prewarm, daemon=True).start()

    def async_execute_ask_model(self, **params: Dict[str, Any]) -> Any:
        """
        Execute an ask model asynchronously based on the provided parameters.

        Args:
            params (Dict[str, Any]): A dictionary of parameters required to execute the ask model.

        Returns:
            Any: The result of the ask model execution.
        """
        self._apply_partition_defaults(params)

        # Defense-in-depth: today this is reached via ``dispatch_ask_model``,
        # which already sets the RLS tenant context. But if this engine method
        # is ever invoked directly (e.g. a pure Lambda dispatch path), the
        # separate DB session would have no ``app.tenant_id`` and every write
        # would be silently rejected by RLS. Re-establish it here to be safe.
        partition_key = params.get("context", {}).get("partition_key")
        if partition_key:
            _set_rls_context(partition_key)
        try:
            return ai_agent_listener.async_execute_ask_model(
                self.logger, self.setting, **params
            )
        finally:
            _clear_rls_context()

    def ask_model(self, **params: Dict[str, Any]) -> Any:
        """Execute ask_model using gateway-initialized settings.

        This is the WebSocket streaming entry point.  The gateway injects
        ``connection_id`` into params so that ``_apply_partition_defaults``
        propagates it into ``context``, which activates streaming mode in
        ``execute_ask_model`` (ai_agent.py:289).

        When ``Config.aws_lambda`` is configured (a real AWS Lambda
        deployment, as opposed to the SilvaEngine Gateway/FastAPI process),
        delegate to the same ``handlers.ai_agent.ask_model`` flow the GraphQL
        ``askModel`` query already uses: it creates the Thread/Run rows and
        dispatches ``async_execute_ask_model`` via ``start_async_task``,
        which is the well-exercised path (vs. hand-rolling record
        pre-creation below for every edge case GraphQL already handles).

        Otherwise, the hand-rolled path below is unchanged: this method is
        the sole source of truth for ``run_uuid`` and ``async_task_uuid`` on
        the WebSocket path, since the gateway forwards the client's message
        unmodified and never generates either id itself. ``async_task_uuid``
        is always server-generated (never taken from the client, since it's
        a tracking id for our own async_task row, not something the caller
        should be able to set or collide on). Both are pre-created (via
        ``_precreate_gateway_records``) before dispatching, because this path
        calls ``async_execute_ask_model`` directly rather than through the
        Lambda invoker the GraphQL path uses, so the ``insert_update_decorator``
        would otherwise raise "Cannot find the async_task" on a count==0 row.
        """
        self._apply_partition_defaults(params)

        # Default arguments to {} when the client doesn't supply it, and
        # write the default back into params (mirroring async_task_uuid
        # below). Without this, params never carries the "arguments" key at
        # all when the client omits it, so the downstream
        # ai_agent_listener.async_execute_ask_model call -- which requires
        # both async_task_uuid and arguments to be present -- rejects the
        # request even though async_task_uuid is always generated.
        arguments = params.get("arguments") or {}
        params["arguments"] = arguments
        partition_key = params.get("context", {}).get("partition_key", "")

        if Config.aws_lambda is not None:
            from .handlers.ai_agent import ask_model as _ai_agent_ask_model
            from .utils.listener import create_listener_info

            info = create_listener_info(self.logger, "ask_model", self.setting, **params)
            result = _ai_agent_ask_model(info, **arguments)
            return result.__dict__ if hasattr(result, "__dict__") else result

        # Default run_uuid when the client doesn't supply one, and always
        # generate async_task_uuid server-side (never trust a client-supplied
        # value). Without a value here, params never carries the key at all,
        # so _precreate_gateway_records short-circuits (no DynamoDB/
        # PostgreSQL async_task row is created to track this request) and the
        # downstream ai_agent_listener.async_execute_ask_model raises a bare
        # KeyError('async_task_uuid') instead of returning a trackable result
        # over the WebSocket connection.
        if arguments and "run_uuid" not in arguments:
            arguments["run_uuid"] = str(uuid.uuid4())
        async_task_uuid = generate_async_task_uuid()
        params["async_task_uuid"] = async_task_uuid

        # Pre-create async_task/thread/run rows before dispatching. When they
        # were created here, tell the core engine to skip its own init write.
        _precreated = self._precreate_gateway_records(
            arguments, async_task_uuid, partition_key, params.get("context", {})
        )
        if not _precreated and partition_key:
            _set_rls_context(partition_key)

        try:
            if _precreated:
                params["_skip_init_write"] = True
            return self.async_execute_ask_model(**params)
        finally:
            _clear_rls_context()

    def _precreate_gateway_records(
        self,
        arguments: Dict[str, Any],
        async_task_uuid: str,
        partition_key: str,
        context: Dict[str, Any],
    ) -> bool:
        """Pre-create the async_task/thread/run rows for the WebSocket path.

        The Lambda path creates these via the invoker; the WebSocket path calls
        ``async_execute_ask_model`` directly, so the ``insert_update_decorator``
        would raise "Cannot find the async_task" on a count==0 row. Returns
        ``True`` when the rows were created (so the caller sets
        ``_skip_init_write``).

        ``async_task_uuid`` is guaranteed non-empty by ``ask_model``, its only
        caller; only ``partition_key`` can legitimately be absent here.
        """
        if not partition_key:
            return False

        run_uuid = arguments.get("run_uuid")
        updated_by = arguments.get("updated_by", "test-user")
        thread_uuid = arguments.get("thread_uuid")

        # Set RLS context for PG mode
        _set_rls_context(partition_key)

        def _precreate_async_task():
            try:
                if Config.DB_BACKEND == "postgresql":
                    from ai_agent_core_engine.models.repositories import get_repo

                    get_repo("async_task").insert_update(
                        None,
                        function_name="async_execute_ask_model",
                        async_task_uuid=async_task_uuid,
                        partition_key=partition_key,
                        output_files=[],
                        status="in_progress",
                        updated_by=updated_by,
                    )
                else:
                    from ai_agent_core_engine.models.dynamodb.async_task import (
                        AsyncTaskModel,
                    )

                    AsyncTaskModel(
                        "async_execute_ask_model",
                        async_task_uuid,
                        partition_key=partition_key,
                        output_files=[],
                        status="in_progress",
                        updated_by=updated_by,
                        created_at=pendulum.now("UTC"),
                        updated_at=pendulum.now("UTC"),
                    ).save()
            except Exception as exc:
                self.logger.warning(
                    "Unable to pre-create async task %s for gateway ask_model: %s",
                    async_task_uuid,
                    exc,
                )

        def _precreate_thread():
            # The gateway streaming path takes ``thread_uuid`` from the client
            # but never persists the thread itself, so runs/messages/tool_calls
            # would reference a thread row that does not exist. Create it here
            # (idempotently) the same way ``_get_thread`` does.
            if not thread_uuid:
                return
            try:
                # NB: the thread model (both backends) has no ``updated_by``
                # field — only these columns/attributes.
                _fields = {
                    "agent_uuid": arguments.get("agent_uuid"),
                    "user_id": arguments.get("user_id"),
                    "endpoint_id": context.get("endpoint_id"),
                    "part_id": context.get("part_id"),
                }
                _fields = {k: v for k, v in _fields.items() if v is not None}
                if Config.DB_BACKEND == "postgresql":
                    from ai_agent_core_engine.models.repositories import get_repo

                    get_repo("thread").insert_update(
                        None,
                        thread_uuid=thread_uuid,
                        partition_key=partition_key,
                        **_fields,
                    )
                else:
                    from ai_agent_core_engine.models.dynamodb.thread import ThreadModel

                    ThreadModel(
                        partition_key,
                        thread_uuid,
                        created_at=pendulum.now("UTC"),
                        **_fields,
                    ).save()
            except Exception as exc:
                self.logger.warning(
                    "Unable to pre-create thread %s for gateway ask_model: %s",
                    thread_uuid,
                    exc,
                )

        def _precreate_run():
            if not (run_uuid and thread_uuid):
                return
            try:
                if Config.DB_BACKEND == "postgresql":
                    from ai_agent_core_engine.models.repositories import get_repo

                    get_repo("run").insert_update(
                        None,
                        thread_uuid=thread_uuid,
                        run_uuid=run_uuid,
                        partition_key=partition_key,
                        prompt_tokens=0,
                        completion_tokens=0,
                        total_tokens=0,
                        updated_by=updated_by,
                    )
                else:
                    from ai_agent_core_engine.models.dynamodb.run import RunModel

                    RunModel(
                        thread_uuid,
                        run_uuid,
                        partition_key=partition_key,
                        prompt_tokens=0,
                        completion_tokens=0,
                        total_tokens=0,
                        updated_by=updated_by,
                        created_at=pendulum.now("UTC"),
                        updated_at=pendulum.now("UTC"),
                    ).save()
            except Exception as exc:
                self.logger.warning(
                    "Unable to pre-create run %s for gateway ask_model: %s",
                    run_uuid,
                    exc,
                )

        # Parallelize the pre-creation writes. thread + run are independent of
        # async_task; the thread has no FK to enforce ordering against the run.
        from concurrent.futures import ThreadPoolExecutor as _TPE

        with _TPE(max_workers=3) as _pool:
            _futures = [
                _pool.submit(_precreate_async_task),
                _pool.submit(_precreate_thread),
                _pool.submit(_precreate_run),
            ]
            for _f in _futures:
                _f.result()
        return True

    def async_insert_update_tool_call(self, **params: Dict[str, Any]) -> Any:
        """
        Insert or update a tool call record asynchronously based on the provided parameters.

        Args:
            params (Dict[str, Any]): A dictionary of parameters required to insert or update the tool call record.
        """
        self._apply_partition_defaults(params)

        # This runs as a separate async invocation with its own DB session, so
        # the RLS tenant context set by the originating request does not carry
        # over. In PostgreSQL mode we must (re)establish it here, otherwise the
        # tool_calls RLS policy rejects the INSERT (app.tenant_id is unset ->
        # NULL) and the tool_call row is silently dropped.
        partition_key = params.get("context", {}).get("partition_key")
        if partition_key:
            _set_rls_context(partition_key)
        try:
            return ai_agent_listener.async_insert_update_tool_call(
                self.logger, self.setting, **params
            )
        finally:
            _clear_rls_context()

    def send_data_to_stream(self, **params: Dict[str, Any]) -> Any:
        """
        Send data to a WebSocket stream based on the provided parameters.

        Args:
            params (Dict[str, Any]): A dictionary of parameters required to send data to the WebSocket stream.
        """
        self._apply_partition_defaults(params)

        return ai_agent_listener.send_data_to_stream(self.logger, **params)

    def ai_agent_core_graphql(self, **params: Dict[str, Any]) -> Any:
        """
        Execute a GraphQL query based on the provided parameters.

        Args:
            params (Dict[str, Any]): A dictionary of parameters required to build the GraphQL query.

        Returns:
            Any: The result of the GraphQL query execution.
        """

        self._apply_partition_defaults(params)

        return self.execute(self.__class__.build_graphql_schema(), **params)

    @staticmethod
    def build_graphql_schema() -> Schema:
        return Schema(
            query=Query,
            mutation=Mutations,
            types=type_class(),
        )


# ---------------------------------------------------------------------------
# Module-level dispatch wrappers for gateway integration
#
# These follow the same pattern as knowledge_graph_engine.main:dispatch_graphql:
# thin module-level functions that build an engine from the initialized Config
# singleton and delegate to the class methods.
#
# The SilvaEngine Gateway resolves these via importlib from routes.yaml:
#   dispatch: "ai_agent_core_engine.main:dispatch_graphql"
#   dispatch: "ai_agent_core_engine.main:dispatch_ask_model"
# ---------------------------------------------------------------------------

# Phase 1.1: Cache the engine instance to avoid re-running Graphql.__init__
# and @graphql_service_initialization on every request.
_engine_instance: Optional["AIAgentCoreEngine"] = None


def _build_engine_from_config() -> "AIAgentCoreEngine":
    """Return a cached engine from the initialized Config singleton.

    The first call constructs the engine; subsequent calls return the
    same instance. ``Config.initialize()`` is already guarded by
    ``_initialized``, so the engine's settings never change after the
    first request.
    """
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = AIAgentCoreEngine(
            Config.get_logger(), **Config.get_setting()
        )
    return _engine_instance


def _set_rls_context(partition_key: str) -> None:
    """Set RLS tenant context for PostgreSQL mode (no-op for DynamoDB)."""
    if Config.DB_BACKEND == "postgresql" and Config.db_session:
        from .utils.rls import set_rls_context

        session = Config.db_session()
        try:
            set_rls_context(session, partition_key)
        except Exception:
            session.rollback()
            raise


def _clear_rls_context() -> None:
    """Clear RLS session after request (PG only)."""
    if Config.DB_BACKEND == "postgresql" and Config.db_session:
        Config.db_session.remove()


def dispatch_graphql(**params: Any) -> Any:
    """Execute a GraphQL query using gateway-initialized settings.

    This is the HTTP GraphQL entry point, matching the pattern used by
    KGE (``knowledge_graph_engine.main:dispatch_graphql``).

    In PostgreSQL mode, sets the RLS tenant context from partition_key
    before GraphQL execution and clears the session after.
    """
    engine = _build_engine_from_config()
    engine._apply_partition_defaults(params)
    partition_key = params.get("context", {}).get("partition_key")
    if partition_key:
        _set_rls_context(partition_key)
    try:
        return engine.ai_agent_core_graphql(**params)
    finally:
        _clear_rls_context()


def dispatch_ask_model(**params: Any) -> Any:
    """WebSocket streaming entry point for ask_model.

    Thin gateway shim: builds the engine from gateway-initialized settings and
    delegates to ``AIAgentCoreEngine.ask_model`` (which pre-creates the
    async_task/thread/run rows and calls ``async_execute_ask_model``).
    """
    return _build_engine_from_config().ask_model(**params)
