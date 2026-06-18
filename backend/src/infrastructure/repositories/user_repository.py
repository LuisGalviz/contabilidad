from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.user import User, UserRole, UserStatus
from src.domain.repositories.user_repository import UserRepository
from src.infrastructure.database.models import UserModel


class SQLUserRepository(UserRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, id: UUID) -> User | None:
        result = await self._session.get(UserModel, id)
        return _to_domain(result) if result else None

    async def get_by_email(self, email: str) -> User | None:
        result = await self._session.execute(select(UserModel).where(UserModel.email == email))
        row = result.scalar_one_or_none()
        return _to_domain(row) if row else None

    async def list_by_tenant(self, tenant_id: UUID, role: UserRole | None = None) -> list[User]:
        q = select(UserModel).where(UserModel.tenant_id == tenant_id)
        if role:
            q = q.where(UserModel.role == role.value)
        result = await self._session.execute(q)
        return [_to_domain(row) for row in result.scalars()]

    async def email_exists(self, email: str) -> bool:
        result = await self._session.execute(select(UserModel.id).where(UserModel.email == email))
        return result.scalar_one_or_none() is not None

    async def save(self, user: User) -> User:
        existing = await self._session.get(UserModel, user.id)
        if existing:
            existing.email = user.email
            existing.name = user.name
            existing.hashed_password = user.hashed_password
            existing.role = user.role.value
            existing.status = user.status.value
            existing.tenant_id = user.tenant_id
            await self._session.flush()
            return _to_domain(existing)

        model = UserModel(
            id=user.id,
            email=user.email,
            name=user.name,
            hashed_password=user.hashed_password,
            role=user.role.value,
            status=user.status.value,
            tenant_id=user.tenant_id,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )
        self._session.add(model)
        await self._session.flush()
        return _to_domain(model)

    async def delete(self, id: UUID) -> None:
        row = await self._session.get(UserModel, id)
        if row:
            await self._session.delete(row)
            await self._session.flush()


def _to_domain(model: UserModel) -> User:
    return User(
        id=model.id,
        email=model.email,
        name=model.name,
        hashed_password=model.hashed_password,
        role=UserRole(model.role),
        status=UserStatus(model.status),
        tenant_id=model.tenant_id,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )
