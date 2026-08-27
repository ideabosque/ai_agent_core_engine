# -*- coding: utf-8 -*-
"""Create runs table (has partition_key for RLS)

Revision ID: 0006
Revises: 0005
Create Date: 2026-06-24 00:12:00.000000
"""
from __future__ import print_function

__author__ = "bibow"

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0006'
down_revision = '0005'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
    "aace_runs",
    sa.Column("thread_uuid", sa.String(), primary_key=True),
        sa.Column("run_uuid", sa.String(), primary_key=True),
        sa.Column("partition_key", sa.String(128), nullable=True),
        sa.Column("run_id", sa.String(), nullable=True),
        sa.Column("completion_tokens", sa.Integer(), nullable=True, server_default='0'),
        sa.Column("prompt_tokens", sa.Integer(), nullable=True, server_default='0'),
        sa.Column("total_tokens", sa.Integer(), nullable=True, server_default='0'),
        sa.Column("time_spent", sa.Integer(), nullable=True),
        sa.Column("updated_by", sa.String(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('NOW()')),
    )
    op.create_index("aace_idx_runs_thread_updated_at", "aace_runs", ["thread_uuid", "updated_at"])
    op.create_index("aace_idx_runs_partition_key", "aace_runs", ["partition_key"])


def downgrade() -> None:
    op.drop_index("aace_idx_runs_thread_updated_at", table_name="aace_runs")
    op.drop_index("aace_idx_runs_partition_key", table_name="aace_runs")
    op.drop_table("aace_runs")
