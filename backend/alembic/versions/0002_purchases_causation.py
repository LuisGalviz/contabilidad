"""purchases causación: DIAN invoice ingestion, mapping rules, causación entries, sector reports

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-01

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("clients", sa.Column("economic_activity", sa.String(50), server_default="", nullable=False))
    op.add_column("clients", sa.Column("ciiu_code", sa.String(10), server_default="", nullable=False))

    op.create_table(
        "puc_accounts",
        sa.Column("code", sa.String(10), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("account_class", sa.String(20), nullable=False),
        sa.Column("parent_code", sa.String(10), nullable=True),
        sa.Column("requires_cost_center", sa.Boolean(), server_default=sa.false()),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true()),
    )

    op.create_table(
        "cost_centers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clients.id"), nullable=False),
        sa.Column("code", sa.String(20), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_cost_centers_tenant_id", "cost_centers", ["tenant_id"])
    op.create_index("ix_cost_centers_client_id", "cost_centers", ["client_id"])

    op.create_table(
        "invoice_import_batches",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clients.id"), nullable=False),
        sa.Column("uploaded_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("source_file_key", sa.String(500), nullable=False),
        sa.Column("original_name", sa.String(255), nullable=False),
        sa.Column("status", sa.String(50), server_default="pending"),
        sa.Column("total_rows", sa.Integer(), server_default="0"),
        sa.Column("new_invoices", sa.Integer(), server_default="0"),
        sa.Column("duplicate_invoices", sa.Integer(), server_default="0"),
        sa.Column("error_rows", sa.Integer(), server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_invoice_import_batches_tenant_id", "invoice_import_batches", ["tenant_id"])
    op.create_index("ix_invoice_import_batches_client_id", "invoice_import_batches", ["client_id"])

    op.create_table(
        "supplier_invoices",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clients.id"), nullable=False),
        sa.Column(
            "import_batch_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("invoice_import_batches.id"),
            nullable=False,
        ),
        sa.Column("cufe", sa.String(100), nullable=False),
        sa.Column("supplier_nit", sa.String(20), nullable=False),
        sa.Column("supplier_name", sa.String(200), nullable=False),
        sa.Column("issue_date", sa.Date(), nullable=False),
        sa.Column("concept_description", sa.Text(), server_default=""),
        sa.Column("subtotal", sa.Numeric(18, 2), nullable=False),
        sa.Column("vat_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("total_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("status", sa.String(30), server_default="pending_review"),
        sa.Column("suggested_account_code", sa.String(10), nullable=True),
        sa.Column("suggested_cost_center_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("suggested_confidence", sa.Float(), server_default="0"),
        sa.Column("classification_source", sa.String(30), nullable=True),
        sa.Column("final_account_code", sa.String(10), nullable=True),
        sa.Column("final_cost_center_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("classified_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("classified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("raw_row", postgresql.JSONB(), server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tenant_id", "client_id", "cufe", name="uq_supplier_invoice_cufe"),
    )
    op.create_index("ix_supplier_invoices_tenant_id", "supplier_invoices", ["tenant_id"])
    op.create_index("ix_supplier_invoices_client_id", "supplier_invoices", ["client_id"])
    op.create_index("ix_supplier_invoices_import_batch_id", "supplier_invoices", ["import_batch_id"])
    op.create_index("ix_supplier_invoices_supplier_nit", "supplier_invoices", ["supplier_nit"])

    op.create_table(
        "supplier_mapping_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clients.id"), nullable=False),
        sa.Column("supplier_nit", sa.String(20), nullable=False),
        sa.Column("concept_keywords", postgresql.JSONB(), server_default="[]"),
        sa.Column("account_code", sa.String(10), nullable=False),
        sa.Column("cost_center_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("confidence", sa.Float(), server_default="0.5"),
        sa.Column("times_confirmed", sa.Integer(), server_default="0"),
        sa.Column("times_corrected", sa.Integer(), server_default="0"),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_supplier_mapping_rules_tenant_client_nit",
        "supplier_mapping_rules",
        ["tenant_id", "client_id", "supplier_nit"],
    )

    op.create_table(
        "classification_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "invoice_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("supplier_invoices.id"), nullable=False
        ),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("action", sa.String(30), nullable=False),
        sa.Column("account_code_before", sa.String(10), nullable=True),
        sa.Column("account_code_after", sa.String(10), nullable=True),
        sa.Column(
            "rule_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("supplier_mapping_rules.id"), nullable=True
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_classification_history_invoice_id", "classification_history", ["invoice_id"])
    op.create_index("ix_classification_history_tenant_id", "classification_history", ["tenant_id"])

    op.create_table(
        "causation_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clients.id"), nullable=False),
        sa.Column(
            "invoice_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("supplier_invoices.id"), nullable=False
        ),
        sa.Column("entry_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(30), server_default="draft"),
        sa.Column("external_reference", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_causation_entries_tenant_id", "causation_entries", ["tenant_id"])
    op.create_index("ix_causation_entries_client_id", "causation_entries", ["client_id"])
    op.create_index("ix_causation_entries_invoice_id", "causation_entries", ["invoice_id"])

    op.create_table(
        "causation_entry_lines",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "entry_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("causation_entries.id"), nullable=False
        ),
        sa.Column("account_code", sa.String(10), nullable=False),
        sa.Column("debit", sa.Numeric(18, 2), server_default="0"),
        sa.Column("credit", sa.Numeric(18, 2), server_default="0"),
        sa.Column("description", sa.String(255), server_default=""),
        sa.Column("cost_center_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index("ix_causation_entry_lines_entry_id", "causation_entry_lines", ["entry_id"])


def downgrade() -> None:
    op.drop_table("causation_entry_lines")
    op.drop_table("causation_entries")
    op.drop_table("classification_history")
    op.drop_table("supplier_mapping_rules")
    op.drop_table("supplier_invoices")
    op.drop_table("invoice_import_batches")
    op.drop_table("cost_centers")
    op.drop_table("puc_accounts")
    op.drop_column("clients", "ciiu_code")
    op.drop_column("clients", "economic_activity")
