from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from src.application.use_cases.purchases.suggest_mapping import (
    SuggestMappingUseCase,
    extract_keywords,
)
from src.domain.entities.classification_history import (
    ClassificationAction,
    ClassificationHistoryEntry,
)
from src.domain.entities.mapping_rule import SupplierMappingRule
from src.domain.entities.supplier_invoice import InvoiceStatus, SupplierInvoice
from src.domain.repositories.classification_history_repository import (
    ClassificationHistoryRepository,
)
from src.domain.repositories.mapping_rule_repository import SupplierMappingRuleRepository
from src.domain.repositories.puc_account_repository import PUCAccountRepository
from src.domain.repositories.supplier_invoice_repository import SupplierInvoiceRepository


class InvoiceNotFoundError(Exception):
    pass


class AccountNotInClientChartError(Exception):
    """La cuenta elegida no existe (o está inactiva) en el plan de cuentas de
    ese cliente. Dejarla pasar significa causar contra una cuenta inexistente,
    que el software contable rechaza cuando ya es tarde."""


@dataclass
class ConfirmInvoiceClassificationUseCase:
    """The "teach the system" flow: applies a human's account choice to an
    invoice and updates (or creates) the learned `SupplierMappingRule` —
    a confirmation if the human accepted what the system had learned for that
    supplier, a correction (which lowers confidence) if they picked something
    different. After learning, the rule is propagated to the other pending
    invoices of the same supplier so the accountant immediately sees the
    recognition ("teach once, recognize the rest").
    """

    invoice_repo: SupplierInvoiceRepository
    mapping_rule_repo: SupplierMappingRuleRepository
    history_repo: ClassificationHistoryRepository
    suggest_mapping: SuggestMappingUseCase
    puc_account_repo: PUCAccountRepository

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

        # El plan de cuentas es de la empresa: un código válido para un cliente
        # puede no existir en otro. Se valida acá, que es donde el humano elige.
        account = await self.puc_account_repo.get_by_code(invoice.tenant_id, invoice.client_id, account_code)
        if account is None or not account.is_active:
            raise AccountNotInClientChartError(
                f"La cuenta {account_code} no existe o está inactiva en el plan de cuentas de este cliente."
            )

        keywords = extract_keywords(invoice.concept_description)
        # The rule as it stands *before* this human action — what the system
        # "would have suggested" for this supplier, whether or not that
        # suggestion was surfaced on this particular invoice.
        rule = await self.mapping_rule_repo.find_best_match(
            invoice.tenant_id, invoice.client_id, invoice.supplier_nit, keywords
        )
        # Accepted-as-suggested if the human's choice matches the suggestion
        # shown on the invoice OR the account the rule already learned. This is
        # what makes repeat confirmations raise confidence instead of being
        # mistaken for corrections.
        was_suggested = invoice.suggested_account_code == account_code or (
            rule is not None and rule.account_code == account_code
        )
        account_before = invoice.suggested_account_code or (rule.account_code if rule else None)
        is_new_rule = rule is None

        invoice.confirm_classification(account_code, cost_center_id, user_id)
        await self.invoice_repo.save(invoice)

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
                action=ClassificationAction.CONFIRMED
                if (was_suggested or is_new_rule)
                else ClassificationAction.CORRECTED,
                account_code_before=account_before,
                account_code_after=account_code,
                rule_id=rule.id,
                user_id=user_id,
            )
        )

        await self._propagate_to_pending_siblings(invoice, rule)

        return invoice, rule

    async def _propagate_to_pending_siblings(
        self, invoice: SupplierInvoice, rule: SupplierMappingRule
    ) -> None:
        """Apply the just-learned rule as a suggestion to the other still-pending
        invoices of the same supplier, so a single classification lights up all
        of that supplier's remaining invoices in the review screen."""
        pending = await self.invoice_repo.list_by_client(
            invoice.tenant_id, invoice.client_id, InvoiceStatus.PENDING_REVIEW
        )
        for sibling in pending:
            if sibling.id == invoice.id or sibling.supplier_nit != invoice.supplier_nit:
                continue
            used = await self.suggest_mapping.execute(sibling)
            if used is not None:
                await self.invoice_repo.save(sibling)
