# -*- coding: utf-8 -*-
"""PostgreSQL SQLAlchemy model for FineTuningMessage entity.

Mirrors the DynamoDB FineTuningMessageModel schema.  Adds a
``partition_key`` column (not the hash key in DynamoDB) to enable
Row-Level Security.
"""
from __future__ import print_function

__author__ = "bibow"

from sqlalchemy import (
    Boolean,
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


class FineTuningMessageModel(Base):
    """SQLAlchemy model for the FineTuningMessage entity (table: aace_fine_tuning_messages)."""

    @declared_attr
    def __tablename__(cls) -> str:
        return prefixed_table("fine_tuning_messages")

    # Primary key: composite (agent_uuid, message_uuid)
    agent_uuid = Column(String, nullable=False, primary_key=True)
    message_uuid = Column(String, nullable=False, primary_key=True)

    # Added for RLS (not the DynamoDB hash key, but present as an attribute)
    partition_key = Column(String(128), nullable=True)

    # FineTuningMessage attributes
    thread_uuid = Column(String, nullable=False)
    timestamp = Column(Integer, nullable=False)
    endpoint_id = Column(String)
    role = Column(String, nullable=False)
    tool_calls = Column(JSONB, nullable=True)
    tool_call_uuid = Column(String, nullable=True)
    content = Column(Text, nullable=True)
    weight = Column(Integer, default=0)
    trained = Column(Boolean, default=False)

    # Audit
    updated_by = Column(String)

    # Timestamps
    updated_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
    )

    __table_args__ = (
        # LSI: thread_uuid within agent
        Index(
            prefixed_index("idx_fine_tuning_messages_agent_thread_uuid"),
            "agent_uuid",
            "thread_uuid",
        ),
        # LSI: timestamp within agent
        Index(
            prefixed_index("idx_fine_tuning_messages_agent_timestamp"),
            "agent_uuid",
            "timestamp",
        ),
        # Support RLS queries by partition_key
        Index(
            prefixed_index("idx_fine_tuning_messages_partition_updated_at"),
            "partition_key",
            "updated_at",
        ),
    )


__all__ = ["FineTuningMessageModel"]