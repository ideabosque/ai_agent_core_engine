# -*- coding: utf-8 -*-
"""Create mcp_servers table (partition-keyed, RLS)

Revision ID: 0015
Revises: 0014
Create Date: 2026-06-24 00:30:00.000000
"""
from __future__ import print_function

__author__ = "bibow"

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0015'
down_revision = '0014'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
    "aace_mcp_servers",
    sa.Column("partition_key", sa.String(128), primary_key=True),
        sa.Column("mcp_server_uuid", sa.String(), primary_key=True),
        sa.Column("endpoint_id", sa.String(64), nullable=True),
        sa.Column("part_id", sa.String(64), nullable=True),
        sa.Column("mcp_label", sa.String(), nullable=False),
        sa.Column("mcp_server_url", sa.String(), nullable=False),
        sa.Column("headers", postgresql.JSONB, nullable=True),
        sa.Column("updated_by", sa.String(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('NOW()')),
    )
    op.create_index("aace_idx_mcp_servers_partition_updated_at", "aace_mcp_servers", ["partition_key", "updated_at"])


def downgrade() -> None:
    op.drop_index("aace_idx_mcp_servers_partition_updated_at", table_name="aace_mcp_servers")
    op.drop_table("aace_mcp_servers")
