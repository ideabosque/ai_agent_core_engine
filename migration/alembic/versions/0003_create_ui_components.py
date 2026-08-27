# -*- coding: utf-8 -*-
"""Create ui_components table (global registry, no RLS)

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-24 00:06:00.000000
"""
from __future__ import print_function

__author__ = "bibow"

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
    "aace_ui_components",
    sa.Column("ui_component_type", sa.String(), primary_key=True),
        sa.Column("ui_component_uuid", sa.String(), primary_key=True),
        sa.Column("tag_name", sa.String(), nullable=False),
        sa.Column("tag_alias", sa.String(), nullable=True),
        sa.Column("parameters", postgresql.JSONB, nullable=True),
        sa.Column("wait_for", sa.String(), nullable=True),
        sa.Column("updated_by", sa.String(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('NOW()')),
    )
    op.create_index("aace_idx_ui_components_type_updated_at", "aace_ui_components", ["ui_component_type", "updated_at"])


def downgrade() -> None:
    op.drop_index("aace_idx_ui_components_type_updated_at", table_name="aace_ui_components")
    op.drop_table("aace_ui_components")
