# -*- coding: utf-8 -*-
"""PostgreSQL SQLAlchemy model for WizardGroup entity.

Mirrors the DynamoDB WizardGroupModel schema with PostgreSQL-appropriate types.
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


class WizardGroupModel(Base):
    """SQLAlchemy model for the WizardGroup entity (table: aace_wizard_groups)."""

    @declared_attr
    def __tablename__(cls) -> str:
        return prefixed_table("wizard_groups")

    # Primary key: composite (partition_key, wizard_group_uuid)
    partition_key = Column(String(128), nullable=False, primary_key=True)
    wizard_group_uuid = Column(String, nullable=False, primary_key=True)

    # Tenant metadata
    endpoint_id = Column(String(64))
    part_id = Column(String(64))

    # WizardGroup attributes
    wizard_group_name = Column(String, nullable=False)
    wizard_group_description = Column(Text, nullable=True)
    weight = Column(Integer, default=0)
    wizard_uuids = Column(JSONB, nullable=True)

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
            prefixed_index("idx_wizard_groups_partition_updated_at"),
            "partition_key",
            "updated_at",
        ),
    )


__all__ = ["WizardGroupModel"]