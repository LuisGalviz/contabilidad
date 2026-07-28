"""desactivar el plan de cuentas sembrado por defecto

Revision ID: 0007
Revises: 0006
Create Date: 2026-07-28

Un cliente nuevo se sembraba con el subconjunto PUC del decreto 2650 (2205,
240801, 5135…). Verificado contra la exportación real de Siigo, **ninguno de
esos códigos existe allá como cuenta de movimiento**: el plan real usa auxiliares
de 8 dígitos (22050501, 24081001) y los del decreto son cuentas de agrupación,
contra las que Siigo rechaza el comprobante completo.

O sea que el seed mostraba cuentas que parecían usables y no lo eran. El plan de
cuentas debe salir siempre de importar el de la empresa desde Siigo.

Las cuentas sembradas se **desactivan, no se borran**: puede haber facturas ya
clasificadas y reglas aprendidas apuntando a esos códigos, y borrarlas dejaría
huérfano el histórico. Desactivadas desaparecen del selector, que es el objetivo.

Solo se tocan los clientes que nunca importaron su plan real (los que no tienen
ninguna cuenta fuera del seed); a quien ya importó no se le toca nada.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from src.infrastructure.purchases.puc.puc_seed import PUC_SEED_ACCOUNTS

revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SEED_CODES = tuple(str(account["code"]) for account in PUC_SEED_ACCOUNTS)


def upgrade() -> None:
    connection = op.get_bind()

    # Clientes cuyo plan es exactamente el sembrado: no importaron el suyo.
    untouched = sa.text(
        """
        SELECT client_id
        FROM puc_accounts
        GROUP BY client_id
        HAVING bool_and(code = ANY(:seed_codes))
        """
    ).bindparams(sa.bindparam("seed_codes", value=list(SEED_CODES)))
    client_ids = [row[0] for row in connection.execute(untouched)]
    if not client_ids:
        return

    connection.execute(
        sa.text(
            "UPDATE puc_accounts SET is_active = false "
            "WHERE client_id = ANY(:client_ids) AND code = ANY(:seed_codes)"
        ).bindparams(
            sa.bindparam("client_ids", value=client_ids),
            sa.bindparam("seed_codes", value=list(SEED_CODES)),
        )
    )
    # La configuración contable apuntaba a esas mismas cuentas; dejarla sería
    # apuntar a códigos inactivos. Se define al importar el plan real.
    connection.execute(
        sa.text("DELETE FROM client_account_settings WHERE client_id = ANY(:client_ids)").bindparams(
            sa.bindparam("client_ids", value=client_ids)
        )
    )


def downgrade() -> None:
    # Reactivar a ciegas volvería a mostrar cuentas inservibles; el plan real se
    # importa desde Siigo. Sin vuelta atrás a propósito.
    pass
