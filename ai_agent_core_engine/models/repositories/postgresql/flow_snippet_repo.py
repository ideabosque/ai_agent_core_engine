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
            pass  # session lifecycle managed by scoped_session

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
            pass  # session lifecycle managed by scoped_session

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
            pass  # session lifecycle managed by scoped_session

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
            pass  # session lifecycle managed by scoped_session

    def _deactivate_others(
        self, session: Any, partition_key: str, flow_snippet_uuid: str
    ) -> None:
        """Set status='inactive' for all other active flow_snippets with the same flow_snippet_uuid."""
        session.query(FlowSnippetModel).filter(
            FlowSnippetModel.partition_key == partition_key,
            FlowSnippetModel.flow_snippet_uuid == flow_snippet_uuid,
            FlowSnippetModel.status == "active",
        ).update({FlowSnippetModel.status: "inactive"}, synchronize_session=False)

    # ---- write ----

    def insert_update(self, info: Any, **kwargs: Any) -> Optional[Dict[str, Any]]:
        from ....handlers.config import Config

        partition_key = kwargs.get("partition_key") or _get_partition_key(info)
        flow_snippet_version_uuid = kwargs.get("flow_snippet_version_uuid")
        if not partition_key or not flow_snippet_version_uuid:
            raise ValueError("partition_key and flow_snippet_version_uuid are required")

        session = Config.db_session()
        try:
            now = pendulum.now("UTC")
            row = (
                session.query(FlowSnippetModel)
                .filter(
                    FlowSnippetModel.partition_key == partition_key,
                    FlowSnippetModel.flow_snippet_version_uuid == flow_snippet_version_uuid,
                )
                .first()
            )

            if row is None:
                row = FlowSnippetModel(
                    partition_key=partition_key,
                    flow_snippet_version_uuid=flow_snippet_version_uuid,
                    created_at=now,
                    updated_at=now,
                )
            else:
                row.updated_at = now

            for field in _UPDATABLE_FIELDS:
                if field in kwargs:
                    setattr(row, field, kwargs[field])

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
            return result
        except Exception:
            session.rollback()
            raise
        finally:
            pass  # session lifecycle managed by scoped_session

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
            pass  # session lifecycle managed by scoped_session

    def get_type(self, info: Any, instance: Any) -> Any:
        from ....types.flow_snippet import FlowSnippetType

        data = instance if isinstance(instance, dict) else _normalize(instance)
        if data is None:
            return None
        return FlowSnippetType(**data)

    def resolve_single(self, info: Any, **kwargs: Any) -> Any:
        data = self.get(**kwargs)
        if data is None:
            return None
        return self.get_type(info, data)


__all__ = ["FlowSnippetRepository"]