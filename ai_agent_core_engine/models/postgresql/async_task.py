# -*- coding: utf-8 -*-
"""PostgreSQL SQLAlchemy model for AsyncTask entity.

Mirrors the DynamoDB AsyncTaskModel schema.  The ``partition_key`` column
is already present in the DynamoDB model (as a non-key attribute) and is
used for Row-Level Security.
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


class AsyncTaskModel(Base):
    """SQLAlchemy model for the AsyncTask entity (table: aace_async_tasks)."""

    @declared_attr
    def __tablename__(cls) -> str:
        return prefixed_table("async_tasks")

    # Primary key: composite (function_name, async_task_uuid)
    function_name = Column(String, nullable=False, primary_key=True)
    async_task_uuid = Column(String, nullable=False, primary_key=True)

    # Present in DynamoDB model — used for RLS
    partition_key = Column(String(128), nullable=True)

    # AsyncTask attributes
    arguments = Column(JSONB, nullable=True)
    result = Column(Text, nullable=True)
    output_files = Column(JSONB, nullable=True)
    status = Column(String, default="initial")
    notes = Column(Text, nullable=True)
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
        # GSI: partition_key + updated_at
        Index(
            prefixed_index("idx_async_tasks_partition_updated_at"),
            "partition_key",
            "updated_at",
        ),
    )


__all__ = ["AsyncTaskModel"]