from __future__ import annotations

from src.domain.entities.client import Client
from src.infrastructure.reporting.sector_templates.base import SectorReportTemplate
from src.infrastructure.reporting.sector_templates.generic_template import GenericSectorTemplate
from src.infrastructure.reporting.sector_templates.restaurant_template import RestaurantSectorTemplate

# Single source of truth for "which sectors ContaFlow supports" — the
# contador picks `Client.economic_activity` from this same key list
# (see frontend `dashboard/clients` sector `<select>`); adding a sector is
# "write one class, add one line here."
SECTOR_TEMPLATE_REGISTRY: dict[str, type[SectorReportTemplate]] = {
    RestaurantSectorTemplate.sector_key: RestaurantSectorTemplate,
    GenericSectorTemplate.sector_key: GenericSectorTemplate,
}

DEFAULT_SECTOR_KEY = GenericSectorTemplate.sector_key


def resolve_template(client: Client) -> SectorReportTemplate:
    template_cls = SECTOR_TEMPLATE_REGISTRY.get(client.economic_activity)
    if template_cls is None:
        template_cls = SECTOR_TEMPLATE_REGISTRY[DEFAULT_SECTOR_KEY]
    return template_cls()


def sector_keys() -> list[str]:
    return list(SECTOR_TEMPLATE_REGISTRY.keys())
