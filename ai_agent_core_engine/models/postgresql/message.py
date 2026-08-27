# -*- coding: utf-8 -*-
"""PostgreSQL SQLAlchemy model for Message entity.

Mirrors the DynamoDB MessageModel schema.  Adds a ``partition_key`` column
(not the hash key in DynamoDB) to enable Row-Level Security.
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
from sqlalchemy.orm import declared_attr

from .base import Base, prefixed_index, prefixed_table


class MessageModel(Base):
    """SQLAlchemy model for the Message entity (table: aace_messages)."""

    @declared_attr
    def __tablename__(cls) -> str:
        return prefixed_table("messages")

    # Primary key: composite (thread_uuid, message_uuid)
    thread_uuid = Column(String, nullable=False, primary_key=True)
    message_uuid = Column(String, nullable=False, primary_key=True)

    # Added for RLS (not the DynamoDB hash key, but present as an attribute)
    partition_key = Column(String(128), nullable=True)

    # Message attributes
    run_uuid = Column(String, nullable=True)
    message_id = Column(String, nullable=True)
    role = Column(String, nullable=False)
    message = Column(Text, nullable=False)

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
            prefixed_index("idx_messages_thread_run_uuid"),
            "thread_uuid",
            "run_uuid",
        ),
        # LSI: updated_at within thread
        Index(
            prefixed_index("idx_messages_thread_updated_at"),
            "thread_uuid",
            "updated_at",
        ),
        # Support RLS queries by partition_key
        Index(
            prefixed_index("idx_messages_partition_updated_at"),
            "partition_key",
            "updated_at",
        ),
    )


__all__ = ["MessageModel"]