# -*- coding: utf-8 -*-
"""Create llms table (global registry, no RLS)

Revision ID: 0001
Revises: None
Create Date: 2026-06-24 00:02:00.000000
"""
from __future__ import print_function

__author__ = "bibow"

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
    "aace_llms",
    sa.Column("llm_provider", sa.String(), primary_key=True),
        sa.Column("llm_name", sa.String(), primary_key=True),
        sa.Column("module_name", sa.String(), nullable=True),
        sa.Column("class_name", sa.String(), nullable=True),
        sa.Column("configuration_schema", postgresql.JSONB, nullable=True),
        sa.Column("updated_by", sa.String(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('NOW()')),
    )
    op.create_index("aace_idx_llms_provider_updated_at", "aace_llms", ["llm_provider", "updated_at"])


def downgrade() -> None:
    op.drop_index("aace_idx_llms_provider_updated_at", table_name="aace_llms")
    op.drop_table("aace_llms")
