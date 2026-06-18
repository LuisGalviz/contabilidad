from __future__ import annotations

import re
import unicodedata
from io import BytesIO
from typing import Iterable

import pandas as pd


MONTHS_ES = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
    5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
    9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre",
}

MONTH_ALIASES = {
    "ene": 1, "enero": 1, "feb": 2, "febrero": 2, "mar": 3, "marzo": 3,
    "abr": 4, "abril": 4, "may": 5, "mayo": 5, "jun": 6, "junio": 6,
    "jul": 7, "julio": 7, "ago": 8, "agosto": 8, "sep": 9, "sept": 9,
    "septiembre": 9, "oct": 10, "octubre": 10, "nov": 11, "noviembre": 11,
    "dic": 12, "diciembre": 12,
}

SALES_ALIASES = {
    "FECHA": ["FECHA", "DATE"],
    "CLIENTE": ["CLIENTE", "NOMBRE CLIENTE", "CUSTOMER"],
    "ID CLIENTE": ["ID CLIENTE", "IDENTIFICACION", "NIT", "DOCUMENTO"],
    "NUMERO FACTURA": ["NUMERO FACTURA", "N FACTURA", "FACTURA", "NUM FACTURA", "NO FACTURA"],
    "SUBTOTAL": ["SUBTOTAL", "SUB TOTAL"],
    "IVA": ["IVA", "IMPUESTO"],
    "TOTAL": ["TOTAL", "VALOR TOTAL"],
    "DESCUENTO": ["DES- CUENTO", "DESCUENTO", "DESCUENTOS"],
    "PROPINA": ["PROPINA", "TIP", "SERVICIO"],
    "FORMA DE PAGO": ["FORMA DE PAGO", "FORMA_PAGO", "MEDIO DE PAGO", "PAGO"],
    "TARJETA": ["TARJETA", "TARJETAS", "DATAFONO", "DATÁFONO"],
    "EFECTIVO": ["EFECTIVO", "CASH"],
    "TRANSFERENCIA": ["TRANSFERENCIA", "TRANSFE RENCIA", "TRANSFE", "TRANSFER"],
    "CREDITO": ["CREDITO", "CRÉDITO", "CARTERA"],
    "CORTESIA": ["CORTESIA", "CORTESÍA", "CORTESIAS", "CORTESÍAS"],
    "PROPINA TARJETA": ["PROPINA TARJETA", "TIP TARJETA"],
    "PROPINA RESTO": ["PROPINA RESTO", "PROPINA EFECTIVO", "TIP EFECTIVO"],
    "VALOR FACTURA": ["VALOR FACTURA", "VALOR FACT", "TOTAL FACTURA", "TOTAL"],
    "VALOR NETO": ["VALOR NETO", "NETO", "VALOR RECIBIDO", "RECIBIDO"],
    "ATENDIO": ["ATENDIO", "ATENDIÓ", "VENDEDOR", "Vendedor", "MESERO", "CAJERO"],
}

NUMERIC_SALES_COLUMNS = [
    "SUBTOTAL", "IVA", "TOTAL", "DESCUENTO", "PROPINA", "TARJETA",
    "EFECTIVO", "TRANSFERENCIA", "CREDITO", "CORTESIA", "CORTESIAS_VALOR",
    "PROPINA TARJETA", "PROPINA RESTO", "VALOR FACTURA", "VALOR NETO",
]


def normalize_text(value: object) -> str:
    text = "" if pd.isna(value) else str(value)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^A-Za-z0-9]+", " ", text.upper()).strip()
    return re.sub(r"\s+", " ", text)


def normalize_month(value: object) -> int | None:
    text = normalize_text(value).lower()
    if not text:
        return None
    for token in re.split(r"\s+", text):
        if token in MONTH_ALIASES:
            return MONTH_ALIASES[token]
    return MONTH_ALIASES.get(text)


def clean_money(value: object) -> float:
    if pd.isna(value) or value == "":
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text or normalize_text(text) in {"NAN", "NONE", "NULL"}:
        return 0.0
    negative = bool(re.search(r"^\(.*\)$", text)) or text.startswith("-")
    text = re.sub(r"[^0-9,.\-]", "", text).replace("-", "")
    if "," in text and "." in text:
        text = text.replace(".", "").replace(",", ".") if text.rfind(",") > text.rfind(".") else text.replace(",", "")
    elif "," in text:
        parts = text.split(",")
        text = "".join(parts) if len(parts[-1]) == 3 else text.replace(",", ".")
    elif "." in text:
        parts = text.split(".")
        if len(parts) > 1 and all(len(p) == 3 for p in parts[1:]):
            text = "".join(parts)
    try:
        number = float(text)
    except ValueError:
        return 0.0
    return -number if negative else number


def _infer_expected_months_from_name(name: str | None) -> set[int]:
    if not name:
        return set()
    found: list[int] = []
    for token in re.split(r"[^A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+", str(name)):
        month = normalize_month(token)
        if month and month not in found:
            found.append(month)
    if len(found) >= 2:
        start, end = found[0], found[-1]
        if start <= end:
            return set(range(start, end + 1))
    return set(found)


def _swap_month_day(timestamp: pd.Timestamp) -> pd.Timestamp | None:
    try:
        return pd.Timestamp(year=timestamp.year, month=timestamp.day, day=timestamp.month)
    except ValueError:
        return None


def clean_date(value: object, expected_months: set[int] | None = None) -> pd.Timestamp | None:
    expected_months = expected_months or set()
    if pd.isna(value) or value == "":
        return None
    if isinstance(value, pd.Timestamp):
        parsed = value
    elif hasattr(value, "year") and hasattr(value, "month") and hasattr(value, "day"):
        parsed = pd.Timestamp(value)
    elif isinstance(value, (int, float)):
        parsed = pd.to_datetime(value, unit="D", origin="1899-12-30", errors="coerce")
    else:
        text = str(value).strip()
        match = re.match(r"^(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})$", text)
        if match:
            first, second, year = [int(p) for p in match.groups()]
            year = 2000 + year if year < 100 else year
            candidates = []
            for month, day in [(first, second), (second, first)]:
                try:
                    candidates.append(pd.Timestamp(year=year, month=month, day=day))
                except ValueError:
                    continue
            expected = [c for c in candidates if c.month in expected_months]
            if expected:
                return expected[0]
        parsed = pd.to_datetime(value, errors="coerce", dayfirst=True)

    if pd.isna(parsed):
        return None
    if expected_months and parsed.month not in expected_months:
        swapped = _swap_month_day(parsed)
        if swapped is not None and swapped.month in expected_months:
            return swapped
    return parsed


def _is_empty(df: pd.DataFrame) -> bool:
    return df is None or df.dropna(how="all").empty


def _drop_empty_frame_parts(df: pd.DataFrame) -> pd.DataFrame:
    df = df.dropna(how="all").dropna(axis=1, how="all")
    df.columns = [str(col).strip() for col in df.columns]
    return df


def _best_header_frame(raw_df: pd.DataFrame) -> pd.DataFrame:
    raw_df = raw_df.dropna(how="all").dropna(axis=1, how="all")
    if raw_df.empty:
        return pd.DataFrame()
    known = {alias for aliases in SALES_ALIASES.values() for alias in aliases}
    best_idx, best_score = 0, -1
    for idx in range(min(12, len(raw_df))):
        row_values = [normalize_text(v) for v in raw_df.iloc[idx].tolist()]
        score = sum(any(v == normalize_text(a) for a in known) for v in row_values)
        if score > best_score:
            best_idx, best_score = idx, score
    if best_score >= 2:
        df = raw_df.iloc[best_idx + 1:].copy()
        df.columns = raw_df.iloc[best_idx].fillna("").astype(str).tolist()
    else:
        df = raw_df.copy()
    return _drop_empty_frame_parts(df)


def _rename_with_aliases(df: pd.DataFrame, aliases: dict[str, Iterable[str]]) -> pd.DataFrame:
    normalized_columns = {normalize_text(col): col for col in df.columns}
    rename_map = {}
    for standard, options in aliases.items():
        for option in options:
            normalized = normalize_text(option)
            if normalized in normalized_columns:
                rename_map[normalized_columns[normalized]] = standard
                break
    return df.rename(columns=rename_map)


def _score_sales_sheet(df: pd.DataFrame) -> int:
    names = {normalize_text(col) for col in df.columns}
    important = ["FECHA", "TOTAL", "VALOR NETO", "FORMA DE PAGO", "CLIENTE", "ATENDIO", "PROPINA"]
    return sum(1 for item in important if any(normalize_text(a) in names for a in SALES_ALIASES.get(item, [item])))


def load_sales_data(file: BytesIO) -> tuple[pd.DataFrame, list[str]]:
    messages: list[str] = []
    try:
        sheets = pd.read_excel(file, sheet_name=None, dtype=object, engine="openpyxl")
    except Exception as exc:
        raise ValueError("No fue posible leer el archivo Excel de ventas.") from exc

    expected_months = _infer_expected_months_from_name(getattr(file, "name", ""))
    preferred = {"RESUMEN", "RESUMEN 2", "ENERO", "FEBRERO", "MARZO", "ABRIL", "MAYO"}
    candidates = []
    for name, raw_df in sheets.items():
        if _is_empty(raw_df):
            continue
        df = _rename_with_aliases(_best_header_frame(raw_df), SALES_ALIASES)
        score = _score_sales_sheet(df)
        name_score = 3 if normalize_text(name) in preferred else 0
        if score >= 2:
            candidates.append((score + name_score, name, df))

    if not candidates:
        raise ValueError("No se encontró una hoja de ventas con columnas reconocibles.")

    candidates.sort(key=lambda x: x[0], reverse=True)
    df = candidates[0][2].copy()
    messages.append(f"Ventas leídas desde la hoja '{candidates[0][1]}'.")

    for column in SALES_ALIASES:
        if column not in df.columns:
            df[column] = "" if column in {"FECHA", "CLIENTE", "NUMERO FACTURA", "FORMA DE PAGO", "ATENDIO", "ID CLIENTE"} else 0

    for column in NUMERIC_SALES_COLUMNS:
        if column in df.columns:
            df[column] = df[column].map(clean_money)

    df["FECHA"] = df["FECHA"].map(lambda v: clean_date(v, expected_months))
    df = df.dropna(subset=["FECHA"])
    if df.empty:
        raise ValueError("El archivo de ventas no tiene fechas válidas.")

    df["NUMERO_MES"] = df["FECHA"].dt.month
    df["MES"] = df["NUMERO_MES"].map(MONTHS_ES)
    df["CLIENTE"] = df["CLIENTE"].fillna("Sin cliente").replace("", "Sin cliente")
    df["ATENDIO"] = df["ATENDIO"].fillna("Sin vendedor").replace("", "Sin vendedor")
    df["FORMA DE PAGO"] = df["FORMA DE PAGO"].fillna("Sin forma de pago").replace("", "Sin forma de pago")
    df["NUMERO FACTURA"] = df["NUMERO FACTURA"].fillna("").astype(str)

    if df["VALOR FACTURA"].sum() == 0 and df["TOTAL"].sum() > 0:
        df["VALOR FACTURA"] = df["TOTAL"]
    if df["VALOR NETO"].sum() == 0:
        df["VALOR NETO"] = df["VALOR FACTURA"] - df["PROPINA"]

    df["CORTESIAS_VALOR"] = df["DESCUENTO"]
    if df["CORTESIAS_VALOR"].sum() == 0 and df["CORTESIA"].sum() > 0:
        df["CORTESIAS_VALOR"] = df["CORTESIA"]

    return df.reset_index(drop=True), messages


def load_expenses_data(file: BytesIO) -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    messages: list[str] = []
    try:
        sheets = pd.read_excel(file, sheet_name=None, dtype=object, engine="openpyxl")
    except Exception as exc:
        raise ValueError("No fue posible leer el archivo Excel de gastos.") from exc

    def _find_amount_cols(df: pd.DataFrame) -> list[str]:
        markers = ["VALOR", "GASTO", "TOTAL", "AMOUNT", "CANTIDAD", "PAGO", "DEBITO"]
        return [c for c in df.columns if any(m in normalize_text(c) for m in markers)]

    summary_name = next((n for n in sheets if normalize_text(n) == "TENDENCIAS ANUALES"), None)
    monthly_rows: list[pd.DataFrame] = []
    detail_rows: list[dict] = []

    if summary_name and not _is_empty(sheets[summary_name]):
        raw = sheets[summary_name]
        df = _drop_empty_frame_parts(_best_header_frame(raw))
        month_col = next((c for c in df.columns if "MES" in normalize_text(c) or normalize_month(c)), None)
        if month_col is None and df.columns.any() and df[df.columns[0]].map(normalize_month).notna().any():
            month_col = df.columns[0]
        if month_col:
            amount_cols = [c for c in _find_amount_cols(df) if c != month_col]
            if not amount_cols:
                amount_cols = [c for c in df.columns if c != month_col]
            rows = []
            for _, row in df.iterrows():
                month = normalize_month(row.get(month_col))
                if month is None:
                    continue
                total = sum(clean_money(row.get(c)) for c in amount_cols)
                rows.append({"NUMERO_MES": month, "MES": MONTHS_ES[month], "GASTOS": total})
            if rows:
                monthly_rows.append(pd.DataFrame(rows))
                messages.append("Gastos leídos desde la hoja 'Tendencias anuales'.")

    if not monthly_rows:
        for name, raw_df in sheets.items():
            month = normalize_month(name)
            if month is None or _is_empty(raw_df):
                continue
            df = _drop_empty_frame_parts(_best_header_frame(raw_df))
            if df.empty:
                continue
            amount_cols = _find_amount_cols(df) or list(df.columns[-1:])
            desc_col = next((c for c in df.columns if any(t in normalize_text(c) for t in ["PROVEEDOR", "DESCRIPCION", "CONCEPTO"])), None)
            total = 0.0
            for _, row in df.iterrows():
                amount = sum(clean_money(row.get(c)) for c in amount_cols)
                if amount == 0:
                    continue
                total += amount
                detail_rows.append({
                    "NUMERO_MES": month, "MES": MONTHS_ES[month],
                    "PROVEEDOR_CONCEPTO": str(row.get(desc_col, "Sin descripción") or "Sin descripción"),
                    "GASTOS": amount,
                })
            monthly_rows.append(pd.DataFrame([{"NUMERO_MES": month, "MES": MONTHS_ES[month], "GASTOS": total}]))
        messages.append("Gastos calculados desde hojas mensuales.")

    if monthly_rows:
        monthly = pd.concat(monthly_rows, ignore_index=True)
        monthly = monthly.groupby(["NUMERO_MES", "MES"], as_index=False)["GASTOS"].sum()
    else:
        monthly = pd.DataFrame(columns=["NUMERO_MES", "MES", "GASTOS"])
        messages.append("No se encontraron gastos con información numérica.")

    details = pd.DataFrame(detail_rows, columns=["NUMERO_MES", "MES", "PROVEEDOR_CONCEPTO", "GASTOS"]) if detail_rows else pd.DataFrame(columns=["NUMERO_MES", "MES", "PROVEEDOR_CONCEPTO", "GASTOS"])
    return monthly.sort_values("NUMERO_MES").reset_index(drop=True), details, messages
