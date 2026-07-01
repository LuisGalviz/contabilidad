from __future__ import annotations

from src.domain.entities.client import Client
from src.infrastructure.reporting.sazon.generator import format_cop, format_percent
from src.infrastructure.reporting.sector_templates.base import SectorReportTemplate
from src.infrastructure.reporting.sector_templates.kpis import PeriodPurchaseKPIs


class GenericSectorTemplate(SectorReportTemplate):
    """Fallback for clients whose `economic_activity` doesn't match any
    registered sector, and the base for the contador's general (technical,
    non-personalized) report — that one is deliberately *not* sector-flavored.
    """

    sector_key = "generico"

    def phrase_narrative(self, client: Client, kpis: PeriodPurchaseKPIs) -> str:
        if kpis.invoice_count == 0:
            return (
                f"No hay facturas de compra causadas para {client.name} en el periodo {kpis.period}. "
                "Sube el Excel de documentos recibidos de la DIAN para generar este informe."
            )

        top_category = kpis.by_category[0] if kpis.by_category else None
        top_supplier = kpis.top_suppliers[0] if kpis.top_suppliers else None

        parts = [
            f"Durante {kpis.period}, {client.name} causó compras por {format_cop(float(kpis.total_amount))} "
            f"en {kpis.invoice_count} facturas."
        ]

        if top_category:
            parts.append(
                f"La categoría con mayor participación fue \"{self.category_label(top_category)}\" "
                f"({format_cop(float(top_category.total))})."
            )

        if top_supplier:
            parts.append(
                f"El proveedor principal fue {top_supplier.supplier_name or top_supplier.supplier_nit}, "
                f"con {format_cop(float(top_supplier.total))} facturados."
            )

        change = kpis.change_vs_prior_period
        if change is not None:
            direction = "un incremento" if change > 0 else "una reducción"
            parts.append(f"Frente al periodo anterior se observa {direction} del {format_percent(abs(change))}.")

        parts.append(
            f"El {format_percent(kpis.auto_classified_share)} de las facturas fue clasificado "
            "automáticamente sin corrección manual."
        )

        return " ".join(parts)
