# -*- coding: utf-8 -*-
"""PostgreSQL repository for message entity.

PK(thread_uuid, message_uuid), has partition_key column for RLS.
Implements get_messages_by_thread for parent-relationship queries.
"""
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict, List, Optional

import pendulum

from ..base import EntityRepository
from ...postgresql.message import MessageModel
from ._base import (
    _apply_pagination,
    _get_partition_key,
    _normalize,
    _purge_cache,
)

_PK_FIELDS = ("thread_uuid", "message_uuid")
_UPDATABLE_FIELDS = (
    "run_uuid",
    "message_id",
    "role",
    "message",
    "partition_key",
    "updated_by",
)


class MessageRepository(EntityRepository):
    """PostgreSQL repository for message entity."""

    @property
    def entity_type(self) -> str:
        return "message"

    def get(self, **keys: Any) -> Optional[Dict[str, Any]]:
        thread_uuid = keys.get("thread_uuid")
        message_uuid = keys.get("message_uuid")
        if not thread_uuid or not message_uuid:
            return None
        from ....handlers.config import Config

        session = Config.db_session()
        try:
            row = (
                session.query(MessageModel)
                .filter(
                    MessageModel.thread_uuid == thread_uuid,
                    MessageModel.message_uuid == message_uuid,
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
        message_uuid = keys.get("message_uuid")
        if not thread_uuid or not message_uuid:
            return 0
        from ....handlers.config import Config

        session = Config.db_session()
        try:
            return (
                session.query(MessageModel)
                .filter(
                    MessageModel.thread_uuid == thread_uuid,
                    MessageModel.message_uuid == message_uuid,
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
        from ....types.message import MessageListType, MessageType

        page_number = filters.get("page_number", 1)
        limit = filters.get("limit", 100)
        thread_uuid = filters.get("thread_uuid")
        run_uuid = filters.get("run_uuid")
        message_id = filters.get("message_id")
        roles = filters.get("roles")
        updated_at_gt = filters.get("updated_at_gt")
        updated_at_lt = filters.get("updated_at_lt")

        session = Config.db_session()
        try:
            query = session.query(MessageModel)
            if thread_uuid:
                query = query.filter(MessageModel.thread_uuid == thread_uuid)
            if run_uuid:
                query = query.filter(MessageModel.run_uuid == run_uuid)
            if message_id:
                query = query.filter(MessageModel.message_id == message_id)
            if roles:
                query = query.filter(MessageModel.role.in_(roles))
            if updated_at_gt:
                query = query.filter(MessageModel.updated_at > updated_at_gt)
            if updated_at_lt:
                query = query.filter(MessageModel.updated_at < updated_at_lt)

            total = query.count()
            query = query.order_by(MessageModel.updated_at.desc())
            query, _o, _l = _apply_pagination(query, page_number, limit)
            rows = query.all()

            return MessageListType(
                message_list=[
                    MessageType(**{
                        k: v for k, v in _normalize(r).items()
                        if k in ("thread_uuid", "message_uuid", "run_uuid",
                                 "message_id", "role", "message",
                                 "updated_by", "created_at", "updated_at")
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

    def get_messages_by_thread(self, thread_uuid: str) -> List[Dict[str, Any]]:
        """Return all messages for a given thread_uuid."""
        from ....handlers.config import Config

        session = Config.db_session()
        try:
            rows = (
                session.query(MessageModel)
                .filter(MessageModel.thread_uuid == thread_uuid)
                .order_by(MessageModel.updated_at.desc())
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
        message_uuid = kwargs.get("message_uuid")
        if not thread_uuid or not message_uuid:
            raise ValueError("thread_uuid and message_uuid are required")

        partition_key = kwargs.get("partition_key") or _get_partition_key(info)

        session = Config.db_session()
        try:
            now = pendulum.now("UTC")
            row = (
                session.query(MessageModel)
                .filter(
                    MessageModel.thread_uuid == thread_uuid,
                    MessageModel.message_uuid == message_uuid,
                )
                .first()
            )
            if row is None:
                row = MessageModel(
                    thread_uuid=thread_uuid,
                    message_uuid=message_uuid,
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
                "message",
                {"thread_uuid": thread_uuid, "message_uuid": message_uuid},
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
        message_uuid = kwargs.get("message_uuid")
        if not thread_uuid or not message_uuid:
            return False

        session = Config.db_session()
        try:
            row = (
                session.query(MessageModel)
                .filter(
                    MessageModel.thread_uuid == thread_uuid,
                    MessageModel.message_uuid == message_uuid,
                )
                .first()
            )
            if row is None:
                return False
            session.delete(row)
            session.commit()
            _purge_cache(
                info,
                "message",
                {"thread_uuid": thread_uuid, "message_uuid": message_uuid},
            )
            return True
        except Exception:
            session.rollback()
            raise
        finally:
            Config.db_session.remove()  # session lifecycle managed by scoped_session

    def get_type(self, info: Any, instance: Any) -> Any:
        from ....types.message import MessageType

        data = instance if isinstance(instance, dict) else _normalize(instance)
        if data is None:
            return None
        _allowed = ("thread_uuid", "message_uuid", "run_uuid",
                    "message_id", "role", "message",
                    "updated_by", "created_at", "updated_at")
        return MessageType(**{k: v for k, v in data.items() if k in _allowed})

    def resolve_single(self, info: Any, **kwargs: Any) -> Any:
        data = self.get(**kwargs)
        if data is None:
            return None
        return self.get_type(info, data)


__all__ = ["MessageRepository"]