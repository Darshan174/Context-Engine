"""Add review_items and job_type support for trust/operator APIs.

Revision ID: 20260331_0004
Revises: 20260331_0003
Create Date: 2026-03-31 00:30:00.000000
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "20260331_0004"
down_revision = "20260331_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "components",
        sa.Column(
            "valid_from",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )
    op.add_column(
        "components",
        sa.Column("valid_to", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "components",
        sa.Column("superseded_by_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        op.f("fk_components_superseded_by_id_components"),
        "components",
        "components",
        ["superseded_by_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        op.f("ix_components_superseded_by_id"),
        "components",
        ["superseded_by_id"],
    )
    op.add_column(
        "relationships",
        sa.Column(
            "valid_from",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )
    op.add_column(
        "relationships",
        sa.Column("valid_to", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "relationships",
        sa.Column("superseded_by_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        op.f("fk_relationships_superseded_by_id_relationships"),
        "relationships",
        "relationships",
        ["superseded_by_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        op.f("ix_relationships_superseded_by_id"),
        "relationships",
        ["superseded_by_id"],
    )

    op.add_column(
        "sync_jobs",
        sa.Column(
            "job_type",
            sa.String(length=50),
            nullable=False,
            server_default="sync",
        ),
    )

    op.create_table(
        "review_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("component_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="needs_review"),
        sa.Column("severity", sa.String(length=50), nullable=False, server_default="medium"),
        sa.Column("kind", sa.String(length=50), nullable=False, server_default="review_item"),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column("suggested_action", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)",
            name=op.f("ck_review_items_review_items_confidence_range"),
        ),
        sa.ForeignKeyConstraint(
            ["component_id"],
            ["components.id"],
            name=op.f("fk_review_items_component_id_components"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_review_items")),
        sa.UniqueConstraint("component_id", name=op.f("uq_review_items_component_id")),
    )
    op.create_index(op.f("ix_review_items_component_id"), "review_items", ["component_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_review_items_component_id"), table_name="review_items")
    op.drop_table("review_items")
    op.drop_column("sync_jobs", "job_type")
    op.drop_index(op.f("ix_relationships_superseded_by_id"), table_name="relationships")
    op.drop_constraint(
        op.f("fk_relationships_superseded_by_id_relationships"),
        "relationships",
        type_="foreignkey",
    )
    op.drop_column("relationships", "superseded_by_id")
    op.drop_column("relationships", "valid_to")
    op.drop_column("relationships", "valid_from")
    op.drop_index(op.f("ix_components_superseded_by_id"), table_name="components")
    op.drop_constraint(
        op.f("fk_components_superseded_by_id_components"),
        "components",
        type_="foreignkey",
    )
    op.drop_column("components", "superseded_by_id")
    op.drop_column("components", "valid_to")
    op.drop_column("components", "valid_from")
