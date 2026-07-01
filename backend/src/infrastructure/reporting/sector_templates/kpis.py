from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from src.domain.entities.causation_entry import CausationEntry
from src.domain.entities.puc_account import PUCAccount
from src.domain.entities.supplier_invoice import SupplierInvoice

ZERO = Decimal("0")


@dataclass
class CategoryTotal:
    account_code: str
    account_name: str
    account_class: str
    total: Decimal


@dataclass
class SupplierTotal:
    supplier_nit: str
    supplier_name: str
    total: Decimal = ZERO
    invoice_count: int = 0


@dataclass
class PeriodPurchaseKPIs:
    period: str
    total_amount: Decimal
    invoice_count: int
    by_category: list[CategoryTotal] = field(default_factory=list)
    top_suppliers: list[SupplierTotal] = field(default_factory=list)
    prior_period_total: Decimal | None = None
    auto_classified_share: float = 0.0

    @property
    def change_vs_prior_period(self) -> float | None:
        if not self.prior_period_total:
            return None
        if self.prior_period_total == 0:
            return None
        return float((self.total_amount - self.prior_period_total) / self.prior_period_total)


def compute_purchase_kpis(
    period: str,
    invoices: list[SupplierInvoice],
    causation_entries: list[CausationEntry],
    accounts_by_code: dict[str, PUCAccount],
    prior_period_total: Decimal | None = None,
) -> PeriodPurchaseKPIs:
    """Aggregate a period's causación data into report-ready KPIs.

    Purchases-only by design (this feature automates compras causación, not
    sales) — so KPIs are framed around "en qué se fue la plata", not a full
    P&L margin (that would need sales data ContaFlow doesn't ingest yet).
    """
    total_amount = sum((inv.total_amount for inv in invoices), ZERO)
    invoice_count = len(invoices)

    category_totals: dict[str, Decimal] = {}
    for entry in causation_entries:
        for line in entry.lines:
            if line.debit <= 0:
                continue  # only the debit (expense/cost/asset) side represents "spend"
            category_totals[line.account_code] = category_totals.get(line.account_code, ZERO) + line.debit

    by_category = [
        CategoryTotal(
            account_code=code,
            account_name=accounts_by_code[code].name if code in accounts_by_code else code,
            account_class=accounts_by_code[code].account_class if code in accounts_by_code else "gasto",
            total=total,
        )
        for code, total in sorted(category_totals.items(), key=lambda kv: kv[1], reverse=True)
    ]

    supplier_totals: dict[str, SupplierTotal] = {}
    for inv in invoices:
        bucket = supplier_totals.setdefault(
            inv.supplier_nit, SupplierTotal(supplier_nit=inv.supplier_nit, supplier_name=inv.supplier_name)
        )
        bucket.total += inv.total_amount
        bucket.invoice_count += 1
    top_suppliers = sorted(supplier_totals.values(), key=lambda s: s.total, reverse=True)[:5]

    auto_confirmed = sum(
        1
        for inv in invoices
        if inv.classification_source is not None
        and inv.classification_source.value.startswith("auto")
        and inv.suggested_account_code == inv.final_account_code
    )
    auto_classified_share = auto_confirmed / invoice_count if invoice_count else 0.0

    return PeriodPurchaseKPIs(
        period=period,
        total_amount=total_amount,
        invoice_count=invoice_count,
        by_category=by_category,
        top_suppliers=top_suppliers,
        prior_period_total=prior_period_total,
        auto_classified_share=auto_classified_share,
    )
