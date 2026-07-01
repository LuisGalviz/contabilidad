from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.puc_account import PUCAccount
from src.domain.repositories.puc_account_repository import PUCAccountRepository
from src.infrastructure.database.models import PUCAccountModel


class SQLPUCAccountRepository(PUCAccountRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, id: str) -> PUCAccount | None:  # type: ignore[override]
        return await self.get_by_code(id)

    async def get_by_code(self, code: str) -> PUCAccount | None:
        row = await self._session.get(PUCAccountModel, code)
        return _to_domain(row) if row else None

    async def list_active(self, account_class: str | None = None, search: str | None = None) -> list[PUCAccount]:
        q = select(PUCAccountModel).where(PUCAccountModel.is_active.is_(True))
        if account_class:
            q = q.where(PUCAccountModel.account_class == account_class)
        if search:
            like = f"%{search.lower()}%"
            q = q.where(PUCAccountModel.name.ilike(like) | PUCAccountModel.code.ilike(like))
        result = await self._session.execute(q.order_by(PUCAccountModel.code))
        return [_to_domain(row) for row in result.scalars()]

    async def save(self, account: PUCAccount) -> PUCAccount:
        existing = await self._session.get(PUCAccountModel, account.code)
        if existing:
            existing.name = account.name
            existing.account_class = account.account_class
            existing.parent_code = account.parent_code
            existing.requires_cost_center = account.requires_cost_center
            existing.is_active = account.is_active
            await self._session.flush()
            return account

        model = PUCAccountModel(
            code=account.code,
            name=account.name,
            account_class=account.account_class,
            parent_code=account.parent_code,
            requires_cost_center=account.requires_cost_center,
            is_active=account.is_active,
        )
        self._session.add(model)
        await self._session.flush()
        return account

    async def delete(self, id: str) -> None:  # type: ignore[override]
        row = await self._session.get(PUCAccountModel, id)
        if row:
            await self._session.delete(row)
            await self._session.flush()


def _to_domain(model: PUCAccountModel) -> PUCAccount:
    return PUCAccount(
        code=model.code,
        name=model.name,
        account_class=model.account_class,
        parent_code=model.parent_code,
        requires_cost_center=model.requires_cost_center,
        is_active=model.is_active,
    )
