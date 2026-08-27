# -*- coding: utf-8 -*-
"""PostgreSQL SQLAlchemy model for UIComponent entity.

Mirrors the DynamoDB UIComponentModel schema.  This is a global registry —
no ``partition_key`` and no RLS policy.
"""
from __future__ import print_function

__author__ = "bibow"

from sqlalchemy import (
    Column,
    Index,
    String,
    TIMESTAMP,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declared_attr

from .base import Base, prefixed_index, prefixed_table


class UIComponentModel(Base):
    """SQLAlchemy model for the UIComponent entity (table: aace_ui_components)."""

    @declared_attr
    def __tablename__(cls) -> str:
        return prefixed_table("ui_components")

    # Primary key: composite (ui_component_type, ui_component_uuid)
    ui_component_type = Column(String, nullable=False, primary_key=True)
    ui_component_uuid = Column(String, nullable=False, primary_key=True)

    # UIComponent attributes
    tag_name = Column(String, nullable=False)
    tag_alias = Column(String, nullable=True)
    parameters = Column(JSONB)
    wait_for = Column(String, nullable=True)

    # Audit
    updated_by = Column(String)

    # Timestamps
    created_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
    )
    updated_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
    )

    __table_args__ = (
        # LSI: updated_at within component type
        Index(
            prefixed_index("idx_ui_components_type_updated_at"),
            "ui_component_type",
            "updated_at",
        ),
    )


__all__ = ["UIComponentModel"]