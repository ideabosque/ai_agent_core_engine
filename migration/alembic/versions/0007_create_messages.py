# -*- coding: utf-8 -*-
"""Create messages table (has partition_key for RLS)

Revision ID: 0007
Revises: 0006
Create Date: 2026-06-24 00:14:00.000000
"""
from __future__ import print_function

__author__ = "bibow"

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0007'
down_revision = '0006'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
    "aace_messages",
    sa.Column("thread_uuid", sa.String(), primary_key=True),
        sa.Column("message_uuid", sa.String(), primary_key=True),
        sa.Column("partition_key", sa.String(128), nullable=True),
        sa.Column("run_uuid", sa.String(), nullable=True),
        sa.Column("message_id", sa.String(), nullable=True),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("updated_by", sa.String(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('NOW()')),
    )
    op.create_index("aace_idx_messages_thread_run_uuid", "aace_messages", ["thread_uuid", "run_uuid"])
    op.create_index("aace_idx_messages_thread_updated_at", "aace_messages", ["thread_uuid", "updated_at"])
    op.create_index("aace_idx_messages_partition_key", "aace_messages", ["partition_key"])


def downgrade() -> None:
    op.drop_index("aace_idx_messages_thread_run_uuid", table_name="aace_messages")
    op.drop_index("aace_idx_messages_thread_updated_at", table_name="aace_messages")
    op.drop_index("aace_idx_messages_partition_key", table_name="aace_messages")
    op.drop_table("aace_messages")
