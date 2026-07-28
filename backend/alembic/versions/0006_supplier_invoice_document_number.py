"""prefijo y numero de la factura del proveedor

Revision ID: 0006
Revises: 0005
Create Date: 2026-07-28

Siigo exige `provider_invoice` (prefijo + número) al registrar una factura de
compra por `POST /v1/purchases`. El CUFE no sirve para eso: identifica el
documento electrónico ante la DIAN, no es el consecutivo del proveedor.

Quedan vacíos en las facturas ya importadas: el dato solo aparece al releer el
archivo de la DIAN, y no todos los archivos traen esas columnas.
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE supplier_invoices ADD COLUMN IF NOT EXISTS document_prefix VARCHAR(50) NOT NULL DEFAULT ''"
    )
    op.execute(
        "ALTER TABLE supplier_invoices ADD COLUMN IF NOT EXISTS document_number VARCHAR(50) NOT NULL DEFAULT ''"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE supplier_invoices DROP COLUMN IF EXISTS document_number")
    op.execute("ALTER TABLE supplier_invoices DROP COLUMN IF EXISTS document_prefix")
