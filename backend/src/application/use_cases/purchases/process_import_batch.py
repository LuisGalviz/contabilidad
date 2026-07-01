from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from io import BytesIO

import structlog

from src.application.use_cases.purchases.suggest_mapping import SuggestMappingUseCase
from src.domain.entities.classification_history import (
    ClassificationAction,
    ClassificationHistoryEntry,
)
from src.domain.entities.invoice_import_batch import InvoiceImportBatch
from src.domain.entities.supplier_invoice import ClassificationSource, SupplierInvoice
from src.domain.repositories.classification_history_repository import (
    ClassificationHistoryRepository,
)
from src.domain.repositories.import_batch_repository import InvoiceImportBatchRepository
from src.domain.repositories.mapping_rule_repository import SupplierMappingRuleRepository
from src.domain.repositories.supplier_invoice_repository import SupplierInvoiceRepository

logger = structlog.get_logger()


@dataclass
class ProcessImportBatchUseCase:
    batch_repo: InvoiceImportBatchRepository
    invoice_repo: SupplierInvoiceRepository
    mapping_rule_repo: SupplierMappingRuleRepository
    suggest_mapping: SuggestMappingUseCase
    history_repo: ClassificationHistoryRepository

    async def execute(self, batch: InvoiceImportBatch, file_bytes: bytes) -> None:
        try:
            batch.mark_processing()
            await self.batch_repo.save(batch)

            from src.infrastructure.purchases.dian.cleaner import load_dian_invoices, row_issue_date

            df, _ = load_dian_invoices(BytesIO(file_bytes))

            total_rows = len(df)
            new_invoices: list[SupplierInvoice] = []
            duplicate_count = 0
            error_count = 0

            for _, row in df.iterrows():
                try:
                    cufe = str(row["CUFE"]).strip()
                    if await self.invoice_repo.exists_by_cufe(batch.tenant_id, batch.client_id, cufe):
                        duplicate_count += 1
                        continue

                    invoice = SupplierInvoice(
                        tenant_id=batch.tenant_id,
                        client_id=batch.client_id,
                        import_batch_id=batch.id,
                        cufe=cufe,
                        supplier_nit=str(row["NIT_EMISOR"]),
                        supplier_name=str(row["RAZON_SOCIAL_EMISOR"]),
                        issue_date=row_issue_date(row["FECHA_EMISION"]),
                        concept_description=str(row["CONCEPTO"]),
                        subtotal=_as_decimal(row["SUBTOTAL"]),
                        vat_amount=_as_decimal(row["IVA"]),
                        total_amount=_as_decimal(row["TOTAL"]),
                        raw_row={str(k): str(v) for k, v in row.items()},
                    )

                    await self._suggest_and_maybe_auto_confirm(invoice)
                    new_invoices.append(invoice)
                except Exception as row_exc:
                    error_count += 1
                    logger.warning("dian_row_skipped", batch_id=str(batch.id), error=str(row_exc))

            if new_invoices:
                await self.invoice_repo.save_many(new_invoices)

            batch.mark_completed(total_rows, len(new_invoices), duplicate_count, error_count)
            await self.batch_repo.save(batch)

        except Exception as exc:
            logger.error("import_batch_failed", batch_id=str(batch.id), error=str(exc))
            batch.mark_failed(str(exc))
            await self.batch_repo.save(batch)

    async def _suggest_and_maybe_auto_confirm(self, invoice: SupplierInvoice) -> None:
        rule = await self.suggest_mapping.execute(invoice)
        if rule is None:
            return

        auto_confirmed = invoice.classification_source == ClassificationSource.AUTO_HIGH_CONFIDENCE
        if auto_confirmed:
            invoice.confirm_classification(invoice.suggested_account_code, invoice.suggested_cost_center_id, user_id=None)  # type: ignore[arg-type]
            rule.record_confirmation()
            await self.mapping_rule_repo.save(rule)

        await self.history_repo.append(
            ClassificationHistoryEntry(
                invoice_id=invoice.id,
                tenant_id=invoice.tenant_id,
                action=ClassificationAction.AUTO_SUGGESTED,
                account_code_after=invoice.final_account_code or invoice.suggested_account_code,
                rule_id=rule.id,
            )
        )


def _as_decimal(value: object) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return Decimal("0")
