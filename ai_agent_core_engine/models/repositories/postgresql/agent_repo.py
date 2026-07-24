# -*- coding: utf-8 -*-
"""PostgreSQL repository for agent entity.

Implements get/count/list/insert_update/delete + get_type/resolve_single
and the single-active invariant (resolve_active / deactivate-others).
"""
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict, List, Optional

import pendulum
from sqlalchemy import and_, or_

from ..base import EntityRepository
from ...postgresql.agent import AgentModel
from ...postgresql.base import normalize_row
from ._base import (
    _apply_pagination,
    _get_logger,
    _get_partition_key,
    _get_updated_by,
    _normalize,
    _purge_cache,
)

_PK_FIELDS = ("partition_key", "agent_version_uuid")
_UPDATABLE_FIELDS = (
    "agent_uuid",
    "agent_name",
    "agent_description",
    "llm_provider",
    "llm_name",
    "instructions",
    "configuration",
    "mcp_server_uuids",
    "variables",
    "num_of_messages",
    "tool_call_role",
    "flow_snippet_version_uuid",
    "status",
    "updated_by",
    "endpoint_id",
    "part_id",
)


class AgentRepository(EntityRepository):
    """PostgreSQL repository for agent entity."""

    @property
    def entity_type(self) -> str:
        return "agent"

    # ---- read ----

    def get(self, **keys: Any) -> Optional[Dict[str, Any]]:
        partition_key = keys.get("partition_key")
        agent_version_uuid = keys.get("agent_version_uuid")
        if not partition_key or not agent_version_uuid:
            return None
        from ....handlers.config import Config

        session = Config.db_session()
        try:
            row = (
                session.query(AgentModel)
                .filter(
                    AgentModel.partition_key == partition_key,
                    AgentModel.agent_version_uuid == agent_version_uuid,
                )
                .first()
            )
            return _normalize(row)
        except Exception:
            session.rollback()
            raise
        finally:
            Config.db_session.remove()  # session lifecycle managed by scoped_session

    def count(self, **keys: Any) -> int:
        partition_key = keys.get("partition_key")
        agent_version_uuid = keys.get("agent_version_uuid")
        if not partition_key or not agent_version_uuid:
            return 0
        from ....handlers.config import Config

        session = Config.db_session()
        try:
            return (
                session.query(AgentModel)
                .filter(
                    AgentModel.partition_key == partition_key,
                    AgentModel.agent_version_uuid == agent_version_uuid,
                )
                .count()
            )
        except Exception:
            session.rollback()
            raise
        finally:
            Config.db_session.remove()  # session lifecycle managed by scoped_session

    def list(self, info: Any, **filters: Any) -> Any:
        from ....handlers.config import Config
        from ....types.agent import AgentListType, AgentType

        page_number = filters.get("page_number", 1)
        limit = filters.get("limit", 100)

        partition_key = filters.get("partition_key") or _get_partition_key(info)
        agent_uuid = filters.get("agent_uuid")
        agent_name = filters.get("agent_name")
        llm_provider = filters.get("llm_provider")
        llm_name = filters.get("llm_name")
        statuses = filters.get("statuses")
        flow_snippet_version_uuid = filters.get("flow_snippet_version_uuid")
        updated_at_gt = filters.get("updated_at_gt")
        updated_at_lt = filters.get("updated_at_lt")

        session = Config.db_session()
        try:
            query = session.query(AgentModel)
            if partition_key:
                query = query.filter(AgentModel.partition_key == partition_key)
            if agent_uuid:
                query = query.filter(AgentModel.agent_uuid == agent_uuid)
            if agent_name:
                query = query.filter(AgentModel.agent_name.ilike(f"%{agent_name}%"))
            if llm_provider:
                query = query.filter(AgentModel.llm_provider == llm_provider)
            if llm_name:
                query = query.filter(AgentModel.llm_name == llm_name)
            if statuses:
                query = query.filter(AgentModel.status.in_(statuses))
            if flow_snippet_version_uuid:
                query = query.filter(
                    AgentModel.flow_snippet_version_uuid == flow_snippet_version_uuid
                )
            if updated_at_gt:
                query = query.filter(AgentModel.updated_at > updated_at_gt)
            if updated_at_lt:
                query = query.filter(AgentModel.updated_at < updated_at_lt)

            total = query.count()
            query = query.order_by(AgentModel.updated_at.desc())
            query, _offset, _limit = _apply_pagination(query, page_number, limit)
            rows = query.all()

            agent_list = [
                AgentType(**_normalize(row)) for row in rows if _normalize(row)
            ]
            return AgentListType(
                agent_list=agent_list,
                total=total,
                page_size=limit,
                page_number=page_number,
            )
        except Exception:
            session.rollback()
            raise
        finally:
            Config.db_session.remove()  # session lifecycle managed by scoped_session

    # ---- single-active ----

    def resolve_active(
        self, partition_key: str, entity_uuid: str = None, **kwargs: Any
    ) -> Optional[Dict[str, Any]]:
        agent_uuid = entity_uuid or kwargs.get("agent_uuid")
        if not partition_key or not agent_uuid:
            return None
        from ....handlers.config import Config

        session = Config.db_session()
        try:
            row = (
                session.query(AgentModel)
                .filter(
                    AgentModel.partition_key == partition_key,
                    AgentModel.agent_uuid == agent_uuid,
                    AgentModel.status == "active",
                )
                .order_by(AgentModel.updated_at.desc())
                .first()
            )
            return _normalize(row)
        except Exception:
            session.rollback()
            raise
        finally:
            Config.db_session.remove()  # session lifecycle managed by scoped_session

    def _deactivate_others(
        self, session: Any, partition_key: str, agent_uuid: str
    ) -> None:
        """Set status='inactive' for all other active agents with the same agent_uuid."""
        session.query(AgentModel).filter(
            AgentModel.partition_key == partition_key,
            AgentModel.agent_uuid == agent_uuid,
            AgentModel.status == "active",
        ).update({AgentModel.status: "inactive"}, synchronize_session=False)

    def _apply_flow_snippet(
        self, partition_key: str, row: AgentModel, kwargs: Dict[str, Any]
    ) -> None:
        """Rebuild ``instructions`` (and mcp_server_uuids / enabled_tools) from
        the referenced flow snippet + its active prompt template.

        Mirrors the DynamoDB ``insert_update_agent`` behaviour: the agent's
        instructions are *derived* from the snippet's flow_context rendered into
        the prompt template, with agent variables substituted. Without this, an
        updated flow snippet never reaches the agent's instructions.
        """
        flow_snippet_version_uuid = getattr(row, "flow_snippet_version_uuid", None)
        if not flow_snippet_version_uuid:
            return

        from .. import get_repo

        flow_snippet = get_repo("flow_snippet").get(
            partition_key=partition_key,
            flow_snippet_version_uuid=flow_snippet_version_uuid,
        )
        if not flow_snippet:
            return
        prompt_template = get_repo("prompt_template").resolve_active(
            partition_key, flow_snippet.get("prompt_uuid")
        )
        if not isinstance(prompt_template, dict) or not prompt_template:
            return

        variables = (
            kwargs.get("variables")
            if "variables" in kwargs
            else getattr(row, "variables", None)
        ) or []
        agent_variables = {
            v["name"]: v["value"]
            for v in variables
            if isinstance(v, dict) and "name" in v and "value" in v
        }
        replace_vars = [
            v["name"]
            for v in (prompt_template.get("variables") or [])
            if isinstance(v, dict) and v.get("name") in agent_variables
        ]

        flow_context = flow_snippet.get("flow_context")
        has_flow_context = False
        if flow_context not in (None, ""):
            for name in replace_vars:
                flow_context = flow_context.replace(
                    f"{{{name}}}", agent_variables[name]
                )
            has_flow_context = True

        instructions = (prompt_template.get("template_context") or "").replace(
            "{flow_snippet}", flow_context or ""
        )
        if not has_flow_context:
            for name in replace_vars:
                instructions = instructions.replace(
                    f"{{{name}}}", agent_variables[name]
                )
        row.instructions = instructions

        row.mcp_server_uuids = [
            m["mcp_server_uuid"]
            for m in (prompt_template.get("mcp_servers") or [])
            if isinstance(m, dict) and m.get("mcp_server_uuid")
        ]

        if "enabled_tools" in flow_snippet:
            # Reassign a new dict so SQLAlchemy detects the JSONB change.
            configuration = dict(getattr(row, "configuration", None) or {})
            configuration["enabled_tools"] = flow_snippet.get("enabled_tools")
            row.configuration = configuration

    def _get_active_row(
        self, session: Any, partition_key: str, agent_uuid: Optional[str]
    ) -> Optional[AgentModel]:
        """Return the active AgentModel row for an agent_uuid (same session)."""
        if not agent_uuid:
            return None
        return (
            session.query(AgentModel)
            .filter(
                AgentModel.partition_key == partition_key,
                AgentModel.agent_uuid == agent_uuid,
                AgentModel.status == "active",
            )
            .order_by(AgentModel.updated_at.desc())
            .first()
        )

    # ---- write ----

    def insert_update(self, info: Any, **kwargs: Any) -> Optional[Dict[str, Any]]:
        import uuid as _uuid

        from ....handlers.config import Config

        partition_key = kwargs.get("partition_key") or _get_partition_key(info)
        if not partition_key:
            raise ValueError("partition_key is required")

        agent_version_uuid = kwargs.get("agent_version_uuid")
        session = Config.db_session()
        try:
            now = pendulum.now("UTC")

            # Only look up an existing row when an explicit version was given.
            row = None
            if agent_version_uuid:
                row = (
                    session.query(AgentModel)
                    .filter(
                        AgentModel.partition_key == partition_key,
                        AgentModel.agent_version_uuid == agent_version_uuid,
                    )
                    .first()
                )

            if row is None:
                # New version / agent. The DynamoDB path auto-generates the
                # version id (and agent_uuid) here via its insert_update
                # decorator; the PG repo must do the same. Version id matches
                # the DynamoDB 20-digit format.
                if not agent_version_uuid:
                    agent_version_uuid = f"{_uuid.uuid1().int % (10 ** 20):020d}"

                # Seed defaults mirroring the DynamoDB AgentModel
                # (status='active', tool_call_role='developer').
                seed: Dict[str, Any] = {
                    "configuration": {},
                    "mcp_server_uuids": [],
                    "variables": [],
                    "status": "active",
                    "tool_call_role": "developer",
                }

                agent_uuid = kwargs.get("agent_uuid")
                duplicate = kwargs.get("duplicate", False)
                active = self._get_active_row(session, partition_key, agent_uuid)
                if active is not None:
                    # New version of an existing agent: inherit its fields.
                    excluded = {
                        "partition_key", "endpoint_id", "part_id",
                        "agent_version_uuid", "status", "updated_by",
                        "created_at", "updated_at",
                    }
                    for k, v in (_normalize(active) or {}).items():
                        if k not in excluded:
                            seed[k] = v
                    if duplicate:
                        seed["agent_name"] = f"{seed.get('agent_name', '')} (Copy)"
                else:
                    # Brand-new agent identity.
                    seed["agent_uuid"] = (
                        f"agent-{now.int_timestamp}-{str(_uuid.uuid4())[:8]}"
                    )

                row = AgentModel(
                    partition_key=partition_key,
                    agent_version_uuid=agent_version_uuid,
                    created_at=now,
                    updated_at=now,
                )
                for _k, _v in seed.items():
                    setattr(row, _k, _v)
            else:
                row.updated_at = now

            # Caller-provided fields override seeded/inherited values.
            for field in _UPDATABLE_FIELDS:
                if field in kwargs:
                    setattr(row, field, kwargs[field])

            # Derive endpoint_id/part_id from partition_key when absent.
            if not getattr(row, "endpoint_id", None) and "#" in partition_key:
                _ep, _pt = partition_key.split("#", 1)
                row.endpoint_id = _ep
                row.part_id = _pt

            # Derive instructions from the referenced flow snippet, so snippet
            # edits propagate into the agent (matches the DynamoDB behaviour).
            self._apply_flow_snippet(partition_key, row, kwargs)

            # Enforce single-active: if status == 'active', deactivate others
            # BEFORE adding the new row to the session, to avoid violating
            # the partial unique index (only one active row per agent_uuid).
            if getattr(row, "status", None) == "active" and getattr(
                row, "agent_uuid", None
            ):
                self._deactivate_others(
                    session, row.partition_key, row.agent_uuid
                )
                # Ensure this row is active (the bulk update may have set it inactive)
                row.status = "active"

            # Add to session after deactivation to avoid unique index violation
            if row not in session:
                session.add(row)

            session.commit()
            result = _normalize(row)
            _purge_cache(
                info,
                "agent",
                {
                    "agent_version_uuid": row.agent_version_uuid,
                    "agent_uuid": row.agent_uuid,
                },
                context_keys={"partition_key": partition_key},
            )
            return result
        except Exception:
            session.rollback()
            raise
        finally:
            Config.db_session.remove()  # session lifecycle managed by scoped_session

    def delete(self, info: Any, **kwargs: Any) -> bool:
        from ....handlers.config import Config

        partition_key = kwargs.get("partition_key") or _get_partition_key(info)
        agent_version_uuid = kwargs.get("agent_version_uuid")
        if not partition_key or not agent_version_uuid:
            return False

        session = Config.db_session()
        try:
            row = (
                session.query(AgentModel)
                .filter(
                    AgentModel.partition_key == partition_key,
                    AgentModel.agent_version_uuid == agent_version_uuid,
                )
                .first()
            )
            if row is None:
                return False
            agent_uuid = row.agent_uuid
            session.delete(row)
            session.commit()
            _purge_cache(
                info,
                "agent",
                {
                    "agent_version_uuid": agent_version_uuid,
                    "agent_uuid": agent_uuid,
                },
                context_keys={"partition_key": partition_key},
            )
            return True
        except Exception:
            session.rollback()
            raise
        finally:
            Config.db_session.remove()  # session lifecycle managed by scoped_session

    # ---- type conversion ----

    def get_type(self, info: Any, instance: Any) -> Any:
        from ....types.agent import AgentType

        data = instance if isinstance(instance, dict) else _normalize(instance)
        if data is None:
            return None
        return AgentType(**data)

    def resolve_single(self, info: Any, **kwargs: Any) -> Any:
        # When agent_uuid is provided (e.g. from _get_agent), fetch the
        # single active agent via resolve_active — mirrors the DynamoDB
        # resolve_agent path which routes agent_uuid to _get_active_agent.
        partition_key = kwargs.get("partition_key") or _get_partition_key(info)
        if "agent_uuid" in kwargs and "agent_version_uuid" not in kwargs:
            data = self.resolve_active(partition_key, kwargs["agent_uuid"])
        else:
            # get() requires partition_key in kwargs; it lives in info.context
            # (injected by the gateway via Graphql.execute context_value), not
            # in the GraphQL field arguments.
            kwargs.setdefault("partition_key", partition_key)
            data = self.get(**kwargs)
        if data is None:
            return None
        return self.get_type(info, data)


__all__ = ["AgentRepository"]