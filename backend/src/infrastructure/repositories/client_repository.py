from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.client import Client
from src.domain.repositories.client_repository import ClientRepository
from src.infrastructure.database.models import ClientModel


class SQLClientRepository(ClientRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, id: UUID) -> Client | None:
        result = await self._session.get(ClientModel, id)
        return _to_domain(result) if result else None

    async def list_by_tenant(self, tenant_id: UUID, active_only: bool = True) -> list[Client]:
        q = select(ClientModel).where(ClientModel.tenant_id == tenant_id)
        if active_only:
            q = q.where(ClientModel.is_active.is_(True))
        result = await self._session.execute(q.order_by(ClientModel.name))
        return [_to_domain(row) for row in result.scalars()]

    async def nit_exists_in_tenant(self, nit: str, tenant_id: UUID) -> bool:
        result = await self._session.execute(
            select(ClientModel.id).where(
                ClientModel.nit == nit,
                ClientModel.tenant_id == tenant_id,
                ClientModel.is_active.is_(True),
            )
        )
        return result.scalar_one_or_none() is not None

    async def count_by_tenant(self, tenant_id: UUID) -> int:
        result = await self._session.execute(
            select(func.count()).select_from(ClientModel).where(
                ClientModel.tenant_id == tenant_id,
                ClientModel.is_active.is_(True),
            )
        )
        return result.scalar_one()

    async def save(self, client: Client) -> Client:
        existing = await self._session.get(ClientModel, client.id)
        if existing:
            existing.name = client.name
            existing.nit = client.nit
            existing.contact_email = client.contact_email
            existing.contact_name = client.contact_name
            existing.contact_phone = client.contact_phone
            existing.is_active = client.is_active
            await self._session.flush()
            return _to_domain(existing)

        model = ClientModel(
            id=client.id,
            tenant_id=client.tenant_id,
            name=client.name,
            nit=client.nit,
            contact_email=client.contact_email,
            contact_name=client.contact_name,
            contact_phone=client.contact_phone,
            is_active=client.is_active,
            created_at=client.created_at,
            updated_at=client.updated_at,
        )
        self._session.add(model)
        await self._session.flush()
        return _to_domain(model)

    async def delete(self, id: UUID) -> None:
        row = await self._session.get(ClientModel, id)
        if row:
            await self._session.delete(row)
            await self._session.flush()


def _to_domain(model: ClientModel) -> Client:
    return Client(
        id=model.id,
        tenant_id=model.tenant_id,
        name=model.name,
        nit=model.nit,
        contact_email=model.contact_email,
        contact_name=model.contact_name,
        contact_phone=model.contact_phone,
        is_active=model.is_active,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )
