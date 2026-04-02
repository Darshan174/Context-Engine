"""Add github to connector_type_enum.

Revision ID: 20260401_0010
Revises: 20260401_0009
Create Date: 2026-04-01 23:59:00.000000
"""
from __future__ import annotations

from alembic import op


revision = "20260401_0010"
down_revision = "20260401_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE connector_type_enum ADD VALUE IF NOT EXISTS 'github'")


def downgrade() -> None:
    op.execute(
        "CREATE TYPE connector_type_enum_old AS ENUM "
        "('slack', 'notion', 'zoom', 'gdrive', 'gong')"
    )
    op.execute(
        "ALTER TABLE connectors "
        "ALTER COLUMN connector_type TYPE connector_type_enum_old "
        "USING connector_type::text::connector_type_enum_old"
    )
    op.execute(
        "ALTER TABLE source_documents "
        "ALTER COLUMN connector_type TYPE connector_type_enum_old "
        "USING connector_type::text::connector_type_enum_old"
    )
    op.execute("DROP TYPE connector_type_enum")
    op.execute("ALTER TYPE connector_type_enum_old RENAME TO connector_type_enum")
