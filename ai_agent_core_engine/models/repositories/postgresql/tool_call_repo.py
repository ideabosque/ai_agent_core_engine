# -*- coding: utf-8 -*-
"""PostgreSQL repository for tool_call entity.

PK(thread_uuid, tool_call_uuid), has partition_key column for RLS.
Implements get_tool_calls_by_run and get_tool_calls_by_thread.
"""
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict, List, Optional

import pendulum

from ..base import EntityRepository
from ...postgresql.tool_call import ToolCallModel
from ._base import (
    _apply_pagination,
    _get_partition_key,
    _normalize,
    _purge_cache,
)

_PK_FIELDS = ("thread_uuid", "tool_call_uuid")
_UPDATABLE_FIELDS = (
    "run_uuid",
    "tool_call_id",
    "tool_type",
    "name",
    "arguments",
    "content",
    "status",
    "notes",
    "time_spent",
    "partition_key",
    "updated_by",
)


class ToolCallRepository(EntityRepository):
    """PostgreSQL repository for tool_call entity."""

    @property
    def entity_type(self) -> str:
        return "tool_call"

    def get(self, **keys: Any) -> Optional[Dict[str, Any]]:
        thread_uuid = keys.get("thread_uuid")
        tool_call_uuid = keys.get("tool_call_uuid")
        if not thread_uuid or not tool_call_uuid:
            return None
        from ....handlers.config import Config

        session = Config.db_session()
        try:
            row = (
                session.query(ToolCallModel)
                .filter(
                    ToolCallModel.thread_uuid == thread_uuid,
                    ToolCallModel.tool_call_uuid == tool_call_uuid,
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
        thread_uuid = keys.get("thread_uuid")
        tool_call_uuid = keys.get("tool_call_uuid")
        if not thread_uuid or not tool_call_uuid:
            return 0
        from ....handlers.config import Config

        session = Config.db_session()
        try:
            return (
                session.query(ToolCallModel)
                .filter(
                    ToolCallModel.thread_uuid == thread_uuid,
                    ToolCallModel.tool_call_uuid == tool_call_uuid,
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
        from ....types.tool_call import ToolCallListType, ToolCallType

        page_number = filters.get("page_number", 1)
        limit = filters.get("limit", 100)
        thread_uuid = filters.get("thread_uuid")
        run_uuid = filters.get("run_uuid")
        tool_call_id = filters.get("tool_call_id")
        tool_type = filters.get("tool_type")
        name = filters.get("name")
        statuses = filters.get("statuses")
        updated_at_gt = filters.get("updated_at_gt")
        updated_at_lt = filters.get("updated_at_lt")

        session = Config.db_session()
        try:
            query = session.query(ToolCallModel)
            if thread_uuid:
                query = query.filter(ToolCallModel.thread_uuid == thread_uuid)
            if run_uuid:
                query = query.filter(ToolCallModel.run_uuid == run_uuid)
            if tool_call_id:
                query = query.filter(ToolCallModel.tool_call_id == tool_call_id)
            if tool_type:
                query = query.filter(ToolCallModel.tool_type == tool_type)
            if name:
                query = query.filter(ToolCallModel.name == name)
            if statuses:
                query = query.filter(ToolCallModel.status.in_(statuses))
            if updated_at_gt:
                query = query.filter(ToolCallModel.updated_at > updated_at_gt)
            if updated_at_lt:
                query = query.filter(ToolCallModel.updated_at < updated_at_lt)

            total = query.count()
            query = query.order_by(ToolCallModel.updated_at.desc())
            query, _o, _l = _apply_pagination(query, page_number, limit)
            rows = query.all()

            return ToolCallListType(
                tool_call_list=[
                    ToolCallType(**{
                        k: v for k, v in _normalize(r).items()
                        if k != "partition_key"
                    })
                    for r in rows if _normalize(r)
                ],
                total=total,
                page_size=limit,
                page_number=page_number,
            )
        except Exception:
            session.rollback()
            raise
        finally:
            Config.db_session.remove()  # session lifecycle managed by scoped_session

    def get_tool_calls_by_run(self, run_uuid: str) -> List[Dict[str, Any]]:
        """Return all tool calls for a given run_uuid."""
        from ....handlers.config import Config

        session = Config.db_session()
        try:
            rows = (
                session.query(ToolCallModel)
                .filter(ToolCallModel.run_uuid == run_uuid)
                .order_by(ToolCallModel.updated_at.desc())
                .all()
            )
            return [_normalize(r) for r in rows if _normalize(r)]
        except Exception:
            session.rollback()
            raise
        finally:
            Config.db_session.remove()  # session lifecycle managed by scoped_session

    def get_tool_calls_by_thread(self, thread_uuid: str) -> List[Dict[str, Any]]:
        """Return all tool calls for a given thread_uuid."""
        from ....handlers.config import Config

        session = Config.db_session()
        try:
            rows = (
                session.query(ToolCallModel)
                .filter(ToolCallModel.thread_uuid == thread_uuid)
                .order_by(ToolCallModel.updated_at.desc())
                .all()
            )
            return [_normalize(r) for r in rows if _normalize(r)]
        except Exception:
            session.rollback()
            raise
        finally:
            Config.db_session.remove()  # session lifecycle managed by scoped_session

    def insert_update(self, info: Any, **kwargs: Any) -> Optional[Dict[str, Any]]:
        from ....handlers.config import Config

        thread_uuid = kwargs.get("thread_uuid")
        tool_call_uuid = kwargs.get("tool_call_uuid")
        if not thread_uuid or not tool_call_uuid:
            raise ValueError("thread_uuid and tool_call_uuid are required")

        partition_key = kwargs.get("partition_key") or _get_partition_key(info)

        session = Config.db_session()
        try:
            now = pendulum.now("UTC")
            row = (
                session.query(ToolCallModel)
                .filter(
                    ToolCallModel.thread_uuid == thread_uuid,
                    ToolCallModel.tool_call_uuid == tool_call_uuid,
                )
                .first()
            )
            if row is None:
                row = ToolCallModel(
                    thread_uuid=thread_uuid,
                    tool_call_uuid=tool_call_uuid,
                    partition_key=partition_key,
                    created_at=now,
                    updated_at=now,
                )
                session.add(row)
            else:
                row.updated_at = now

            for field in _UPDATABLE_FIELDS:
                if field in kwargs:
                    setattr(row, field, kwargs[field])

            session.commit()
            result = _normalize(row)
            _purge_cache(
                info,
                "tool_call",
                {"thread_uuid": thread_uuid, "tool_call_uuid": tool_call_uuid},
            )
            return result
        except Exception:
            session.rollback()
            raise
        finally:
            Config.db_session.remove()  # session lifecycle managed by scoped_session

    def delete(self, info: Any, **kwargs: Any) -> bool:
        from ....handlers.config import Config

        thread_uuid = kwargs.get("thread_uuid")
        tool_call_uuid = kwargs.get("tool_call_uuid")
        if not thread_uuid or not tool_call_uuid:
            return False

        session = Config.db_session()
        try:
            row = (
                session.query(ToolCallModel)
                .filter(
                    ToolCallModel.thread_uuid == thread_uuid,
                    ToolCallModel.tool_call_uuid == tool_call_uuid,
                )
                .first()
            )
            if row is None:
                return False
            session.delete(row)
            session.commit()
            _purge_cache(
                info,
                "tool_call",
                {"thread_uuid": thread_uuid, "tool_call_uuid": tool_call_uuid},
            )
            return True
        except Exception:
            session.rollback()
            raise
        finally:
            Config.db_session.remove()  # session lifecycle managed by scoped_session

    def get_type(self, info: Any, instance: Any) -> Any:
        from ....types.tool_call import ToolCallType

        data = instance if isinstance(instance, dict) else _normalize(instance)
        if data is None:
            return None
        return ToolCallType(**{
            k: v for k, v in data.items() if k != "partition_key"
        })

    def resolve_single(self, info: Any, **kwargs: Any) -> Any:
        data = self.get(**kwargs)
        if data is None:
            return None
        return self.get_type(info, data)


__all__ = ["ToolCallRepository"]