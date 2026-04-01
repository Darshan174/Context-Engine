"""Add content_hash and extracted_value to component_sources.

Revision ID: 20260331_0006
Revises: 20260331_0005
Create Date: 2026-04-01 00:00:00.000000
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260331_0006"
down_revision = "20260331_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "component_sources",
        sa.Column("content_hash", sa.String(64), nullable=True),
    )
    op.create_index(
        op.f("ix_component_sources_content_hash"),
        "component_sources",
        ["content_hash"],
    )
    op.add_column(
        "component_sources",
        sa.Column("extracted_value", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("component_sources", "extracted_value")
    op.drop_index(
        op.f("ix_component_sources_content_hash"),
        table_name="component_sources",
    )
    op.drop_column("component_sources", "content_hash")
