# -*- coding: utf-8 -*-
"""Create wizard_groups table (partition-keyed, RLS)

Revision ID: 0013
Revises: 0012
Create Date: 2026-06-24 00:26:00.000000
"""
from __future__ import print_function

__author__ = "bibow"

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0013'
down_revision = '0012'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
    "aace_wizard_groups",
    sa.Column("partition_key", sa.String(128), primary_key=True),
        sa.Column("wizard_group_uuid", sa.String(), primary_key=True),
        sa.Column("endpoint_id", sa.String(64), nullable=True),
        sa.Column("part_id", sa.String(64), nullable=True),
        sa.Column("wizard_group_name", sa.String(), nullable=False),
        sa.Column("wizard_group_description", sa.Text(), nullable=True),
        sa.Column("weight", sa.Integer(), nullable=True, server_default='0'),
        sa.Column("wizard_uuids", postgresql.JSONB, nullable=True),
        sa.Column("updated_by", sa.String(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('NOW()')),
    )
    op.create_index("aace_idx_wizard_groups_partition_updated_at", "aace_wizard_groups", ["partition_key", "updated_at"])


def downgrade() -> None:
    op.drop_index("aace_idx_wizard_groups_partition_updated_at", table_name="aace_wizard_groups")
    op.drop_table("aace_wizard_groups")
