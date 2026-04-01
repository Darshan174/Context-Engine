"""Add auth refresh, authority weight, and extractor provenance fields.

Revision ID: 20260401_0007
Revises: 20260331_0006
Create Date: 2026-04-01 18:00:00.000000
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260401_0007"
down_revision = "20260331_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "connectors",
        sa.Column("refresh_token_encrypted", sa.Text(), nullable=True),
    )

    op.add_column(
        "components",
        sa.Column(
            "authority_weight",
            sa.Float(),
            nullable=False,
            server_default=sa.text("0.5"),
        ),
    )
    op.create_check_constraint(
        op.f("ck_components_components_authority_weight_range"),
        "components",
        "authority_weight >= 0 AND authority_weight <= 1",
    )

    op.add_column(
        "component_sources",
        sa.Column("extractor_name", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "component_sources",
        sa.Column("extractor_kind", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "component_sources",
        sa.Column("extractor_schema_version", sa.String(length=50), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("component_sources", "extractor_schema_version")
    op.drop_column("component_sources", "extractor_kind")
    op.drop_column("component_sources", "extractor_name")
    op.drop_constraint(
        op.f("ck_components_components_authority_weight_range"),
        "components",
        type_="check",
    )
    op.drop_column("components", "authority_weight")
    op.drop_column("connectors", "refresh_token_encrypted")
