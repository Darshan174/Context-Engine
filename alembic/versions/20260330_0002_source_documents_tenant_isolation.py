"""Add connector_id FK and processed_at to source_documents.

Scopes source documents to a specific connector (and therefore
workspace), fixing multi-tenant data isolation.  Also adds the
processed_at column used by the ingestion pipeline.

Revision ID: 20260330_0002
Revises: 20260328_0001
Create Date: 2026-03-30 00:00:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "20260330_0002"
down_revision = "20260328_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # -- Add processed_at (nullable, no backfill needed) --
    op.add_column(
        "source_documents",
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
    )

    # -- Add connector_id column (nullable initially for backfill) --
    op.add_column(
        "source_documents",
        sa.Column(
            "connector_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )

    # -- Backfill: match existing rows to their connector ONLY when the
    # connector_type maps to exactly one connector.  If multiple connectors
    # share the same type (e.g. two Slack connectors in different workspaces)
    # we cannot determine which connector owns which documents, so those
    # rows are left NULL and deleted below to avoid cross-tenant leaks. --
    op.execute(
        """
        UPDATE source_documents sd
        SET connector_id = c.id
        FROM connectors c
        WHERE c.connector_type = sd.connector_type
          AND sd.connector_id IS NULL
          AND (
              SELECT count(*) FROM connectors c2
              WHERE c2.connector_type = sd.connector_type
          ) = 1
        """
    )

    # -- Remove rows that couldn't be unambiguously matched --
    op.execute(
        "DELETE FROM source_documents WHERE connector_id IS NULL"
    )

    # -- Now make connector_id NOT NULL --
    op.alter_column(
        "source_documents",
        "connector_id",
        nullable=False,
    )

    # -- Add FK constraint --
    op.create_foreign_key(
        op.f("fk_source_documents_connector_id_connectors"),
        "source_documents",
        "connectors",
        ["connector_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # -- Drop old unique constraint and index --
    op.drop_constraint(
        op.f("uq_source_documents_connector_type"),
        "source_documents",
        type_="unique",
    )

    # -- Create new unique constraint scoped to connector --
    op.create_unique_constraint(
        op.f("uq_source_documents_connector_id"),
        "source_documents",
        ["connector_id", "external_id"],
    )

    # -- Index on connector_id for fast lookups --
    op.create_index(
        op.f("ix_source_documents_connector_id"),
        "source_documents",
        ["connector_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_source_documents_connector_id"),
        table_name="source_documents",
    )
    op.drop_constraint(
        op.f("uq_source_documents_connector_id"),
        "source_documents",
        type_="unique",
    )
    op.create_unique_constraint(
        op.f("uq_source_documents_connector_type"),
        "source_documents",
        ["connector_type", "external_id"],
    )
    op.drop_constraint(
        op.f("fk_source_documents_connector_id_connectors"),
        "source_documents",
        type_="foreignkey",
    )
    op.drop_column("source_documents", "connector_id")
    op.drop_column("source_documents", "processed_at")
