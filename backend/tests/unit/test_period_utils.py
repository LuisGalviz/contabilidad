from __future__ import annotations

from datetime import date

from src.infrastructure.purchases.period_utils import period_bounds


class TestPeriodBounds:
    def test_regular_month(self):
        start, end = period_bounds("2026-03")
        assert start == date(2026, 3, 1)
        assert end == date(2026, 4, 1)

    def test_december_rolls_into_next_year(self):
        start, end = period_bounds("2026-12")
        assert start == date(2026, 12, 1)
        assert end == date(2027, 1, 1)
