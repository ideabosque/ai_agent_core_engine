# -*- coding: utf-8 -*-
"""PostgreSQL SQLAlchemy model for Element entity.

Mirrors the DynamoDB ElementModel schema with PostgreSQL-appropriate types.
"""
from __future__ import print_function

__author__ = "bibow"

from sqlalchemy import (
    Column,
    Index,
    Integer,
    String,
    TIMESTAMP,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declared_attr

from .base import Base, prefixed_index, prefixed_table


class ElementModel(Base):
    """SQLAlchemy model for the Element entity (table: aace_elements)."""

    @declared_attr
    def __tablename__(cls) -> str:
        return prefixed_table("elements")

    # Primary key: composite (partition_key, element_uuid)
    partition_key = Column(String(128), nullable=False, primary_key=True)
    element_uuid = Column(String, nullable=False, primary_key=True)

    # Tenant metadata
    endpoint_id = Column(String(64))
    part_id = Column(String(64))

    # Element attributes
    data_type = Column(String, nullable=False)
    element_title = Column(String, nullable=False)
    priority = Column(Integer, default=0)
    attribute_name = Column(String, nullable=False)
    attribute_type = Column(String, nullable=False)
    option_values = Column(JSONB)
    conditions = Column(JSONB)
    pattern = Column(String)

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
        # LSI: data_type within partition
        Index(
            prefixed_index("idx_elements_partition_data_type"),
            "partition_key",
            "data_type",
        ),
        # LSI: updated_at within partition
        Index(
            prefixed_index("idx_elements_partition_updated_at"),
            "partition_key",
            "updated_at",
        ),
    )


__all__ = ["ElementModel"]