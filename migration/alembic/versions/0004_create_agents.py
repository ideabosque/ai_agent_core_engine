# -*- coding: utf-8 -*-
"""Create agents table (partition-keyed, RLS, single-active)

Revision ID: 0004
Revises: 0003
Create Date: 2026-06-24 00:08:00.000000
"""
from __future__ import print_function

__author__ = "bibow"

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0004'
down_revision = '0003'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
    "aace_agents",
    sa.Column("partition_key", sa.String(128), primary_key=True),
        sa.Column("agent_version_uuid", sa.String(), primary_key=True),
        sa.Column("endpoint_id", sa.String(64), nullable=True),
        sa.Column("part_id", sa.String(64), nullable=True),
        sa.Column("agent_uuid", sa.String(), nullable=False),
        sa.Column("agent_name", sa.String(), nullable=False),
        sa.Column("agent_description", sa.Text(), nullable=True),
        sa.Column("llm_provider", sa.String(), nullable=False),
        sa.Column("llm_name", sa.String(), nullable=False),
        sa.Column("instructions", sa.Text(), nullable=True),
        sa.Column("configuration", postgresql.JSONB, nullable=True),
        sa.Column("mcp_server_uuids", postgresql.JSONB, nullable=True),
        sa.Column("variables", postgresql.JSONB, nullable=True),
        sa.Column("num_of_messages", sa.Integer(), nullable=True, server_default='10'),
        sa.Column("tool_call_role", sa.String(), nullable=True, server_default='developer'),
        sa.Column("flow_snippet_version_uuid", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=True, server_default='active'),
        sa.Column("updated_by", sa.String(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('NOW()')),
    )
    op.create_index("aace_idx_agents_partition_agent_uuid", "aace_agents", ["partition_key", "agent_uuid"])
    op.create_index("aace_idx_agents_partition_updated_at", "aace_agents", ["partition_key", "updated_at"])
    op.create_index("aace_idx_agents_one_active", "aace_agents", ["partition_key", "agent_uuid"], unique=True, postgresql_where=sa.text("status = 'active'"))


def downgrade() -> None:
    op.drop_index("aace_idx_agents_partition_agent_uuid", table_name="aace_agents")
    op.drop_index("aace_idx_agents_partition_updated_at", table_name="aace_agents")
    op.drop_index("aace_idx_agents_one_active", table_name="aace_agents")
    op.drop_table("aace_agents")
