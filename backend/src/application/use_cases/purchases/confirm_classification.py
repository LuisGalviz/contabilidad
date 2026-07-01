from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from src.application.use_cases.purchases.suggest_mapping import extract_keywords
from src.domain.entities.classification_history import (
    ClassificationAction,
    ClassificationHistoryEntry,
)
from src.domain.entities.mapping_rule import SupplierMappingRule
from src.domain.entities.supplier_invoice import SupplierInvoice
from src.domain.repositories.classification_history_repository import (
    ClassificationHistoryRepository,
)
from src.domain.repositories.mapping_rule_repository import SupplierMappingRuleRepository
from src.domain.repositories.supplier_invoice_repository import SupplierInvoiceRepository


class InvoiceNotFoundError(Exception):
    pass


@dataclass
class ConfirmInvoiceClassificationUseCase:
    """The "teach the system" flow: applies a human's account choice to an
    invoice and updates (or creates) the learned `SupplierMappingRule` —
    a confirmation if the human accepted the suggestion as-is, a correction
    (which lowers confidence) if they picked something different.
    """

    invoice_repo: SupplierInvoiceRepository
    mapping_rule_repo: SupplierMappingRuleRepository
    history_repo: ClassificationHistoryRepository

    async def execute(
        self,
        invoice_id: UUID,
        account_code: str,
        cost_center_id: UUID | None,
        user_id: UUID,
    ) -> tuple[SupplierInvoice, SupplierMappingRule]:
        invoice = await self.invoice_repo.get_by_id(invoice_id)
        if invoice is None:
            raise InvoiceNotFoundError(f"Invoice {invoice_id} not found")

        was_suggested = invoice.suggested_account_code == account_code
        account_before = invoice.suggested_account_code

        invoice.confirm_classification(account_code, cost_center_id, user_id)
        await self.invoice_repo.save(invoice)

        keywords = extract_keywords(invoice.concept_description)
        rule = await self.mapping_rule_repo.find_best_match(
            invoice.tenant_id, invoice.client_id, invoice.supplier_nit, keywords
        )

        if rule is None:
            rule = SupplierMappingRule(
                tenant_id=invoice.tenant_id,
                client_id=invoice.client_id,
                supplier_nit=invoice.supplier_nit,
                account_code=account_code,
                concept_keywords=keywords,
                cost_center_id=cost_center_id,
                created_by=user_id,
                confidence=0.5,
                times_confirmed=1,
            )
        elif was_suggested:
            rule.record_confirmation()
        else:
            rule.record_correction(account_code, cost_center_id)
        await self.mapping_rule_repo.save(rule)

        await self.history_repo.append(
            ClassificationHistoryEntry(
                invoice_id=invoice.id,
                tenant_id=invoice.tenant_id,
                action=ClassificationAction.CONFIRMED if was_suggested else ClassificationAction.CORRECTED,
                account_code_before=account_before,
                account_code_after=account_code,
                rule_id=rule.id,
                user_id=user_id,
            )
        )

        return invoice, rule
