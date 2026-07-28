"""Lector del Excel "Listado de cuentas contables" que exporta Siigo Nube.

Siigo **no expone el catálogo de cuentas por API** (revisado contra su
documentación pública: hay `/v1/products`, `/customers`, `/invoices`,
`/purchases`, `/journals`… pero ninguna de plan de cuentas; ojo con
`/v1/account-groups`, que son grupos de inventario, no el PUC). La ruta viable
es el Excel que el contador descarga desde
`Reportes → Contables → Contables → Listado de cuentas contables → Descargar Excel`.

Mismo enfoque que `dian/cleaner.py`: un diccionario de alias por columna, para
que un cambio de encabezado en Siigo sea una línea aquí y no una reescritura.
Los alias son una apuesta razonable hasta tener un archivo real de muestra.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd

from src.infrastructure.reporting.sazon.cleaner import normalize_text

if TYPE_CHECKING:
    from io import BytesIO

SIIGO_ALIASES: dict[str, list[str]] = {
    "CODIGO": ["CODIGO", "CODIGO CUENTA", "CUENTA", "CODIGO CONTABLE", "COD", "CODIGO DE CUENTA"],
    "NOMBRE": ["NOMBRE", "NOMBRE CUENTA", "DESCRIPCION", "NOMBRE DE LA CUENTA", "DESCRIPCION CUENTA"],
    "CLASE": ["CLASE", "TIPO", "NATURALEZA", "CLASE CUENTA", "GRUPO"],
    "ACTIVA": ["ACTIVO", "ACTIVA", "ESTADO", "HABILITADA"],
    "CENTRO_COSTO": ["CENTRO DE COSTO", "EXIGE CENTRO DE COSTO", "MANEJA CENTRO DE COSTO", "CENTRO COSTO"],
    # Siigo distingue cuentas de agrupación de las que admiten movimiento.
    "NIVEL": ["NIVEL AGRUPACION", "NIVEL DE AGRUPACION", "NIVEL", "TIPO DE CUENTA"],
}

REQUIRED_COLUMNS = ["CODIGO", "NOMBRE"]

# Valor de `Nivel agrupación` que marca las cuentas donde sí se puede registrar
# movimiento. Las demás son niveles de agrupación del árbol contable.
TRANSACTIONAL_LEVEL = "TRANSACCIONAL"

# Primer dígito del código PUC -> clase, según el decreto 2650. Se usa cuando el
# archivo no trae columna de clase, que es lo normal: en el PUC la clase está
# codificada en el propio número de cuenta.
CLASS_BY_FIRST_DIGIT: dict[str, str] = {
    "1": "activo",
    "2": "pasivo",
    "3": "patrimonio",
    "4": "ingreso",
    "5": "gasto",
    "6": "costo",
    "7": "costo",
    "8": "orden",
    "9": "orden",
}

# Siigo nombra las clases distinto al decreto (plurales, "Costos de venta",
# "Cuentas de orden acreedoras"…), así que no se pueden comparar directo.
SIIGO_CLASS_LABELS: dict[str, str] = {
    "ACTIVO": "activo",
    "PASIVO": "pasivo",
    "PATRIMONIO": "patrimonio",
    "INGRESO": "ingreso",
    "INGRESOS": "ingreso",
    "GASTO": "gasto",
    "GASTOS": "gasto",
}

VALID_CLASSES = {"activo", "pasivo", "patrimonio", "ingreso", "gasto", "costo", "orden"}

_TRUTHY = {"SI", "S", "TRUE", "1", "X", "ACTIVA", "ACTIVO", "HABILITADA"}
_FALSY = {"NO", "N", "FALSE", "0", "INACTIVA", "INACTIVO", "ANULADA"}


def _cell_text(value: object) -> str:
    """Texto de una celda, tratando los vacíos de pandas como cadena vacía.

    `str(float("nan"))` es `"nan"`, que colándose como nombre de cuenta crearía
    cuentas fantasma llamadas "nan".
    """
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    return str(value).strip()


def normalize_account_code(value: object) -> str:
    """Deja solo dígitos. Siigo exporta códigos con puntos o guiones según la
    configuración de la empresa ("5135-05", "1.1.05"), y pandas convierte los
    numéricos en float ("5135.0")."""
    text = _cell_text(value)
    if text.endswith(".0") and text[:-2].isdigit():
        text = text[:-2]
    return "".join(ch for ch in text if ch.isdigit())


def _parse_bool(value: object, default: bool) -> bool:
    text = normalize_text(value)
    if not text:
        return default
    if text in _TRUTHY:
        return True
    if text in _FALSY:
        return False
    return default


def resolve_account_class(code: str, raw_class: object) -> str:
    """Traduce la clase declarada por Siigo; si no se reconoce, se deduce del
    primer dígito del código, que en el PUC ya codifica la clase."""
    declared = normalize_text(raw_class)
    if declared in SIIGO_CLASS_LABELS:
        return SIIGO_CLASS_LABELS[declared]
    # "Costos de venta", "Costos de producción o de operación"…
    if declared.startswith("COSTO"):
        return "costo"
    if declared.startswith("CUENTAS DE ORDEN"):
        return "orden"
    if declared.lower() in VALID_CLASSES:
        return declared.lower()
    return CLASS_BY_FIRST_DIGIT.get(code[:1], "gasto")


def _rename_with_aliases(df: pd.DataFrame) -> pd.DataFrame:
    normalized_columns = {normalize_text(col): col for col in df.columns}
    rename_map: dict[str, str] = {}
    for standard, options in SIIGO_ALIASES.items():
        for option in options:
            normalized = normalize_text(option)
            if normalized in normalized_columns:
                rename_map[normalized_columns[normalized]] = standard
                break
    return df.rename(columns=rename_map)


def _find_header_row(raw: pd.DataFrame) -> int | None:
    """Los reportes de Siigo suelen traer título y filtros antes de la tabla, así
    que la primera fila del archivo no es el encabezado. Se busca la primera fila
    que contenga las columnas obligatorias."""
    wanted = {normalize_text(alias) for column in REQUIRED_COLUMNS for alias in SIIGO_ALIASES[column]}
    for index in range(min(len(raw), 30)):
        values = {normalize_text(v) for v in raw.iloc[index].tolist()}
        if len(values & wanted) >= len(REQUIRED_COLUMNS):
            return index
    return None


def load_siigo_chart_of_accounts(file: BytesIO) -> tuple[list[dict[str, object]], list[str]]:
    """Devuelve las cuentas del archivo y los avisos para mostrarle al contador.

    Lanza ValueError si el archivo no parece un listado de cuentas contables —
    mejor rechazarlo que importar basura sobre el plan de una empresa.
    """
    messages: list[str] = []
    try:
        raw = pd.read_excel(file, dtype=object, header=None, engine="openpyxl")
    except Exception as exc:
        raise ValueError("No fue posible leer el archivo Excel de Siigo.") from exc

    raw = raw.dropna(how="all").dropna(axis=1, how="all")
    if raw.empty:
        raise ValueError("El archivo está vacío.")

    header_row = _find_header_row(raw)
    if header_row is None:
        raise ValueError(
            "No se encontraron las columnas de código y nombre de cuenta. "
            "Verifica que sea el 'Listado de cuentas contables' exportado desde Siigo."
        )

    df = raw.iloc[header_row + 1 :].copy()
    df.columns = [str(c).strip() for c in raw.iloc[header_row].tolist()]
    df = _rename_with_aliases(df)

    missing = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    if missing:
        raise ValueError(f"Al archivo le faltan columnas obligatorias: {', '.join(missing)}.")

    for column in SIIGO_ALIASES:
        if column not in df.columns:
            df[column] = None

    # Si el archivo declara el nivel, solo las transaccionales sirven. Cuando la
    # columna no viene (otra versión del reporte) no hay forma de distinguirlas
    # y se importan todas.
    has_level_column = df["NIVEL"].notna().any()

    accounts: list[dict[str, object]] = []
    seen: set[str] = set()
    skipped_without_code = 0
    skipped_group_accounts = 0
    duplicates = 0

    for _, row in df.iterrows():
        code = normalize_account_code(row["CODIGO"])
        name = _cell_text(row["NOMBRE"])
        if not code or not name:
            skipped_without_code += 1
            continue
        # Las cuentas de agrupación no admiten movimiento: Siigo rechaza el
        # comprobante entero si se causa contra una de ellas, así que no deben
        # llegar siquiera al selector de clasificación.
        if has_level_column and normalize_text(row["NIVEL"]) != TRANSACTIONAL_LEVEL:
            skipped_group_accounts += 1
            continue
        # `puc_accounts.code` es VARCHAR(10); un código más largo indica que la
        # columna leída no es la de código.
        if len(code) > 10:
            skipped_without_code += 1
            continue
        if code in seen:
            duplicates += 1
            continue
        seen.add(code)

        accounts.append(
            {
                "code": code,
                "name": name[:200],
                "account_class": resolve_account_class(code, row["CLASE"]),
                "requires_cost_center": _parse_bool(row["CENTRO_COSTO"], False),
                "is_active": _parse_bool(row["ACTIVA"], True),
            }
        )

    if not accounts:
        raise ValueError(
            "El archivo no contiene ninguna cuenta de movimiento con código y nombre válidos."
        )

    messages.append(f"{len(accounts)} cuentas de movimiento leídas del archivo de Siigo.")
    if skipped_group_accounts:
        messages.append(
            f"{skipped_group_accounts} cuentas de agrupación omitidas: no admiten movimiento contable."
        )
    if skipped_without_code:
        messages.append(f"{skipped_without_code} filas ignoradas por no tener código o nombre válido.")
    if duplicates:
        messages.append(f"{duplicates} códigos repetidos en el archivo; se conservó la primera aparición.")

    return accounts, messages
