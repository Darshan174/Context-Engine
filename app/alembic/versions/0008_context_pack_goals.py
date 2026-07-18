from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "0008_context_pack_goals"
down_revision = "0007_workspace_lifecycle"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    columns = {column["name"] for column in sa.inspect(bind).get_columns("context_packs")}
    if "workspace_goal_id" not in columns:
        op.add_column(
            "context_packs",
            sa.Column(
                "workspace_goal_id",
                sa.Uuid(),
                sa.ForeignKey("workspace_goals.id"),
                nullable=True,
            ),
        )
    if "ix_context_packs_workspace_goal" not in {
        item["name"] for item in sa.inspect(bind).get_indexes("context_packs")
    }:
        op.create_index(
            "ix_context_packs_workspace_goal",
            "context_packs",
            ["workspace_goal_id"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    if "ix_context_packs_workspace_goal" in {
        item["name"] for item in sa.inspect(bind).get_indexes("context_packs")
    }:
        op.drop_index("ix_context_packs_workspace_goal", table_name="context_packs")
    if "workspace_goal_id" in {
        column["name"] for column in sa.inspect(bind).get_columns("context_packs")
    }:
        with op.batch_alter_table("context_packs") as batch:
            batch.drop_column("workspace_goal_id")
