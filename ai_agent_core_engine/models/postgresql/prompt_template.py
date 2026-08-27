# -*- coding: utf-8 -*-
"""PostgreSQL SQLAlchemy model for PromptTemplate entity.

Mirrors the DynamoDB PromptTemplateModel schema with PostgreSQL-appropriate types.
Enforces the single-active invariant via a partial unique index on
(partition_key, prompt_uuid) WHERE status = 'active'.
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


class PromptTemplateModel(Base):
    """SQLAlchemy model for the PromptTemplate entity (table: aace_prompt_templates)."""

    @declared_attr
    def __tablename__(cls) -> str:
        return prefixed_table("prompt_templates")

    # Primary key: composite (partition_key, prompt_version_uuid)
    partition_key = Column(String(128), nullable=False, primary_key=True)
    prompt_version_uuid = Column(String, nullable=False, primary_key=True)

    # Tenant metadata
    endpoint_id = Column(String(64))
    part_id = Column(String(64))

    # PromptTemplate attributes
    prompt_uuid = Column(String, nullable=False)
    prompt_type = Column(String, nullable=False)
    prompt_name = Column(String, nullable=False)
    prompt_description = Column(Text, nullable=True)
    template_context = Column(Text, nullable=False)
    variables = Column(JSONB)
    mcp_servers = Column(JSONB)
    ui_components = Column(JSONB)

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
        # LSI: prompt_uuid within partition
        Index(
            prefixed_index("idx_prompt_templates_partition_prompt_uuid"),
            "partition_key",
            "prompt_uuid",
        ),
        # LSI: prompt_type within partition
        Index(
            prefixed_index("idx_prompt_templates_partition_prompt_type"),
            "partition_key",
            "prompt_type",
        ),
        # LSI: updated_at within partition
        Index(
            prefixed_index("idx_prompt_templates_partition_updated_at"),
            "partition_key",
            "updated_at",
        ),
        # Partial unique index for single-active invariant
        Index(
            prefixed_index("idx_prompt_templates_one_active"),
            "partition_key",
            "prompt_uuid",
            unique=True,
            postgresql_where=text("status = 'active'"),
        ),
    )


__all__ = ["PromptTemplateModel"]