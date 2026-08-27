# -*- coding: utf-8 -*-
"""PostgreSQL SQLAlchemy model for LLM entity.

Mirrors the DynamoDB LlmModel schema.  This is a global registry —
no ``partition_key`` and no RLS policy.
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
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declared_attr

from .base import Base, prefixed_index, prefixed_table


class LlmModel(Base):
    """SQLAlchemy model for the LLM entity (table: aace_llms)."""

    @declared_attr
    def __tablename__(cls) -> str:
        return prefixed_table("llms")

    # Primary key: composite (llm_provider, llm_name)
    llm_provider = Column(String, nullable=False, primary_key=True)
    llm_name = Column(String, nullable=False, primary_key=True)

    # LLM attributes
    module_name = Column(String)
    class_name = Column(String)
    configuration_schema = Column(JSONB)

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
        # LSI: updated_at within provider
        Index(
            prefixed_index("idx_llms_provider_updated_at"),
            "llm_provider",
            "updated_at",
        ),
    )


__all__ = ["LlmModel"]