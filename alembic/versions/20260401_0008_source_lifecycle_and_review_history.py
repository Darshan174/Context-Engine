"""Add source lifecycle soft-delete and review decision history.

Revision ID: 20260401_0008
Revises: 20260401_0007
Create Date: 2026-04-01 22:00:00.000000
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "20260401_0008"
down_revision = "20260401_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "source_documents",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        op.f("ix_source_documents_deleted_at"),
        "source_documents",
        ["deleted_at"],
        unique=False,
    )

    op.create_table(
        "review_decisions",
        sa.Column("review_item_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("previous_status", sa.String(length=50), nullable=True),
        sa.Column("new_status", sa.String(length=50), nullable=False),
        sa.Column(
            "actor_type",
            sa.String(length=50),
            nullable=False,
            server_default=sa.text("'operator'"),
        ),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["review_item_id"],
            ["review_items.id"],
            name=op.f("fk_review_decisions_review_item_id_review_items"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_review_decisions")),
    )
    op.create_index(
        op.f("ix_review_decisions_review_item_id"),
        "review_decisions",
        ["review_item_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_review_decisions_review_item_id"),
        table_name="review_decisions",
    )
    op.drop_table("review_decisions")
    op.drop_index(
        op.f("ix_source_documents_deleted_at"),
        table_name="source_documents",
    )
    op.drop_column("source_documents", "deleted_at")
