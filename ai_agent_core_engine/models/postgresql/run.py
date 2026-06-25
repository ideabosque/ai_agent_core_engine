# -*- coding: utf-8 -*-
"""PostgreSQL SQLAlchemy model for Run entity.

Mirrors the DynamoDB RunModel schema.  Adds a ``partition_key`` column
(not the hash key in DynamoDB) to enable Row-Level Security.
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
from sqlalchemy.orm import declared_attr

from .base import Base, prefixed_index, prefixed_table


class RunModel(Base):
    """SQLAlchemy model for the Run entity (table: aace_runs)."""

    @declared_attr
    def __tablename__(cls) -> str:
        return prefixed_table("runs")

    # Primary key: composite (thread_uuid, run_uuid)
    thread_uuid = Column(String, nullable=False, primary_key=True)
    run_uuid = Column(String, nullable=False, primary_key=True)

    # Added for RLS (not the DynamoDB hash key, but present as an attribute)
    partition_key = Column(String(128), nullable=True)

    # Run attributes
    run_id = Column(String, nullable=True)
    completion_tokens = Column(Integer, default=0)
    prompt_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    time_spent = Column(Integer, nullable=True)

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
        # LSI: updated_at within thread
        Index(
            prefixed_index("idx_runs_thread_updated_at"),
            "thread_uuid",
            "updated_at",
        ),
        # Support RLS queries by partition_key
        Index(
            prefixed_index("idx_runs_partition_updated_at"),
            "partition_key",
            "updated_at",
        ),
    )


__all__ = ["RunModel"]