"""configuracion de cuentas por cliente (saca los codigos quemados de la causacion)

Revision ID: 0005
Revises: 0004
Create Date: 2026-07-28

La causación traía "2205" y "240801" escritos en el código. Con el plan de
cuentas ya por cliente, eso significaba que dos de las tres líneas de todo
asiento seguían siendo globales. Esta tabla guarda qué cuenta usa cada cliente
para cada papel (proveedores, IVA descontable), y la causación las lee de ahí.

Los clientes existentes reciben los códigos que estaban quemados, de modo que
su comportamiento no cambia hasta que alguien los edite.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Los valores que estaban quemados en generate_causation_entries.py.
LEGACY_ROLE_CODES = [("accounts_payable", "2205"), ("vat_deductible", "240801")]


def upgrade() -> None:
    op.create_table(
        "client_account_settings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clients.id"), nullable=False),
        sa.Column("role", sa.String(50), nullable=False),
        sa.Column("account_code", sa.String(10), nullable=False),
        sa.UniqueConstraint("client_id", "role", name="uq_client_account_settings_client_role"),
    )
    op.create_index("ix_client_account_settings_tenant_id", "client_account_settings", ["tenant_id"])
    op.create_index("ix_client_account_settings_client_id", "client_account_settings", ["client_id"])

    # Sin esto, los clientes que ya existen dejarían de poder causar: la
    # causación exige configuración explícita y fallaría por falta de datos.
    for role, code in LEGACY_ROLE_CODES:
        op.execute(
            sa.text(
                """
                INSERT INTO client_account_settings (id, tenant_id, client_id, role, account_code)
                SELECT gen_random_uuid(), c.tenant_id, c.id, :role, :code
                FROM clients c
                """
            ).bindparams(role=role, code=code)
        )


def downgrade() -> None:
    op.drop_index("ix_client_account_settings_client_id", table_name="client_account_settings")
    op.drop_index("ix_client_account_settings_tenant_id", table_name="client_account_settings")
    op.drop_table("client_account_settings")
