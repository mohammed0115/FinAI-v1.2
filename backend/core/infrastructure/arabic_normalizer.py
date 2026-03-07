"""
Arabic / Eastern-Arabic / Hindi numeral normalizer — Infrastructure Layer.

Implements INormalizer from domain/interfaces.py.

Eastern-Arabic digits (٠١٢٣٤٥٦٧٨٩) and Persian/Hindi digits (۰۱۲۳۴۵۶۷۸۹)
are widely used in GCC invoices. Financial systems require Western digits (0-9)
for arithmetic operations. This module converts all variants before any
Decimal parsing or storage occurs.

DRY: single source for this mapping — used by:
  - InvoiceNormalizationService.normalize()
  - DualExtractionService (post-extraction hook)
  - CSV / JSON ingestors

SOLID — Open/Closed: extend TRANSLATION_TABLE to add new digit sets without
touching any other module.
"""
from __future__ import annotations

import re
from typing import Any, Dict

# Unicode codepoint mappings
# Eastern-Arabic digits + Arabic decimal separator (٫ U+066B → .)
_EASTERN_ARABIC = str.maketrans(
    "٠١٢٣٤٥٦٧٨٩٫",
    "0123456789.",
)

# Extended Arabic-Indic (used in Persian / Farsi / Urdu)
_PERSIAN = str.maketrans(
    "۰۱۲۳۴۵۶۷۸۹",
    "0123456789",
)


class ArabicNumeralNormalizer:
    """
    Converts Eastern-Arabic and Persian/Hindi numerals to Western digits.

    Conforms to INormalizer protocol: accepts a dict, returns a cleaned dict.
    Also exposes a standalone convert_string() for use in other services.
    """

    # ── Public API ────────────────────────────────────────────────────────────

    @staticmethod
    def convert_string(text: str) -> str:
        """
        Replace all Eastern-Arabic / Persian digits in *text* with 0-9.

        >>> ArabicNumeralNormalizer.convert_string("الفاتورة رقم ١٢٣٤")
        'الفاتورة رقم 1234'
        >>> ArabicNumeralNormalizer.convert_string("المبلغ ۱٬۵۰۰٫۰۰ ريال")
        'المبلغ 1٬500.00 ريال'
        """
        if not isinstance(text, str):
            return text
        text = text.translate(_EASTERN_ARABIC)
        text = text.translate(_PERSIAN)
        return text

    @classmethod
    def normalize(cls, raw: Dict[str, Any]) -> Dict[str, Any]:
        """
        Walk every string value in *raw* and convert Arabic/Hindi numerals.
        Operates recursively on nested dicts and lists.

        This is the INormalizer.normalize() implementation.
        """
        return cls._walk(raw)

    # ── Private helpers ───────────────────────────────────────────────────────

    @classmethod
    def _walk(cls, obj: Any) -> Any:
        if isinstance(obj, dict):
            return {k: cls._walk(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [cls._walk(item) for item in obj]
        if isinstance(obj, str):
            return cls.convert_string(obj)
        return obj


# ── Module-level singleton (import once, use everywhere) ─────────────────────
arabic_normalizer = ArabicNumeralNormalizer()
