# -*- coding: utf-8 -*-
"""PostgreSQL repository for fine_tuning_message entity."""
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict, Optional

import pendulum

from ..base import EntityRepository
from ...postgresql.fine_tuning_message import FineTuningMessageModel
from ._base import (
    _apply_pagination,
    _get_logger,
    _get_partition_key,
    _get_updated_by,
    _normalize,
    _purge_cache,
)


_PK_FIELDS = ("agent_uuid", "message_uuid")
_UPDATABLE_FIELDS = (
    "partition_key",
    "thread_uuid",
    "timestamp",
    "endpoint_id",
    "role",
    "tool_calls",
    "tool_call_uuid",
    "content",
    "weight",
    "trained",
    "updated_by",
)


class FineTuningMessageRepository(EntityRepository):
    """PostgreSQL repository for fine_tuning_message entity."""

    @property
    def entity_type(self) -> str:
        return "fine_tuning_message"

    def get(self, **keys: Any) -> Optional[Dict[str, Any]]:
        agent_uuid = keys.get("agent_uuid")
        message_uuid = keys.get("message_uuid")
        if not agent_uuid or not message_uuid:
            return None
        from ....handlers.config import Config

        session = Config.db_session()
        try:
            row = (
                session.query(FineTuningMessageModel)
                .filter(
                    FineTuningMessageModel.agent_uuid == agent_uuid,
                    FineTuningMessageModel.message_uuid == message_uuid,
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
        agent_uuid = keys.get("agent_uuid")
        message_uuid = keys.get("message_uuid")
        if not agent_uuid or not message_uuid:
            return 0
        from ....handlers.config import Config

        session = Config.db_session()
        try:
            return (
                session.query(FineTuningMessageModel)
                .filter(
                    FineTuningMessageModel.agent_uuid == agent_uuid,
                    FineTuningMessageModel.message_uuid == message_uuid,
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
        from ....types.fine_tuning_message import FineTuningMessageListType, FineTuningMessageType

        page_number = filters.get('page_number', 1)
        limit = filters.get('limit', 100)
        agent_uuid = filters.get('agent_uuid')
        thread_uuid = filters.get('thread_uuid')
        roles = filters.get('roles')
        trained = filters.get('trained')
        from_date = filters.get('from_date')
        to_date = filters.get('to_date')

        session = Config.db_session()
        try:
            query = session.query(FineTuningMessageModel)
            if agent_uuid:
                query = query.filter(FineTuningMessageModel.agent_uuid == agent_uuid)
            if thread_uuid:
                query = query.filter(FineTuningMessageModel.thread_uuid == thread_uuid)
            if roles:
                query = query.filter(FineTuningMessageModel.role.in_(roles))
            if trained is not None:
                query = query.filter(FineTuningMessageModel.trained == trained)
            if from_date:
                query = query.filter(FineTuningMessageModel.timestamp >= from_date)
            if to_date:
                query = query.filter(FineTuningMessageModel.timestamp <= to_date)

            total = query.count()
            query = query.order_by(FineTuningMessageModel.updated_at.desc())
            query, _offset, _limit = _apply_pagination(query, page_number, limit)
            rows = query.all()

            entity_list = [
                FineTuningMessageType(**_normalize(row)) for row in rows if _normalize(row)
            ]
            return FineTuningMessageListType(
                fine_tuning_message_list=entity_list,
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

        agent_uuid = kwargs.get("agent_uuid") or _get_partition_key(info)
        message_uuid = kwargs.get("message_uuid")
        if not agent_uuid or not message_uuid:
            raise ValueError("agent_uuid and message_uuid are required")

        session = Config.db_session()
        try:
            now = pendulum.now("UTC")
            row = (
                session.query(FineTuningMessageModel)
                .filter(
                    FineTuningMessageModel.agent_uuid == agent_uuid,
                    FineTuningMessageModel.message_uuid == message_uuid,
                )
                .first()
            )

            if row is None:
                row = FineTuningMessageModel(
                    agent_uuid=agent_uuid,
                    message_uuid=message_uuid,
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
                "fine_tuning_message",
                {"message_uuid": row.message_uuid},
                context_keys={"agent_uuid": agent_uuid},
            )
            return result
        except Exception:
            session.rollback()
            raise
        finally:
            pass  # session lifecycle managed by scoped_session

    def delete(self, info: Any, **kwargs: Any) -> bool:
        from ....handlers.config import Config

        agent_uuid = kwargs.get("agent_uuid") or _get_partition_key(info)
        message_uuid = kwargs.get("message_uuid")
        if not agent_uuid or not message_uuid:
            return False

        session = Config.db_session()
        try:
            row = (
                session.query(FineTuningMessageModel)
                .filter(
                    FineTuningMessageModel.agent_uuid == agent_uuid,
                    FineTuningMessageModel.message_uuid == message_uuid,
                )
                .first()
            )
            if row is None:
                return False
            session.delete(row)
            session.commit()
            _purge_cache(
                info,
                "fine_tuning_message",
                {"message_uuid": message_uuid},
                context_keys={"agent_uuid": agent_uuid},
            )
            return True
        except Exception:
            session.rollback()
            raise
        finally:
            pass  # session lifecycle managed by scoped_session

    def get_type(self, info: Any, instance: Any) -> Any:
        from ....types.fine_tuning_message import FineTuningMessageType

        data = instance if isinstance(instance, dict) else _normalize(instance)
        if data is None:
            return None
        return FineTuningMessageType(**data)

    def resolve_single(self, info: Any, **kwargs: Any) -> Any:
        data = self.get(**kwargs)
        if data is None:
            return None
        return self.get_type(info, data)


__all__ = ["FineTuningMessageRepository"]
