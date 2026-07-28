from __future__ import annotations

from io import BytesIO

import pandas as pd
import pytest

from src.infrastructure.purchases.puc.siigo_chart_importer import (
    load_siigo_chart_of_accounts,
    normalize_account_code,
    resolve_account_class,
)


def _excel(rows: list[list[object]], preamble: list[list[object]] | None = None) -> BytesIO:
    """Arma un Excel como el de Siigo: título/filtros antes del encabezado."""
    data = list(preamble or []) + rows
    buffer = BytesIO()
    pd.DataFrame(data).to_excel(buffer, index=False, header=False)
    buffer.seek(0)
    return buffer


class TestNormalizeAccountCode:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("5135", "5135"),
            ("5135.0", "5135"),  # pandas convierte numéricos a float
            ("5135-05", "513505"),  # separadores según configuración de la empresa
            ("1.1.05", "1105"),
            ("  2205  ", "2205"),
            (None, ""),
        ],
    )
    def test_keeps_only_digits(self, raw, expected):
        assert normalize_account_code(raw) == expected


class TestResolveAccountClass:
    def test_declared_class_wins_when_recognized(self):
        assert resolve_account_class("5135", "Gasto") == "gasto"

    @pytest.mark.parametrize(
        ("code", "expected"),
        [("1435", "activo"), ("2205", "pasivo"), ("3105", "patrimonio"), ("4135", "ingreso"), ("5135", "gasto"), ("6135", "costo")],
    )
    def test_falls_back_to_first_digit_of_the_puc_code(self, code, expected):
        # En el PUC la clase está codificada en el número de cuenta, así que el
        # archivo no necesita traer columna de clase.
        assert resolve_account_class(code, None) == expected


class TestLoadSiigoChartOfAccounts:
    def test_reads_accounts_skipping_the_report_preamble(self):
        file = _excel(
            preamble=[["Listado de cuentas contables"], ["Empresa: Rest Uno"], []],
            rows=[
                ["Código", "Nombre", "Clase", "Activa"],
                ["2205", "Proveedores nacionales", "Pasivo", "Si"],
                ["240801", "IVA descontable", "Pasivo", "Si"],
                ["5135", "Servicios", "Gasto", "No"],
            ],
        )

        accounts, messages = load_siigo_chart_of_accounts(file)

        assert [a["code"] for a in accounts] == ["2205", "240801", "5135"]
        assert accounts[0]["name"] == "Proveedores nacionales"
        assert accounts[2]["is_active"] is False
        assert "3 cuentas leídas" in messages[0]

    def test_infers_class_when_the_file_has_no_class_column(self):
        file = _excel([["Codigo", "Nombre"], ["1524", "Equipo de oficina"], ["5110", "Honorarios"]])

        accounts, _ = load_siigo_chart_of_accounts(file)

        assert accounts[0]["account_class"] == "activo"
        assert accounts[1]["account_class"] == "gasto"

    def test_keeps_first_of_duplicated_codes_and_reports_it(self):
        file = _excel(
            [["Codigo", "Nombre"], ["5135", "Servicios"], ["5135", "Servicios repetida"], ["5110", "Honorarios"]]
        )

        accounts, messages = load_siigo_chart_of_accounts(file)

        assert [a["code"] for a in accounts] == ["5135", "5110"]
        assert accounts[0]["name"] == "Servicios"
        assert any("repetidos" in m for m in messages)

    def test_skips_rows_without_usable_code_or_name(self):
        file = _excel([["Codigo", "Nombre"], ["5135", "Servicios"], [None, "Sin código"], ["5110", ""]])

        accounts, messages = load_siigo_chart_of_accounts(file)

        assert [a["code"] for a in accounts] == ["5135"]
        assert any("ignoradas" in m for m in messages)

    def test_skips_codes_longer_than_the_column_allows(self):
        # `puc_accounts.code` es VARCHAR(10): un código más largo delata que se
        # leyó la columna equivocada, y guardarlo reventaría en la base.
        file = _excel([["Codigo", "Nombre"], ["12345678901", "Demasiado larga"], ["5110", "Honorarios"]])

        accounts, _ = load_siigo_chart_of_accounts(file)

        assert [a["code"] for a in accounts] == ["5110"]

    def test_rejects_a_file_that_is_not_a_chart_of_accounts(self):
        file = _excel([["Fecha", "Total"], ["2026-01-01", 1000]])

        with pytest.raises(ValueError, match="Listado de cuentas contables"):
            load_siigo_chart_of_accounts(file)

    def test_rejects_a_chart_with_no_valid_rows(self):
        file = _excel([["Codigo", "Nombre"], [None, None]])

        with pytest.raises(ValueError, match="ninguna cuenta"):
            load_siigo_chart_of_accounts(file)
