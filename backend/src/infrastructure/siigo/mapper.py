from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.domain.entities.causation_entry import CausationEntry


def causation_entry_to_journal_payload(entry: CausationEntry, document_id: int) -> dict[str, Any]:
    """Maps a ContaFlow causación entry to Siigo's `POST /v1/journals` body
    (comprobante de contabilidad).

    `document_id` is the Siigo document-type id the accountants chose for
    these entries (see GET /v1/document-types?type=CC). Values are sent as
    floats because Siigo's API takes JSON numbers; amounts are COP with two
    decimals so the float round-trip is exact.
    """
    items: list[dict[str, Any]] = []
    for line in entry.lines:
        is_debit = line.debit > 0
        items.append(
            {
                "account": {
                    "code": line.account_code,
                    "movement": "Debit" if is_debit else "Credit",
                },
                "description": line.description[:255],
                "value": float(line.debit if is_debit else line.credit),
            }
        )

    return {
        "document": {"id": document_id},
        "date": entry.entry_date.isoformat(),
        "items": items,
        "observations": f"ContaFlow causación {entry.id} (factura {entry.invoice_id})",
    }
