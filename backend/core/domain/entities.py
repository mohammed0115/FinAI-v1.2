"""
Domain Entities — Value Objects for the FinAI invoice pipeline.

Rules:
- Pure Python dataclasses, zero framework imports.
- Immutable after construction (frozen=True where possible).
- All money fields use Decimal; all dates are str ISO-8601 YYYY-MM-DD.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional


# ── Enumerations ──────────────────────────────────────────────────────────────

class ExtractionProvider(str, Enum):
    OPENAI   = "openai_vision"
    TESSERACT = "tesseract_ocr"
    UNKNOWN  = "unknown"


class RiskLevel(str, Enum):
    LOW      = "Low"
    MEDIUM   = "Medium"
    HIGH     = "High"
    CRITICAL = "Critical"


class DocumentStatus(str, Enum):
    PENDING         = "pending"
    PROCESSING      = "processing"
    COMPLETED       = "completed"
    FAILED          = "failed"
    PENDING_REVIEW  = "pending_review"   # NEW — unclear data, awaiting human correction
    VALIDATED       = "validated"


# ── Line Item ─────────────────────────────────────────────────────────────────

@dataclass
class LineItem:
    description: str
    quantity:    Decimal
    unit_price:  Decimal
    total:       Decimal
    discount:    Decimal = Decimal("0")

    @property
    def calculated_total(self) -> Decimal:
        return (self.quantity * self.unit_price) - self.discount


# ── Core Invoice Value Object ─────────────────────────────────────────────────

@dataclass
class InvoiceData:
    """Normalised invoice data — single source of truth inside the pipeline."""
    invoice_number:   Optional[str]     = None
    issue_date:       Optional[str]     = None   # YYYY-MM-DD
    due_date:         Optional[str]     = None   # YYYY-MM-DD
    vendor_name:      Optional[str]     = None
    vendor_tax_id:    Optional[str]     = None
    customer_name:    Optional[str]     = None
    customer_tax_id:  Optional[str]     = None
    currency:         Optional[str]     = None   # ISO-4217 e.g. SAR
    subtotal:         Optional[Decimal] = None
    tax_amount:       Optional[Decimal] = None
    total_amount:     Optional[Decimal] = None
    items:            List[LineItem]    = field(default_factory=list)
    raw_text:         Optional[str]     = None
    confidence:       int               = 0       # 0-100


# ── Extraction Result ─────────────────────────────────────────────────────────

@dataclass
class ExtractionResult:
    """Output of any IExtractionProvider implementation."""
    invoice:          InvoiceData
    provider:         ExtractionProvider
    is_fallback:      bool              = False  # True when secondary provider was used
    confidence:       int               = 0
    raw_response:     Optional[Dict]    = None
    error:            Optional[str]     = None
    processing_ms:    int               = 0

    @property
    def succeeded(self) -> bool:
        return self.error is None


# ── Ingestion Result ─────────────────────────────────────────────────────────

@dataclass
class IngestionResult:
    """Output of any IIngestionProvider implementation (CSV / JSON / image)."""
    invoices:    List[InvoiceData]      = field(default_factory=list)
    errors:      List[str]              = field(default_factory=list)
    source_type: str                    = "unknown"
    total_rows:  int                    = 0

    @property
    def success_count(self) -> int:
        return len(self.invoices)

    @property
    def error_count(self) -> int:
        return len(self.errors)


# ── Compliance Check ─────────────────────────────────────────────────────────

@dataclass
class ComplianceResult:
    check_name:  str
    passed:      bool
    severity:    str          # "info" | "warning" | "error" | "critical"
    message:     str
    details:     Optional[str] = None


# ── Risk Assessment ───────────────────────────────────────────────────────────

@dataclass
class RiskAssessment:
    score:         int                    # 0-100
    level:         RiskLevel
    factors:       List[str]              = field(default_factory=list)
    vendor_score:  int                    = 0
    anomaly_score: int                    = 0
    duplicate_pct: int                    = 0
