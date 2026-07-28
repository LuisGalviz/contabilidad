"""puc_accounts pasa a ser por cliente en vez de global

Revision ID: 0004
Revises: fb3058618fff
Create Date: 2026-07-28

`puc_accounts` tenía `code` como llave primaria, es decir un único plan de
cuentas compartido por todos los clientes. Cada empresa lleva el suyo (y en
Siigo cada compañía tiene su propio catálogo), así que dos clientes con planes
distintos chocaban en la llave primaria.

La tabla pasa a tener id propio y `(client_id, code)` único. Las cuentas que
existían se replican tal cual a cada cliente, conservando cualquier ajuste
manual que se les hubiera hecho.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004"
down_revision: Union[str, None] = "fb3058618fff"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("puc_accounts", sa.Column("id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("puc_accounts", sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("puc_accounts", sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=True))

    # Debe caer antes de insertar: mientras `code` sea la llave primaria, la
    # réplica por cliente viola unicidad.
    op.drop_constraint("puc_accounts_pkey", "puc_accounts", type_="primary")

    op.execute(
        """
        INSERT INTO puc_accounts (
            id, tenant_id, client_id, code, name, account_class,
            parent_code, requires_cost_center, is_active
        )
        SELECT gen_random_uuid(), c.tenant_id, c.id, p.code, p.name, p.account_class,
               p.parent_code, COALESCE(p.requires_cost_center, false), COALESCE(p.is_active, true)
        FROM puc_accounts p
        CROSS JOIN clients c
        WHERE p.client_id IS NULL
        """
    )
    # Las filas globales originales ya no aplican a nadie. Si no había clientes
    # la tabla queda vacía, que es lo correcto: cada cliente nuevo se siembra
    # al crearse (`CreateClientUseCase`).
    op.execute("DELETE FROM puc_accounts WHERE client_id IS NULL")

    op.alter_column("puc_accounts", "id", existing_type=postgresql.UUID(as_uuid=True), nullable=False)
    op.alter_column("puc_accounts", "tenant_id", existing_type=postgresql.UUID(as_uuid=True), nullable=False)
    op.alter_column("puc_accounts", "client_id", existing_type=postgresql.UUID(as_uuid=True), nullable=False)

    op.create_primary_key("puc_accounts_pkey", "puc_accounts", ["id"])
    op.create_unique_constraint("uq_puc_accounts_client_code", "puc_accounts", ["client_id", "code"])
    op.create_foreign_key("fk_puc_accounts_tenant", "puc_accounts", "tenants", ["tenant_id"], ["id"])
    op.create_foreign_key("fk_puc_accounts_client", "puc_accounts", "clients", ["client_id"], ["id"])
    op.create_index("ix_puc_accounts_tenant_id", "puc_accounts", ["tenant_id"])
    op.create_index("ix_puc_accounts_client_id", "puc_accounts", ["client_id"])


def downgrade() -> None:
    op.drop_index("ix_puc_accounts_client_id", table_name="puc_accounts")
    op.drop_index("ix_puc_accounts_tenant_id", table_name="puc_accounts")
    op.drop_constraint("fk_puc_accounts_client", "puc_accounts", type_="foreignkey")
    op.drop_constraint("fk_puc_accounts_tenant", "puc_accounts", type_="foreignkey")
    op.drop_constraint("uq_puc_accounts_client_code", "puc_accounts", type_="unique")
    op.drop_constraint("puc_accounts_pkey", "puc_accounts", type_="primary")

    # Volver a un plan único obliga a colapsar los de cada cliente: se conserva
    # una fila por código y se pierden las divergencias entre clientes.
    op.execute("DELETE FROM puc_accounts a USING puc_accounts b WHERE a.code = b.code AND a.ctid > b.ctid")

    op.drop_column("puc_accounts", "client_id")
    op.drop_column("puc_accounts", "tenant_id")
    op.drop_column("puc_accounts", "id")

    op.create_primary_key("puc_accounts_pkey", "puc_accounts", ["code"])
