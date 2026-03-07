"""
IngestDocumentUseCase — Application Layer.

Orchestrates the ingestion of structured files (CSV / JSON) into the system.
Depends only on domain interfaces — no Django, no ORM references here.

SOLID compliance:
  SRP  — one class, one job: coordinate providers → persist results via callback.
  OCP  — add new providers to the registry without modifying this class.
  LSP  — any IIngestionProvider can be swapped in.
  ISP  — callers receive only what they need (IngestionResult).
  DIP  — depends on abstractions (IIngestionProvider), not concretions.
"""
from __future__ import annotations

import logging
from typing import Callable, List, Optional

from core.domain.entities import IngestionResult, InvoiceData
from core.domain.interfaces import IIngestionProvider

logger = logging.getLogger(__name__)


class IngestDocumentUseCase:
    """
    Execute ingestion for a given file using the first matching provider.

    Usage:
        from core.infrastructure.ingestors import CsvIngestor, JsonIngestor
        use_case = IngestDocumentUseCase(providers=[CsvIngestor(), JsonIngestor()])
        result = use_case.execute("/tmp/invoices.csv")
    """

    def __init__(self, providers: List[IIngestionProvider]):
        self._providers = providers

    def execute(
        self,
        file_path: str,
        on_invoice: Optional[Callable[[InvoiceData], None]] = None,
    ) -> IngestionResult:
        """
        Find the first capable provider, run ingestion, and optionally call
        *on_invoice* for each successfully parsed invoice.

        Args:
            file_path:  Absolute path to the file to ingest.
            on_invoice: Optional callback executed for each InvoiceData; use this
                        to persist to the database (keeps use-case DB-agnostic).

        Returns:
            IngestionResult with invoices and any errors.
        """
        provider = self._find_provider(file_path)
        if provider is None:
            result = IngestionResult(source_type="unsupported")
            result.errors.append(
                f"No ingestor found for '{file_path}'. "
                f"Supported: {[type(p).__name__ for p in self._providers]}"
            )
            logger.warning("No provider for %s", file_path)
            return result

        logger.info("Ingesting %s with %s", file_path, type(provider).__name__)
        result = provider.ingest(file_path)

        if on_invoice:
            for invoice in result.invoices:
                try:
                    on_invoice(invoice)
                except Exception as exc:
                    result.errors.append(f"Persist error: {exc}")
                    logger.exception("on_invoice callback failed for %s", file_path)

        return result

    # ── Private ───────────────────────────────────────────────────────────────

    def _find_provider(self, file_path: str) -> Optional[IIngestionProvider]:
        for p in self._providers:
            if p.can_handle(file_path):
                return p
        return None


# ── Default singleton (DRY: import this instead of re-instantiating everywhere) ─

from core.infrastructure.ingestors import CsvIngestor, JsonIngestor   # noqa: E402

default_ingest_usecase = IngestDocumentUseCase(
    providers=[CsvIngestor(), JsonIngestor()]
)
