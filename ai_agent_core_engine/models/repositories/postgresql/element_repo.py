# -*- coding: utf-8 -*-
"""PostgreSQL repository for element entity."""
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict, Optional

import pendulum

from ..base import EntityRepository
from ...postgresql.element import ElementModel
from ._base import (
    _apply_pagination,
    _get_logger,
    _get_partition_key,
    _get_updated_by,
    _normalize,
    _purge_cache,
)


_PK_FIELDS = ("partition_key", "element_uuid")
_UPDATABLE_FIELDS = (
    "endpoint_id",
    "part_id",
    "data_type",
    "element_title",
    "priority",
    "attribute_name",
    "attribute_type",
    "option_values",
    "conditions",
    "pattern",
    "updated_by",
)


class ElementRepository(EntityRepository):
    """PostgreSQL repository for element entity."""

    @property
    def entity_type(self) -> str:
        return "element"

    def get(self, **keys: Any) -> Optional[Dict[str, Any]]:
        partition_key = keys.get("partition_key")
        element_uuid = keys.get("element_uuid")
        if not partition_key or not element_uuid:
            return None
        from ....handlers.config import Config

        session = Config.db_session()
        try:
            row = (
                session.query(ElementModel)
                .filter(
                    ElementModel.partition_key == partition_key,
                    ElementModel.element_uuid == element_uuid,
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
        element_uuid = keys.get("element_uuid")
        if not partition_key or not element_uuid:
            return 0
        from ....handlers.config import Config

        session = Config.db_session()
        try:
            return (
                session.query(ElementModel)
                .filter(
                    ElementModel.partition_key == partition_key,
                    ElementModel.element_uuid == element_uuid,
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
        from ....types.element import ElementListType, ElementType

        page_number = filters.get('page_number', 1)
        limit = filters.get('limit', 100)
        partition_key = filters.get('partition_key') or _get_partition_key(info)
        data_type = filters.get('data_type')
        attribute_name = filters.get('attribute_name')
        updated_at_gt = filters.get('updated_at_gt')
        updated_at_lt = filters.get('updated_at_lt')

        session = Config.db_session()
        try:
            query = session.query(ElementModel)
            if partition_key:
                query = query.filter(ElementModel.partition_key == partition_key)
            if data_type:
                query = query.filter(ElementModel.data_type == data_type)
            if attribute_name:
                query = query.filter(ElementModel.attribute_name == attribute_name)
            if updated_at_gt:
                query = query.filter(ElementModel.updated_at > updated_at_gt)
            if updated_at_lt:
                query = query.filter(ElementModel.updated_at < updated_at_lt)

            total = query.count()
            query = query.order_by(ElementModel.updated_at.desc())
            query, _offset, _limit = _apply_pagination(query, page_number, limit)
            rows = query.all()

            entity_list = [
                ElementType(**_normalize(row)) for row in rows if _normalize(row)
            ]
            return ElementListType(
                element_list=entity_list,
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
        element_uuid = kwargs.get("element_uuid")
        if not element_uuid:
            # DynamoDB's insert_update decorator auto-generates this id when
            # the caller omits it (new record); the PG repo must do the same.
            import uuid as _uuid

            element_uuid = f"{_uuid.uuid1().int % (10 ** 20):020d}"

        session = Config.db_session()
        try:
            now = pendulum.now("UTC")
            row = (
                session.query(ElementModel)
                .filter(
                    ElementModel.partition_key == partition_key,
                    ElementModel.element_uuid == element_uuid,
                )
                .first()
            )

            if row is None:
                row = ElementModel(
                    partition_key=partition_key,
                    element_uuid=element_uuid,
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
                "element",
                {"element_uuid": row.element_uuid},
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
        element_uuid = kwargs.get("element_uuid")
        if not partition_key or not element_uuid:
            return False

        session = Config.db_session()
        try:
            row = (
                session.query(ElementModel)
                .filter(
                    ElementModel.partition_key == partition_key,
                    ElementModel.element_uuid == element_uuid,
                )
                .first()
            )
            if row is None:
                return False
            session.delete(row)
            session.commit()
            _purge_cache(
                info,
                "element",
                {"element_uuid": element_uuid},
                context_keys={"partition_key": partition_key},
            )
            return True
        except Exception:
            session.rollback()
            raise
        finally:
            Config.db_session.remove()  # session lifecycle managed by scoped_session

    def get_type(self, info: Any, instance: Any) -> Any:
        from ....types.element import ElementType

        data = instance if isinstance(instance, dict) else _normalize(instance)
        if data is None:
            return None
        return ElementType(**data)

    def resolve_single(self, info: Any, **kwargs: Any) -> Any:
        if "partition_key" not in kwargs:
            kwargs["partition_key"] = _get_partition_key(info)
        data = self.get(**kwargs)
        if data is None:
            return None
        return self.get_type(info, data)


__all__ = ["ElementRepository"]
