from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.entities.classification_history import ClassificationHistoryEntry


class ClassificationHistoryRepository(ABC):
    @abstractmethod
    async def append(self, entry: ClassificationHistoryEntry) -> ClassificationHistoryEntry: ...

    @abstractmethod
    async def list_by_invoice(self, invoice_id: UUID) -> list[ClassificationHistoryEntry]: ...

    @abstractmethod
    async def list_by_rule(self, rule_id: UUID) -> list[ClassificationHistoryEntry]: ...
