"""
Domain Interfaces — Protocol definitions (Dependency Inversion Principle).

All concrete implementations live in core/infrastructure/.
Application use-cases depend ONLY on these abstractions.
"""
from __future__ import annotations

from typing import Any, Dict, List, Protocol, runtime_checkable

from .entities import ExtractionResult, IngestionResult, InvoiceData


@runtime_checkable
class IExtractionProvider(Protocol):
    """Contract for any OCR / AI extraction backend."""

    def extract(self, file_path: str) -> ExtractionResult:
        """Extract structured invoice data from a document file."""
        ...

    @property
    def provider_name(self) -> str:
        """Human-readable name, e.g. 'openai_vision'."""
        ...


@runtime_checkable
class IIngestionProvider(Protocol):
    """Contract for structured-file parsers (CSV, JSON)."""

    def can_handle(self, file_path: str) -> bool:
        """Return True if this provider handles the given file extension."""
        ...

    def ingest(self, file_path: str) -> IngestionResult:
        """Parse the file and return a list of InvoiceData objects."""
        ...


@runtime_checkable
class INormalizer(Protocol):
    """Contract for any data normalisation step."""

    def normalize(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        """Return a cleaned, normalised copy of the input dict."""
        ...


@runtime_checkable
class IRiskScorer(Protocol):
    """Contract for risk-scoring strategies."""

    def score(self, invoice: InvoiceData, context: Dict[str, Any]) -> int:
        """Return an integer risk score 0-100."""
        ...
