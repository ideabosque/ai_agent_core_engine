# -*- coding: utf-8 -*-
"""PostgreSQL SQLAlchemy model for FlowSnippet entity.

Mirrors the DynamoDB FlowSnippetModel schema with PostgreSQL-appropriate types.
Enforces the single-active invariant via a partial unique index on
(partition_key, flow_snippet_uuid) WHERE status = 'active'.
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
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declared_attr

from .base import Base, prefixed_index, prefixed_table


class FlowSnippetModel(Base):
    """SQLAlchemy model for the FlowSnippet entity (table: aace_flow_snippets)."""

    @declared_attr
    def __tablename__(cls) -> str:
        return prefixed_table("flow_snippets")

    # Primary key: composite (partition_key, flow_snippet_version_uuid)
    partition_key = Column(String(128), nullable=False, primary_key=True)
    flow_snippet_version_uuid = Column(String, nullable=False, primary_key=True)

    # Tenant metadata
    endpoint_id = Column(String(64))
    part_id = Column(String(64))

    # FlowSnippet attributes
    flow_snippet_uuid = Column(String, nullable=False)
    prompt_uuid = Column(String, nullable=False)
    flow_name = Column(String, nullable=False)
    flow_relationship = Column(Text, nullable=True)
    flow_context = Column(Text, nullable=True)
    enabled_tools = Column(JSONB, nullable=True)

    # Status & audit
    status = Column(String, default="active")
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
        # LSI: flow_snippet_uuid within partition
        Index(
            prefixed_index("idx_flow_snippets_partition_flow_snippet_uuid"),
            "partition_key",
            "flow_snippet_uuid",
        ),
        # LSI: prompt_uuid within partition
        Index(
            prefixed_index("idx_flow_snippets_partition_prompt_uuid"),
            "partition_key",
            "prompt_uuid",
        ),
        # LSI: updated_at within partition
        Index(
            prefixed_index("idx_flow_snippets_partition_updated_at"),
            "partition_key",
            "updated_at",
        ),
        # Partial unique index for single-active invariant
        Index(
            prefixed_index("idx_flow_snippets_one_active"),
            "partition_key",
            "flow_snippet_uuid",
            unique=True,
            postgresql_where=text("status = 'active'"),
        ),
    )


__all__ = ["FlowSnippetModel"]