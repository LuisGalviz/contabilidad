from __future__ import annotations

from datetime import date


def period_bounds(period: str) -> tuple[date, date]:
    """Turn a "YYYY-MM" period string into [start, end) date bounds.

    Used to filter `SupplierInvoice.issue_date` / `CausationEntry.entry_date`
    by period without storing a redundant period column on either table.
    """
    year_str, month_str = period.split("-", 1)
    year, month = int(year_str), int(month_str)
    start = date(year, month, 1)
    end = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    return start, end
