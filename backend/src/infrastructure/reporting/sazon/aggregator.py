from __future__ import annotations

import pandas as pd


def build_sazon_tables(
    sales: pd.DataFrame,
    expenses: pd.DataFrame,
    expense_details: pd.DataFrame,
) -> dict[str, pd.DataFrame]:
    """Transform raw cleaned dataframes into report-ready tables."""
    sales = sales.copy()
    sales["VENTAS_BRUTAS"] = sales["SUBTOTAL"]
    if sales["VENTAS_BRUTAS"].sum() == 0:
        sales["VENTAS_BRUTAS"] = sales["TOTAL"]
    if sales["VENTAS_BRUTAS"].sum() == 0:
        sales["VENTAS_BRUTAS"] = sales["VALOR FACTURA"] + sales["CORTESIAS_VALOR"]
    sales["VENTAS_NETAS"] = sales["VENTAS_BRUTAS"] - sales["CORTESIAS_VALOR"]
    sales["RECAUDO_REAL"] = sales["EFECTIVO"] + sales["TARJETA"] + sales["TRANSFERENCIA"]
    sales["DIFERENCIA_CONTROL"] = sales["VENTAS_NETAS"] + sales["PROPINA"] - sales["RECAUDO_REAL"]

    monthly_sales = (
        sales.groupby(["NUMERO_MES", "MES"], as_index=False)
        .agg(**{
            "Ventas brutas": ("VENTAS_BRUTAS", "sum"),
            "Cortesías": ("CORTESIAS_VALOR", "sum"),
            "Ventas netas": ("VENTAS_NETAS", "sum"),
            "Ventas": ("VENTAS_NETAS", "sum"),
            "Recaudo real": ("RECAUDO_REAL", "sum"),
            "Diferencia de control": ("DIFERENCIA_CONTROL", "sum"),
            "Valor neto recibido": ("VALOR NETO", "sum"),
            "Propinas": ("PROPINA", "sum"),
            "Número de facturas": ("NUMERO FACTURA", "nunique"),
        })
        .rename(columns={"MES": "Mes"})
    )
    monthly = monthly_sales.merge(
        expenses.rename(columns={"MES": "Mes", "GASTOS": "Gastos"}),
        on=["NUMERO_MES", "Mes"],
        how="outer",
    ).fillna(0).sort_values("NUMERO_MES")
    monthly["Utilidad estimada"] = monthly["Ventas"] - monthly["Gastos"]
    monthly["Margen estimado"] = (monthly["Utilidad estimada"] / monthly["Ventas"].replace(0, pd.NA)).fillna(0)
    monthly["Ticket promedio"] = (monthly["Ventas"] / monthly["Número de facturas"].replace(0, pd.NA)).fillna(0)

    gross_sales = sales["VENTAS_BRUTAS"].sum()
    real_collected = sales["RECAUDO_REAL"].sum()
    payment_values = {
        "Efectivo": sales["EFECTIVO"].sum(),
        "Transferencia": sales["TRANSFERENCIA"].sum(),
        "Tarjeta": sales["TARJETA"].sum(),
        "Cortesías / descuentos otorgados": sales["CORTESIAS_VALOR"].sum(),
    }
    payments = pd.DataFrame({"Forma de pago": list(payment_values.keys()), "Valor": list(payment_values.values())})
    payments["Participación %"] = payments.apply(
        lambda row: row["Valor"] / gross_sales if "Cortesías" in str(row["Forma de pago"]) and gross_sales else row["Valor"] / real_collected if real_collected else 0,
        axis=1,
    )
    payments = payments.sort_values("Valor", ascending=False)

    sellers = (
        sales.groupby("ATENDIO", as_index=False)
        .agg(**{
            "Total ventas": ("VALOR FACTURA", "sum"),
            "Total valor neto": ("VALOR NETO", "sum"),
            "Total propinas": ("PROPINA", "sum"),
            "Total cortesías": ("CORTESIAS_VALOR", "sum"),
            "Número de facturas": ("NUMERO FACTURA", "nunique"),
        })
        .rename(columns={"ATENDIO": "Vendedor"})
    )
    sellers["Ticket promedio"] = (sellers["Total ventas"] / sellers["Número de facturas"].replace(0, pd.NA)).fillna(0)
    sellers = sellers.sort_values("Total ventas", ascending=False)

    client_key = "CLIENTE" if sales["CLIENTE"].nunique() > 1 else "ID CLIENTE"
    clients = (
        sales.groupby(client_key, as_index=False)
        .agg(**{
            "Número de compras": ("NUMERO FACTURA", "nunique"),
            "Total vendido": ("VALOR FACTURA", "sum"),
            "Última fecha de compra": ("FECHA", "max"),
        })
        .rename(columns={client_key: "Cliente"})
    )
    clients["Ticket promedio"] = (clients["Total vendido"] / clients["Número de compras"].replace(0, pd.NA)).fillna(0)
    clients = clients.sort_values("Total vendido", ascending=False)

    tips = sales.groupby(["NUMERO_MES", "MES"], as_index=False)["PROPINA"].sum().rename(columns={"MES": "Mes", "PROPINA": "Propinas"})

    provider_summary = pd.DataFrame()
    if not expense_details.empty and "PROVEEDOR_CONCEPTO" in expense_details.columns:
        provider_summary = (
            expense_details.groupby("PROVEEDOR_CONCEPTO", as_index=False)["GASTOS"].sum()
            .rename(columns={"PROVEEDOR_CONCEPTO": "Proveedor o concepto", "GASTOS": "Gastos"})
            .sort_values("Gastos", ascending=False)
        )

    operating = monthly[["Mes", "Ventas", "Gastos", "Utilidad estimada", "Margen estimado"]].copy()

    return {
        "monthly": monthly,
        "payments": payments,
        "sellers": sellers,
        "clients": clients,
        "tips": tips,
        "provider_summary": provider_summary,
        "operating": operating,
        "sales": sales,
        "expenses": expenses,
    }
