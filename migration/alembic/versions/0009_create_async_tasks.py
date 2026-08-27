# -*- coding: utf-8 -*-
"""Create async_tasks table (has partition_key for RLS)

Revision ID: 0009
Revises: 0008
Create Date: 2026-06-24 00:18:00.000000
"""
from __future__ import print_function

__author__ = "bibow"

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0009'
down_revision = '0008'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
    "aace_async_tasks",
    sa.Column("function_name", sa.String(), primary_key=True),
        sa.Column("async_task_uuid", sa.String(), primary_key=True),
        sa.Column("partition_key", sa.String(128), nullable=True),
        sa.Column("arguments", postgresql.JSONB, nullable=True),
        sa.Column("result", sa.Text(), nullable=True),
        sa.Column("output_files", postgresql.JSONB, nullable=True),
        sa.Column("status", sa.String(), nullable=True, server_default='initial'),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("time_spent", sa.Integer(), nullable=True),
        sa.Column("updated_by", sa.String(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('NOW()')),
    )
    op.create_index("aace_idx_async_tasks_partition_updated_at", "aace_async_tasks", ["partition_key", "updated_at"])


def downgrade() -> None:
    op.drop_index("aace_idx_async_tasks_partition_updated_at", table_name="aace_async_tasks")
    op.drop_table("aace_async_tasks")
