"""add economic_activity and ciiu_code to clients

Revision ID: 54e590e6494f
Revises: 0003
Create Date: 2026-07-06 15:29:40.496320

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '54e590e6494f'
down_revision: Union[str, None] = '0003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Estas columnas ya las crea 0002. Esta revisión se autogeneró contra una
    # base bootstrapeada con `create_all()` y luego stampeada, donde 0002 nunca
    # llegó a ejecutarse y por tanto sí faltaban. En una base creada desde cero
    # 0002 sí corre y un `ADD COLUMN` normal aquí revienta con DuplicateColumn.
    #
    # Se conserva la revisión (en vez de borrarla) porque las bases que ya la
    # aplicaron la tienen registrada en `alembic_version` y romper la cadena las
    # dejaría sin ruta hacia head. Idempotente: no hace nada si ya existen.
    op.execute("ALTER TABLE clients ADD COLUMN IF NOT EXISTS economic_activity VARCHAR(50) NOT NULL DEFAULT ''")
    op.execute("ALTER TABLE clients ADD COLUMN IF NOT EXISTS ciiu_code VARCHAR(10) NOT NULL DEFAULT ''")


def downgrade() -> None:
    # Deliberadamente vacío: las columnas pertenecen a 0002, que ya las elimina
    # en su propio downgrade. Borrarlas aquí dejaría el esquema por debajo de lo
    # que 0002 garantiza.
    pass
