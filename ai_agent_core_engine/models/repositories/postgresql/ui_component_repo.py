# -*- coding: utf-8 -*-
"""PostgreSQL repository for ui_component entity."""
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict, Optional

import pendulum

from ..base import EntityRepository
from ...postgresql.ui_component import UIComponentModel
from ._base import (
    _apply_pagination,
    _get_logger,
    _get_partition_key,
    _get_updated_by,
    _normalize,
    _purge_cache,
)


_PK_FIELDS = ("ui_component_type", "ui_component_uuid")
_UPDATABLE_FIELDS = (
    "tag_name",
    "tag_alias",
    "parameters",
    "wait_for",
    "updated_by",
)


class UIComponentRepository(EntityRepository):
    """PostgreSQL repository for ui_component entity."""

    @property
    def entity_type(self) -> str:
        return "ui_component"

    def get(self, **keys: Any) -> Optional[Dict[str, Any]]:
        ui_component_type = keys.get("ui_component_type")
        ui_component_uuid = keys.get("ui_component_uuid")
        if not ui_component_type or not ui_component_uuid:
            return None
        from ....handlers.config import Config

        session = Config.db_session()
        try:
            row = (
                session.query(UIComponentModel)
                .filter(
                    UIComponentModel.ui_component_type == ui_component_type,
                    UIComponentModel.ui_component_uuid == ui_component_uuid,
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
        ui_component_type = keys.get("ui_component_type")
        ui_component_uuid = keys.get("ui_component_uuid")
        if not ui_component_type or not ui_component_uuid:
            return 0
        from ....handlers.config import Config

        session = Config.db_session()
        try:
            return (
                session.query(UIComponentModel)
                .filter(
                    UIComponentModel.ui_component_type == ui_component_type,
                    UIComponentModel.ui_component_uuid == ui_component_uuid,
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
        from ....types.ui_component import UIComponentListType, UIComponentType

        page_number = filters.get('page_number', 1)
        limit = filters.get('limit', 100)
        ui_component_type = filters.get('ui_component_type')
        tag_name = filters.get('tag_name')
        tag_alias = filters.get('tag_alias')
        updated_at_gt = filters.get('updated_at_gt')
        updated_at_lt = filters.get('updated_at_lt')

        session = Config.db_session()
        try:
            query = session.query(UIComponentModel)
            if ui_component_type:
                query = query.filter(UIComponentModel.ui_component_type == ui_component_type)
            if tag_name:
                query = query.filter(UIComponentModel.tag_name == tag_name)
            if tag_alias:
                query = query.filter(UIComponentModel.tag_alias == tag_alias)
            if updated_at_gt:
                query = query.filter(UIComponentModel.updated_at > updated_at_gt)
            if updated_at_lt:
                query = query.filter(UIComponentModel.updated_at < updated_at_lt)

            total = query.count()
            query = query.order_by(UIComponentModel.updated_at.desc())
            query, _offset, _limit = _apply_pagination(query, page_number, limit)
            rows = query.all()

            entity_list = [
                UIComponentType(**_normalize(row)) for row in rows if _normalize(row)
            ]
            return UIComponentListType(
                ui_component_list=entity_list,
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

        ui_component_type = kwargs.get("ui_component_type") or _get_partition_key(info)
        if not ui_component_type:
            raise ValueError("ui_component_type is required")
        ui_component_uuid = kwargs.get("ui_component_uuid")
        if not ui_component_uuid:
            # DynamoDB's insert_update decorator auto-generates this id when
            # the caller omits it (new record); the PG repo must do the same.
            import uuid as _uuid

            ui_component_uuid = f"{_uuid.uuid1().int % (10 ** 20):020d}"

        session = Config.db_session()
        try:
            now = pendulum.now("UTC")
            row = (
                session.query(UIComponentModel)
                .filter(
                    UIComponentModel.ui_component_type == ui_component_type,
                    UIComponentModel.ui_component_uuid == ui_component_uuid,
                )
                .first()
            )

            if row is None:
                row = UIComponentModel(
                    ui_component_type=ui_component_type,
                    ui_component_uuid=ui_component_uuid,
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
                "ui_component",
                {"ui_component_uuid": row.ui_component_uuid},
                context_keys={"ui_component_type": ui_component_type},
            )
            return result
        except Exception:
            session.rollback()
            raise
        finally:
            Config.db_session.remove()  # session lifecycle managed by scoped_session

    def delete(self, info: Any, **kwargs: Any) -> bool:
        from ....handlers.config import Config

        ui_component_type = kwargs.get("ui_component_type") or _get_partition_key(info)
        ui_component_uuid = kwargs.get("ui_component_uuid")
        if not ui_component_type or not ui_component_uuid:
            return False

        session = Config.db_session()
        try:
            row = (
                session.query(UIComponentModel)
                .filter(
                    UIComponentModel.ui_component_type == ui_component_type,
                    UIComponentModel.ui_component_uuid == ui_component_uuid,
                )
                .first()
            )
            if row is None:
                return False
            session.delete(row)
            session.commit()
            _purge_cache(
                info,
                "ui_component",
                {"ui_component_uuid": ui_component_uuid},
                context_keys={"ui_component_type": ui_component_type},
            )
            return True
        except Exception:
            session.rollback()
            raise
        finally:
            Config.db_session.remove()  # session lifecycle managed by scoped_session

    def get_type(self, info: Any, instance: Any) -> Any:
        from ....types.ui_component import UIComponentType

        data = instance if isinstance(instance, dict) else _normalize(instance)
        if data is None:
            return None
        return UIComponentType(**data)

    def resolve_single(self, info: Any, **kwargs: Any) -> Any:
        data = self.get(**kwargs)
        if data is None:
            return None
        return self.get_type(info, data)


__all__ = ["UIComponentRepository"]
