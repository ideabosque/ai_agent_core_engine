# -*- coding: utf-8 -*-
"""PostgreSQL repository for wizard_group_filter entity."""
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict, Optional

import pendulum

from ..base import EntityRepository
from ...postgresql.wizard_group_filter import WizardGroupFilterModel
from ._base import (
    _apply_pagination,
    _get_logger,
    _get_partition_key,
    _get_updated_by,
    _normalize,
    _purge_cache,
)


_PK_FIELDS = ("partition_key", "wizard_group_filter_uuid")
_UPDATABLE_FIELDS = (
    "endpoint_id",
    "part_id",
    "wizard_group_filter_name",
    "wizard_group_filter_description",
    "region",
    "criteria",
    "weight",
    "wizard_group_uuid",
    "updated_by",
)


class WizardGroupFilterRepository(EntityRepository):
    """PostgreSQL repository for wizard_group_filter entity."""

    @property
    def entity_type(self) -> str:
        return "wizard_group_filter"

    def get(self, **keys: Any) -> Optional[Dict[str, Any]]:
        partition_key = keys.get("partition_key")
        wizard_group_filter_uuid = keys.get("wizard_group_filter_uuid")
        if not partition_key or not wizard_group_filter_uuid:
            return None
        from ....handlers.config import Config

        session = Config.db_session()
        try:
            row = (
                session.query(WizardGroupFilterModel)
                .filter(
                    WizardGroupFilterModel.partition_key == partition_key,
                    WizardGroupFilterModel.wizard_group_filter_uuid == wizard_group_filter_uuid,
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
        wizard_group_filter_uuid = keys.get("wizard_group_filter_uuid")
        if not partition_key or not wizard_group_filter_uuid:
            return 0
        from ....handlers.config import Config

        session = Config.db_session()
        try:
            return (
                session.query(WizardGroupFilterModel)
                .filter(
                    WizardGroupFilterModel.partition_key == partition_key,
                    WizardGroupFilterModel.wizard_group_filter_uuid == wizard_group_filter_uuid,
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
        from ....types.wizard_group_filter import WizardGroupFilterListType, WizardGroupFilterType

        page_number = filters.get('page_number', 1)
        limit = filters.get('limit', 100)
        partition_key = filters.get('partition_key') or _get_partition_key(info)
        wizard_group_filter_name = filters.get('wizard_group_filter_name')
        region = filters.get('region')
        wizard_group_uuid = filters.get('wizard_group_uuid')
        updated_at_gt = filters.get('updated_at_gt')
        updated_at_lt = filters.get('updated_at_lt')

        session = Config.db_session()
        try:
            query = session.query(WizardGroupFilterModel)
            if partition_key:
                query = query.filter(WizardGroupFilterModel.partition_key == partition_key)
            if wizard_group_filter_name:
                query = query.filter(WizardGroupFilterModel.wizard_group_filter_name.ilike(f"%{wizard_group_filter_name}%"))
            if region:
                query = query.filter(WizardGroupFilterModel.region == region)
            if wizard_group_uuid:
                query = query.filter(WizardGroupFilterModel.wizard_group_uuid == wizard_group_uuid)
            if updated_at_gt:
                query = query.filter(WizardGroupFilterModel.updated_at > updated_at_gt)
            if updated_at_lt:
                query = query.filter(WizardGroupFilterModel.updated_at < updated_at_lt)

            total = query.count()
            query = query.order_by(WizardGroupFilterModel.updated_at.desc())
            query, _offset, _limit = _apply_pagination(query, page_number, limit)
            rows = query.all()

            entity_list = [
                WizardGroupFilterType(**_normalize(row)) for row in rows if _normalize(row)
            ]
            return WizardGroupFilterListType(
                wizard_group_filter_list=entity_list,
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
        wizard_group_filter_uuid = kwargs.get("wizard_group_filter_uuid")
        if not partition_key or not wizard_group_filter_uuid:
            raise ValueError("partition_key and wizard_group_filter_uuid are required")

        session = Config.db_session()
        try:
            now = pendulum.now("UTC")
            row = (
                session.query(WizardGroupFilterModel)
                .filter(
                    WizardGroupFilterModel.partition_key == partition_key,
                    WizardGroupFilterModel.wizard_group_filter_uuid == wizard_group_filter_uuid,
                )
                .first()
            )

            if row is None:
                row = WizardGroupFilterModel(
                    partition_key=partition_key,
                    wizard_group_filter_uuid=wizard_group_filter_uuid,
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
                "wizard_group_filter",
                {"wizard_group_filter_uuid": row.wizard_group_filter_uuid},
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
        wizard_group_filter_uuid = kwargs.get("wizard_group_filter_uuid")
        if not partition_key or not wizard_group_filter_uuid:
            return False

        session = Config.db_session()
        try:
            row = (
                session.query(WizardGroupFilterModel)
                .filter(
                    WizardGroupFilterModel.partition_key == partition_key,
                    WizardGroupFilterModel.wizard_group_filter_uuid == wizard_group_filter_uuid,
                )
                .first()
            )
            if row is None:
                return False
            session.delete(row)
            session.commit()
            _purge_cache(
                info,
                "wizard_group_filter",
                {"wizard_group_filter_uuid": wizard_group_filter_uuid},
                context_keys={"partition_key": partition_key},
            )
            return True
        except Exception:
            session.rollback()
            raise
        finally:
            Config.db_session.remove()  # session lifecycle managed by scoped_session

    def get_type(self, info: Any, instance: Any) -> Any:
        from ....types.wizard_group_filter import WizardGroupFilterType

        data = instance if isinstance(instance, dict) else _normalize(instance)
        if data is None:
            return None
        return WizardGroupFilterType(**data)

    def resolve_single(self, info: Any, **kwargs: Any) -> Any:
        if "partition_key" not in kwargs:
            kwargs["partition_key"] = _get_partition_key(info)
        data = self.get(**kwargs)
        if data is None:
            return None
        return self.get_type(info, data)


__all__ = ["WizardGroupFilterRepository"]
