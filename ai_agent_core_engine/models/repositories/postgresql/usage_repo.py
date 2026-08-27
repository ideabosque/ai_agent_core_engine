# -*- coding: utf-8 -*-
"""PostgreSQL repository for the usage entity (usage_limit / usage_summary).

Unlike the GraphQL entities, usage is an internal enforcement mechanism, so
beyond the ``EntityRepository`` contract it exposes two domain methods used by
``utils.decorators.check_usage_limit``:

* ``resolve_usage_limit(partition_key, usage_key)`` — the active usage_limit as
  an attribute-accessible object (``.status`` / ``.period_end`` / ``.usage_limit``),
  datetimes intact, safe to read after the scoped session is removed.
* ``add_usage_summary(partition_key, usage_key, usage_key_period_start, limit)``
  — atomic increment that raises ``Exception("Usage Limit Exceeded")`` once the
  period total reaches ``limit``.
"""
from __future__ import print_function

__author__ = "bibow"

from types import SimpleNamespace
from typing import Any, Dict, Optional

import pendulum
from sqlalchemy.dialects.postgresql import insert as pg_insert

from ..base import EntityRepository
from ...postgresql.usage import UsageLimitModel, UsageSummaryModel
from ._base import _normalize


class UsageRepository(EntityRepository):
    """PostgreSQL repository for the usage entity."""

    @property
    def entity_type(self) -> str:
        return "usage"

    # ---- EntityRepository contract (usage_limit is the addressable row) ----

    def get(self, **keys: Any) -> Optional[Dict[str, Any]]:
        partition_key = keys.get("partition_key")
        usage_key = keys.get("usage_key")
        if not partition_key or not usage_key:
            return None
        from ....handlers.config import Config

        session = Config.db_session()
        try:
            row = (
                session.query(UsageLimitModel)
                .filter(
                    UsageLimitModel.partition_key == partition_key,
                    UsageLimitModel.usage_key == usage_key,
                )
                .first()
            )
            return _normalize(row)
        except Exception:
            session.rollback()
            raise
        finally:
            Config.db_session.remove()

    def count(self, **keys: Any) -> int:
        partition_key = keys.get("partition_key")
        usage_key = keys.get("usage_key")
        if not partition_key or not usage_key:
            return 0
        from ....handlers.config import Config

        session = Config.db_session()
        try:
            return (
                session.query(UsageLimitModel)
                .filter(
                    UsageLimitModel.partition_key == partition_key,
                    UsageLimitModel.usage_key == usage_key,
                )
                .count()
            )
        except Exception:
            session.rollback()
            raise
        finally:
            Config.db_session.remove()

    def list(self, info: Any, **filters: Any) -> Any:
        raise NotImplementedError("usage entity does not support list()")

    def insert_update(self, info: Any, **kwargs: Any) -> Optional[Dict[str, Any]]:
        partition_key = kwargs.get("partition_key")
        usage_key = kwargs.get("usage_key")
        from ....handlers.config import Config

        session = Config.db_session()
        try:
            row = (
                session.query(UsageLimitModel)
                .filter(
                    UsageLimitModel.partition_key == partition_key,
                    UsageLimitModel.usage_key == usage_key,
                )
                .first()
            )
            now = pendulum.now("UTC")
            if row is None:
                row = UsageLimitModel(
                    partition_key=partition_key,
                    usage_key=usage_key,
                    usage_limit=kwargs.get("usage_limit"),
                    allow_overage=kwargs.get("allow_overage"),
                    period_start=kwargs.get("period_start"),
                    period_end=kwargs.get("period_end"),
                    created_from=kwargs.get("created_from"),
                    status=kwargs.get("status"),
                    created_at=now,
                    updated_at=now,
                )
                session.add(row)
            else:
                for field in (
                    "usage_limit",
                    "allow_overage",
                    "period_start",
                    "period_end",
                    "created_from",
                    "status",
                ):
                    if field in kwargs:
                        setattr(row, field, kwargs[field])
                row.updated_at = now
            session.commit()
            return _normalize(row)
        except Exception:
            session.rollback()
            raise
        finally:
            Config.db_session.remove()

    def delete(self, info: Any, **kwargs: Any) -> bool:
        partition_key = kwargs.get("partition_key")
        usage_key = kwargs.get("usage_key")
        if not partition_key or not usage_key:
            return False
        from ....handlers.config import Config

        session = Config.db_session()
        try:
            row = (
                session.query(UsageLimitModel)
                .filter(
                    UsageLimitModel.partition_key == partition_key,
                    UsageLimitModel.usage_key == usage_key,
                )
                .first()
            )
            if row is None:
                return False
            session.delete(row)
            session.commit()
            return True
        except Exception:
            session.rollback()
            raise
        finally:
            Config.db_session.remove()

    # ---- domain methods (used by utils.decorators.check_usage_limit) ----

    def resolve_usage_limit(
        self, partition_key: str, usage_key: str
    ) -> Optional[Any]:
        """Return the usage_limit as a detached, attribute-accessible object.

        Values are materialized into a ``SimpleNamespace`` so ``.status`` /
        ``.period_end`` / ``.usage_limit`` remain readable after the scoped
        session is removed.  Returns ``None`` when there is no matching row.
        """
        from ....handlers.config import Config

        session = Config.db_session()
        try:
            row = (
                session.query(UsageLimitModel)
                .filter(
                    UsageLimitModel.partition_key == partition_key,
                    UsageLimitModel.usage_key == usage_key,
                )
                .first()
            )
            if row is None:
                return None
            return SimpleNamespace(
                partition_key=row.partition_key,
                usage_key=row.usage_key,
                usage_limit=row.usage_limit,
                allow_overage=row.allow_overage,
                period_start=row.period_start,
                period_end=row.period_end,
                created_from=row.created_from,
                status=row.status,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
        except Exception:
            session.rollback()
            raise
        finally:
            Config.db_session.remove()

    def add_usage_summary(
        self,
        partition_key: str,
        usage_key: str,
        usage_key_period_start: str,
        limit: int,
    ) -> None:
        """Atomically increment the period total, rejecting once it reaches ``limit``.

        Uses ``INSERT ... ON CONFLICT DO UPDATE ... WHERE total < limit RETURNING``.
        A brand-new period inserts ``total=1``; an existing period is incremented
        only while ``total < limit``.  When the guard fails no row is returned, so
        we raise "Usage Limit Exceeded" — matching the DynamoDB conditional update.
        """
        from ....handlers.config import Config

        session = Config.db_session()
        try:
            stmt = (
                pg_insert(UsageSummaryModel)
                .values(
                    partition_key=partition_key,
                    usage_key_period_start=usage_key_period_start,
                    usage_key=usage_key,
                    total=1,
                )
                .on_conflict_do_update(
                    index_elements=[
                        UsageSummaryModel.partition_key,
                        UsageSummaryModel.usage_key_period_start,
                    ],
                    set_={
                        "total": UsageSummaryModel.total + 1,
                        "usage_key": usage_key,
                    },
                    where=(UsageSummaryModel.total < limit),
                )
                .returning(UsageSummaryModel.total)
            )
            row = session.execute(stmt).first()
            session.commit()
            if row is None:
                raise Exception("Usage Limit Exceeded")
        except Exception:
            session.rollback()
            raise
        finally:
            Config.db_session.remove()


__all__ = ["UsageRepository"]
