from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.domain.entities.causation_entry import (
    CausationEntry,
    CausationEntryLine,
    CausationEntryStatus,
)
from src.domain.repositories.causation_entry_repository import CausationEntryRepository
from src.infrastructure.database.models import CausationEntryLineModel, CausationEntryModel
from src.infrastructure.purchases.period_utils import period_bounds


class SQLCausationEntryRepository(CausationEntryRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, id: UUID) -> CausationEntry | None:
        result = await self._session.execute(
            select(CausationEntryModel).options(selectinload(CausationEntryModel.lines)).where(CausationEntryModel.id == id)
        )
        row = result.scalar_one_or_none()
        return _to_domain(row) if row else None

    async def list_by_client(self, tenant_id: UUID, client_id: UUID, period: str | None = None) -> list[CausationEntry]:
        if period:
            return await self.list_by_client_and_period(tenant_id, client_id, period)
        result = await self._session.execute(
            select(CausationEntryModel)
            .options(selectinload(CausationEntryModel.lines))
            .where(CausationEntryModel.tenant_id == tenant_id, CausationEntryModel.client_id == client_id)
            .order_by(CausationEntryModel.entry_date.desc())
        )
        return [_to_domain(row) for row in result.scalars()]

    async def list_by_client_and_period(
        self,
        tenant_id: UUID,
        client_id: UUID,
        period: str,
    ) -> list[CausationEntry]:
        start, end = period_bounds(period)
        result = await self._session.execute(
            select(CausationEntryModel)
            .options(selectinload(CausationEntryModel.lines))
            .where(
                CausationEntryModel.tenant_id == tenant_id,
                CausationEntryModel.client_id == client_id,
                CausationEntryModel.entry_date >= start,
                CausationEntryModel.entry_date < end,
            )
            .order_by(CausationEntryModel.entry_date)
        )
        return [_to_domain(row) for row in result.scalars()]

    async def save(self, entry: CausationEntry) -> CausationEntry:
        existing = await self._session.execute(
            select(CausationEntryModel).options(selectinload(CausationEntryModel.lines)).where(CausationEntryModel.id == entry.id)
        )
        row = existing.scalar_one_or_none()

        if row:
            row.status = entry.status.value
            row.external_reference = entry.external_reference
            row.updated_at = entry.updated_at
            await self._session.flush()
            return entry

        model = CausationEntryModel(
            id=entry.id,
            tenant_id=entry.tenant_id,
            client_id=entry.client_id,
            invoice_id=entry.invoice_id,
            entry_date=entry.entry_date,
            status=entry.status.value,
            external_reference=entry.external_reference,
            created_at=entry.created_at,
            updated_at=entry.updated_at,
        )
        self._session.add(model)
        for line in entry.lines:
            self._session.add(
                CausationEntryLineModel(
                    entry_id=entry.id,
                    account_code=line.account_code,
                    debit=line.debit,
                    credit=line.credit,
                    description=line.description,
                    cost_center_id=line.cost_center_id,
                )
            )
        await self._session.flush()
        return entry

    async def delete(self, id: UUID) -> None:
        row = await self._session.get(CausationEntryModel, id)
        if row:
            await self._session.delete(row)
            await self._session.flush()


def _to_domain(model: CausationEntryModel) -> CausationEntry:
    return CausationEntry(
        id=model.id,
        tenant_id=model.tenant_id,
        client_id=model.client_id,
        invoice_id=model.invoice_id,
        entry_date=model.entry_date,
        lines=[
            CausationEntryLine(
                account_code=line.account_code,
                debit=line.debit,
                credit=line.credit,
                description=line.description,
                cost_center_id=line.cost_center_id,
            )
            for line in model.lines
        ],
        status=CausationEntryStatus(model.status),
        external_reference=model.external_reference,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )
