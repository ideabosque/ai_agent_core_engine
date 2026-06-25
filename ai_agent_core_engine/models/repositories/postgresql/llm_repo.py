# -*- coding: utf-8 -*-
"""PostgreSQL repository for llm entity (global registry, no partition_key)."""
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict, Optional

import pendulum

from ..base import EntityRepository
from ...postgresql.llm import LlmModel
from ._base import (
    _apply_pagination,
    _get_logger,
    _normalize,
    _purge_cache,
)

_PK_FIELDS = ("llm_provider", "llm_name")
_UPDATABLE_FIELDS = (
    "module_name",
    "class_name",
    "configuration_schema",
    "updated_by",
)


class LlmRepository(EntityRepository):
    """PostgreSQL repository for llm entity."""

    @property
    def entity_type(self) -> str:
        return "llm"

    def get(self, **keys: Any) -> Optional[Dict[str, Any]]:
        llm_provider = keys.get("llm_provider")
        llm_name = keys.get("llm_name")
        if not llm_provider or not llm_name:
            return None
        from ....handlers.config import Config

        session = Config.db_session()
        try:
            row = (
                session.query(LlmModel)
                .filter(
                    LlmModel.llm_provider == llm_provider,
                    LlmModel.llm_name == llm_name,
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
        llm_provider = keys.get("llm_provider")
        llm_name = keys.get("llm_name")
        if not llm_provider or not llm_name:
            return 0
        from ....handlers.config import Config

        session = Config.db_session()
        try:
            return (
                session.query(LlmModel)
                .filter(
                    LlmModel.llm_provider == llm_provider,
                    LlmModel.llm_name == llm_name,
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
        from ....types.llm import LlmListType, LlmType

        page_number = filters.get("page_number", 1)
        limit = filters.get("limit", 100)
        llm_provider = filters.get("llm_provider")
        module_name = filters.get("module_name")
        class_name = filters.get("class_name")

        session = Config.db_session()
        try:
            query = session.query(LlmModel)
            if llm_provider:
                query = query.filter(LlmModel.llm_provider == llm_provider)
            if module_name:
                query = query.filter(LlmModel.module_name == module_name)
            if class_name:
                query = query.filter(LlmModel.class_name == class_name)

            total = query.count()
            query = query.order_by(LlmModel.updated_at.desc())
            query, _o, _l = _apply_pagination(query, page_number, limit)
            rows = query.all()

            return LlmListType(
                llm_list=[LlmType(**_normalize(r)) for r in rows if _normalize(r)],
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

        llm_provider = kwargs.get("llm_provider")
        llm_name = kwargs.get("llm_name")
        if not llm_provider or not llm_name:
            raise ValueError("llm_provider and llm_name are required")

        session = Config.db_session()
        try:
            now = pendulum.now("UTC")
            row = (
                session.query(LlmModel)
                .filter(
                    LlmModel.llm_provider == llm_provider,
                    LlmModel.llm_name == llm_name,
                )
                .first()
            )
            if row is None:
                row = LlmModel(
                    llm_provider=llm_provider,
                    llm_name=llm_name,
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
            _purge_cache(info, "llm", {"llm_provider": llm_provider, "llm_name": llm_name})
            return result
        except Exception:
            session.rollback()
            raise
        finally:
            pass  # session lifecycle managed by scoped_session

    def delete(self, info: Any, **kwargs: Any) -> bool:
        from ....handlers.config import Config

        llm_provider = kwargs.get("llm_provider")
        llm_name = kwargs.get("llm_name")
        if not llm_provider or not llm_name:
            return False

        session = Config.db_session()
        try:
            row = (
                session.query(LlmModel)
                .filter(
                    LlmModel.llm_provider == llm_provider,
                    LlmModel.llm_name == llm_name,
                )
                .first()
            )
            if row is None:
                return False
            session.delete(row)
            session.commit()
            _purge_cache(info, "llm", {"llm_provider": llm_provider, "llm_name": llm_name})
            return True
        except Exception:
            session.rollback()
            raise
        finally:
            pass  # session lifecycle managed by scoped_session

    def get_type(self, info: Any, instance: Any) -> Any:
        from ....types.llm import LlmType

        data = instance if isinstance(instance, dict) else _normalize(instance)
        if data is None:
            return None
        return LlmType(**data)

    def resolve_single(self, info: Any, **kwargs: Any) -> Any:
        data = self.get(**kwargs)
        if data is None:
            return None
        return self.get_type(info, data)


__all__ = ["LlmRepository"]