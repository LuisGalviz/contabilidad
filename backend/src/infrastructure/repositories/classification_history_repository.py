from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.classification_history import (
    ClassificationAction,
    ClassificationHistoryEntry,
)
from src.domain.repositories.classification_history_repository import (
    ClassificationHistoryRepository,
)
from src.infrastructure.database.models import ClassificationHistoryModel


class SQLClassificationHistoryRepository(ClassificationHistoryRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def append(self, entry: ClassificationHistoryEntry) -> ClassificationHistoryEntry:
        model = ClassificationHistoryModel(
            id=entry.id,
            invoice_id=entry.invoice_id,
            tenant_id=entry.tenant_id,
            action=entry.action.value,
            account_code_before=entry.account_code_before,
            account_code_after=entry.account_code_after,
            rule_id=entry.rule_id,
            user_id=entry.user_id,
            created_at=entry.created_at,
        )
        self._session.add(model)
        await self._session.flush()
        return entry

    async def list_by_invoice(self, invoice_id: UUID) -> list[ClassificationHistoryEntry]:
        result = await self._session.execute(
            select(ClassificationHistoryModel)
            .where(ClassificationHistoryModel.invoice_id == invoice_id)
            .order_by(ClassificationHistoryModel.created_at)
        )
        return [_to_domain(row) for row in result.scalars()]

    async def list_by_rule(self, rule_id: UUID) -> list[ClassificationHistoryEntry]:
        result = await self._session.execute(
            select(ClassificationHistoryModel)
            .where(ClassificationHistoryModel.rule_id == rule_id)
            .order_by(ClassificationHistoryModel.created_at)
        )
        return [_to_domain(row) for row in result.scalars()]


def _to_domain(model: ClassificationHistoryModel) -> ClassificationHistoryEntry:
    return ClassificationHistoryEntry(
        id=model.id,
        invoice_id=model.invoice_id,
        tenant_id=model.tenant_id,
        action=ClassificationAction(model.action),
        account_code_before=model.account_code_before,
        account_code_after=model.account_code_after,
        rule_id=model.rule_id,
        user_id=model.user_id,
        created_at=model.created_at,
    )
