# -*- coding: utf-8 -*-
"""PostgreSQL repository for thread entity."""
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict, Optional

import pendulum

from ..base import EntityRepository
from ...postgresql.thread import ThreadModel
from ._base import (
    _apply_pagination,
    _get_partition_key,
    _normalize,
    _purge_cache,
)

_PK_FIELDS = ("partition_key", "thread_uuid")
_UPDATABLE_FIELDS = (
    "agent_uuid",
    "user_id",
    "endpoint_id",
    "part_id",
    "updated_by",
)


class ThreadRepository(EntityRepository):
    """PostgreSQL repository for thread entity."""

    @property
    def entity_type(self) -> str:
        return "thread"

    def get(self, **keys: Any) -> Optional[Dict[str, Any]]:
        partition_key = keys.get("partition_key")
        thread_uuid = keys.get("thread_uuid")
        if not partition_key or not thread_uuid:
            return None
        from ....handlers.config import Config

        session = Config.db_session()
        try:
            row = (
                session.query(ThreadModel)
                .filter(
                    ThreadModel.partition_key == partition_key,
                    ThreadModel.thread_uuid == thread_uuid,
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
        thread_uuid = keys.get("thread_uuid")
        if not partition_key or not thread_uuid:
            return 0
        from ....handlers.config import Config

        session = Config.db_session()
        try:
            return (
                session.query(ThreadModel)
                .filter(
                    ThreadModel.partition_key == partition_key,
                    ThreadModel.thread_uuid == thread_uuid,
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
        from ....types.thread import ThreadListType, ThreadType

        page_number = filters.get("page_number", 1)
        limit = filters.get("limit", 100)
        partition_key = filters.get("partition_key") or _get_partition_key(info)
        agent_uuid = filters.get("agent_uuid")
        user_id = filters.get("user_id")
        created_at_gt = filters.get("created_at_gt")
        created_at_lt = filters.get("created_at_lt")

        session = Config.db_session()
        try:
            query = session.query(ThreadModel)
            if partition_key:
                query = query.filter(ThreadModel.partition_key == partition_key)
            if agent_uuid:
                query = query.filter(ThreadModel.agent_uuid == agent_uuid)
            if user_id:
                query = query.filter(ThreadModel.user_id == user_id)
            if created_at_gt:
                query = query.filter(ThreadModel.created_at > created_at_gt)
            if created_at_lt:
                query = query.filter(ThreadModel.created_at < created_at_lt)

            total = query.count()
            query = query.order_by(ThreadModel.created_at.desc())
            query, _o, _l = _apply_pagination(query, page_number, limit)
            rows = query.all()

            return ThreadListType(
                thread_list=[
                    ThreadType(**_normalize(r)) for r in rows if _normalize(r)
                ],
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

        partition_key = kwargs.get("partition_key") or _get_partition_key(info)
        thread_uuid = kwargs.get("thread_uuid")
        if not partition_key or not thread_uuid:
            raise ValueError("partition_key and thread_uuid are required")

        session = Config.db_session()
        try:
            now = pendulum.now("UTC")
            row = (
                session.query(ThreadModel)
                .filter(
                    ThreadModel.partition_key == partition_key,
                    ThreadModel.thread_uuid == thread_uuid,
                )
                .first()
            )
            if row is None:
                row = ThreadModel(
                    partition_key=partition_key,
                    thread_uuid=thread_uuid,
                    created_at=now,
                )
                session.add(row)

            for field in _UPDATABLE_FIELDS:
                if field in kwargs:
                    setattr(row, field, kwargs[field])

            session.commit()
            result = _normalize(row)
            _purge_cache(
                info,
                "thread",
                {"thread_uuid": thread_uuid},
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
        thread_uuid = kwargs.get("thread_uuid")
        if not partition_key or not thread_uuid:
            return False

        session = Config.db_session()
        try:
            row = (
                session.query(ThreadModel)
                .filter(
                    ThreadModel.partition_key == partition_key,
                    ThreadModel.thread_uuid == thread_uuid,
                )
                .first()
            )
            if row is None:
                return False
            session.delete(row)
            session.commit()
            _purge_cache(
                info,
                "thread",
                {"thread_uuid": thread_uuid},
                context_keys={"partition_key": partition_key},
            )
            return True
        except Exception:
            session.rollback()
            raise
        finally:
            pass  # session lifecycle managed by scoped_session

    def get_type(self, info: Any, instance: Any) -> Any:
        from ....types.thread import ThreadType

        data = instance if isinstance(instance, dict) else _normalize(instance)
        if data is None:
            return None
        return ThreadType(**data)

    def resolve_single(self, info: Any, **kwargs: Any) -> Any:
        data = self.get(**kwargs)
        if data is None:
            return None
        return self.get_type(info, data)


__all__ = ["ThreadRepository"]