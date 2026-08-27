# -*- coding: utf-8 -*-
"""Create tool_calls table (has partition_key for RLS)

Revision ID: 0008
Revises: 0007
Create Date: 2026-06-24 00:16:00.000000
"""
from __future__ import print_function

__author__ = "bibow"

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0008'
down_revision = '0007'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
    "aace_tool_calls",
    sa.Column("thread_uuid", sa.String(), primary_key=True),
        sa.Column("tool_call_uuid", sa.String(), primary_key=True),
        sa.Column("partition_key", sa.String(128), nullable=True),
        sa.Column("run_uuid", sa.String(), nullable=True),
        sa.Column("tool_call_id", sa.String(), nullable=True),
        sa.Column("tool_type", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("arguments", sa.Text(), nullable=True),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("status", sa.String(), nullable=True, server_default='initial'),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("time_spent", sa.Integer(), nullable=True),
        sa.Column("updated_by", sa.String(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('NOW()')),
    )
    op.create_index("aace_idx_tool_calls_thread_run_uuid", "aace_tool_calls", ["thread_uuid", "run_uuid"])
    op.create_index("aace_idx_tool_calls_thread_updated_at", "aace_tool_calls", ["thread_uuid", "updated_at"])
    op.create_index("aace_idx_tool_calls_partition_key", "aace_tool_calls", ["partition_key"])


def downgrade() -> None:
    op.drop_index("aace_idx_tool_calls_thread_run_uuid", table_name="aace_tool_calls")
    op.drop_index("aace_idx_tool_calls_thread_updated_at", table_name="aace_tool_calls")
    op.drop_index("aace_idx_tool_calls_partition_key", table_name="aace_tool_calls")
    op.drop_table("aace_tool_calls")
