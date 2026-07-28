"""
Re-siembra el plan de cuentas PUC (subconjunto de causación de compras) sin
correr una migración completa. Útil en desarrollo cuando se edita
`src/infrastructure/purchases/puc/puc_seed.py` y se quiere refrescar la tabla
`puc_accounts` sin reconstruir la base de datos.

El plan es por cliente, así que siembra el de todos los clientes existentes.
Es un upsert: actualiza nombre y clase de las cuentas del subconjunto y no
toca las que la empresa haya importado o creado aparte.

Uso: python scripts/seed_puc.py
"""
from __future__ import annotations

import asyncio

from sqlalchemy import select

from src.infrastructure.database.connection import AsyncSessionLocal
from src.infrastructure.database.models import ClientModel
from src.infrastructure.purchases.puc.puc_seed import build_client_seed_accounts
from src.infrastructure.repositories.puc_account_repository import SQLPUCAccountRepository


async def main() -> None:
    async with AsyncSessionLocal() as session:
        repo = SQLPUCAccountRepository(session)
        clients = (await session.execute(select(ClientModel))).scalars().all()
        if not clients:
            print("No hay clientes; nada que sembrar.")
            return

        total = 0
        for client in clients:
            total += await repo.save_many(build_client_seed_accounts(client.tenant_id, client.id))
        await session.commit()

    print(f"Sembradas {total} cuentas PUC en {len(clients)} clientes.")


if __name__ == "__main__":
    asyncio.run(main())
