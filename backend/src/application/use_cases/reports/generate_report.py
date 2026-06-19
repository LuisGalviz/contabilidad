from __future__ import annotations

import asyncio
import math
import uuid
from dataclasses import dataclass
from io import BytesIO
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any

import structlog

from src.domain.entities.report import Report, ReportFile, ReportStatus, ReportType
from src.domain.repositories.report_repository import ReportRepository
from src.infrastructure.storage.minio_service import upload_bytes

logger = structlog.get_logger()


def _df_to_records(df: Any, max_rows: int | None = None) -> list[dict[str, Any]]:
    """Convert a pandas DataFrame to a JSON-serializable list of dicts."""
    try:
        import pandas as pd
        if df is None or (hasattr(df, "empty") and df.empty):
            return []
        df = df.copy()
        if max_rows:
            df = df.head(max_rows)
        for col in df.columns:
            if pd.api.types.is_datetime64_any_dtype(df[col]):
                df[col] = df[col].dt.strftime("%Y-%m-%d")
            elif df[col].dtype == object:
                df[col] = df[col].astype(str)
        records = df.to_dict(orient="records")
        # Replace NaN/Inf with None so JSON serialization works
        clean = []
        for row in records:
            clean.append({
                k: (None if isinstance(v, float) and (math.isnan(v) or math.isinf(v)) else v)
                for k, v in row.items()
            })
        return clean
    except Exception:
        return []


@dataclass
class GenerateReportUseCase:
    report_repo: ReportRepository

    async def execute(self, report: Report, raw_files: list[tuple[str, bytes]]) -> None:
        """Process uploaded files and generate output files. Updates report status in DB."""
        try:
            await self._update_status(report, ReportStatus.PROCESSING)

            output_files, metadata, detected_period = await asyncio.get_event_loop().run_in_executor(
                None, self._run_sync, report, raw_files
            )

            report.metadata = metadata
            if detected_period:
                report.period = detected_period
            for f in output_files:
                report.output_files.append(f)
            await self._update_status(report, ReportStatus.COMPLETED)

        except Exception as exc:
            logger.error("report_generation_failed", report_id=str(report.id), error=str(exc))
            report.error_message = str(exc)
            await self._update_status(report, ReportStatus.FAILED)

    def _run_sync(self, report: Report, raw_files: list[tuple[str, bytes]]) -> tuple[list[ReportFile], dict[str, Any], str]:
        if report.report_type == ReportType.SAZON:
            return self._generate_sazon(report, raw_files)
        if report.report_type == ReportType.TLG:
            return self._generate_tlg(report, raw_files)
        if report.report_type == ReportType.MENSUALIZADOS:
            return self._generate_mensualizados(report, raw_files)
        raise ValueError(f"Tipo de informe no soportado: {report.report_type}")

    def _generate_sazon(self, report: Report, raw_files: list[tuple[str, bytes]]) -> tuple[list[ReportFile], dict[str, Any], str]:
        from src.infrastructure.reporting.sazon.cleaner import load_expenses_data, load_sales_data
        from src.infrastructure.reporting.sazon.aggregator import build_sazon_tables
        from src.infrastructure.reporting.sazon.generator import (
            automatic_interpretation,
            build_excel_report,
            build_pdf_report_v2,
            format_cop,
            format_percent,
        )
        import pandas as pd

        if len(raw_files) < 2:
            raise ValueError("El informe Sazón requiere dos archivos: ventas y gastos.")

        sales_buf = BytesIO(raw_files[0][1])
        sales_buf.name = raw_files[0][0]
        expenses_buf = BytesIO(raw_files[1][1])
        expenses_buf.name = raw_files[1][0]

        sales_df, _ = load_sales_data(sales_buf)
        expenses_df, expense_details_df, _ = load_expenses_data(expenses_buf)

        tables = build_sazon_tables(sales_df, expenses_df, expense_details_df)
        monthly = tables["monthly"]
        payments = tables["payments"]
        sellers = tables["sellers"]
        clients = tables["clients"]
        tips = tables["tips"]
        operating = tables["operating"]
        sales = tables["sales"]
        expenses = tables["expenses"]

        gross_sales = sales["VENTAS_BRUTAS"].sum()
        sales_total = sales["VENTAS_NETAS"].sum()
        expenses_total = expenses["GASTOS"].sum() if not expenses.empty else 0
        profit_total = sales_total - expenses_total
        margin_total = profit_total / sales_total if sales_total else 0
        invoice_count = sales["NUMERO FACTURA"].nunique()
        avg_ticket = sales_total / invoice_count if invoice_count else 0
        courtesy_total = sales["CORTESIAS_VALOR"].sum()
        courtesy_pct = courtesy_total / gross_sales if gross_sales else 0
        tips_total = sales["PROPINA"].sum()
        tips_tarjeta = sales["PROPINA TARJETA"].sum() if "PROPINA TARJETA" in sales.columns else 0
        tips_resto = sales["PROPINA RESTO"].sum() if "PROPINA RESTO" in sales.columns else tips_total - tips_tarjeta
        real_collected = sales["RECAUDO_REAL"].sum()

        top_sales_month = monthly.sort_values("Ventas", ascending=False)["Mes"].iloc[0] if not monthly.empty else "Sin datos"
        top_expense_month = monthly.sort_values("Gastos", ascending=False)["Mes"].iloc[0] if not monthly.empty and monthly["Gastos"].sum() else "Sin datos"
        payment_recaudo = payments[~payments["Forma de pago"].str.contains("Cortesías", case=False, na=False)]
        top_payment = payment_recaudo.iloc[0]["Forma de pago"] if not payment_recaudo.empty and payment_recaudo["Valor"].sum() else "Sin datos"
        top_payment_share = payment_recaudo.iloc[0]["Valor"] / payment_recaudo["Valor"].sum() if not payment_recaudo.empty and payment_recaudo["Valor"].sum() else 0
        top_seller = sellers.iloc[0]["Vendedor"] if not sellers.empty else "Sin datos"
        top_courtesy_month = monthly.sort_values("Cortesías", ascending=False)["Mes"].iloc[0] if not monthly.empty else "Sin datos"

        kpi_rows = [
            {"label": "Ventas brutas", "value": format_cop(gross_sales), "raw": float(gross_sales)},
            {"label": "Cortesías otorgadas", "value": format_cop(courtesy_total), "raw": float(courtesy_total)},
            {"label": "Ventas netas", "value": format_cop(sales_total), "raw": float(sales_total)},
            {"label": "Recaudo real", "value": format_cop(real_collected), "raw": float(real_collected)},
            {"label": "% cortesías sobre ventas", "value": format_percent(courtesy_pct), "raw": float(courtesy_pct)},
            {"label": "Gastos acumulados", "value": format_cop(expenses_total), "raw": float(expenses_total)},
            {"label": "Utilidad estimada", "value": format_cop(profit_total), "raw": float(profit_total)},
            {"label": "Margen estimado", "value": format_percent(margin_total), "raw": float(margin_total)},
            {"label": "Total propinas", "value": format_cop(tips_total), "raw": float(tips_total)},
            {"label": "Propinas en tarjeta", "value": format_cop(tips_tarjeta), "raw": float(tips_tarjeta)},
            {"label": "Propinas en efectivo", "value": format_cop(tips_resto), "raw": float(tips_resto)},
            {"label": "Número de facturas", "value": f"{invoice_count:,.0f}".replace(",", "."), "raw": float(invoice_count)},
            {"label": "Ticket promedio", "value": format_cop(avg_ticket), "raw": float(avg_ticket)},
            {"label": "Mes con mayor venta", "value": top_sales_month, "raw": None},
            {"label": "Forma de pago más usada", "value": top_payment, "raw": None},
            {"label": "Vendedor con mayor venta", "value": top_seller, "raw": None},
        ]

        expenses_display = expenses.rename(columns={"MES": "Mes", "GASTOS": "Gastos"}).drop(columns=["NUMERO_MES"], errors="ignore")
        interpretation = automatic_interpretation(
            sales_total, expenses_total, profit_total, margin_total,
            top_sales_month, top_expense_month, top_payment, top_payment_share, top_seller,
        )

        # Courtesy analysis
        courtesy_by_month = _df_to_records(monthly[["Mes", "Cortesías"]].copy())
        courtesy_by_seller = _df_to_records(
            sellers[["Vendedor", "Total cortesías"]].rename(columns={"Total cortesías": "Cortesías"}).sort_values("Cortesías", ascending=False).head(10)
        )

        excel_bytes = build_excel_report(
            pd.DataFrame({"Indicador": [k["label"] for k in kpi_rows], "Valor": [k["value"] for k in kpi_rows]}),
            monthly.drop(columns=["NUMERO_MES"], errors="ignore"),
            payments,
            sellers,
            clients.head(50),
            tips,
            expenses_display,
            operating,
        )
        pdf_bytes = build_pdf_report_v2(
            pd.DataFrame({"Indicador": [k["label"] for k in kpi_rows], "Valor": [k["value"] for k in kpi_rows]}),
            monthly.drop(columns=["NUMERO_MES"], errors="ignore"),
            payments,
            sellers,
            clients,
            tips,
            expenses_display,
            operating,
            interpretation,
        )

        prefix = f"reports/{report.tenant_id}/{report.id}"
        excel_key = f"{prefix}/sazon.xlsx"
        pdf_key = f"{prefix}/sazon.pdf"
        upload_bytes(excel_key, excel_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        upload_bytes(pdf_key, pdf_bytes, "application/pdf")

        metadata = {
            "kpis": kpi_rows,
            "monthly": _df_to_records(monthly.drop(columns=["NUMERO_MES"], errors="ignore")),
            "payments": _df_to_records(payments),
            "sellers": _df_to_records(sellers),
            "clients": _df_to_records(clients.head(50)),
            "tips": _df_to_records(tips),
            "provider_summary": _df_to_records(tables["provider_summary"].head(10) if not tables["provider_summary"].empty else tables["provider_summary"]),
            "operating": _df_to_records(operating),
            "expenses_display": _df_to_records(expenses_display),
            "interpretation": interpretation,
            "courtesy_by_month": courtesy_by_month,
            "courtesy_by_seller": courtesy_by_seller,
            "summary": {
                "courtesy_total": format_cop(courtesy_total),
                "courtesy_pct": format_percent(courtesy_pct),
                "top_courtesy_month": top_courtesy_month,
                "tips_total": format_cop(tips_total),
                "tips_tarjeta": format_cop(tips_tarjeta),
                "tips_resto": format_cop(tips_resto),
                "expenses_total": format_cop(expenses_total),
                "top_expense_month": top_expense_month,
                "expense_ratio": format_percent(expenses_total / sales_total if sales_total else 0),
            },
        }

        # Auto-detect period from months in data
        from src.infrastructure.reporting.sazon.cleaner import MONTHS_ES
        months_found = sorted(monthly["NUMERO_MES"].dropna().unique().tolist()) if "NUMERO_MES" in monthly.columns else []
        years_found = sorted(sales["FECHA"].dt.year.dropna().unique().tolist()) if pd.api.types.is_datetime64_any_dtype(sales.get("FECHA", pd.Series())) else []
        if months_found:
            year_str = str(int(years_found[0])) if years_found else ""
            if len(months_found) == 1:
                detected_period = f"{MONTHS_ES.get(int(months_found[0]), '')} {year_str}".strip()
            else:
                detected_period = f"{MONTHS_ES.get(int(months_found[0]), '')} - {MONTHS_ES.get(int(months_found[-1]), '')} {year_str}".strip()
        else:
            detected_period = ""

        return [
            ReportFile(report_id=report.id, file_type="output_excel", original_name="informe_sazon.xlsx", storage_key=excel_key),
            ReportFile(report_id=report.id, file_type="output_pdf", original_name="informe_sazon.pdf", storage_key=pdf_key),
        ], metadata, detected_period

    def _generate_tlg(self, report: Report, raw_files: list[tuple[str, bytes]]) -> tuple[list[ReportFile], dict[str, Any], str]:
        from src.infrastructure.reporting.tlg.cleaner import load_tlg_trial_balance
        from src.infrastructure.reporting.tlg.statements import build_tlg_financial_summary, build_tlg_management_text
        from src.infrastructure.reporting.tlg.generator import build_tlg_summary_excel, build_tlg_management_pdf

        if not raw_files:
            raise ValueError("El informe TLG requiere el archivo de balance de prueba.")

        buf = BytesIO(raw_files[0][1])
        df, tlg_meta = load_tlg_trial_balance(buf)
        summary = build_tlg_financial_summary(df)
        management_text = build_tlg_management_text(summary["metrics"], tlg_meta)

        metrics = {k: float(v) if isinstance(v, (int, float)) else v for k, v in summary["metrics"].items()}

        # Validation rows
        difference = metrics.get("diferencia_cuadre", 0)
        validation_rows = [
            {"Validación": "Empresa detectada", "Resultado": str(tlg_meta.get("empresa", ""))},
            {"Validación": "NIT detectado", "Resultado": str(tlg_meta.get("nit", ""))},
            {"Validación": "Periodo detectado", "Resultado": str(tlg_meta.get("periodo", ""))},
            {"Validación": "Mes detectado", "Resultado": str(tlg_meta.get("mes", ""))},
            {"Validación": "Número de cuentas", "Resultado": str(int(metrics.get("cuentas", 0)))},
            {"Validación": "Total saldo inicial", "Resultado": f"${metrics.get('total_saldo_inicial', 0):,.0f}"},
            {"Validación": "Total débitos", "Resultado": f"${metrics.get('total_debito', 0):,.0f}"},
            {"Validación": "Total créditos", "Resultado": f"${metrics.get('total_credito', 0):,.0f}"},
            {"Validación": "Total saldo final", "Resultado": f"${metrics.get('total_saldo_final', 0):,.0f}"},
            {"Validación": "Diferencia de cuadre", "Resultado": f"${difference:,.0f}"},
        ]

        excel_bytes = build_tlg_summary_excel(summary, tlg_meta)
        pdf_bytes = build_tlg_management_pdf(management_text, summary["metrics"], tlg_meta)

        prefix = f"reports/{report.tenant_id}/{report.id}"
        excel_key = f"{prefix}/tlg.xlsx"
        pdf_key = f"{prefix}/tlg.pdf"
        upload_bytes(excel_key, excel_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        upload_bytes(pdf_key, pdf_bytes, "application/pdf")

        metadata = {
            "empresa": str(tlg_meta.get("empresa", "")),
            "nit": str(tlg_meta.get("nit", "")),
            "periodo": str(tlg_meta.get("periodo", "")),
            "mes": str(tlg_meta.get("mes", "")),
            "anio": str(tlg_meta.get("anio", "")),
            "metrics": metrics,
            "balance": _df_to_records(summary["balance"]),
            "income_statement": _df_to_records(summary["income_statement"]),
            "management_text": management_text,
            "validation_rows": validation_rows,
            "cuadre_ok": abs(difference) <= 1000,
        }

        detected_period = str(tlg_meta.get("periodo", "")).strip()

        return [
            ReportFile(report_id=report.id, file_type="output_excel", original_name="tlg_estados_financieros.xlsx", storage_key=excel_key),
            ReportFile(report_id=report.id, file_type="output_pdf", original_name="tlg_resumen.pdf", storage_key=pdf_key),
        ], metadata, detected_period

    def _generate_mensualizados(self, report: Report, raw_files: list[tuple[str, bytes]]) -> tuple[list[ReportFile], dict[str, Any], str]:
        from src.infrastructure.reporting.mensualizados.engine import build_monthly_reports, export_monthly_reports

        if not raw_files:
            raise ValueError("El informe mensualizado requiere al menos un balance de prueba.")

        monthly_file_objects = []
        previous_file = None
        initial_file = None

        for name, data in raw_files:
            buf = BytesIO(data)
            buf.name = name
            lname = name.lower()
            if "inicial" in lname or "base" in lname:
                initial_file = buf
            elif "anterior" in lname or "previo" in lname:
                previous_file = buf
            else:
                monthly_file_objects.append(buf)

        if not monthly_file_objects:
            monthly_file_objects = [BytesIO(raw_files[0][1])]
            monthly_file_objects[0].name = raw_files[0][0]

        report_data = build_monthly_reports(
            monthly_file_objects,
            previous_file=previous_file,
            initial_balance_file=initial_file,
            start_year=None,
        )

        excel_bytes = export_monthly_reports(report_data)

        prefix = f"reports/{report.tenant_id}/{report.id}"
        excel_key = f"{prefix}/mensualizados.xlsx"
        upload_bytes(excel_key, excel_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        raw_metrics = report_data.get("metrics", [])
        monthly_metrics = raw_metrics if isinstance(raw_metrics, list) else []

        # Executive summary from last monthly period
        exec_summary: dict = {}
        monthly_only = [m for m in monthly_metrics if m.get("Tipo") == "Mensual"]
        if monthly_only:
            last = monthly_only[-1]
            ventas = last.get("Ventas", 0)
            ub = last.get("Utilidad bruta", 0)
            uo = last.get("Utilidad operacional", 0)
            res = last.get("Resultado", 0)
            ebitda = last.get("EBITDA", 0)
            activos = last.get("Activos", 0)
            pasivos = last.get("Pasivos", 0)
            patrimonio = last.get("Patrimonio", 0)
            activos_c = last.get("Activos corrientes", 0)
            pasivos_c = last.get("Pasivos corrientes", 0)
            exec_summary = {
                "Ventas": ventas,
                "Utilidad bruta": ub,
                "Margen bruto": ub / ventas if ventas else 0,
                "Utilidad operacional": uo,
                "Margen operacional": uo / ventas if ventas else 0,
                "Resultado neto": res,
                "Margen neto": res / ventas if ventas else 0,
                "EBITDA": ebitda,
                "Activos": activos,
                "Pasivos": pasivos,
                "Patrimonio": patrimonio,
                "Razón corriente": activos_c / pasivos_c if pasivos_c else 0,
                "Endeudamiento": pasivos / activos if activos else 0,
                "Capital de trabajo": activos_c - pasivos_c,
            }

        import pandas as pd
        receivables = report_data.get("third_party_receivables", pd.DataFrame())
        payables = report_data.get("third_party_payables", pd.DataFrame())
        activity = report_data.get("third_party_activity", pd.DataFrame())

        metadata = {
            "source_name": str(report_data.get("source_name", "")),
            "last_period": str(report_data.get("last_period", "")),
            "start_year": report_data.get("start_year"),
            "periods": _df_to_records(report_data.get("periods")),
            "monthly_metrics": monthly_metrics,
            "exec_summary": exec_summary,
            "receivables": _df_to_records(receivables.head(20) if hasattr(receivables, "head") else None),
            "payables": _df_to_records(payables.head(20) if hasattr(payables, "head") else None),
            "activity": _df_to_records(activity.head(30) if hasattr(activity, "head") else None),
        }

        detected_period = str(report_data.get("last_period", "")).strip()

        return [
            ReportFile(report_id=report.id, file_type="output_excel", original_name="estados_financieros_mensualizados.xlsx", storage_key=excel_key),
        ], metadata, detected_period

    async def _update_status(self, report: Report, status: ReportStatus) -> None:
        report.status = status
        await self.report_repo.save(report)
