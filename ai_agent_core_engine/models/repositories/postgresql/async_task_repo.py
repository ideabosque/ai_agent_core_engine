# -*- coding: utf-8 -*-
"""PostgreSQL repository for async_task entity."""
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict, Optional

import pendulum

from ..base import EntityRepository
from ...postgresql.async_task import AsyncTaskModel
from ._base import (
    _apply_pagination,
    _get_logger,
    _get_partition_key,
    _get_updated_by,
    _normalize,
    _purge_cache,
)


_PK_FIELDS = ("function_name", "async_task_uuid")
_UPDATABLE_FIELDS = (
    "partition_key",
    "arguments",
    "result",
    "output_files",
    "status",
    "notes",
    "time_spent",
    "updated_by",
)


class AsyncTaskRepository(EntityRepository):
    """PostgreSQL repository for async_task entity."""

    @property
    def entity_type(self) -> str:
        return "async_task"

    def get(self, **keys: Any) -> Optional[Dict[str, Any]]:
        function_name = keys.get("function_name")
        async_task_uuid = keys.get("async_task_uuid")
        if not function_name or not async_task_uuid:
            return None
        from ....handlers.config import Config

        session = Config.db_session()
        try:
            row = (
                session.query(AsyncTaskModel)
                .filter(
                    AsyncTaskModel.function_name == function_name,
                    AsyncTaskModel.async_task_uuid == async_task_uuid,
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
        function_name = keys.get("function_name")
        async_task_uuid = keys.get("async_task_uuid")
        if not function_name or not async_task_uuid:
            return 0
        from ....handlers.config import Config

        session = Config.db_session()
        try:
            return (
                session.query(AsyncTaskModel)
                .filter(
                    AsyncTaskModel.function_name == function_name,
                    AsyncTaskModel.async_task_uuid == async_task_uuid,
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
        from ....types.async_task import AsyncTaskListType, AsyncTaskType

        page_number = filters.get('page_number', 1)
        limit = filters.get('limit', 100)
        function_name = filters.get('function_name')
        statuses = filters.get('statuses')

        session = Config.db_session()
        try:
            query = session.query(AsyncTaskModel)
            if function_name:
                query = query.filter(AsyncTaskModel.function_name == function_name)
            if statuses:
                query = query.filter(AsyncTaskModel.status.in_(statuses))

            total = query.count()
            query = query.order_by(AsyncTaskModel.updated_at.desc())
            query, _offset, _limit = _apply_pagination(query, page_number, limit)
            rows = query.all()

            entity_list = [
                AsyncTaskType(**_normalize(row)) for row in rows if _normalize(row)
            ]
            return AsyncTaskListType(
                async_task_list=entity_list,
                total=total,
                page_size=limit,
                page_number=page_number,
            )
        except Exception:
            session.rollback()
            raise
        finally:
            pass  # session lifecycle managed by scoped_session

    def insert_update(self, info: Any, **kwargs: Any) -> Optional[Dict[str, Any]]:
        from ....handlers.config import Config

        function_name = kwargs.get("function_name") or _get_partition_key(info)
        async_task_uuid = kwargs.get("async_task_uuid")
        if not function_name or not async_task_uuid:
            raise ValueError("function_name and async_task_uuid are required")

        session = Config.db_session()
        try:
            now = pendulum.now("UTC")
            row = (
                session.query(AsyncTaskModel)
                .filter(
                    AsyncTaskModel.function_name == function_name,
                    AsyncTaskModel.async_task_uuid == async_task_uuid,
                )
                .first()
            )

            if row is None:
                row = AsyncTaskModel(
                    function_name=function_name,
                    async_task_uuid=async_task_uuid,
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
                "async_task",
                {"async_task_uuid": row.async_task_uuid},
                context_keys={"function_name": function_name},
            )
            return result
        except Exception:
            session.rollback()
            raise
        finally:
            pass  # session lifecycle managed by scoped_session

    def delete(self, info: Any, **kwargs: Any) -> bool:
        from ....handlers.config import Config

        function_name = kwargs.get("function_name") or _get_partition_key(info)
        async_task_uuid = kwargs.get("async_task_uuid")
        if not function_name or not async_task_uuid:
            return False

        session = Config.db_session()
        try:
            row = (
                session.query(AsyncTaskModel)
                .filter(
                    AsyncTaskModel.function_name == function_name,
                    AsyncTaskModel.async_task_uuid == async_task_uuid,
                )
                .first()
            )
            if row is None:
                return False
            session.delete(row)
            session.commit()
            _purge_cache(
                info,
                "async_task",
                {"async_task_uuid": async_task_uuid},
                context_keys={"function_name": function_name},
            )
            return True
        except Exception:
            session.rollback()
            raise
        finally:
            pass  # session lifecycle managed by scoped_session

    def get_type(self, info: Any, instance: Any) -> Any:
        from ....types.async_task import AsyncTaskType

        data = instance if isinstance(instance, dict) else _normalize(instance)
        if data is None:
            return None
        return AsyncTaskType(**data)

    def resolve_single(self, info: Any, **kwargs: Any) -> Any:
        data = self.get(**kwargs)
        if data is None:
            return None
        return self.get_type(info, data)


__all__ = ["AsyncTaskRepository"]
