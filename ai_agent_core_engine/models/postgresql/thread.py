# -*- coding: utf-8 -*-
"""PostgreSQL SQLAlchemy model for Thread entity.

Mirrors the DynamoDB ThreadModel schema with PostgreSQL-appropriate types.
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
from sqlalchemy.orm import declared_attr

from .base import Base, prefixed_index, prefixed_table


class ThreadModel(Base):
    """SQLAlchemy model for the Thread entity (table: aace_threads)."""

    @declared_attr
    def __tablename__(cls) -> str:
        return prefixed_table("threads")

    # Primary key: composite (partition_key, thread_uuid)
    partition_key = Column(String(128), nullable=False, primary_key=True)
    thread_uuid = Column(String, nullable=False, primary_key=True)

    # Tenant metadata
    endpoint_id = Column(String(64))
    part_id = Column(String(64))

    # Thread attributes
    agent_uuid = Column(String, nullable=False)
    user_id = Column(String, nullable=True)

    # Timestamps
    created_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
    )

    __table_args__ = (
        # LSI: agent_uuid within partition
        Index(
            prefixed_index("idx_threads_partition_agent_uuid"),
            "partition_key",
            "agent_uuid",
        ),
        # LSI: created_at within partition
        Index(
            prefixed_index("idx_threads_partition_created_at"),
            "partition_key",
            "created_at",
        ),
    )


__all__ = ["ThreadModel"]