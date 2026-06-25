# -*- coding: utf-8 -*-
"""PostgreSQL repository for wizard entity."""
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict, Optional

import pendulum

from ..base import EntityRepository
from ...postgresql.wizard import WizardModel
from ._base import (
    _apply_pagination,
    _get_logger,
    _get_partition_key,
    _get_updated_by,
    _normalize,
    _purge_cache,
)


_PK_FIELDS = ("partition_key", "wizard_uuid")
_UPDATABLE_FIELDS = (
    "endpoint_id",
    "part_id",
    "wizard_title",
    "wizard_description",
    "wizard_type",
    "wizard_schema_type",
    "wizard_schema_name",
    "wizard_attributes",
    "wizard_elements",
    "priority",
    "updated_by",
)


class WizardRepository(EntityRepository):
    """PostgreSQL repository for wizard entity."""

    @property
    def entity_type(self) -> str:
        return "wizard"

    def get(self, **keys: Any) -> Optional[Dict[str, Any]]:
        partition_key = keys.get("partition_key")
        wizard_uuid = keys.get("wizard_uuid")
        if not partition_key or not wizard_uuid:
            return None
        from ....handlers.config import Config

        session = Config.db_session()
        try:
            row = (
                session.query(WizardModel)
                .filter(
                    WizardModel.partition_key == partition_key,
                    WizardModel.wizard_uuid == wizard_uuid,
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
        wizard_uuid = keys.get("wizard_uuid")
        if not partition_key or not wizard_uuid:
            return 0
        from ....handlers.config import Config

        session = Config.db_session()
        try:
            return (
                session.query(WizardModel)
                .filter(
                    WizardModel.partition_key == partition_key,
                    WizardModel.wizard_uuid == wizard_uuid,
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
        from ....types.wizard import WizardListType, WizardType

        page_number = filters.get('page_number', 1)
        limit = filters.get('limit', 100)
        partition_key = filters.get('partition_key') or _get_partition_key(info)
        wizard_type = filters.get('wizard_type')
        wizard_title = filters.get('wizard_title')
        updated_at_gt = filters.get('updated_at_gt')
        updated_at_lt = filters.get('updated_at_lt')

        session = Config.db_session()
        try:
            query = session.query(WizardModel)
            if partition_key:
                query = query.filter(WizardModel.partition_key == partition_key)
            if wizard_type:
                query = query.filter(WizardModel.wizard_type == wizard_type)
            if wizard_title:
                query = query.filter(WizardModel.wizard_title.ilike(f"%{wizard_title}%"))
            if updated_at_gt:
                query = query.filter(WizardModel.updated_at > updated_at_gt)
            if updated_at_lt:
                query = query.filter(WizardModel.updated_at < updated_at_lt)

            total = query.count()
            query = query.order_by(WizardModel.updated_at.desc())
            query, _offset, _limit = _apply_pagination(query, page_number, limit)
            rows = query.all()

            entity_list = [
                WizardType(**_normalize(row)) for row in rows if _normalize(row)
            ]
            return WizardListType(
                wizard_list=entity_list,
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
        wizard_uuid = kwargs.get("wizard_uuid")
        if not partition_key or not wizard_uuid:
            raise ValueError("partition_key and wizard_uuid are required")

        session = Config.db_session()
        try:
            now = pendulum.now("UTC")
            row = (
                session.query(WizardModel)
                .filter(
                    WizardModel.partition_key == partition_key,
                    WizardModel.wizard_uuid == wizard_uuid,
                )
                .first()
            )

            if row is None:
                row = WizardModel(
                    partition_key=partition_key,
                    wizard_uuid=wizard_uuid,
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
                "wizard",
                {"wizard_uuid": row.wizard_uuid},
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
        wizard_uuid = kwargs.get("wizard_uuid")
        if not partition_key or not wizard_uuid:
            return False

        session = Config.db_session()
        try:
            row = (
                session.query(WizardModel)
                .filter(
                    WizardModel.partition_key == partition_key,
                    WizardModel.wizard_uuid == wizard_uuid,
                )
                .first()
            )
            if row is None:
                return False
            session.delete(row)
            session.commit()
            _purge_cache(
                info,
                "wizard",
                {"wizard_uuid": wizard_uuid},
                context_keys={"partition_key": partition_key},
            )
            return True
        except Exception:
            session.rollback()
            raise
        finally:
            Config.db_session.remove()  # session lifecycle managed by scoped_session

    def get_type(self, info: Any, instance: Any) -> Any:
        from ....types.wizard import WizardType

        data = instance if isinstance(instance, dict) else _normalize(instance)
        if data is None:
            return None
        return WizardType(**data)

    def resolve_single(self, info: Any, **kwargs: Any) -> Any:
        if "partition_key" not in kwargs:
            kwargs["partition_key"] = _get_partition_key(info)
        data = self.get(**kwargs)
        if data is None:
            return None
        return self.get_type(info, data)


__all__ = ["WizardRepository"]
