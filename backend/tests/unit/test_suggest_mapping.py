from __future__ import annotations

import uuid
from datetime import date

import pytest

from src.application.use_cases.purchases.suggest_mapping import (
    AUTO_CONFIRM_THRESHOLD,
    MIN_CONFIRMATIONS_FOR_AUTO,
    SuggestMappingUseCase,
    extract_keywords,
)
from src.domain.entities.mapping_rule import SupplierMappingRule
from src.domain.entities.supplier_invoice import ClassificationSource, SupplierInvoice
from src.domain.repositories.mapping_rule_repository import SupplierMappingRuleRepository


class FakeMappingRuleRepo(SupplierMappingRuleRepository):
    def __init__(self, rule: SupplierMappingRule | None) -> None:
        self._rule = rule

    async def get_by_id(self, id):  # noqa: A002
        return self._rule

    async def find_best_match(self, tenant_id, client_id, supplier_nit, keywords):
        if self._rule and self._rule.supplier_nit == supplier_nit:
            return self._rule
        return None

    async def list_by_client(self, tenant_id, client_id):
        return [self._rule] if self._rule else []

    async def save(self, rule):
        self._rule = rule
        return rule

    async def delete(self, id):  # noqa: A002
        self._rule = None


def _make_invoice(supplier_nit: str = "900123456") -> SupplierInvoice:
    return SupplierInvoice(
        tenant_id=uuid.uuid4(),
        client_id=uuid.uuid4(),
        import_batch_id=uuid.uuid4(),
        cufe="a" * 40,
        supplier_nit=supplier_nit,
        supplier_name="Proveedor Test",
        issue_date=date(2026, 1, 10),
        concept_description="Compra de insumos de cocina",
        subtotal=100000,
        vat_amount=19000,
        total_amount=119000,
    )


def _make_rule(supplier_nit: str, confidence: float, times_confirmed: int) -> SupplierMappingRule:
    return SupplierMappingRule(
        tenant_id=uuid.uuid4(),
        client_id=uuid.uuid4(),
        supplier_nit=supplier_nit,
        account_code="6205",
        confidence=confidence,
        times_confirmed=times_confirmed,
    )


@pytest.mark.asyncio
class TestSuggestMappingUseCase:
    async def test_no_rule_means_no_suggestion(self):
        use_case = SuggestMappingUseCase(mapping_rule_repo=FakeMappingRuleRepo(None))
        invoice = _make_invoice()
        rule = await use_case.execute(invoice)
        assert rule is None
        assert invoice.suggested_account_code is None

    async def test_high_confidence_rule_with_enough_confirmations_auto_confirms(self):
        rule = _make_rule("900123456", confidence=AUTO_CONFIRM_THRESHOLD, times_confirmed=MIN_CONFIRMATIONS_FOR_AUTO)
        use_case = SuggestMappingUseCase(mapping_rule_repo=FakeMappingRuleRepo(rule))
        invoice = _make_invoice(supplier_nit="900123456")

        result = await use_case.execute(invoice)

        assert result is rule
        assert invoice.suggested_account_code == "6205"
        assert invoice.classification_source == ClassificationSource.AUTO_HIGH_CONFIDENCE

    async def test_high_confidence_but_not_enough_confirmations_is_low_confidence(self):
        rule = _make_rule("900123456", confidence=AUTO_CONFIRM_THRESHOLD, times_confirmed=1)
        use_case = SuggestMappingUseCase(mapping_rule_repo=FakeMappingRuleRepo(rule))
        invoice = _make_invoice(supplier_nit="900123456")

        result = await use_case.execute(invoice)

        assert result is rule
        assert invoice.classification_source == ClassificationSource.AUTO_LOW_CONFIDENCE

    async def test_low_confidence_rule_below_threshold_gives_no_suggestion(self):
        rule = _make_rule("900123456", confidence=0.1, times_confirmed=0)
        use_case = SuggestMappingUseCase(mapping_rule_repo=FakeMappingRuleRepo(rule))
        invoice = _make_invoice(supplier_nit="900123456")

        result = await use_case.execute(invoice)

        assert result is None
        assert invoice.suggested_account_code is None


class TestExtractKeywords:
    def test_filters_short_tokens_and_normalizes(self):
        keywords = extract_keywords("Compra de Insumos y Café")
        assert "COMPRA" in keywords
        assert "INSUMOS" in keywords
        assert "DE" not in keywords  # too short (< 3 chars)
        assert "Y" not in keywords  # too short (< 3 chars)
