# -*- coding: utf-8 -*-
"""Create elements table (partition-keyed, RLS)

Revision ID: 0011
Revises: 0010
Create Date: 2026-06-24 00:22:00.000000
"""
from __future__ import print_function

__author__ = "bibow"

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0011'
down_revision = '0010'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
    "aace_elements",
    sa.Column("partition_key", sa.String(128), primary_key=True),
        sa.Column("element_uuid", sa.String(), primary_key=True),
        sa.Column("endpoint_id", sa.String(64), nullable=True),
        sa.Column("part_id", sa.String(64), nullable=True),
        sa.Column("data_type", sa.String(), nullable=False),
        sa.Column("element_title", sa.String(), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=True, server_default='0'),
        sa.Column("attribute_name", sa.String(), nullable=False),
        sa.Column("attribute_type", sa.String(), nullable=False),
        sa.Column("option_values", postgresql.JSONB, nullable=True),
        sa.Column("conditions", postgresql.JSONB, nullable=True),
        sa.Column("pattern", sa.String(), nullable=True),
        sa.Column("updated_by", sa.String(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('NOW()')),
    )
    op.create_index("aace_idx_elements_partition_data_type", "aace_elements", ["partition_key", "data_type"])
    op.create_index("aace_idx_elements_partition_updated_at", "aace_elements", ["partition_key", "updated_at"])


def downgrade() -> None:
    op.drop_index("aace_idx_elements_partition_data_type", table_name="aace_elements")
    op.drop_index("aace_idx_elements_partition_updated_at", table_name="aace_elements")
    op.drop_table("aace_elements")
