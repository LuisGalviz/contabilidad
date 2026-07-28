from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.domain.entities.causation_entry import CausationEntry
    from src.domain.entities.supplier_invoice import SupplierInvoice


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


def causation_entry_to_purchase_payload(
    entry: CausationEntry,
    invoice: SupplierInvoice,
    document_id: int,
    payment_type_id: int,
) -> dict[str, Any]:
    """Mapea la causación al cuerpo de `POST /v1/purchases` (factura de compra).

    Diferencia de fondo con `/v1/journals`: allá mandamos el asiento ya armado y
    replicamos nosotros la lógica contable; acá mandamos la **factura** y Siigo
    la contabiliza con sus propias reglas de impuestos y cuenta por pagar.

    Por eso solo se envían las líneas de gasto/costo como ítems de tipo
    `Account`: el IVA y la cuenta por pagar los deriva Siigo. Se excluyen las
    líneas de IVA y proveedores del asiento para no duplicarlas.

    `payment_type_id` es el medio de pago de Siigo (`GET /v1/payment-types`);
    hasta que el equipo contable defina cuál usar, esto no se puede activar.
    """
    excluded = {_vat_code(entry, invoice), _payable_code(entry, invoice)}
    items = [
        {
            "type": "Account",
            "code": line.account_code,
            "description": line.description[:255],
            "quantity": 1,
            "price": float(line.debit if line.debit > 0 else line.credit),
        }
        for line in entry.lines
        if line.account_code not in excluded
    ]

    payload: dict[str, Any] = {
        "document": {"id": document_id},
        "date": entry.entry_date.isoformat(),
        "supplier": {"identification": invoice.supplier_nit},
        "items": items,
        "payments": [{"id": payment_type_id, "value": float(invoice.total_amount)}],
        "observations": f"ContaFlow causación {entry.id} (CUFE {invoice.cufe})"[:4000],
    }

    # Siigo rechaza `provider_invoice` incompleto, así que solo se manda cuando
    # el archivo de la DIAN trajo el número.
    if invoice.document_number:
        payload["provider_invoice"] = {
            "prefix": invoice.document_prefix,
            "number": invoice.document_number,
        }
    return payload


def _vat_code(entry: CausationEntry, invoice: SupplierInvoice) -> str | None:
    """La línea de IVA es la que iguala `vat_amount` y no es la del gasto."""
    if invoice.vat_amount <= 0:
        return None
    for line in entry.lines:
        amount = line.debit if line.debit > 0 else line.credit
        if amount == invoice.vat_amount and line.account_code != invoice.final_account_code:
            return line.account_code
    return None


def _payable_code(entry: CausationEntry, invoice: SupplierInvoice) -> str | None:
    for line in entry.lines:
        amount = line.debit if line.debit > 0 else line.credit
        if amount == invoice.total_amount and line.account_code != invoice.final_account_code:
            return line.account_code
    return None
