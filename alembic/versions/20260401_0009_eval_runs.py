"""Add persisted eval runs and per-case results.

Revision ID: 20260401_0009
Revises: 20260401_0008
Create Date: 2026-04-01 23:20:00.000000
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "20260401_0009"
down_revision = "20260401_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "eval_runs",
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "total",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "passed_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "failed_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "pass_rate",
            sa.Float(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "pass_threshold",
            sa.Float(),
            nullable=False,
            server_default=sa.text("0.5"),
        ),
        sa.Column(
            "average_retrieval_hit_quality",
            sa.Float(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "average_extracted_fact_correctness",
            sa.Float(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "average_final_answer_correctness",
            sa.Float(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "confidence_calibration_error",
            sa.Float(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "trigger_source",
            sa.String(length=50),
            nullable=False,
            server_default=sa.text("'manual'"),
        ),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name=op.f("fk_eval_runs_workspace_id_workspaces"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_eval_runs")),
    )
    op.create_index(
        op.f("ix_eval_runs_workspace_id"),
        "eval_runs",
        ["workspace_id"],
        unique=False,
    )

    op.create_table(
        "eval_case_results",
        sa.Column("eval_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("case_id", sa.String(length=255), nullable=False),
        sa.Column("domain", sa.String(length=100), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("predicted_confidence", sa.Float(), nullable=False),
        sa.Column("retrieval_hit_quality", sa.Float(), nullable=False),
        sa.Column("extracted_fact_correctness", sa.Float(), nullable=False),
        sa.Column("final_answer_correctness", sa.Float(), nullable=False),
        sa.Column(
            "passed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "detail",
            sa.Text(),
            nullable=False,
            server_default=sa.text("''"),
        ),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["eval_run_id"],
            ["eval_runs.id"],
            name=op.f("fk_eval_case_results_eval_run_id_eval_runs"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_eval_case_results")),
    )
    op.create_index(
        op.f("ix_eval_case_results_eval_run_id"),
        "eval_case_results",
        ["eval_run_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_eval_case_results_case_id"),
        "eval_case_results",
        ["case_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_eval_case_results_domain"),
        "eval_case_results",
        ["domain"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_eval_case_results_domain"),
        table_name="eval_case_results",
    )
    op.drop_index(
        op.f("ix_eval_case_results_case_id"),
        table_name="eval_case_results",
    )
    op.drop_index(
        op.f("ix_eval_case_results_eval_run_id"),
        table_name="eval_case_results",
    )
    op.drop_table("eval_case_results")
    op.drop_index(op.f("ix_eval_runs_workspace_id"), table_name="eval_runs")
    op.drop_table("eval_runs")
