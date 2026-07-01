"""
Re-siembra el plan de cuentas PUC (subconjunto de causación de compras) sin
correr una migración completa. Útil en desarrollo cuando se edita
`src/infrastructure/purchases/puc/puc_seed.py` y se quiere refrescar la tabla
`puc_accounts` sin reconstruir la base de datos.

Uso: python scripts/seed_puc.py
"""
from __future__ import annotations

import asyncio

from sqlalchemy.dialects.postgresql import insert as pg_insert

from src.infrastructure.database.connection import AsyncSessionLocal
from src.infrastructure.database.models import PUCAccountModel
from src.infrastructure.purchases.puc.puc_seed import PUC_SEED_ACCOUNTS


async def main() -> None:
    async with AsyncSessionLocal() as session:
        for account in PUC_SEED_ACCOUNTS:
            stmt = pg_insert(PUCAccountModel).values(
                code=account["code"],
                name=account["name"],
                account_class=account["account_class"],
                parent_code=account["parent_code"],
                requires_cost_center=False,
                is_active=True,
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=[PUCAccountModel.code],
                set_={"name": stmt.excluded.name, "account_class": stmt.excluded.account_class},
            )
            await session.execute(stmt)
        await session.commit()
    print(f"Sembradas {len(PUC_SEED_ACCOUNTS)} cuentas PUC.")


if __name__ == "__main__":
    asyncio.run(main())
