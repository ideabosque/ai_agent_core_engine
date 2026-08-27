# -*- coding: utf-8 -*-
"""Create wizard_schemas table (global registry, no RLS)

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-24 00:04:00.000000
"""
from __future__ import print_function

__author__ = "bibow"

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
    "aace_wizard_schemas",
    sa.Column("wizard_schema_type", sa.String(), primary_key=True),
        sa.Column("wizard_schema_name", sa.String(), primary_key=True),
        sa.Column("wizard_schema_description", sa.Text(), nullable=True),
        sa.Column("attributes", postgresql.JSONB, nullable=True),
        sa.Column("attribute_groups", postgresql.JSONB, nullable=True),
        sa.Column("updated_by", sa.String(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('NOW()')),
    )
    op.create_index("aace_idx_wizard_schemas_type_updated_at", "aace_wizard_schemas", ["wizard_schema_type", "updated_at"])


def downgrade() -> None:
    op.drop_index("aace_idx_wizard_schemas_type_updated_at", table_name="aace_wizard_schemas")
    op.drop_table("aace_wizard_schemas")
