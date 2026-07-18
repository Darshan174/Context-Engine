from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "0009_workspace_goal_contract"
down_revision = "0008_context_pack_goals"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    columns = {
        column["name"]
        for column in sa.inspect(bind).get_columns("workspace_goals")
    }
    if "contract_json" not in columns:
        op.add_column(
            "workspace_goals",
            sa.Column(
                "contract_json",
                sa.Text(),
                nullable=False,
                server_default=sa.text("'{}'"),
            ),
        )


def downgrade() -> None:
    bind = op.get_bind()
    columns = {
        column["name"]
        for column in sa.inspect(bind).get_columns("workspace_goals")
    }
    if "contract_json" in columns:
        with op.batch_alter_table("workspace_goals") as batch:
            batch.drop_column("contract_json")
