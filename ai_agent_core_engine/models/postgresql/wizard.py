# -*- coding: utf-8 -*-
"""PostgreSQL SQLAlchemy model for Wizard entity.

Mirrors the DynamoDB WizardModel schema with PostgreSQL-appropriate types.
"""
from __future__ import print_function

__author__ = "bibow"

from sqlalchemy import (
    Column,
    Index,
    Integer,
    String,
    Text,
    TIMESTAMP,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declared_attr

from .base import Base, prefixed_index, prefixed_table


class WizardModel(Base):
    """SQLAlchemy model for the Wizard entity (table: aace_wizards)."""

    @declared_attr
    def __tablename__(cls) -> str:
        return prefixed_table("wizards")

    # Primary key: composite (partition_key, wizard_uuid)
    partition_key = Column(String(128), nullable=False, primary_key=True)
    wizard_uuid = Column(String, nullable=False, primary_key=True)

    # Tenant metadata
    endpoint_id = Column(String(64))
    part_id = Column(String(64))

    # Wizard attributes
    wizard_title = Column(String, nullable=False)
    wizard_description = Column(Text, nullable=True)
    wizard_type = Column(String, nullable=False)
    wizard_schema_type = Column(String, nullable=False)
    wizard_schema_name = Column(String, nullable=False)
    wizard_attributes = Column(JSONB)
    wizard_elements = Column(JSONB)
    priority = Column(Integer, default=0)

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
        # LSI: updated_at within partition
        Index(
            prefixed_index("idx_wizards_partition_updated_at"),
            "partition_key",
            "updated_at",
        ),
    )


__all__ = ["WizardModel"]