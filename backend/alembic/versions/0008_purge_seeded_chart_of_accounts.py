"""borrar el plan de cuentas sembrado y lo que quedo apuntando a el

Revision ID: 0008
Revises: 0007
Create Date: 2026-07-28

La 0007 desactivó las cuentas sembradas por defecto en vez de borrarlas, por
prudencia con el histórico. No hay histórico que proteger -el producto todavía
está en MVP y esos datos son de prueba-, así que se eliminan de verdad.

Dejarlas inactivas dejaba el sistema en un estado incoherente: facturas marcadas
como clasificadas contra códigos que ya no existen, y reglas aprendidas que
seguirían sugiriendo esos códigos. Se limpia todo junto:

1. Se borran las cuentas sembradas de los clientes que nunca importaron su plan.
2. Se borran las reglas de clasificación que apuntan a cuentas inexistentes: una
   regla que sugiere un código muerto solo hace perder tiempo al contador.
3. Las facturas clasificadas contra esas cuentas vuelven a revisión pendiente,
   para que se reclasifiquen con el plan real. Sin esto quedarían en un limbo:
   marcadas como listas para causar, pero condenadas a fallar.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from src.infrastructure.purchases.puc.puc_seed import PUC_SEED_ACCOUNTS

revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SEED_CODES = [str(account["code"]) for account in PUC_SEED_ACCOUNTS]


def upgrade() -> None:
    connection = op.get_bind()

    # Clientes cuyo plan es exactamente el sembrado: nunca importaron el suyo.
    untouched = sa.text(
        """
        SELECT client_id
        FROM puc_accounts
        GROUP BY client_id
        HAVING bool_and(code = ANY(:seed_codes))
        """
    ).bindparams(sa.bindparam("seed_codes", value=SEED_CODES))
    client_ids = [row[0] for row in connection.execute(untouched)]
    if not client_ids:
        return

    connection.execute(
        sa.text(
            "UPDATE supplier_invoices SET status = 'pending_review', final_account_code = NULL, "
            "final_cost_center_id = NULL, classified_by = NULL, classified_at = NULL "
            "WHERE client_id = ANY(:client_ids) AND final_account_code IS NOT NULL"
        ).bindparams(sa.bindparam("client_ids", value=client_ids))
    )
    # El historial de clasificación referencia las reglas por FK, así que va primero.
    connection.execute(
        sa.text(
            "DELETE FROM classification_history WHERE rule_id IN "
            "(SELECT id FROM supplier_mapping_rules WHERE client_id = ANY(:client_ids))"
        ).bindparams(sa.bindparam("client_ids", value=client_ids))
    )
    connection.execute(
        sa.text("DELETE FROM supplier_mapping_rules WHERE client_id = ANY(:client_ids)").bindparams(
            sa.bindparam("client_ids", value=client_ids)
        )
    )
    connection.execute(
        sa.text("DELETE FROM puc_accounts WHERE client_id = ANY(:client_ids)").bindparams(
            sa.bindparam("client_ids", value=client_ids)
        )
    )
    connection.execute(
        sa.text("DELETE FROM client_account_settings WHERE client_id = ANY(:client_ids)").bindparams(
            sa.bindparam("client_ids", value=client_ids)
        )
    )


def downgrade() -> None:
    # No hay vuelta atrás: el plan real se importa desde Siigo.
    pass
