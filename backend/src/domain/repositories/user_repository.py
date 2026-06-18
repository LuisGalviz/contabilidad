from __future__ import annotations

from abc import abstractmethod
from uuid import UUID

from src.domain.entities.user import User, UserRole
from src.domain.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    @abstractmethod
    async def get_by_email(self, email: str) -> User | None: ...

    @abstractmethod
    async def list_by_tenant(self, tenant_id: UUID, role: UserRole | None = None) -> list[User]: ...

    @abstractmethod
    async def email_exists(self, email: str) -> bool: ...
