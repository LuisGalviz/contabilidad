from __future__ import annotations

from abc import abstractmethod

from src.domain.entities.puc_account import PUCAccount
from src.domain.repositories.base import BaseRepository


class PUCAccountRepository(BaseRepository[PUCAccount]):
    @abstractmethod
    async def get_by_code(self, code: str) -> PUCAccount | None: ...

    @abstractmethod
    async def list_active(self, account_class: str | None = None, search: str | None = None) -> list[PUCAccount]: ...
