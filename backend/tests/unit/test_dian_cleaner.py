from __future__ import annotations

from io import BytesIO

import openpyxl
import pytest

from src.infrastructure.purchases.dian.cleaner import (
    load_dian_invoices,
    normalize_nit,
    row_issue_date,
)


def _make_dian_excel(rows: list[list[object]]) -> BytesIO:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["CUFE", "NIT Emisor", "Razon Social Emisor", "Fecha Emision", "Concepto", "Subtotal", "IVA", "Total"])
    for row in rows:
        ws.append(row)
    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


class TestNormalizeNit:
    def test_strips_check_digit_and_punctuation(self):
        assert normalize_nit("900.123.456-7") == "900123456"

    def test_plain_digits_pass_through(self):
        assert normalize_nit("900123456") == "900123456"

    def test_empty_value(self):
        assert normalize_nit(None) == ""


class TestLoadDianInvoices:
    def test_parses_valid_rows(self):
        buf = _make_dian_excel(
            [
                ["a" * 40, "900.123.456-7", "Proveedor Uno", "2026-01-15", "Insumos de cocina", 100000, 19000, 119000],
                ["b" * 40, "800999888-1", "Proveedor Dos", "2026-01-20", "Servicios de aseo", 50000, 9500, 59500],
            ]
        )
        df, messages = load_dian_invoices(buf)

        assert len(df) == 2
        assert messages
        assert df.iloc[0]["NIT_EMISOR"] == "900123456"
        assert df.iloc[0]["TOTAL"] == 119000.0

    def test_missing_cufe_column_raises(self):
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["NIT Emisor", "Total"])
        ws.append(["900123456", 1000])
        buf = BytesIO()
        wb.save(buf)
        buf.seek(0)

        with pytest.raises(ValueError):
            load_dian_invoices(buf)

    def test_row_issue_date_falls_back_to_today_for_missing_dates(self):
        from datetime import date

        assert row_issue_date(None) == date.today()
