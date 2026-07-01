from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.mapping_rule import SupplierMappingRule
from src.domain.repositories.mapping_rule_repository import SupplierMappingRuleRepository
from src.infrastructure.database.models import SupplierMappingRuleModel


class SQLSupplierMappingRuleRepository(SupplierMappingRuleRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, id: UUID) -> SupplierMappingRule | None:
        row = await self._session.get(SupplierMappingRuleModel, id)
        return _to_domain(row) if row else None

    async def find_best_match(
        self,
        tenant_id: UUID,
        client_id: UUID,
        supplier_nit: str,
        keywords: list[str],
    ) -> SupplierMappingRule | None:
        result = await self._session.execute(
            select(SupplierMappingRuleModel).where(
                SupplierMappingRuleModel.tenant_id == tenant_id,
                SupplierMappingRuleModel.client_id == client_id,
                SupplierMappingRuleModel.supplier_nit == supplier_nit,
                SupplierMappingRuleModel.is_active.is_(True),
            )
        )
        rows = list(result.scalars())
        if not rows:
            return None

        keyword_set = set(keywords)

        def _sort_key(row: SupplierMappingRuleModel) -> tuple[int, float, int]:
            overlap = len(set(row.concept_keywords or []) & keyword_set)
            return (overlap, row.confidence, row.times_confirmed)

        best = max(rows, key=_sort_key)
        return _to_domain(best)

    async def list_by_client(self, tenant_id: UUID, client_id: UUID) -> list[SupplierMappingRule]:
        result = await self._session.execute(
            select(SupplierMappingRuleModel)
            .where(
                SupplierMappingRuleModel.tenant_id == tenant_id,
                SupplierMappingRuleModel.client_id == client_id,
                SupplierMappingRuleModel.is_active.is_(True),
            )
            .order_by(SupplierMappingRuleModel.supplier_nit)
        )
        return [_to_domain(row) for row in result.scalars()]

    async def save(self, rule: SupplierMappingRule) -> SupplierMappingRule:
        existing = await self._session.get(SupplierMappingRuleModel, rule.id)
        kwargs = dict(
            tenant_id=rule.tenant_id,
            client_id=rule.client_id,
            supplier_nit=rule.supplier_nit,
            concept_keywords=rule.concept_keywords,
            account_code=rule.account_code,
            cost_center_id=rule.cost_center_id,
            confidence=rule.confidence,
            times_confirmed=rule.times_confirmed,
            times_corrected=rule.times_corrected,
            created_by=rule.created_by,
            is_active=rule.is_active,
            updated_at=rule.updated_at,
        )
        if existing:
            for key, value in kwargs.items():
                setattr(existing, key, value)
            await self._session.flush()
            return rule

        model = SupplierMappingRuleModel(id=rule.id, created_at=rule.created_at, **kwargs)
        self._session.add(model)
        await self._session.flush()
        return rule

    async def delete(self, id: UUID) -> None:
        row = await self._session.get(SupplierMappingRuleModel, id)
        if row:
            await self._session.delete(row)
            await self._session.flush()


def _to_domain(model: SupplierMappingRuleModel) -> SupplierMappingRule:
    return SupplierMappingRule(
        id=model.id,
        tenant_id=model.tenant_id,
        client_id=model.client_id,
        supplier_nit=model.supplier_nit,
        concept_keywords=list(model.concept_keywords or []),
        account_code=model.account_code,
        cost_center_id=model.cost_center_id,
        confidence=model.confidence,
        times_confirmed=model.times_confirmed,
        times_corrected=model.times_corrected,
        created_by=model.created_by,
        is_active=model.is_active,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )
