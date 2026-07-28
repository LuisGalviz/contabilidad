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
    "TIPO_DOCUMENTO": ["TIPO DE DOCUMENTO", "TIPO DOCUMENTO"],
    "CUFE": ["CUFE/CUDE", "CUFE", "CUDE", "CODIGO UNICO"],
    "NIT_EMISOR": ["NIT EMISOR", "NIT DEL EMISOR", "IDENTIFICACION EMISOR", "NIT", "DOCUMENTO EMISOR"],
    "RAZON_SOCIAL_EMISOR": ["RAZON SOCIAL EMISOR", "NOMBRE EMISOR", "RAZON SOCIAL", "EMISOR"],
    "FECHA_EMISION": ["FECHA EMISION", "FECHA DE EMISION", "FECHA"],
    "CONCEPTO": ["CONCEPTO", "DESCRIPCION", "DETALLE", "OBSERVACIONES"],
    # Prefijo y número de la factura del proveedor: Siigo los exige en
    # `provider_invoice` al registrar una factura de compra (POST /v1/purchases).
    "PREFIJO": ["PREFIJO", "PREFIJO DOCUMENTO", "SERIE"],
    "NUMERO": ["NUMERO DOCUMENTO", "NUMERO", "NUMERO DE DOCUMENTO", "FOLIO", "NUMERO FACTURA", "NRO DOCUMENTO"],
    "SUBTOTAL": ["SUBTOTAL", "VALOR ANTES DE IMPUESTOS", "BASE"],
    "IVA": ["IVA", "VALOR IMPUESTO", "IMPUESTO"],
    "TOTAL": ["TOTAL", "VALOR TOTAL", "VALOR TOTAL A PAGAR", "TOTAL FACTURA"],
}

REQUIRED_COLUMNS = ["CUFE", "NIT_EMISOR", "TOTAL"]


def is_credit_note(document_type: object) -> bool:
    """DIAN's `Tipo de documento` reads 'Nota de crédito electrónica' for credit
    notes (vs 'Factura electrónica'). Credit notes reverse the purchase, so
    causación must invert their accounting entry."""
    return "CREDITO" in normalize_text(document_type)


def clean_document_part(value: object) -> str:
    """Prefijo o número de la factura tal como los pide Siigo.

    Pandas convierte los números en float ("1234.0"), y el prefijo a veces
    viene pegado al número ("FE-1234"); acá solo se limpia el valor, no se
    intenta separarlos.
    """
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    text = str(value).strip()
    if text.endswith(".0") and text[:-2].isdigit():
        text = text[:-2]
    return text[:50]


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
    df["PREFIJO"] = df["PREFIJO"].map(clean_document_part)
    df["NUMERO"] = df["NUMERO"].map(clean_document_part)

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
