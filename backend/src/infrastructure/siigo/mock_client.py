from __future__ import annotations

from itertools import count
from typing import Any
from uuid import uuid4

import structlog

from src.infrastructure.siigo.client import SiigoClient, SiigoJournalResult

logger = structlog.get_logger()


class MockSiigoClient(SiigoClient):
    """In-memory stand-in for the Siigo API, used while real credentials are
    unavailable (SIIGO_USE_MOCK=true). Accepts any payload shaped like the
    real journal request and returns responses shaped like Siigo's, so the
    rest of the flow (external_reference, statuses, UI) behaves identically.
    """

    def __init__(self) -> None:
        self.journals: list[dict[str, Any]] = []
        self.purchases: list[dict[str, Any]] = []
        self._sequence = count(1)

    async def create_journal(self, payload: dict[str, Any]) -> SiigoJournalResult:
        self.journals.append(payload)
        return self._result("siigo_mock_journal_created", payload)

    async def create_purchase(self, payload: dict[str, Any]) -> SiigoJournalResult:
        self.purchases.append(payload)
        return self._result("siigo_mock_purchase_created", payload)

    def _result(self, event: str, payload: dict[str, Any]) -> SiigoJournalResult:
        result = SiigoJournalResult(siigo_id=str(uuid4()), document_number=f"MOCK-{next(self._sequence)}")
        logger.info(
            event,
            siigo_id=result.siigo_id,
            document_number=result.document_number,
            items=len(payload.get("items", [])),
        )
        return result
