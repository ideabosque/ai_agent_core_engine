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
            pass  # session lifecycle managed by scoped_session

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
            pass  # session lifecycle managed by scoped_session

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
            pass  # session lifecycle managed by scoped_session

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
            pass  # session lifecycle managed by scoped_session

    def _deactivate_others(
        self, session: Any, partition_key: str, agent_uuid: str
    ) -> None:
        """Set status='inactive' for all other active agents with the same agent_uuid."""
        session.query(AgentModel).filter(
            AgentModel.partition_key == partition_key,
            AgentModel.agent_uuid == agent_uuid,
            AgentModel.status == "active",
        ).update({AgentModel.status: "inactive"}, synchronize_session=False)

    # ---- write ----

    def insert_update(self, info: Any, **kwargs: Any) -> Optional[Dict[str, Any]]:
        from ....handlers.config import Config

        partition_key = kwargs.get("partition_key") or _get_partition_key(info)
        agent_version_uuid = kwargs.get("agent_version_uuid")
        if not partition_key or not agent_version_uuid:
            raise ValueError("partition_key and agent_version_uuid are required")

        session = Config.db_session()
        try:
            now = pendulum.now("UTC")
            row = (
                session.query(AgentModel)
                .filter(
                    AgentModel.partition_key == partition_key,
                    AgentModel.agent_version_uuid == agent_version_uuid,
                )
                .first()
            )

            if row is None:
                row = AgentModel(
                    partition_key=partition_key,
                    agent_version_uuid=agent_version_uuid,
                    created_at=now,
                    updated_at=now,
                )
            else:
                row.updated_at = now

            for field in _UPDATABLE_FIELDS:
                if field in kwargs:
                    setattr(row, field, kwargs[field])

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
            pass  # session lifecycle managed by scoped_session

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
            pass  # session lifecycle managed by scoped_session

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
        if "agent_uuid" in kwargs and "agent_version_uuid" not in kwargs:
            partition_key = kwargs.get("partition_key") or _get_partition_key(info)
            data = self.resolve_active(partition_key, kwargs["agent_uuid"])
        else:
            data = self.get(**kwargs)
        if data is None:
            return None
        return self.get_type(info, data)


__all__ = ["AgentRepository"]