# -*- coding: utf-8 -*-
"""Create threads table (partition-keyed, RLS)

Revision ID: 0005
Revises: 0004
Create Date: 2026-06-24 00:10:00.000000
"""
from __future__ import print_function

__author__ = "bibow"

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0005'
down_revision = '0004'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
    "aace_threads",
    sa.Column("partition_key", sa.String(128), primary_key=True),
        sa.Column("thread_uuid", sa.String(), primary_key=True),
        sa.Column("endpoint_id", sa.String(64), nullable=True),
        sa.Column("part_id", sa.String(64), nullable=True),
        sa.Column("agent_uuid", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('NOW()')),
    )
    op.create_index("aace_idx_threads_partition_agent_uuid", "aace_threads", ["partition_key", "agent_uuid"])
    op.create_index("aace_idx_threads_partition_created_at", "aace_threads", ["partition_key", "created_at"])


def downgrade() -> None:
    op.drop_index("aace_idx_threads_partition_agent_uuid", table_name="aace_threads")
    op.drop_index("aace_idx_threads_partition_created_at", table_name="aace_threads")
    op.drop_table("aace_threads")
