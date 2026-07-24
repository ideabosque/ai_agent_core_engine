# -*- coding: utf-8 -*-
"""PostgreSQL repository for flow_snippet entity — single-active invariant."""
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict, Optional

import pendulum

from ..base import EntityRepository
from ...postgresql.flow_snippet import FlowSnippetModel
from ._base import (
    _apply_pagination,
    _get_logger,
    _get_partition_key,
    _get_updated_by,
    _normalize,
    _purge_cache,
)

_PK_FIELDS = ("partition_key", "flow_snippet_version_uuid")
_UPDATABLE_FIELDS = (
    "endpoint_id",
    "part_id",
    "flow_snippet_uuid",
    "prompt_uuid",
    "flow_name",
    "flow_relationship",
    "flow_context",
    "enabled_tools",
    "status",
    "updated_by",
)


class FlowSnippetRepository(EntityRepository):
    """PostgreSQL repository for flow_snippet entity."""

    @property
    def entity_type(self) -> str:
        return "flow_snippet"

    def get(self, **keys: Any) -> Optional[Dict[str, Any]]:
        partition_key = keys.get("partition_key")
        flow_snippet_version_uuid = keys.get("flow_snippet_version_uuid")
        if not partition_key or not flow_snippet_version_uuid:
            return None
        from ....handlers.config import Config

        session = Config.db_session()
        try:
            row = (
                session.query(FlowSnippetModel)
                .filter(
                    FlowSnippetModel.partition_key == partition_key,
                    FlowSnippetModel.flow_snippet_version_uuid == flow_snippet_version_uuid,
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
        flow_snippet_version_uuid = keys.get("flow_snippet_version_uuid")
        if not partition_key or not flow_snippet_version_uuid:
            return 0
        from ....handlers.config import Config

        session = Config.db_session()
        try:
            return (
                session.query(FlowSnippetModel)
                .filter(
                    FlowSnippetModel.partition_key == partition_key,
                    FlowSnippetModel.flow_snippet_version_uuid == flow_snippet_version_uuid,
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
        from ....types.flow_snippet import FlowSnippetListType, FlowSnippetType

        page_number = filters.get("page_number", 1)
        limit = filters.get("limit", 100)
        partition_key = filters.get("partition_key") or _get_partition_key(info)
        flow_snippet_uuid = filters.get("flow_snippet_uuid")
        prompt_uuid = filters.get("prompt_uuid")
        flow_name = filters.get("flow_name")
        statuses = filters.get("statuses")
        updated_at_gt = filters.get("updated_at_gt")
        updated_at_lt = filters.get("updated_at_lt")

        session = Config.db_session()
        try:
            query = session.query(FlowSnippetModel)
            if partition_key:
                query = query.filter(FlowSnippetModel.partition_key == partition_key)
            if flow_snippet_uuid:
                query = query.filter(FlowSnippetModel.flow_snippet_uuid == flow_snippet_uuid)
            if prompt_uuid:
                query = query.filter(FlowSnippetModel.prompt_uuid == prompt_uuid)
            if flow_name:
                query = query.filter(FlowSnippetModel.flow_name.ilike(f"%{flow_name}%"))
            if statuses:
                query = query.filter(FlowSnippetModel.status.in_(statuses))
            if updated_at_gt:
                query = query.filter(FlowSnippetModel.updated_at > updated_at_gt)
            if updated_at_lt:
                query = query.filter(FlowSnippetModel.updated_at < updated_at_lt)

            total = query.count()
            query = query.order_by(FlowSnippetModel.updated_at.desc())
            query, _offset, _limit = _apply_pagination(query, page_number, limit)
            rows = query.all()

            entity_list = [
                FlowSnippetType(**_normalize(row)) for row in rows if _normalize(row)
            ]
            return FlowSnippetListType(
                flow_snippet_list=entity_list,
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
        flow_snippet_uuid = entity_uuid or kwargs.get("flow_snippet_uuid")
        if not partition_key or not flow_snippet_uuid:
            return None
        from ....handlers.config import Config

        session = Config.db_session()
        try:
            row = (
                session.query(FlowSnippetModel)
                .filter(
                    FlowSnippetModel.partition_key == partition_key,
                    FlowSnippetModel.flow_snippet_uuid == flow_snippet_uuid,
                    FlowSnippetModel.status == "active",
                )
                .order_by(FlowSnippetModel.updated_at.desc())
                .first()
            )
            return _normalize(row)
        except Exception:
            session.rollback()
            raise
        finally:
            Config.db_session.remove()  # session lifecycle managed by scoped_session

    def _deactivate_others(
        self, session: Any, partition_key: str, flow_snippet_uuid: str
    ) -> None:
        """Set status='inactive' for all other active flow_snippets with the same flow_snippet_uuid."""
        session.query(FlowSnippetModel).filter(
            FlowSnippetModel.partition_key == partition_key,
            FlowSnippetModel.flow_snippet_uuid == flow_snippet_uuid,
            FlowSnippetModel.status == "active",
        ).update({FlowSnippetModel.status: "inactive"}, synchronize_session=False)

    def _get_active_row(
        self, session: Any, partition_key: str, flow_snippet_uuid: Optional[str]
    ) -> Optional[FlowSnippetModel]:
        """Return the active FlowSnippetModel row for a flow_snippet_uuid (same session)."""
        if not flow_snippet_uuid:
            return None
        return (
            session.query(FlowSnippetModel)
            .filter(
                FlowSnippetModel.partition_key == partition_key,
                FlowSnippetModel.flow_snippet_uuid == flow_snippet_uuid,
                FlowSnippetModel.status == "active",
            )
            .order_by(FlowSnippetModel.updated_at.desc())
            .first()
        )

    def _propagate_to_agents(
        self,
        info: Any,
        partition_key: str,
        previous_version_uuid: str,
        new_version_uuid: str,
    ) -> None:
        """Re-point agents from the previous snippet version to the new one.

        Mirrors DynamoDB's ``update_agents_by_flow_snippet``: every agent that
        referenced the old version gets a new version pointing at the updated
        snippet, which rebuilds its ``instructions``. Without this an edited
        flow snippet never reaches the agents using it.

        Failures are logged rather than raised — the snippet write itself has
        already been committed.
        """
        try:
            from .. import get_repo

            agent_repo = get_repo("agent")
            listing = agent_repo.list(
                info,
                flow_snippet_version_uuid=previous_version_uuid,
                limit=1000,
            )
            seen = set()
            for agent in (getattr(listing, "agent_list", None) or []):
                agent_uuid = getattr(agent, "agent_uuid", None)
                if not agent_uuid or agent_uuid in seen:
                    continue
                seen.add(agent_uuid)
                agent_repo.insert_update(
                    info,
                    partition_key=partition_key,
                    agent_uuid=agent_uuid,
                    flow_snippet_version_uuid=new_version_uuid,
                    updated_by=getattr(agent, "updated_by", None) or "system",
                )
        except Exception:
            _get_logger(info).exception(
                "Failed to propagate flow snippet %s -> %s to agents",
                previous_version_uuid,
                new_version_uuid,
            )

    # ---- write ----

    def insert_update(self, info: Any, **kwargs: Any) -> Optional[Dict[str, Any]]:
        import uuid as _uuid

        from ....handlers.config import Config

        partition_key = kwargs.get("partition_key") or _get_partition_key(info)
        if not partition_key:
            raise ValueError("partition_key is required")

        flow_snippet_version_uuid = kwargs.get("flow_snippet_version_uuid")
        _prev_version_uuid = None
        session = Config.db_session()
        try:
            now = pendulum.now("UTC")

            # Only look up an existing row when an explicit version was given.
            row = None
            if flow_snippet_version_uuid:
                row = (
                    session.query(FlowSnippetModel)
                    .filter(
                        FlowSnippetModel.partition_key == partition_key,
                        FlowSnippetModel.flow_snippet_version_uuid
                        == flow_snippet_version_uuid,
                    )
                    .first()
                )

            if row is None:
                # New version / snippet. The DynamoDB path auto-generates the
                # version id (and flow_snippet_uuid) via its insert_update
                # decorator; the PG repo must do the same. Version id matches
                # the DynamoDB 20-digit format.
                if not flow_snippet_version_uuid:
                    flow_snippet_version_uuid = (
                        f"{_uuid.uuid1().int % (10 ** 20):020d}"
                    )

                seed: Dict[str, Any] = {"status": "active"}
                flow_snippet_uuid = kwargs.get("flow_snippet_uuid")
                duplicate = kwargs.get("duplicate", False)
                active = self._get_active_row(
                    session, partition_key, flow_snippet_uuid
                )
                if active is not None and not duplicate:
                    # New version of the same snippet — agents referencing the
                    # previous version must be re-pointed after the commit.
                    _prev_version_uuid = active.flow_snippet_version_uuid
                if active is not None:
                    # New version of an existing snippet: inherit its fields.
                    excluded = {
                        "partition_key", "endpoint_id", "part_id",
                        "flow_snippet_version_uuid", "status", "updated_by",
                        "created_at", "updated_at",
                    }
                    for k, v in (_normalize(active) or {}).items():
                        if k not in excluded:
                            seed[k] = v
                    if duplicate:
                        # A duplicate becomes a NEW snippet identity.
                        seed["flow_snippet_uuid"] = (
                            f"flow-snippet-{now.int_timestamp}-"
                            f"{str(_uuid.uuid4())[:8]}"
                        )
                        seed["flow_name"] = f"{seed.get('flow_name', '')} (Copy)"
                else:
                    # Brand-new snippet identity.
                    seed["flow_snippet_uuid"] = (
                        f"flow-snippet-{now.int_timestamp}-"
                        f"{str(_uuid.uuid4())[:8]}"
                    )

                row = FlowSnippetModel(
                    partition_key=partition_key,
                    flow_snippet_version_uuid=flow_snippet_version_uuid,
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

            # Enforce single-active
            if getattr(row, "status", None) == "active" and getattr(
                row, "flow_snippet_uuid", None
            ):
                self._deactivate_others(
                    session, row.partition_key, row.flow_snippet_uuid
                )
                row.status = "active"

            # Add to session after deactivation to avoid unique index violation
            if row not in session:
                session.add(row)

            session.commit()
            result = _normalize(row)
            _purge_cache(
                info,
                "flow_snippet",
                {"flow_snippet_version_uuid": row.flow_snippet_version_uuid},
                context_keys={"partition_key": partition_key},
            )

            # Propagate the new version to agents that referenced the previous
            # one (after commit, so they resolve the updated snippet).
            _new_version_uuid = result.get("flow_snippet_version_uuid")
            if _prev_version_uuid and _prev_version_uuid != _new_version_uuid:
                self._propagate_to_agents(
                    info, partition_key, _prev_version_uuid, _new_version_uuid
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
        flow_snippet_version_uuid = kwargs.get("flow_snippet_version_uuid")
        if not partition_key or not flow_snippet_version_uuid:
            return False

        session = Config.db_session()
        try:
            row = (
                session.query(FlowSnippetModel)
                .filter(
                    FlowSnippetModel.partition_key == partition_key,
                    FlowSnippetModel.flow_snippet_version_uuid == flow_snippet_version_uuid,
                )
                .first()
            )
            if row is None:
                return False
            session.delete(row)
            session.commit()
            _purge_cache(
                info,
                "flow_snippet",
                {"flow_snippet_version_uuid": flow_snippet_version_uuid},
                context_keys={"partition_key": partition_key},
            )
            return True
        except Exception:
            session.rollback()
            raise
        finally:
            Config.db_session.remove()  # session lifecycle managed by scoped_session

    def get_type(self, info: Any, instance: Any) -> Any:
        from ....types.flow_snippet import FlowSnippetType

        data = instance if isinstance(instance, dict) else _normalize(instance)
        if data is None:
            return None
        return FlowSnippetType(**data)

    def resolve_single(self, info: Any, **kwargs: Any) -> Any:
        if "partition_key" not in kwargs:
            kwargs["partition_key"] = _get_partition_key(info)
        data = self.get(**kwargs)
        if data is None:
            return None
        return self.get_type(info, data)


__all__ = ["FlowSnippetRepository"]