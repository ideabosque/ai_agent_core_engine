# -*- coding: utf-8 -*-
"""Create wizards table (partition-keyed, RLS)

Revision ID: 0012
Revises: 0011
Create Date: 2026-06-24 00:24:00.000000
"""
from __future__ import print_function

__author__ = "bibow"

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0012'
down_revision = '0011'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
    "aace_wizards",
    sa.Column("partition_key", sa.String(128), primary_key=True),
        sa.Column("wizard_uuid", sa.String(), primary_key=True),
        sa.Column("endpoint_id", sa.String(64), nullable=True),
        sa.Column("part_id", sa.String(64), nullable=True),
        sa.Column("wizard_title", sa.String(), nullable=False),
        sa.Column("wizard_description", sa.Text(), nullable=True),
        sa.Column("wizard_type", sa.String(), nullable=False),
        sa.Column("wizard_schema_type", sa.String(), nullable=False),
        sa.Column("wizard_schema_name", sa.String(), nullable=False),
        sa.Column("wizard_attributes", postgresql.JSONB, nullable=True),
        sa.Column("wizard_elements", postgresql.JSONB, nullable=True),
        sa.Column("priority", sa.Integer(), nullable=True, server_default='0'),
        sa.Column("updated_by", sa.String(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('NOW()')),
    )
    op.create_index("aace_idx_wizards_partition_updated_at", "aace_wizards", ["partition_key", "updated_at"])


def downgrade() -> None:
    op.drop_index("aace_idx_wizards_partition_updated_at", table_name="aace_wizards")
    op.drop_table("aace_wizards")
