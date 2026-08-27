# -*- coding: utf-8 -*-
"""Create flow_snippets table (partition-keyed, RLS, single-active)

Revision ID: 0016
Revises: 0015
Create Date: 2026-06-24 00:32:00.000000
"""
from __future__ import print_function

__author__ = "bibow"

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0016'
down_revision = '0015'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
    "aace_flow_snippets",
    sa.Column("partition_key", sa.String(128), primary_key=True),
        sa.Column("flow_snippet_version_uuid", sa.String(), primary_key=True),
        sa.Column("endpoint_id", sa.String(64), nullable=True),
        sa.Column("part_id", sa.String(64), nullable=True),
        sa.Column("flow_snippet_uuid", sa.String(), nullable=False),
        sa.Column("prompt_uuid", sa.String(), nullable=False),
        sa.Column("flow_name", sa.String(), nullable=False),
        sa.Column("flow_relationship", sa.Text(), nullable=True),
        sa.Column("flow_context", sa.Text(), nullable=True),
        sa.Column("enabled_tools", postgresql.JSONB, nullable=True),
        sa.Column("status", sa.String(), nullable=True, server_default='active'),
        sa.Column("updated_by", sa.String(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('NOW()')),
    )
    op.create_index("aace_idx_flow_snippets_partition_flow_snippet_uuid", "aace_flow_snippets", ["partition_key", "flow_snippet_uuid"])
    op.create_index("aace_idx_flow_snippets_partition_prompt_uuid", "aace_flow_snippets", ["partition_key", "prompt_uuid"])
    op.create_index("aace_idx_flow_snippets_partition_updated_at", "aace_flow_snippets", ["partition_key", "updated_at"])
    op.create_index("aace_idx_flow_snippets_one_active", "aace_flow_snippets", ["partition_key", "flow_snippet_uuid"], unique=True, postgresql_where=sa.text("status = 'active'"))


def downgrade() -> None:
    op.drop_index("aace_idx_flow_snippets_partition_flow_snippet_uuid", table_name="aace_flow_snippets")
    op.drop_index("aace_idx_flow_snippets_partition_prompt_uuid", table_name="aace_flow_snippets")
    op.drop_index("aace_idx_flow_snippets_partition_updated_at", table_name="aace_flow_snippets")
    op.drop_index("aace_idx_flow_snippets_one_active", table_name="aace_flow_snippets")
    op.drop_table("aace_flow_snippets")
