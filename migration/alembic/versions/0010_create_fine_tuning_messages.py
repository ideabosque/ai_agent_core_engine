# -*- coding: utf-8 -*-
"""Create fine_tuning_messages table (has partition_key for RLS)

Revision ID: 0010
Revises: 0009
Create Date: 2026-06-24 00:20:00.000000
"""
from __future__ import print_function

__author__ = "bibow"

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0010'
down_revision = '0009'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
    "aace_fine_tuning_messages",
    sa.Column("agent_uuid", sa.String(), primary_key=True),
        sa.Column("message_uuid", sa.String(), primary_key=True),
        sa.Column("partition_key", sa.String(128), nullable=True),
        sa.Column("thread_uuid", sa.String(), nullable=False),
        sa.Column("timestamp", sa.Integer(), nullable=False),
        sa.Column("endpoint_id", sa.String(), nullable=True),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("tool_calls", postgresql.JSONB, nullable=True),
        sa.Column("tool_call_uuid", sa.String(), nullable=True),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("weight", sa.Integer(), nullable=True, server_default='0'),
        sa.Column("trained", sa.Boolean(), nullable=True, server_default='false'),
        sa.Column("updated_by", sa.String(), nullable=True),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('NOW()')),
    )
    op.create_index("aace_idx_fine_tuning_messages_agent_thread", "aace_fine_tuning_messages", ["agent_uuid", "thread_uuid"])
    op.create_index("aace_idx_fine_tuning_messages_agent_timestamp", "aace_fine_tuning_messages", ["agent_uuid", "timestamp"])
    op.create_index("aace_idx_fine_tuning_messages_partition_key", "aace_fine_tuning_messages", ["partition_key"])


def downgrade() -> None:
    op.drop_index("aace_idx_fine_tuning_messages_agent_thread", table_name="aace_fine_tuning_messages")
    op.drop_index("aace_idx_fine_tuning_messages_agent_timestamp", table_name="aace_fine_tuning_messages")
    op.drop_index("aace_idx_fine_tuning_messages_partition_key", table_name="aace_fine_tuning_messages")
    op.drop_table("aace_fine_tuning_messages")
