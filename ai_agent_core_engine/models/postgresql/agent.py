# -*- coding: utf-8 -*-
"""PostgreSQL SQLAlchemy model for Agent entity.

Mirrors the DynamoDB AgentModel schema with PostgreSQL-appropriate types.
Uses string-based UUIDs (e.g. "agent-..."), not native UUID columns.
Enforces the single-active invariant via a partial unique index on
(partition_key, agent_uuid) WHERE status = 'active'.
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


class AgentModel(Base):
    """SQLAlchemy model for the Agent entity (table: aace_agents)."""

    @declared_attr
    def __tablename__(cls) -> str:
        return prefixed_table("agents")

    # Primary key: composite (partition_key, agent_version_uuid)
    partition_key = Column(String(128), nullable=False, primary_key=True)
    agent_version_uuid = Column(String, nullable=False, primary_key=True)

    # Tenant metadata
    endpoint_id = Column(String(64))
    part_id = Column(String(64))

    # Agent attributes
    agent_uuid = Column(String, nullable=False)
    agent_name = Column(String, nullable=False)
    agent_description = Column(Text, nullable=True)
    llm_provider = Column(String, nullable=False)
    llm_name = Column(String, nullable=False)
    instructions = Column(Text, nullable=True)
    configuration = Column(JSONB)
    mcp_server_uuids = Column(JSONB, nullable=True)
    variables = Column(JSONB, nullable=True)
    num_of_messages = Column(Integer, default=10)
    tool_call_role = Column(String, default="developer")
    flow_snippet_version_uuid = Column(String, nullable=True)

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
        # LSI: agent_uuid within partition
        Index(
            prefixed_index("idx_agents_partition_agent_uuid"),
            "partition_key",
            "agent_uuid",
        ),
        # LSI: updated_at within partition
        Index(
            prefixed_index("idx_agents_partition_updated_at"),
            "partition_key",
            "updated_at",
        ),
        # Partial unique index for single-active invariant
        Index(
            prefixed_index("idx_agents_one_active"),
            "partition_key",
            "agent_uuid",
            unique=True,
            postgresql_where=text("status = 'active'"),
        ),
    )


__all__ = ["AgentModel"]