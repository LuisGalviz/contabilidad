from __future__ import annotations

from abc import ABC, abstractmethod
from io import BytesIO

import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from src.domain.entities.causation_entry import CausationEntry
from src.domain.entities.client import Client
from src.domain.entities.puc_account import PUCAccount
from src.domain.entities.supplier_invoice import SupplierInvoice
from src.infrastructure.reporting.sazon.generator import BarChart, INK, KPIGrid, MUTED, PRIMARY, format_cop, format_percent
from src.infrastructure.reporting.sector_templates.kpis import CategoryTotal, PeriodPurchaseKPIs, compute_purchase_kpis


class SectorReportTemplate(ABC):
    """One template per business sector (`sector_key`), resolved via
    `registry.resolve_template(client)`. Adding a new sector is "write one
    new subclass + register it" — `compute_kpis()`/`compute_chart_series()`/
    `build_excel()`/`build_pdf()` are shared here since Phase 1's templates
    only really differ in narrative tone and category naming; override them
    too if a future sector genuinely needs different KPIs.
    """

    sector_key: str = "generic"

    def compute_kpis(
        self,
        period: str,
        invoices: list[SupplierInvoice],
        causation_entries: list[CausationEntry],
        accounts_by_code: dict[str, PUCAccount],
        prior_period_total: object | None = None,
    ) -> PeriodPurchaseKPIs:
        return compute_purchase_kpis(period, invoices, causation_entries, accounts_by_code, prior_period_total)

    def compute_chart_series(self, kpis: PeriodPurchaseKPIs) -> dict[str, object]:
        """Structured series feeding both the frontend recharts view and the
        PDF chart flowables from a single source of truth."""
        return {
            "by_category": [
                {"label": self.category_label(c), "value": float(c.total)} for c in kpis.by_category[:8]
            ],
            "top_suppliers": [
                {"label": s.supplier_name or s.supplier_nit, "value": float(s.total)} for s in kpis.top_suppliers
            ],
        }

    def category_label(self, category: CategoryTotal) -> str:
        return category.account_name

    @abstractmethod
    def phrase_narrative(self, client: Client, kpis: PeriodPurchaseKPIs) -> str: ...

    def build_excel(self, kpis: PeriodPurchaseKPIs, chart_series: dict[str, object]) -> bytes:
        output = BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            summary = pd.DataFrame(
                [
                    {"Indicador": "Periodo", "Valor": kpis.period},
                    {"Indicador": "Total comprado", "Valor": format_cop(float(kpis.total_amount))},
                    {"Indicador": "Número de facturas causadas", "Valor": kpis.invoice_count},
                    {"Indicador": "% clasificado automáticamente", "Valor": format_percent(kpis.auto_classified_share)},
                ]
            )
            summary.to_excel(writer, sheet_name="Resumen", index=False)

            categories = pd.DataFrame(
                [
                    {
                        "Cuenta PUC": c.account_code,
                        "Categoría": self.category_label(c),
                        "Total": format_cop(float(c.total)),
                    }
                    for c in kpis.by_category
                ]
            )
            categories.to_excel(writer, sheet_name="Por categoría", index=False)

            suppliers = pd.DataFrame(
                [
                    {
                        "Proveedor": s.supplier_name,
                        "NIT": s.supplier_nit,
                        "Total": format_cop(float(s.total)),
                        "Facturas": s.invoice_count,
                    }
                    for s in kpis.top_suppliers
                ]
            )
            suppliers.to_excel(writer, sheet_name="Principales proveedores", index=False)

            for sheet_name in ("Resumen", "Por categoría", "Principales proveedores"):
                worksheet = writer.sheets[sheet_name]
                worksheet.set_column(0, 3, 26)
        return output.getvalue()

    def build_pdf(
        self,
        client: Client,
        kpis: PeriodPurchaseKPIs,
        chart_series: dict[str, object],
        narrative: str,
    ) -> bytes:
        output = BytesIO()
        doc = SimpleDocTemplate(
            output,
            pagesize=letter,
            topMargin=0.6 * inch,
            bottomMargin=0.6 * inch,
            leftMargin=0.6 * inch,
            rightMargin=0.6 * inch,
        )
        base_styles = getSampleStyleSheet()
        styles = {
            "Title": ParagraphStyle("Title", parent=base_styles["Title"], textColor=INK, fontSize=18),
            "SectionTitle": ParagraphStyle(
                "SectionTitle", parent=base_styles["Heading2"], textColor=PRIMARY, fontSize=13
            ),
            "Body": ParagraphStyle("Body", parent=base_styles["BodyText"], textColor=INK, fontSize=10.5, leading=15),
            "Muted": ParagraphStyle("Muted", parent=base_styles["BodyText"], textColor=MUTED, fontSize=9),
        }

        story: list = [
            Paragraph(f"Informe de compras — {client.name}", styles["Title"]),
            Paragraph(f"Periodo: {kpis.period}", styles["Muted"]),
            Spacer(1, 0.15 * inch),
            KPIGrid(
                [
                    ("Total comprado", format_cop(float(kpis.total_amount))),
                    ("Facturas causadas", str(kpis.invoice_count)),
                    ("Clasificado automático", format_percent(kpis.auto_classified_share)),
                    ("Proveedores principales", str(len(kpis.top_suppliers))),
                ]
            ),
            Spacer(1, 0.2 * inch),
            Paragraph("¿En qué se fue la plata?", styles["SectionTitle"]),
            Spacer(1, 0.08 * inch),
        ]

        by_category = chart_series.get("by_category", [])
        if by_category:
            story.append(
                BarChart(
                    [item["label"] for item in by_category],
                    [item["value"] for item in by_category],
                    width=460,
                    height=140,
                )
            )

        top_suppliers = chart_series.get("top_suppliers", [])
        if top_suppliers:
            story.append(Spacer(1, 0.2 * inch))
            story.append(Paragraph("Principales proveedores", styles["SectionTitle"]))
            story.append(Spacer(1, 0.08 * inch))
            story.append(
                BarChart(
                    [item["label"] for item in top_suppliers],
                    [item["value"] for item in top_suppliers],
                    width=460,
                    height=120,
                )
            )

        story.append(Spacer(1, 0.25 * inch))
        story.append(Paragraph("En palabras simples", styles["SectionTitle"]))
        story.append(Spacer(1, 0.08 * inch))
        story.append(Paragraph(narrative.replace("\n", "<br/>"), styles["Body"]))

        doc.build(story)
        return output.getvalue()
