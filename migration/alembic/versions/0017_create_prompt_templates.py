# -*- coding: utf-8 -*-
"""Create prompt_templates table (partition-keyed, RLS, single-active)

Revision ID: 0017
Revises: 0016
Create Date: 2026-06-24 00:34:00.000000
"""
from __future__ import print_function

__author__ = "bibow"

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0017'
down_revision = '0016'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
    "aace_prompt_templates",
    sa.Column("partition_key", sa.String(128), primary_key=True),
        sa.Column("prompt_version_uuid", sa.String(), primary_key=True),
        sa.Column("endpoint_id", sa.String(64), nullable=True),
        sa.Column("part_id", sa.String(64), nullable=True),
        sa.Column("prompt_uuid", sa.String(), nullable=False),
        sa.Column("prompt_type", sa.String(), nullable=False),
        sa.Column("prompt_name", sa.String(), nullable=False),
        sa.Column("prompt_description", sa.Text(), nullable=True),
        sa.Column("template_context", sa.Text(), nullable=False),
        sa.Column("variables", postgresql.JSONB, nullable=True),
        sa.Column("mcp_servers", postgresql.JSONB, nullable=True),
        sa.Column("ui_components", postgresql.JSONB, nullable=True),
        sa.Column("status", sa.String(), nullable=True, server_default='active'),
        sa.Column("updated_by", sa.String(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('NOW()')),
    )
    op.create_index("aace_idx_prompt_templates_partition_prompt_uuid", "aace_prompt_templates", ["partition_key", "prompt_uuid"])
    op.create_index("aace_idx_prompt_templates_partition_prompt_type", "aace_prompt_templates", ["partition_key", "prompt_type"])
    op.create_index("aace_idx_prompt_templates_partition_updated_at", "aace_prompt_templates", ["partition_key", "updated_at"])
    op.create_index("aace_idx_prompt_templates_one_active", "aace_prompt_templates", ["partition_key", "prompt_uuid"], unique=True, postgresql_where=sa.text("status = 'active'"))


def downgrade() -> None:
    op.drop_index("aace_idx_prompt_templates_partition_prompt_uuid", table_name="aace_prompt_templates")
    op.drop_index("aace_idx_prompt_templates_partition_prompt_type", table_name="aace_prompt_templates")
    op.drop_index("aace_idx_prompt_templates_partition_updated_at", table_name="aace_prompt_templates")
    op.drop_index("aace_idx_prompt_templates_one_active", table_name="aace_prompt_templates")
    op.drop_table("aace_prompt_templates")
