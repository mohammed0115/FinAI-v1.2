"""
JSON Ingestor — Infrastructure Layer.

Implements IIngestionProvider for .json files.

Supported input shapes:
  1. Single invoice object   {"invoice_number": ..., "vendor": {...}, ...}
  2. Array of invoices       [{...}, {...}, ...]
  3. Wrapped array           {"invoices": [...]}  /  {"data": [...]}

DRY:  normalisation delegated to InvoiceNormalizationService (same as CSV).
OCP:  add new wrapper keys to WRAPPER_KEYS without touching parse logic.
LSP:  substitutable for CsvIngestor wherever IIngestionProvider is expected.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Union

logger = logging.getLogger(__name__)

# Top-level keys that may wrap an array of invoices
WRAPPER_KEYS = ("invoices", "data", "items", "records", "فواتير")


class JsonIngestor:
    """Parse a JSON file into a list of InvoiceData objects."""

    source_type = "json"

    # ── IIngestionProvider protocol ───────────────────────────────────────────

    def can_handle(self, file_path: str) -> bool:
        return file_path.lower().endswith(".json")

    def ingest(self, file_path: str):
        from core.domain.entities import IngestionResult
        from core.infrastructure.arabic_normalizer import arabic_normalizer

        result = IngestionResult(source_type=self.source_type)

        with open(file_path, encoding="utf-8") as fh:
            raw = fh.read()

        # Convert Eastern-Arabic digits before JSON parsing
        raw = arabic_normalizer.convert_string(raw)

        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            result.errors.append(f"Invalid JSON: {exc}")
            return result

        records = self._extract_records(payload)
        result.total_rows = len(records)

        for i, record in enumerate(records, start=1):
            try:
                invoice = self._map_record(record)
                result.invoices.append(invoice)
            except Exception as exc:
                result.errors.append(f"Record {i}: {exc}")
                logger.warning("JSON ingest record %d error: %s", i, exc)

        logger.info("JSON ingested: %d ok / %d errors from %s",
                    result.success_count, result.error_count, file_path)
        return result

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _extract_records(payload: Any) -> List[Dict]:
        """Normalise payload to a flat list of dicts."""
        if isinstance(payload, list):
            return payload
        if isinstance(payload, dict):
            for key in WRAPPER_KEYS:
                if key in payload and isinstance(payload[key], list):
                    return payload[key]
            # Single object — wrap it
            return [payload]
        return []

    @staticmethod
    def _map_record(record: Dict[str, Any]):
        """Map a JSON object to InvoiceData, handling nested vendor/customer."""
        from core.domain.entities import InvoiceData
        from core.invoice_normalization_service import InvoiceNormalizationService as N

        vendor  = record.get("vendor") or {}
        customer = record.get("customer") or {}

        return InvoiceData(
            invoice_number = record.get("invoice_number") or record.get("inv_no") or None,
            issue_date     = N.normalize_date(record.get("issue_date") or record.get("date")),
            due_date       = N.normalize_date(record.get("due_date")),
            vendor_name    = (vendor.get("name") if isinstance(vendor, dict)
                              else record.get("vendor_name") or None),
            vendor_tax_id  = (vendor.get("tax_id") if isinstance(vendor, dict) else None),
            customer_name  = (customer.get("name") if isinstance(customer, dict)
                              else record.get("customer_name") or None),
            customer_tax_id= (customer.get("tax_id") if isinstance(customer, dict) else None),
            currency       = N.normalize_currency(record.get("currency") or "SAR"),
            total_amount   = N.normalize_amount(record.get("total_amount") or record.get("total")),
            tax_amount     = N.normalize_amount(record.get("tax_amount") or record.get("vat")),
            raw_text       = json.dumps(record, ensure_ascii=False),
            confidence     = 85,   # structured JSON — higher default confidence
        )
