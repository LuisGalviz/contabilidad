from __future__ import annotations

from src.domain.entities.client import Client
from src.infrastructure.reporting.sazon.generator import format_cop, format_percent
from src.infrastructure.reporting.sector_templates.base import SectorReportTemplate
from src.infrastructure.reporting.sector_templates.kpis import CategoryTotal, PeriodPurchaseKPIs

# Friendlier, restaurant-flavored names for the PUC codes a restaurant's
# purchases most commonly hit (see puc_seed.py). Falls back to the PUC
# account's own name for anything not in this map.
_RESTAURANT_CATEGORY_NAMES: dict[str, str] = {
    "6205": "Insumos de cocina (materia prima)",
    "6135": "Mercancía comprada para vender",
    "5105": "Personal del restaurante",
    "5120": "Arriendo del local",
    "5135": "Servicios públicos (agua, luz, gas)",
    "5145": "Mantenimiento y reparaciones",
    "5195": "Otros gastos varios",
}


class RestaurantSectorTemplate(SectorReportTemplate):
    """Refactor of the plain-language narrative style that used to be
    hardcoded for restaurants in `sazon/generator.py::automatic_interpretation`
    — same "explain it simply" spirit, now framed around purchases/gastos
    (this feature automates compras causación, not sales) instead of a full
    sales-and-expenses P&L.
    """

    sector_key = "restaurante"

    def category_label(self, category: CategoryTotal) -> str:
        return _RESTAURANT_CATEGORY_NAMES.get(category.account_code, category.account_name)

    def phrase_narrative(self, client: Client, kpis: PeriodPurchaseKPIs) -> str:
        if kpis.invoice_count == 0:
            return (
                f"Este mes no encontramos facturas de compra causadas para {client.name}. "
                "En cuanto subas el Excel de la DIAN con tus facturas del periodo, aquí vas a ver "
                "en qué se fue la plata de tu restaurante."
            )

        top_category = kpis.by_category[0] if kpis.by_category else None
        top_supplier = kpis.top_suppliers[0] if kpis.top_suppliers else None

        parts = [
            f"Este mes tu restaurante compró un total de {format_cop(float(kpis.total_amount))}, "
            f"repartido en {kpis.invoice_count} facturas."
        ]

        if top_category:
            parts.append(
                f"Lo que más pesó fue \"{self.category_label(top_category)}\", con "
                f"{format_cop(float(top_category.total))} — piensa en esto como la parte más grande "
                "de la torta de tus gastos."
            )

        if top_supplier:
            parts.append(
                f"Tu proveedor principal fue {top_supplier.supplier_name or top_supplier.supplier_nit}, "
                f"a quien le compraste {format_cop(float(top_supplier.total))} en {top_supplier.invoice_count} "
                "facturas."
            )

        change = kpis.change_vs_prior_period
        if change is not None:
            direction = "subieron" if change > 0 else "bajaron"
            parts.append(f"Comparado con el mes anterior, tus compras {direction} un {format_percent(abs(change))}.")

        if kpis.auto_classified_share > 0:
            parts.append(
                f"El sistema ya reconoce solo el {format_percent(kpis.auto_classified_share)} de tus facturas "
                "sin que tengas que corregirlas — entre más facturas proceses, más rápido se vuelve."
            )

        return " ".join(parts)
