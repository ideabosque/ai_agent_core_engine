# -*- coding: utf-8 -*-
"""PostgreSQL SQLAlchemy model for WizardSchema entity.

Mirrors the DynamoDB WizardSchemaModel schema.  This is a global registry —
no ``partition_key`` and no RLS policy.
"""
from __future__ import print_function

__author__ = "bibow"

from sqlalchemy import (
    Column,
    Index,
    String,
    Text,
    TIMESTAMP,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declared_attr

from .base import Base, prefixed_index, prefixed_table


class WizardSchemaModel(Base):
    """SQLAlchemy model for the WizardSchema entity (table: aace_wizard_schemas)."""

    @declared_attr
    def __tablename__(cls) -> str:
        return prefixed_table("wizard_schemas")

    # Primary key: composite (wizard_schema_type, wizard_schema_name)
    wizard_schema_type = Column(String, nullable=False, primary_key=True)
    wizard_schema_name = Column(String, nullable=False, primary_key=True)

    # WizardSchema attributes
    wizard_schema_description = Column(Text, nullable=True)
    attributes = Column(JSONB)
    attribute_groups = Column(JSONB)

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
        # LSI: updated_at within schema type
        Index(
            prefixed_index("idx_wizard_schemas_type_updated_at"),
            "wizard_schema_type",
            "updated_at",
        ),
    )


__all__ = ["WizardSchemaModel"]