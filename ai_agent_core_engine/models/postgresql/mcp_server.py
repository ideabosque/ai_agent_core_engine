# -*- coding: utf-8 -*-
"""PostgreSQL SQLAlchemy model for MCPServer entity.

Mirrors the DynamoDB MCPServerModel schema with PostgreSQL-appropriate types.
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


class MCPServerModel(Base):
    """SQLAlchemy model for the MCPServer entity (table: aace_mcp_servers)."""

    @declared_attr
    def __tablename__(cls) -> str:
        return prefixed_table("mcp_servers")

    # Primary key: composite (partition_key, mcp_server_uuid)
    partition_key = Column(String(128), nullable=False, primary_key=True)
    mcp_server_uuid = Column(String, nullable=False, primary_key=True)

    # Tenant metadata
    endpoint_id = Column(String(64))
    part_id = Column(String(64))

    # MCPServer attributes
    mcp_label = Column(String, nullable=False)
    mcp_server_url = Column(String, nullable=False)
    headers = Column(JSONB)

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
        # LSI: updated_at within partition
        Index(
            prefixed_index("idx_mcp_servers_partition_updated_at"),
            "partition_key",
            "updated_at",
        ),
    )


__all__ = ["MCPServerModel"]