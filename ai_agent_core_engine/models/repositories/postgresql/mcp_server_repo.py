# -*- coding: utf-8 -*-
"""PostgreSQL repository for mcp_server entity."""
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict, Optional

import pendulum

from ..base import EntityRepository
from ...postgresql.mcp_server import MCPServerModel
from ._base import (
    _apply_pagination,
    _get_logger,
    _get_partition_key,
    _get_updated_by,
    _normalize,
    _purge_cache,
)


_PK_FIELDS = ("partition_key", "mcp_server_uuid")
_UPDATABLE_FIELDS = (
    "endpoint_id",
    "part_id",
    "mcp_label",
    "mcp_server_url",
    "headers",
    "updated_by",
)


class MCPServerRepository(EntityRepository):
    """PostgreSQL repository for mcp_server entity."""

    @property
    def entity_type(self) -> str:
        return "mcp_server"

    def get(self, **keys: Any) -> Optional[Dict[str, Any]]:
        partition_key = keys.get("partition_key")
        mcp_server_uuid = keys.get("mcp_server_uuid")
        if not partition_key or not mcp_server_uuid:
            return None
        from ....handlers.config import Config

        session = Config.db_session()
        try:
            row = (
                session.query(MCPServerModel)
                .filter(
                    MCPServerModel.partition_key == partition_key,
                    MCPServerModel.mcp_server_uuid == mcp_server_uuid,
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
        mcp_server_uuid = keys.get("mcp_server_uuid")
        if not partition_key or not mcp_server_uuid:
            return 0
        from ....handlers.config import Config

        session = Config.db_session()
        try:
            return (
                session.query(MCPServerModel)
                .filter(
                    MCPServerModel.partition_key == partition_key,
                    MCPServerModel.mcp_server_uuid == mcp_server_uuid,
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
        from ....types.mcp_server import MCPServerListType, MCPServerType

        page_number = filters.get('page_number', 1)
        limit = filters.get('limit', 100)
        partition_key = filters.get('partition_key') or _get_partition_key(info)
        mcp_label = filters.get('mcp_label')
        updated_at_gt = filters.get('updated_at_gt')
        updated_at_lt = filters.get('updated_at_lt')

        session = Config.db_session()
        try:
            query = session.query(MCPServerModel)
            if partition_key:
                query = query.filter(MCPServerModel.partition_key == partition_key)
            if mcp_label:
                query = query.filter(MCPServerModel.mcp_label.ilike(f"%{mcp_label}%"))
            if updated_at_gt:
                query = query.filter(MCPServerModel.updated_at > updated_at_gt)
            if updated_at_lt:
                query = query.filter(MCPServerModel.updated_at < updated_at_lt)

            total = query.count()
            query = query.order_by(MCPServerModel.updated_at.desc())
            query, _offset, _limit = _apply_pagination(query, page_number, limit)
            rows = query.all()

            entity_list = [
                MCPServerType(**_normalize(row)) for row in rows if _normalize(row)
            ]
            return MCPServerListType(
                mcp_server_list=entity_list,
                total=total,
                page_size=limit,
                page_number=page_number,
            )
        except Exception:
            session.rollback()
            raise
        finally:
            Config.db_session.remove()  # session lifecycle managed by scoped_session

    def insert_update(self, info: Any, **kwargs: Any) -> Optional[Dict[str, Any]]:
        from ....handlers.config import Config

        partition_key = kwargs.get("partition_key") or _get_partition_key(info)
        if not partition_key:
            raise ValueError("partition_key is required")
        mcp_server_uuid = kwargs.get("mcp_server_uuid")
        if not mcp_server_uuid:
            # DynamoDB's insert_update decorator auto-generates this id when
            # the caller omits it (new record); the PG repo must do the same.
            import uuid as _uuid

            mcp_server_uuid = f"{_uuid.uuid1().int % (10 ** 20):020d}"

        session = Config.db_session()
        try:
            now = pendulum.now("UTC")
            row = (
                session.query(MCPServerModel)
                .filter(
                    MCPServerModel.partition_key == partition_key,
                    MCPServerModel.mcp_server_uuid == mcp_server_uuid,
                )
                .first()
            )

            if row is None:
                row = MCPServerModel(
                    partition_key=partition_key,
                    mcp_server_uuid=mcp_server_uuid,
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
                "mcp_server",
                {"mcp_server_uuid": row.mcp_server_uuid},
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
        mcp_server_uuid = kwargs.get("mcp_server_uuid")
        if not partition_key or not mcp_server_uuid:
            return False

        session = Config.db_session()
        try:
            row = (
                session.query(MCPServerModel)
                .filter(
                    MCPServerModel.partition_key == partition_key,
                    MCPServerModel.mcp_server_uuid == mcp_server_uuid,
                )
                .first()
            )
            if row is None:
                return False
            session.delete(row)
            session.commit()
            _purge_cache(
                info,
                "mcp_server",
                {"mcp_server_uuid": mcp_server_uuid},
                context_keys={"partition_key": partition_key},
            )
            return True
        except Exception:
            session.rollback()
            raise
        finally:
            Config.db_session.remove()  # session lifecycle managed by scoped_session

    def get_type(self, info: Any, instance: Any) -> Any:
        from ....types.mcp_server import MCPServerType

        data = instance if isinstance(instance, dict) else _normalize(instance)
        if data is None:
            return None
        return MCPServerType(**data)

    def resolve_single(self, info: Any, **kwargs: Any) -> Any:
        # Inject partition_key from info context when not explicitly provided
        if "partition_key" not in kwargs:
            kwargs["partition_key"] = _get_partition_key(info)
        data = self.get(**kwargs)
        if data is None:
            return None
        return self.get_type(info, data)


__all__ = ["MCPServerRepository"]
