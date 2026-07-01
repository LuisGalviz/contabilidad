from __future__ import annotations

from dataclasses import dataclass

from src.domain.entities.mapping_rule import SupplierMappingRule
from src.domain.entities.supplier_invoice import ClassificationSource, SupplierInvoice
from src.domain.repositories.mapping_rule_repository import SupplierMappingRuleRepository
from src.infrastructure.reporting.sazon.cleaner import normalize_text

# Confidence thresholds driving auto-confirm vs suggest-for-review vs no
# suggestion. A rule only auto-confirms once it's been confirmed by a human
# at least MIN_CONFIRMATIONS_FOR_AUTO times — "the first few times teach the
# system" (product requirement), expressed as a plain confidence/count check,
# no LLM involved.
AUTO_CONFIRM_THRESHOLD = 0.85
SUGGEST_THRESHOLD = 0.3
MIN_CONFIRMATIONS_FOR_AUTO = 3


def extract_keywords(text: str) -> list[str]:
    normalized = normalize_text(text)
    return [token for token in normalized.split(" ") if len(token) >= 3]


@dataclass
class SuggestMappingUseCase:
    mapping_rule_repo: SupplierMappingRuleRepository

    async def execute(self, invoice: SupplierInvoice) -> SupplierMappingRule | None:
        """Looks up the best-matching learned rule and, if confident enough,
        attaches a suggestion to `invoice` in place. Returns the rule used (or
        None if no suggestion was made) so the caller can decide whether to
        auto-confirm or leave it for human review."""
        keywords = extract_keywords(invoice.concept_description)
        rule = await self.mapping_rule_repo.find_best_match(
            invoice.tenant_id, invoice.client_id, invoice.supplier_nit, keywords
        )
        if rule is None:
            return None

        if rule.confidence >= AUTO_CONFIRM_THRESHOLD and rule.times_confirmed >= MIN_CONFIRMATIONS_FOR_AUTO:
            source = ClassificationSource.AUTO_HIGH_CONFIDENCE
        elif rule.confidence >= SUGGEST_THRESHOLD:
            source = ClassificationSource.AUTO_LOW_CONFIDENCE
        else:
            return None

        invoice.apply_suggestion(rule.account_code, rule.cost_center_id, rule.confidence, source)
        return rule
