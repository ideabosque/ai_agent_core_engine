# -*- coding: utf-8 -*-
"""PostgreSQL repository for run entity.

PK(thread_uuid, run_uuid), has partition_key column for RLS.
Implements get_runs_by_thread for parent-relationship queries.
"""
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict, List, Optional

import pendulum

from ..base import EntityRepository
from ...postgresql.run import RunModel
from ._base import (
    _apply_pagination,
    _get_partition_key,
    _normalize,
    _purge_cache,
)

_PK_FIELDS = ("thread_uuid", "run_uuid")
_UPDATABLE_FIELDS = (
    "run_id",
    "completion_tokens",
    "prompt_tokens",
    "total_tokens",
    "time_spent",
    "partition_key",
    "updated_by",
)


class RunRepository(EntityRepository):
    """PostgreSQL repository for run entity."""

    @property
    def entity_type(self) -> str:
        return "run"

    def get(self, **keys: Any) -> Optional[Dict[str, Any]]:
        thread_uuid = keys.get("thread_uuid")
        run_uuid = keys.get("run_uuid")
        if not thread_uuid or not run_uuid:
            return None
        from ....handlers.config import Config

        session = Config.db_session()
        try:
            row = (
                session.query(RunModel)
                .filter(
                    RunModel.thread_uuid == thread_uuid,
                    RunModel.run_uuid == run_uuid,
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
        thread_uuid = keys.get("thread_uuid")
        run_uuid = keys.get("run_uuid")
        if not thread_uuid or not run_uuid:
            return 0
        from ....handlers.config import Config

        session = Config.db_session()
        try:
            return (
                session.query(RunModel)
                .filter(
                    RunModel.thread_uuid == thread_uuid,
                    RunModel.run_uuid == run_uuid,
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
        from ....types.run import RunListType, RunType

        page_number = filters.get("page_number", 1)
        limit = filters.get("limit", 100)
        thread_uuid = filters.get("thread_uuid")
        run_id = filters.get("run_id")
        token_type = filters.get("token_type")
        great_token = filters.get("great_token")
        less_token = filters.get("less_token")
        updated_at_gt = filters.get("updated_at_gt")
        updated_at_lt = filters.get("updated_at_lt")

        session = Config.db_session()
        try:
            query = session.query(RunModel)
            if thread_uuid:
                query = query.filter(RunModel.thread_uuid == thread_uuid)
            if run_id:
                query = query.filter(RunModel.run_id == run_id)

            if token_type and great_token is not None:
                col = getattr(RunModel, f"{token_type}_tokens", None)
                if col is not None:
                    query = query.filter(col < great_token)
            if token_type and less_token is not None:
                col = getattr(RunModel, f"{token_type}_tokens", None)
                if col is not None:
                    query = query.filter(col >= less_token)

            if updated_at_gt:
                query = query.filter(RunModel.updated_at > updated_at_gt)
            if updated_at_lt:
                query = query.filter(RunModel.updated_at < updated_at_lt)

            total = query.count()
            query = query.order_by(RunModel.updated_at.desc())
            query, _o, _l = _apply_pagination(query, page_number, limit)
            rows = query.all()

            return RunListType(
                run_list=[RunType(**_normalize(r)) for r in rows if _normalize(r)],
                total=total,
                page_size=limit,
                page_number=page_number,
            )
        except Exception:
            session.rollback()
            raise
        finally:
            pass  # session lifecycle managed by scoped_session

    def get_runs_by_thread(self, thread_uuid: str) -> List[Dict[str, Any]]:
        """Return all runs for a given thread_uuid (normalized dicts)."""
        from ....handlers.config import Config

        session = Config.db_session()
        try:
            rows = (
                session.query(RunModel)
                .filter(RunModel.thread_uuid == thread_uuid)
                .order_by(RunModel.updated_at.desc())
                .all()
            )
            return [_normalize(r) for r in rows if _normalize(r)]
        except Exception:
            session.rollback()
            raise
        finally:
            pass  # session lifecycle managed by scoped_session

    def insert_update(self, info: Any, **kwargs: Any) -> Optional[Dict[str, Any]]:
        from ....handlers.config import Config

        thread_uuid = kwargs.get("thread_uuid")
        run_uuid = kwargs.get("run_uuid")
        if not thread_uuid or not run_uuid:
            raise ValueError("thread_uuid and run_uuid are required")

        partition_key = kwargs.get("partition_key") or _get_partition_key(info)

        session = Config.db_session()
        try:
            now = pendulum.now("UTC")
            row = (
                session.query(RunModel)
                .filter(
                    RunModel.thread_uuid == thread_uuid,
                    RunModel.run_uuid == run_uuid,
                )
                .first()
            )
            if row is None:
                row = RunModel(
                    thread_uuid=thread_uuid,
                    run_uuid=run_uuid,
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
            _purge_cache(info, "run", {"thread_uuid": thread_uuid, "run_uuid": run_uuid})
            return result
        except Exception:
            session.rollback()
            raise
        finally:
            pass  # session lifecycle managed by scoped_session

    def delete(self, info: Any, **kwargs: Any) -> bool:
        from ....handlers.config import Config

        thread_uuid = kwargs.get("thread_uuid")
        run_uuid = kwargs.get("run_uuid")
        if not thread_uuid or not run_uuid:
            return False

        session = Config.db_session()
        try:
            row = (
                session.query(RunModel)
                .filter(
                    RunModel.thread_uuid == thread_uuid,
                    RunModel.run_uuid == run_uuid,
                )
                .first()
            )
            if row is None:
                return False
            session.delete(row)
            session.commit()
            _purge_cache(info, "run", {"thread_uuid": thread_uuid, "run_uuid": run_uuid})
            return True
        except Exception:
            session.rollback()
            raise
        finally:
            pass  # session lifecycle managed by scoped_session

    def get_type(self, info: Any, instance: Any) -> Any:
        from ....types.run import RunType

        data = instance if isinstance(instance, dict) else _normalize(instance)
        if data is None:
            return None
        return RunType(**data)

    def resolve_single(self, info: Any, **kwargs: Any) -> Any:
        data = self.get(**kwargs)
        if data is None:
            return None
        return self.get_type(info, data)


__all__ = ["RunRepository"]