# -*- coding: utf-8 -*-
"""PostgreSQL repository for wizard_schema entity."""
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict, Optional

import pendulum

from ..base import EntityRepository
from ...postgresql.wizard_schema import WizardSchemaModel
from ._base import (
    _apply_pagination,
    _get_logger,
    _get_partition_key,
    _get_updated_by,
    _normalize,
    _purge_cache,
)


_PK_FIELDS = ("wizard_schema_type", "wizard_schema_name")
_UPDATABLE_FIELDS = (
    "wizard_schema_description",
    "attributes",
    "attribute_groups",
    "updated_by",
)


class WizardSchemaRepository(EntityRepository):
    """PostgreSQL repository for wizard_schema entity."""

    @property
    def entity_type(self) -> str:
        return "wizard_schema"

    def get(self, **keys: Any) -> Optional[Dict[str, Any]]:
        wizard_schema_type = keys.get("wizard_schema_type")
        wizard_schema_name = keys.get("wizard_schema_name")
        if not wizard_schema_type or not wizard_schema_name:
            return None
        from ....handlers.config import Config

        session = Config.db_session()
        try:
            row = (
                session.query(WizardSchemaModel)
                .filter(
                    WizardSchemaModel.wizard_schema_type == wizard_schema_type,
                    WizardSchemaModel.wizard_schema_name == wizard_schema_name,
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
        wizard_schema_type = keys.get("wizard_schema_type")
        wizard_schema_name = keys.get("wizard_schema_name")
        if not wizard_schema_type or not wizard_schema_name:
            return 0
        from ....handlers.config import Config

        session = Config.db_session()
        try:
            return (
                session.query(WizardSchemaModel)
                .filter(
                    WizardSchemaModel.wizard_schema_type == wizard_schema_type,
                    WizardSchemaModel.wizard_schema_name == wizard_schema_name,
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
        from ....types.wizard_schema import WizardSchemaListType, WizardSchemaType

        page_number = filters.get('page_number', 1)
        limit = filters.get('limit', 100)
        wizard_schema_type = filters.get('wizard_schema_type')
        wizard_schema_name = filters.get('wizard_schema_name')
        updated_at_gt = filters.get('updated_at_gt')
        updated_at_lt = filters.get('updated_at_lt')

        session = Config.db_session()
        try:
            query = session.query(WizardSchemaModel)
            if wizard_schema_type:
                query = query.filter(WizardSchemaModel.wizard_schema_type == wizard_schema_type)
            if wizard_schema_name:
                query = query.filter(WizardSchemaModel.wizard_schema_name == wizard_schema_name)
            if updated_at_gt:
                query = query.filter(WizardSchemaModel.updated_at > updated_at_gt)
            if updated_at_lt:
                query = query.filter(WizardSchemaModel.updated_at < updated_at_lt)

            total = query.count()
            query = query.order_by(WizardSchemaModel.updated_at.desc())
            query, _offset, _limit = _apply_pagination(query, page_number, limit)
            rows = query.all()

            entity_list = [
                WizardSchemaType(**_normalize(row)) for row in rows if _normalize(row)
            ]
            return WizardSchemaListType(
                wizard_schema_list=entity_list,
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

        wizard_schema_type = kwargs.get("wizard_schema_type") or _get_partition_key(info)
        wizard_schema_name = kwargs.get("wizard_schema_name")
        if not wizard_schema_type or not wizard_schema_name:
            raise ValueError("wizard_schema_type and wizard_schema_name are required")

        session = Config.db_session()
        try:
            now = pendulum.now("UTC")
            row = (
                session.query(WizardSchemaModel)
                .filter(
                    WizardSchemaModel.wizard_schema_type == wizard_schema_type,
                    WizardSchemaModel.wizard_schema_name == wizard_schema_name,
                )
                .first()
            )

            if row is None:
                row = WizardSchemaModel(
                    wizard_schema_type=wizard_schema_type,
                    wizard_schema_name=wizard_schema_name,
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
                "wizard_schema",
                {"wizard_schema_name": row.wizard_schema_name},
                context_keys={"wizard_schema_type": wizard_schema_type},
            )
            return result
        except Exception:
            session.rollback()
            raise
        finally:
            Config.db_session.remove()  # session lifecycle managed by scoped_session

    def delete(self, info: Any, **kwargs: Any) -> bool:
        from ....handlers.config import Config

        wizard_schema_type = kwargs.get("wizard_schema_type") or _get_partition_key(info)
        wizard_schema_name = kwargs.get("wizard_schema_name")
        if not wizard_schema_type or not wizard_schema_name:
            return False

        session = Config.db_session()
        try:
            row = (
                session.query(WizardSchemaModel)
                .filter(
                    WizardSchemaModel.wizard_schema_type == wizard_schema_type,
                    WizardSchemaModel.wizard_schema_name == wizard_schema_name,
                )
                .first()
            )
            if row is None:
                return False
            session.delete(row)
            session.commit()
            _purge_cache(
                info,
                "wizard_schema",
                {"wizard_schema_name": wizard_schema_name},
                context_keys={"wizard_schema_type": wizard_schema_type},
            )
            return True
        except Exception:
            session.rollback()
            raise
        finally:
            Config.db_session.remove()  # session lifecycle managed by scoped_session

    def get_type(self, info: Any, instance: Any) -> Any:
        from ....types.wizard_schema import WizardSchemaType

        data = instance if isinstance(instance, dict) else _normalize(instance)
        if data is None:
            return None
        return WizardSchemaType(**data)

    def resolve_single(self, info: Any, **kwargs: Any) -> Any:
        data = self.get(**kwargs)
        if data is None:
            return None
        return self.get_type(info, data)


__all__ = ["WizardSchemaRepository"]
