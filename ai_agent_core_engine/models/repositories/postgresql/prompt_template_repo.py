# -*- coding: utf-8 -*-
"""PostgreSQL repository for prompt_template entity — single-active invariant."""
from __future__ import print_function

__author__ = "bibow"

from typing import Any, Dict, Optional

import pendulum

from ..base import EntityRepository
from ...postgresql.prompt_template import PromptTemplateModel
from ._base import (
    _apply_pagination,
    _get_logger,
    _get_partition_key,
    _get_updated_by,
    _normalize,
    _purge_cache,
)

_PK_FIELDS = ("partition_key", "prompt_version_uuid")
_UPDATABLE_FIELDS = (
    "endpoint_id",
    "part_id",
    "prompt_uuid",
    "prompt_type",
    "prompt_name",
    "prompt_description",
    "template_context",
    "variables",
    "mcp_servers",
    "ui_components",
    "status",
    "updated_by",
)


class PromptTemplateRepository(EntityRepository):
    """PostgreSQL repository for prompt_template entity."""

    @property
    def entity_type(self) -> str:
        return "prompt_template"

    def get(self, **keys: Any) -> Optional[Dict[str, Any]]:
        partition_key = keys.get("partition_key")
        prompt_version_uuid = keys.get("prompt_version_uuid")
        if not partition_key or not prompt_version_uuid:
            return None
        from ....handlers.config import Config

        session = Config.db_session()
        try:
            row = (
                session.query(PromptTemplateModel)
                .filter(
                    PromptTemplateModel.partition_key == partition_key,
                    PromptTemplateModel.prompt_version_uuid == prompt_version_uuid,
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
        prompt_version_uuid = keys.get("prompt_version_uuid")
        if not partition_key or not prompt_version_uuid:
            return 0
        from ....handlers.config import Config

        session = Config.db_session()
        try:
            return (
                session.query(PromptTemplateModel)
                .filter(
                    PromptTemplateModel.partition_key == partition_key,
                    PromptTemplateModel.prompt_version_uuid == prompt_version_uuid,
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
        from ....types.prompt_template import PromptTemplateListType, PromptTemplateType

        page_number = filters.get("page_number", 1)
        limit = filters.get("limit", 100)
        partition_key = filters.get("partition_key") or _get_partition_key(info)
        prompt_uuid = filters.get("prompt_uuid")
        prompt_type = filters.get("prompt_type")
        prompt_name = filters.get("prompt_name")
        statuses = filters.get("statuses")
        updated_at_gt = filters.get("updated_at_gt")
        updated_at_lt = filters.get("updated_at_lt")

        session = Config.db_session()
        try:
            query = session.query(PromptTemplateModel)
            if partition_key:
                query = query.filter(PromptTemplateModel.partition_key == partition_key)
            if prompt_uuid:
                query = query.filter(PromptTemplateModel.prompt_uuid == prompt_uuid)
            if prompt_type:
                query = query.filter(PromptTemplateModel.prompt_type == prompt_type)
            if prompt_name:
                query = query.filter(PromptTemplateModel.prompt_name.ilike(f"%{prompt_name}%"))
            if statuses:
                query = query.filter(PromptTemplateModel.status.in_(statuses))
            if updated_at_gt:
                query = query.filter(PromptTemplateModel.updated_at > updated_at_gt)
            if updated_at_lt:
                query = query.filter(PromptTemplateModel.updated_at < updated_at_lt)

            total = query.count()
            query = query.order_by(PromptTemplateModel.updated_at.desc())
            query, _offset, _limit = _apply_pagination(query, page_number, limit)
            rows = query.all()

            entity_list = [
                PromptTemplateType(**_normalize(row)) for row in rows if _normalize(row)
            ]
            return PromptTemplateListType(
                prompt_template_list=entity_list,
                total=total,
                page_size=limit,
                page_number=page_number,
            )
        except Exception:
            session.rollback()
            raise
        finally:
            Config.db_session.remove()  # session lifecycle managed by scoped_session

    # ---- single-active ----

    def resolve_active(
        self, partition_key: str, entity_uuid: str = None, **kwargs: Any
    ) -> Optional[Dict[str, Any]]:
        prompt_uuid = entity_uuid or kwargs.get("prompt_uuid")
        if not partition_key or not prompt_uuid:
            return None
        from ....handlers.config import Config

        session = Config.db_session()
        try:
            row = (
                session.query(PromptTemplateModel)
                .filter(
                    PromptTemplateModel.partition_key == partition_key,
                    PromptTemplateModel.prompt_uuid == prompt_uuid,
                    PromptTemplateModel.status == "active",
                )
                .order_by(PromptTemplateModel.updated_at.desc())
                .first()
            )
            return _normalize(row)
        except Exception:
            session.rollback()
            raise
        finally:
            Config.db_session.remove()  # session lifecycle managed by scoped_session

    def _deactivate_others(
        self,
        session: Any,
        partition_key: str,
        prompt_uuid: str,
        keep_version_uuid: Optional[str] = None,
    ) -> None:
        """Set status='inactive' for other active prompt_templates with the same
        prompt_uuid, excluding ``keep_version_uuid`` (the row being written) so
        an in-place edit of the active version isn't left inactive.
        """
        query = session.query(PromptTemplateModel).filter(
            PromptTemplateModel.partition_key == partition_key,
            PromptTemplateModel.prompt_uuid == prompt_uuid,
            PromptTemplateModel.status == "active",
        )
        if keep_version_uuid:
            query = query.filter(
                PromptTemplateModel.prompt_version_uuid != keep_version_uuid
            )
        query.update(
            {PromptTemplateModel.status: "inactive"}, synchronize_session=False
        )

    def _get_active_row(
        self, session: Any, partition_key: str, prompt_uuid: Optional[str]
    ) -> Optional[PromptTemplateModel]:
        """Return the active PromptTemplateModel row for a prompt_uuid (same session)."""
        if not prompt_uuid:
            return None
        return (
            session.query(PromptTemplateModel)
            .filter(
                PromptTemplateModel.partition_key == partition_key,
                PromptTemplateModel.prompt_uuid == prompt_uuid,
                PromptTemplateModel.status == "active",
            )
            .order_by(PromptTemplateModel.updated_at.desc())
            .first()
        )

    # ---- write ----

    def insert_update(self, info: Any, **kwargs: Any) -> Optional[Dict[str, Any]]:
        import uuid as _uuid

        from ....handlers.config import Config

        partition_key = kwargs.get("partition_key") or _get_partition_key(info)
        if not partition_key:
            raise ValueError("partition_key is required")

        prompt_version_uuid = kwargs.get("prompt_version_uuid")
        session = Config.db_session()
        try:
            now = pendulum.now("UTC")

            # Only look up an existing row when an explicit version was given.
            row = None
            if prompt_version_uuid:
                row = (
                    session.query(PromptTemplateModel)
                    .filter(
                        PromptTemplateModel.partition_key == partition_key,
                        PromptTemplateModel.prompt_version_uuid == prompt_version_uuid,
                    )
                    .first()
                )

            if row is None:
                # New version / template. The DynamoDB path auto-generates the
                # version id (and prompt_uuid) via its insert_update decorator;
                # the PG repo must do the same.
                if not prompt_version_uuid:
                    prompt_version_uuid = f"{_uuid.uuid1().int % (10 ** 20):020d}"

                seed: Dict[str, Any] = {"status": "active"}
                prompt_uuid = kwargs.get("prompt_uuid")
                duplicate = kwargs.get("duplicate", False)
                active = self._get_active_row(session, partition_key, prompt_uuid)
                if active is not None:
                    excluded = {
                        "partition_key", "endpoint_id", "part_id",
                        "prompt_version_uuid", "status", "updated_by",
                        "created_at", "updated_at",
                    }
                    for k, v in (_normalize(active) or {}).items():
                        if k not in excluded:
                            seed[k] = v
                    if duplicate:
                        # A duplicate becomes a NEW template identity.
                        seed["prompt_uuid"] = (
                            f"prompt-{now.int_timestamp}-{str(_uuid.uuid4())[:8]}"
                        )
                        seed["prompt_name"] = f"{seed.get('prompt_name', '')} (Copy)"
                else:
                    seed["prompt_uuid"] = (
                        f"prompt-{now.int_timestamp}-{str(_uuid.uuid4())[:8]}"
                    )

                row = PromptTemplateModel(
                    partition_key=partition_key,
                    prompt_version_uuid=prompt_version_uuid,
                    created_at=now,
                    updated_at=now,
                )
                for _k, _v in seed.items():
                    setattr(row, _k, _v)
            else:
                row.updated_at = now

            # Caller-provided fields override seeded/inherited values.
            for field in _UPDATABLE_FIELDS:
                if field in kwargs:
                    setattr(row, field, kwargs[field])

            # Derive endpoint_id/part_id from partition_key when absent.
            if not getattr(row, "endpoint_id", None) and "#" in partition_key:
                _ep, _pt = partition_key.split("#", 1)
                row.endpoint_id = _ep
                row.part_id = _pt

            # Enforce single-active
            if getattr(row, "status", None) == "active" and getattr(
                row, "prompt_uuid", None
            ):
                self._deactivate_others(
                    session,
                    row.partition_key,
                    row.prompt_uuid,
                    keep_version_uuid=row.prompt_version_uuid,
                )
                row.status = "active"

            # Add to session after deactivation to avoid unique index violation
            if row not in session:
                session.add(row)

            session.commit()
            result = _normalize(row)
            _purge_cache(
                info,
                "prompt_template",
                {"prompt_version_uuid": row.prompt_version_uuid},
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
        prompt_version_uuid = kwargs.get("prompt_version_uuid")
        if not partition_key or not prompt_version_uuid:
            return False

        session = Config.db_session()
        try:
            row = (
                session.query(PromptTemplateModel)
                .filter(
                    PromptTemplateModel.partition_key == partition_key,
                    PromptTemplateModel.prompt_version_uuid == prompt_version_uuid,
                )
                .first()
            )
            if row is None:
                return False
            session.delete(row)
            session.commit()
            _purge_cache(
                info,
                "prompt_template",
                {"prompt_version_uuid": prompt_version_uuid},
                context_keys={"partition_key": partition_key},
            )
            return True
        except Exception:
            session.rollback()
            raise
        finally:
            Config.db_session.remove()  # session lifecycle managed by scoped_session

    def get_type(self, info: Any, instance: Any) -> Any:
        from ....types.prompt_template import PromptTemplateType

        data = instance if isinstance(instance, dict) else _normalize(instance)
        if data is None:
            return None
        return PromptTemplateType(**data)

    def resolve_single(self, info: Any, **kwargs: Any) -> Any:
        if "partition_key" not in kwargs:
            kwargs["partition_key"] = _get_partition_key(info)
        data = self.get(**kwargs)
        if data is None:
            return None
        return self.get_type(info, data)


__all__ = ["PromptTemplateRepository"]