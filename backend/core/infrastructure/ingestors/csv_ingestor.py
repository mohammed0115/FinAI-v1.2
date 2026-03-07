"""
CSV Ingestor — Infrastructure Layer.

Implements IIngestionProvider for .csv files containing tabular invoice data.

Supported column aliases (case-insensitive, Arabic/English):
  invoice_number / رقم_الفاتورة
  vendor_name    / المورد
  customer_name  / العميل
  issue_date     / تاريخ_الإصدار
  due_date       / تاريخ_الاستحقاق
  total_amount   / الإجمالي
  tax_amount     / الضريبة
  currency       / العملة

DRY:  all amount/date normalisation is delegated to InvoiceNormalizationService.
OCP:  add new column aliases to COLUMN_ALIASES only — no method changes needed.
SRP:  this class only parses; storage is the caller's responsibility.
"""
from __future__ import annotations

import csv
import io
import logging
from decimal import Decimal
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Column alias map: canonical_name -> list[accepted_headers]
COLUMN_ALIASES: Dict[str, List[str]] = {
    "invoice_number": ["invoice_number", "invoice no", "رقم_الفاتورة", "رقم الفاتورة", "inv_no"],
    "vendor_name":    ["vendor_name", "vendor", "supplier", "المورد", "اسم_المورد"],
    "customer_name":  ["customer_name", "customer", "bill_to", "العميل", "اسم_العميل"],
    "issue_date":     ["issue_date", "date", "invoice_date", "تاريخ_الإصدار", "تاريخ الفاتورة"],
    "due_date":       ["due_date", "payment_date", "تاريخ_الاستحقاق", "تاريخ_السداد"],
    "total_amount":   ["total_amount", "total", "amount", "الإجمالي", "المبلغ_الإجمالي"],
    "tax_amount":     ["tax_amount", "vat", "tax", "الضريبة", "ضريبة_القيمة_المضافة"],
    "currency":       ["currency", "curr", "العملة"],
}


class CsvIngestor:
    """Parse a CSV file into a list of invoice-shaped dicts."""

    source_type = "csv"

    # ── IIngestionProvider protocol ───────────────────────────────────────────

    def can_handle(self, file_path: str) -> bool:
        return file_path.lower().endswith(".csv")

    def ingest(self, file_path: str):
        """
        Parse *file_path* and return IngestionResult.
        Lazily imports domain entities to avoid circular imports.
        """
        from core.domain.entities import IngestionResult, InvoiceData
        from core.infrastructure.arabic_normalizer import arabic_normalizer
        from core.invoice_normalization_service import InvoiceNormalizationService

        result = IngestionResult(source_type=self.source_type)

        try:
            with open(file_path, newline="", encoding="utf-8-sig") as fh:
                raw = fh.read()
        except UnicodeDecodeError:
            with open(file_path, newline="", encoding="cp1256") as fh:
                raw = fh.read()

        # Convert Arabic/Hindi digits in the raw text first
        raw = arabic_normalizer.convert_string(raw)

        reader = csv.DictReader(io.StringIO(raw))
        alias_map = self._build_alias_map(reader.fieldnames or [])
        result.total_rows = 0

        for i, row in enumerate(reader, start=1):
            result.total_rows += 1
            try:
                d = self._map_row(row, alias_map, InvoiceNormalizationService)
                result.invoices.append(d)
            except Exception as exc:
                result.errors.append(f"Row {i}: {exc}")
                logger.warning("CSV ingest row %d error: %s", i, exc)

        logger.info("CSV ingested: %d ok / %d errors from %s",
                    result.success_count, result.error_count, file_path)
        return result

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _build_alias_map(headers: List[str]) -> Dict[str, str]:
        """Return {csv_header: canonical_field} for every matched header."""
        mapping: Dict[str, str] = {}
        for h in headers:
            normalized_h = h.strip().lower().replace(" ", "_")
            for canonical, aliases in COLUMN_ALIASES.items():
                if normalized_h in [a.lower().replace(" ", "_") for a in aliases]:
                    mapping[h] = canonical
                    break
        return mapping

    @staticmethod
    def _map_row(
        row: Dict[str, str],
        alias_map: Dict[str, str],
        normalizer,
    ):
        """Convert one CSV row to an InvoiceData-compatible dict."""
        from core.domain.entities import InvoiceData

        mapped: Dict[str, Any] = {}
        for csv_col, canonical in alias_map.items():
            mapped[canonical] = row.get(csv_col, "").strip()

        return InvoiceData(
            invoice_number = mapped.get("invoice_number") or None,
            issue_date     = normalizer.normalize_date(mapped.get("issue_date")),
            due_date       = normalizer.normalize_date(mapped.get("due_date")),
            vendor_name    = mapped.get("vendor_name") or None,
            customer_name  = mapped.get("customer_name") or None,
            currency       = normalizer.normalize_currency(mapped.get("currency") or "SAR"),
            total_amount   = normalizer.normalize_amount(mapped.get("total_amount")),
            tax_amount     = normalizer.normalize_amount(mapped.get("tax_amount")),
            confidence     = 70,   # structured import — medium confidence by default
        )
