"""Initial schema for context engine foundation.

Revision ID: 20260328_0001
Revises:
Create Date: 2026-03-28 00:00:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "20260328_0001"
down_revision = None
branch_labels = None
depends_on = None


connector_type_enum = postgresql.ENUM(
    "slack",
    "notion",
    "gdrive",
    "gong",
    name="connector_type_enum",
)
connector_status_enum = postgresql.ENUM(
    "connected",
    "disconnected",
    "error",
    name="connector_status_enum",
)
knowledge_model_status_enum = postgresql.ENUM(
    "active",
    "archived",
    name="knowledge_model_status_enum",
)
relationship_type_enum = postgresql.ENUM(
    "depends_on",
    "blocked_by",
    "enables",
    "contradicts",
    "supersedes",
    "related_to",
    name="relationship_type_enum",
)
relationship_sentiment_enum = postgresql.ENUM(
    "positive",
    "negative",
    "neutral",
    name="relationship_sentiment_enum",
)


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    bind = op.get_bind()
    connector_type_enum.create(bind, checkfirst=True)
    connector_status_enum.create(bind, checkfirst=True)
    knowledge_model_status_enum.create(bind, checkfirst=True)
    relationship_type_enum.create(bind, checkfirst=True)
    relationship_sentiment_enum.create(bind, checkfirst=True)

    op.create_table(
        "workspaces",
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_workspaces")),
    )
    op.create_table(
        "source_documents",
        sa.Column("connector_type", connector_type_enum, nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("author", sa.String(length=255), nullable=True),
        sa.Column("source_url", sa.String(length=2048), nullable=True),
        sa.Column("created_at_source", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ingested_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_source_documents")),
        sa.UniqueConstraint("connector_type", "external_id", name=op.f("uq_source_documents_connector_type")),
    )
    op.create_index(op.f("ix_source_documents_connector_type"), "source_documents", ["connector_type"], unique=False)
    op.create_table(
        "users",
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], name=op.f("fk_users_workspace_id_workspaces"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("workspace_id", "email", name=op.f("uq_users_workspace_id")),
    )
    op.create_index(op.f("ix_users_workspace_id"), "users", ["workspace_id"], unique=False)
    op.create_table(
        "connectors",
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("connector_type", connector_type_enum, nullable=False),
        sa.Column("status", connector_status_enum, server_default=sa.text("'disconnected'"), nullable=False),
        sa.Column("oauth_token_encrypted", sa.Text(), nullable=True),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], name=op.f("fk_connectors_workspace_id_workspaces"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_connectors")),
        sa.UniqueConstraint("workspace_id", "connector_type", name=op.f("uq_connectors_workspace_id")),
    )
    op.create_index(op.f("ix_connectors_workspace_id"), "connectors", ["workspace_id"], unique=False)
    op.create_table(
        "knowledge_models",
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", knowledge_model_status_enum, server_default=sa.text("'active'"), nullable=False),
        sa.Column("auto_generated", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name=op.f("fk_knowledge_models_workspace_id_workspaces"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_knowledge_models")),
        sa.UniqueConstraint("workspace_id", "name", name=op.f("uq_knowledge_models_workspace_id")),
    )
    op.create_index(op.f("ix_knowledge_models_workspace_id"), "knowledge_models", ["workspace_id"], unique=False)
    op.create_table(
        "sync_states",
        sa.Column("connector_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cursor", sa.Text(), nullable=True),
        sa.Column("last_synced_item_id", sa.String(length=255), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["connector_id"], ["connectors.id"], name=op.f("fk_sync_states_connector_id_connectors"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sync_states")),
        sa.UniqueConstraint("connector_id", name=op.f("uq_sync_states_connector_id")),
    )
    op.create_table(
        "components",
        sa.Column("model_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("authority_source", sa.String(length=255), nullable=True),
        sa.Column("last_verified_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("is_stale", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("embedding", Vector(dim=1024), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("confidence >= 0 AND confidence <= 1", name=op.f("ck_components_components_confidence_range")),
        sa.ForeignKeyConstraint(["model_id"], ["knowledge_models.id"], name=op.f("fk_components_model_id_knowledge_models"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_components")),
    )
    op.create_index(op.f("ix_components_model_id"), "components", ["model_id"], unique=False)
    op.create_table(
        "relationships",
        sa.Column("source_component_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_component_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("relationship_type", relationship_type_enum, nullable=False),
        sa.Column("sentiment", relationship_sentiment_enum, server_default=sa.text("'neutral'"), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.CheckConstraint("confidence >= 0 AND confidence <= 1", name=op.f("ck_relationships_relationships_confidence_range")),
        sa.CheckConstraint("source_component_id <> target_component_id", name=op.f("ck_relationships_relationships_distinct_components")),
        sa.ForeignKeyConstraint(
            ["source_component_id"],
            ["components.id"],
            name=op.f("fk_relationships_source_component_id_components"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["target_component_id"],
            ["components.id"],
            name=op.f("fk_relationships_target_component_id_components"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_relationships")),
    )
    op.create_index(op.f("ix_relationships_source_component_id"), "relationships", ["source_component_id"], unique=False)
    op.create_index(op.f("ix_relationships_target_component_id"), "relationships", ["target_component_id"], unique=False)
    op.create_table(
        "component_sources",
        sa.Column("component_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("extraction_context", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["component_id"], ["components.id"], name=op.f("fk_component_sources_component_id_components"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["source_document_id"],
            ["source_documents.id"],
            name=op.f("fk_component_sources_source_document_id_source_documents"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("component_id", "source_document_id", name=op.f("pk_component_sources")),
    )


def downgrade() -> None:
    op.drop_table("component_sources")
    op.drop_index(op.f("ix_relationships_target_component_id"), table_name="relationships")
    op.drop_index(op.f("ix_relationships_source_component_id"), table_name="relationships")
    op.drop_table("relationships")
    op.drop_index(op.f("ix_components_model_id"), table_name="components")
    op.drop_table("components")
    op.drop_table("sync_states")
    op.drop_index(op.f("ix_knowledge_models_workspace_id"), table_name="knowledge_models")
    op.drop_table("knowledge_models")
    op.drop_index(op.f("ix_connectors_workspace_id"), table_name="connectors")
    op.drop_table("connectors")
    op.drop_index(op.f("ix_users_workspace_id"), table_name="users")
    op.drop_table("users")
    op.drop_index(op.f("ix_source_documents_connector_type"), table_name="source_documents")
    op.drop_table("source_documents")
    op.drop_table("workspaces")

    bind = op.get_bind()
    relationship_sentiment_enum.drop(bind, checkfirst=True)
    relationship_type_enum.drop(bind, checkfirst=True)
    knowledge_model_status_enum.drop(bind, checkfirst=True)
    connector_status_enum.drop(bind, checkfirst=True)
    connector_type_enum.drop(bind, checkfirst=True)
