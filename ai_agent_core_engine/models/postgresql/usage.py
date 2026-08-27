# -*- coding: utf-8 -*-
"""PostgreSQL SQLAlchemy models for usage tracking (usage_limit / usage_summary).

Mirrors the DynamoDB usage models.  Only imported when
``Config.DB_BACKEND == "postgresql"``.  The persistence logic lives in
``models.repositories.postgresql.usage_repo`` (PG convention: models here,
queries in the repository).

The ``partition_key`` column is used for Row-Level Security, matching the other
partition-keyed PostgreSQL tables.
"""
from __future__ import print_function

__author__ = "bibow"

from sqlalchemy import (
    Boolean,
    Column,
    Index,
    Integer,
    String,
    TIMESTAMP,
    text,
)
from sqlalchemy.orm import declared_attr

from .base import Base, prefixed_index, prefixed_table


class UsageLimitModel(Base):
    """SQLAlchemy model for the usage_limit entity (table: aace_usage_limit)."""

    @declared_attr
    def __tablename__(cls) -> str:
        return prefixed_table("usage_limit")

    # Primary key: composite (partition_key, usage_key)
    partition_key = Column(String(128), nullable=False, primary_key=True)
    usage_key = Column(String, nullable=False, primary_key=True)

    usage_limit = Column(Integer, nullable=True)
    allow_overage = Column(Boolean, nullable=True)
    period_start = Column(TIMESTAMP(timezone=True), nullable=True)
    period_end = Column(TIMESTAMP(timezone=True), nullable=True)

    created_from = Column(String, nullable=True)
    status = Column(String, nullable=True)

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


class UsageSummaryModel(Base):
    """SQLAlchemy model for the usage_summary entity (table: aace_usage_summary)."""

    @declared_attr
    def __tablename__(cls) -> str:
        return prefixed_table("usage_summary")

    # Primary key: composite (partition_key, usage_key_period_start)
    partition_key = Column(String(128), nullable=False, primary_key=True)
    usage_key_period_start = Column(String, nullable=False, primary_key=True)

    usage_key = Column(String, nullable=True)
    total = Column(Integer, nullable=False, server_default=text("0"))

    __table_args__ = (
        Index(
            prefixed_index("idx_usage_summary_partition_key"),
            "partition_key",
        ),
    )


__all__ = ["UsageLimitModel", "UsageSummaryModel"]
