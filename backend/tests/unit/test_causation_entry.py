from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from src.domain.entities.causation_entry import CausationEntry, CausationEntryLine


def _make_entry(lines: list[CausationEntryLine]) -> CausationEntry:
    return CausationEntry(
        tenant_id=uuid.uuid4(),
        client_id=uuid.uuid4(),
        invoice_id=uuid.uuid4(),
        entry_date=date(2026, 1, 15),
        lines=lines,
    )


class TestCausationEntryBalance:
    def test_balanced_entry(self):
        entry = _make_entry(
            [
                CausationEntryLine(account_code="5195", debit=Decimal("100000"), credit=Decimal("0"), description="Gasto"),
                CausationEntryLine(account_code="240801", debit=Decimal("19000"), credit=Decimal("0"), description="IVA"),
                CausationEntryLine(account_code="2205", debit=Decimal("0"), credit=Decimal("119000"), description="CxP"),
            ]
        )
        assert entry.is_balanced()

    def test_unbalanced_entry(self):
        entry = _make_entry(
            [
                CausationEntryLine(account_code="5195", debit=Decimal("100000"), credit=Decimal("0"), description="Gasto"),
                CausationEntryLine(account_code="2205", debit=Decimal("0"), credit=Decimal("119000"), description="CxP"),
            ]
        )
        assert not entry.is_balanced()

    def test_mark_posted_and_failed(self):
        entry = _make_entry(
            [
                CausationEntryLine(account_code="5195", debit=Decimal("100000"), credit=Decimal("0"), description="Gasto"),
                CausationEntryLine(account_code="2205", debit=Decimal("0"), credit=Decimal("100000"), description="CxP"),
            ]
        )
        entry.mark_posted()
        assert entry.status.value == "posted"
        entry.mark_failed()
        assert entry.status.value == "failed"
