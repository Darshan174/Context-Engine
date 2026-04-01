"""Add zoom to connector_type_enum.

Revision ID: 20260331_0005
Revises: 20260331_0004
Create Date: 2026-03-31 02:30:00.000000
"""
from __future__ import annotations

from alembic import op


revision = "20260331_0005"
down_revision = "20260331_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE connector_type_enum ADD VALUE IF NOT EXISTS 'zoom'")


def downgrade() -> None:
    op.execute("DELETE FROM source_documents WHERE connector_type = 'zoom'")
    op.execute("DELETE FROM connectors WHERE connector_type = 'zoom'")
    op.execute(
        "ALTER TABLE source_documents "
        "ALTER COLUMN connector_type TYPE text USING connector_type::text"
    )
    op.execute(
        "ALTER TABLE connectors "
        "ALTER COLUMN connector_type TYPE text USING connector_type::text"
    )
    op.execute("CREATE TYPE connector_type_enum_old AS ENUM ('slack', 'notion', 'gdrive', 'gong')")
    op.execute(
        "ALTER TABLE connectors "
        "ALTER COLUMN connector_type TYPE connector_type_enum_old "
        "USING connector_type::connector_type_enum_old"
    )
    op.execute(
        "ALTER TABLE source_documents "
        "ALTER COLUMN connector_type TYPE connector_type_enum_old "
        "USING connector_type::connector_type_enum_old"
    )
    op.execute("DROP TYPE connector_type_enum")
    op.execute("ALTER TYPE connector_type_enum_old RENAME TO connector_type_enum")
