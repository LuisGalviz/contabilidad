"""add is_credit_note to supplier_invoices

Revision ID: fb3058618fff
Revises: 54e590e6494f
Create Date: 2026-07-06 19:30:19.204221

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fb3058618fff'
down_revision: Union[str, None] = '54e590e6494f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Idempotente a propósito: una base bootstrapeada con `create_all()` (que
    # construye las tablas desde los modelos actuales) ya trae la columna, y un
    # `ADD COLUMN` normal fallaría al alcanzarla desde una revisión stampeada.
    op.execute(
        "ALTER TABLE supplier_invoices "
        "ADD COLUMN IF NOT EXISTS is_credit_note BOOLEAN NOT NULL DEFAULT false"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE supplier_invoices DROP COLUMN IF EXISTS is_credit_note")
