from __future__ import annotations

import re
from datetime import date
from typing import TYPE_CHECKING

import pandas as pd

from src.infrastructure.reporting.sazon.cleaner import clean_date, clean_money, normalize_text

if TYPE_CHECKING:
    from io import BytesIO

# Column headers as they appear in DIAN's "Consulta de documentos electrónicos
# recibidos" Excel export (portal web, not an API — see plan). Kept as a
# dict of standard-name -> accepted variants, same alias-dict shape as
# `sazon/cleaner.py::SALES_ALIASES`, so a future column rename on DIAN's side
# is a one-line addition here, not a rewrite.
DIAN_ALIASES: dict[str, list[str]] = {
    "CUFE": ["CUFE", "CUDE", "CODIGO UNICO"],
    "NIT_EMISOR": ["NIT EMISOR", "NIT DEL EMISOR", "IDENTIFICACION EMISOR", "NIT", "DOCUMENTO EMISOR"],
    "RAZON_SOCIAL_EMISOR": ["RAZON SOCIAL EMISOR", "NOMBRE EMISOR", "RAZON SOCIAL", "EMISOR"],
    "FECHA_EMISION": ["FECHA EMISION", "FECHA DE EMISION", "FECHA"],
    "CONCEPTO": ["CONCEPTO", "DESCRIPCION", "DETALLE", "OBSERVACIONES"],
    "SUBTOTAL": ["SUBTOTAL", "VALOR ANTES DE IMPUESTOS", "BASE"],
    "IVA": ["IVA", "VALOR IMPUESTO", "IMPUESTO"],
    "TOTAL": ["TOTAL", "VALOR TOTAL", "VALOR TOTAL A PAGAR", "TOTAL FACTURA"],
}

REQUIRED_COLUMNS = ["CUFE", "NIT_EMISOR", "TOTAL"]


def normalize_nit(value: object) -> str:
    """Canonical NIT form used for both dedupe/matching and `Client.nit` comparisons.

    DIAN exports NITs with the verification digit attached (e.g. "900.123.456-7");
    `Client.nit` is stored without it. Drop the check digit (if present as a
    trailing "-N") and any punctuation, keeping only the base NIT digits.
    """
    text = str(value or "").strip()
    match = re.match(r"^([\d.\s]+)-\s*\d$", text)
    if match:
        text = match.group(1)
    return re.sub(r"[^0-9]", "", text)


def _rename_with_aliases(df: pd.DataFrame) -> pd.DataFrame:
    normalized_columns = {normalize_text(col): col for col in df.columns}
    rename_map: dict[str, str] = {}
    for standard, options in DIAN_ALIASES.items():
        for option in options:
            normalized = normalize_text(option)
            if normalized in normalized_columns:
                rename_map[normalized_columns[normalized]] = standard
                break
    return df.rename(columns=rename_map)


def load_dian_invoices(file: BytesIO) -> tuple[pd.DataFrame, list[str]]:
    """Parse the DIAN "documentos recibidos" Excel into a normalized DataFrame.

    Returns one row per invoice with standardized columns (CUFE, NIT_EMISOR,
    RAZON_SOCIAL_EMISOR, FECHA_EMISION, CONCEPTO, SUBTOTAL, IVA, TOTAL).
    Raises ValueError (surfaced into `InvoiceImportBatch.error_message`) if
    the sheet doesn't contain a CUFE column — that's the one non-negotiable
    column since it's the dedupe key.
    """
    messages: list[str] = []
    try:
        raw_df = pd.read_excel(file, dtype=object, engine="openpyxl")
    except Exception as exc:
        raise ValueError("No fue posible leer el archivo Excel de la DIAN.") from exc

    raw_df = raw_df.dropna(how="all").dropna(axis=1, how="all")
    raw_df.columns = [str(col).strip() for col in raw_df.columns]
    df = _rename_with_aliases(raw_df)

    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(
            "El Excel de la DIAN no tiene las columnas esperadas "
            f"({', '.join(missing)}). Verifica que sea el listado de documentos electrónicos recibidos."
        )

    for column in DIAN_ALIASES:
        if column not in df.columns:
            df[column] = "" if column not in {"SUBTOTAL", "IVA", "TOTAL"} else 0

    for column in ("SUBTOTAL", "IVA", "TOTAL"):
        df[column] = df[column].map(clean_money)

    df["FECHA_EMISION"] = df["FECHA_EMISION"].map(lambda v: clean_date(v))
    df = df.dropna(subset=["CUFE", "NIT_EMISOR"])
    df = df[df["CUFE"].astype(str).str.strip() != ""]
    if df.empty:
        raise ValueError("El archivo no contiene filas con CUFE válido.")

    df["CUFE"] = df["CUFE"].astype(str).str.strip()
    df["NIT_EMISOR"] = df["NIT_EMISOR"].map(normalize_nit)
    df["RAZON_SOCIAL_EMISOR"] = df["RAZON_SOCIAL_EMISOR"].fillna("").astype(str).str.strip()
    df["CONCEPTO"] = df["CONCEPTO"].fillna("").astype(str).str.strip()

    if df["SUBTOTAL"].sum() == 0 and df["TOTAL"].sum() > 0:
        df["SUBTOTAL"] = df["TOTAL"] - df["IVA"]

    messages.append(f"{len(df)} filas con CUFE leídas del archivo DIAN.")
    return df.reset_index(drop=True), messages


def row_issue_date(value: object) -> date:
    if isinstance(value, pd.Timestamp):
        return value.date()  # type: ignore[no-any-return]
    if isinstance(value, date):
        return value
    return date.today()
