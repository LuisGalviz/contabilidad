from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.puc_account import PUCAccount
from src.domain.repositories.puc_account_repository import PUCAccountRepository
from src.infrastructure.database.models import PUCAccountModel


class SQLPUCAccountRepository(PUCAccountRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, id: UUID) -> PUCAccount | None:
        row = await self._session.get(PUCAccountModel, id)
        return _to_domain(row) if row else None

    async def get_by_code(self, tenant_id: UUID, client_id: UUID, code: str) -> PUCAccount | None:
        q = select(PUCAccountModel).where(
            PUCAccountModel.tenant_id == tenant_id,
            PUCAccountModel.client_id == client_id,
            PUCAccountModel.code == code,
        )
        row = (await self._session.execute(q)).scalar_one_or_none()
        return _to_domain(row) if row else None

    async def list_active(
        self,
        tenant_id: UUID,
        client_id: UUID,
        account_class: str | None = None,
        search: str | None = None,
    ) -> list[PUCAccount]:
        q = select(PUCAccountModel).where(
            PUCAccountModel.tenant_id == tenant_id,
            PUCAccountModel.client_id == client_id,
            PUCAccountModel.is_active.is_(True),
        )
        if account_class:
            q = q.where(PUCAccountModel.account_class == account_class)
        if search:
            like = f"%{search.lower()}%"
            q = q.where(PUCAccountModel.name.ilike(like) | PUCAccountModel.code.ilike(like))
        result = await self._session.execute(q.order_by(PUCAccountModel.code))
        return [_to_domain(row) for row in result.scalars()]

    async def save(self, account: PUCAccount) -> PUCAccount:
        existing = await self.get_by_code(account.tenant_id, account.client_id, account.code)
        if existing:
            row = await self._session.get(PUCAccountModel, existing.id)
            if row is not None:
                row.name = account.name
                row.account_class = account.account_class
                row.parent_code = account.parent_code
                row.requires_cost_center = account.requires_cost_center
                row.is_active = account.is_active
                await self._session.flush()
            return account

        self._session.add(
            PUCAccountModel(
                id=account.id,
                tenant_id=account.tenant_id,
                client_id=account.client_id,
                code=account.code,
                name=account.name,
                account_class=account.account_class,
                parent_code=account.parent_code,
                requires_cost_center=account.requires_cost_center,
                is_active=account.is_active,
            )
        )
        await self._session.flush()
        return account

    async def save_many(self, accounts: list[PUCAccount]) -> int:
        """Upsert por `(client_id, code)` en una sola sentencia. Reimportar el
        plan de cuentas actualiza nombre/clase sin duplicar ni perder las
        cuentas que ya estaban."""
        if not accounts:
            return 0

        stmt = pg_insert(PUCAccountModel).values(
            [
                {
                    "id": account.id,
                    "tenant_id": account.tenant_id,
                    "client_id": account.client_id,
                    "code": account.code,
                    "name": account.name,
                    "account_class": account.account_class,
                    "parent_code": account.parent_code,
                    "requires_cost_center": account.requires_cost_center,
                    "is_active": account.is_active,
                }
                for account in accounts
            ]
        )
        stmt = stmt.on_conflict_do_update(
            constraint="uq_puc_accounts_client_code",
            set_={
                "name": stmt.excluded.name,
                "account_class": stmt.excluded.account_class,
                "parent_code": stmt.excluded.parent_code,
                "requires_cost_center": stmt.excluded.requires_cost_center,
                "is_active": stmt.excluded.is_active,
            },
        )
        await self._session.execute(stmt)
        await self._session.flush()
        return len(accounts)

    async def delete(self, id: UUID) -> None:
        row = await self._session.get(PUCAccountModel, id)
        if row:
            await self._session.delete(row)
            await self._session.flush()


def _to_domain(model: PUCAccountModel) -> PUCAccount:
    return PUCAccount(
        id=model.id,
        tenant_id=model.tenant_id,
        client_id=model.client_id,
        code=model.code,
        name=model.name,
        account_class=model.account_class,
        parent_code=model.parent_code,
        requires_cost_center=model.requires_cost_center,
        is_active=model.is_active,
    )
