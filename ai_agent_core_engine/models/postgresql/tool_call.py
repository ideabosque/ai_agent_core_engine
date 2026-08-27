# -*- coding: utf-8 -*-
"""PostgreSQL SQLAlchemy model for ToolCall entity.

Mirrors the DynamoDB ToolCallModel schema.  Adds a ``partition_key`` column
(not the hash key in DynamoDB) to enable Row-Level Security.
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
from sqlalchemy.orm import declared_attr

from .base import Base, prefixed_index, prefixed_table


class ToolCallModel(Base):
    """SQLAlchemy model for the ToolCall entity (table: aace_tool_calls)."""

    @declared_attr
    def __tablename__(cls) -> str:
        return prefixed_table("tool_calls")

    # Primary key: composite (thread_uuid, tool_call_uuid)
    thread_uuid = Column(String, nullable=False, primary_key=True)
    tool_call_uuid = Column(String, nullable=False, primary_key=True)

    # Added for RLS (not the DynamoDB hash key, but present as an attribute)
    partition_key = Column(String(128), nullable=True)

    # ToolCall attributes
    run_uuid = Column(String, nullable=True)
    tool_call_id = Column(String, nullable=True)
    tool_type = Column(String, nullable=False)
    name = Column(String, nullable=False)
    arguments = Column(Text, nullable=True)
    content = Column(Text, nullable=True)
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
        # LSI: run_uuid within thread
        Index(
            prefixed_index("idx_tool_calls_thread_run_uuid"),
            "thread_uuid",
            "run_uuid",
        ),
        # LSI: updated_at within thread
        Index(
            prefixed_index("idx_tool_calls_thread_updated_at"),
            "thread_uuid",
            "updated_at",
        ),
        # Support RLS queries by partition_key
        Index(
            prefixed_index("idx_tool_calls_partition_updated_at"),
            "partition_key",
            "updated_at",
        ),
    )


__all__ = ["ToolCallModel"]