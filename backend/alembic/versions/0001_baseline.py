"""baseline: reflect schema as it exists today (tenants, users, clients, reports, report_files)

Revision ID: 0001
Revises:
Create Date: 2026-07-01

This migration exists to give the project real migration history instead of
pretending the schema started empty. It mirrors exactly what
`Base.metadata.create_all` already produces in dev/test today
(`src/infrastructure/database/models.py` as of this feature's start). An
environment that was only ever bootstrapped via `create_all` should run
`alembic stamp head` after this revision lands, not `alembic upgrade head`
from scratch (the tables already exist there).
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tenants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("slug", sa.String(200), nullable=False),
        sa.Column("owner_email", sa.String(254), nullable=False),
        sa.Column("plan", sa.String(50), server_default="free"),
        sa.Column("status", sa.String(50), server_default="active"),
        sa.Column("max_clients", sa.Integer(), server_default="5"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_tenants_slug", "tenants", ["slug"], unique=True)

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(254), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("hashed_password", sa.String(200), nullable=False),
        sa.Column("role", sa.String(50), nullable=False),
        sa.Column("status", sa.String(50), server_default="pending"),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "clients",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("nit", sa.String(20), nullable=False),
        sa.Column("contact_email", sa.String(254), nullable=False),
        sa.Column("contact_name", sa.String(200), server_default=""),
        sa.Column("contact_phone", sa.String(20), server_default=""),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_clients_tenant_id", "clients", ["tenant_id"])

    op.create_table(
        "reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clients.id"), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("report_type", sa.String(50), nullable=False),
        sa.Column("period", sa.String(20), nullable=False),
        sa.Column("status", sa.String(50), server_default="pending"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_reports_tenant_id", "reports", ["tenant_id"])
    op.create_index("ix_reports_client_id", "reports", ["client_id"])

    op.create_table(
        "report_files",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("report_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("reports.id"), nullable=False),
        sa.Column("file_type", sa.String(50), nullable=False),
        sa.Column("storage_key", sa.String(500), nullable=False),
        sa.Column("original_name", sa.String(255), nullable=False),
        sa.Column("role", sa.String(20), server_default="source"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_report_files_report_id", "report_files", ["report_id"])


def downgrade() -> None:
    op.drop_table("report_files")
    op.drop_table("reports")
    op.drop_table("clients")
    op.drop_table("users")
    op.drop_table("tenants")
