"""
Phase 4: Invoice Duplicate Detection Service

Detects potential duplicate invoices by comparing:
- Invoice number (exact or similar)
- Vendor name (fuzzy matching)
- Issue date (within range)
- Total amount (within percentage)
- Currency
- Line item similarity
"""

import logging
from datetime import timedelta
from difflib import SequenceMatcher
from decimal import Decimal, InvalidOperation

from documents.models import ExtractedData

logger = logging.getLogger(__name__)


class DuplicateMatch:
    """Result object for duplicate detection"""
    
    def __init__(self, matched_document, score, match_reasons):
        self.matched_document = matched_document
        self.score = score  # 0-100
        self.match_reasons = match_reasons  # List of reasons why matched
        self.is_exact = score >= 90
        self.is_likely = score >= 75
        self.is_possible = score >= 60


class InvoiceDuplicateDetectionService:
    """Service for detecting duplicate invoices"""
    
    # Matching thresholds
    INVOICE_NUMBER_EXACT_WEIGHT = 35  # Highest weight
    VENDOR_SIMILARITY_WEIGHT = 20
    AMOUNT_EXACT_WEIGHT = 25  # Also high weight
    DATE_PROXIMITY_WEIGHT = 12
    CURRENCY_MATCH_WEIGHT = 8
    
    # Amount tolerance (percentage)
    AMOUNT_TOLERANCE_PCT = 2.0  # Within 2% is suspicious
    
    # Date proximity (days)
    DATE_PROXIMITY_DAYS = 30  # Within 30 days is suspicious
    
    # String similarity threshold
    STRING_SIMILARITY_THRESHOLD = 0.85  # 85% similarity is match
    
    def detect_duplicates(self, extracted_data):
        """
        Detect potential duplicates for this invoice
        
        Returns:
            list of DuplicateMatch objects
            None if no search possible
        """
        try:
            # Cannot search without basic identifiers
            if not extracted_data.invoice_number or not extracted_data.vendor_name:
                logger.warning(f"Cannot detect duplicates for {extracted_data.id}: missing identifiers")
                return []
            
            # Get historical invoices from same organization
            similar_invoices = ExtractedData.objects.filter(
                organization=extracted_data.organization,
                extraction_status='extracted',
                vendor_name__isnull=False
            ).exclude(
                id=extracted_data.id
            )[0:500]  # Limit to last 500 invoices
            
            if not similar_invoices:
                return []
            
            matches = []
            
            for historical in similar_invoices:
                score = self._calculate_duplicate_score(extracted_data, historical)
                
                if score >= 60:  # Threshold for possible duplicate
                    reasons = self._get_match_reasons(extracted_data, historical, score)
                    match = DuplicateMatch(historical, score, reasons)
                    matches.append(match)
            
            # Sort by score descending
            matches.sort(key=lambda x: x.score, reverse=True)
            
            logger.info(f"Duplicate detection for {extracted_data.invoice_number}: found {len(matches)} matches")
            return matches
            
        except Exception as e:
            logger.error(f"Error detecting duplicates for {extracted_data.id}: {str(e)}")
            return []
    
    def _calculate_duplicate_score(self, current, historical):
        """
        Calculate duplicate score between two invoices
        
        Returns:
            int: 0-100 score
        """
        score = 0
        total_weight = 0
        
        # 1. Invoice number matching (highest priority)
        if self._match_invoice_numbers(current.invoice_number, historical.invoice_number):
            score += self.INVOICE_NUMBER_EXACT_WEIGHT
            total_weight += self.INVOICE_NUMBER_EXACT_WEIGHT
        else:
            total_weight += self.INVOICE_NUMBER_EXACT_WEIGHT
        
        # 2. Vendor name similarity
        vendor_similarity = self._string_similarity(
            current.vendor_name or "",
            historical.vendor_name or ""
        )
        if vendor_similarity >= self.STRING_SIMILARITY_THRESHOLD:
            score += int(self.VENDOR_SIMILARITY_WEIGHT * vendor_similarity)
            total_weight += self.VENDOR_SIMILARITY_WEIGHT
        else:
            total_weight += self.VENDOR_SIMILARITY_WEIGHT
        
        # 3. Amount matching (within tolerance)
        if self._match_amounts(current.total_amount, historical.total_amount):
            score += self.AMOUNT_EXACT_WEIGHT
            total_weight += self.AMOUNT_EXACT_WEIGHT
        else:
            total_weight += self.AMOUNT_EXACT_WEIGHT
        
        # 4. Date proximity
        if self._match_dates(current.invoice_date, historical.invoice_date):
            score += self.DATE_PROXIMITY_WEIGHT
            total_weight += self.DATE_PROXIMITY_WEIGHT
        else:
            total_weight += self.DATE_PROXIMITY_WEIGHT
        
        # 5. Currency match
        if current.currency == historical.currency:
            score += self.CURRENCY_MATCH_WEIGHT
        total_weight += self.CURRENCY_MATCH_WEIGHT
        
        # Normalize to 0-100
        if total_weight > 0:
            return min(100, int((score / total_weight) * 100))
        return 0
    
    def _match_invoice_numbers(self, num1, num2):
        """Check if invoice numbers match (exact or within similarity)"""
        if not num1 or not num2:
            return False
        
        # Exact match
        if num1.strip().upper() == num2.strip().upper():
            return True
        
        # High similarity match
        similarity = self._string_similarity(num1, num2)
        return similarity >= 0.95
    
    def _match_amounts(self, amt1, amt2):
        """Check if amounts match (within tolerance)"""
        if amt1 is None or amt2 is None:
            return False
        
        try:
            amt1 = Decimal(str(amt1))
            amt2 = Decimal(str(amt2))
            
            if amt1 == 0 or amt2 == 0:
                return False
            
            # Check if within tolerance
            diff_pct = abs((amt1 - amt2) / amt2) * 100
            return diff_pct <= self.AMOUNT_TOLERANCE_PCT
            
        except (InvalidOperation, ValueError, TypeError):
            return False
    
    def _match_dates(self, date1, date2):
        """Check if dates are within proximity"""
        if not date1 or not date2:
            return False
        import datetime as _dt
        # Normalise both to date to allow date vs datetime comparison
        if hasattr(date1, 'date'):
            date1 = date1.date()
        if hasattr(date2, 'date'):
            date2 = date2.date()
        date_diff = abs((date1 - date2).days)
        return date_diff <= self.DATE_PROXIMITY_DAYS
    
    def _string_similarity(self, str1, str2):
        """Calculate string similarity (0.0 to 1.0)"""
        if not str1 or not str2:
            return 0.0
        
        return SequenceMatcher(
            None,
            str1.lower().strip(),
            str2.lower().strip()
        ).ratio()
    
    def _get_match_reasons(self, current, historical, score):
        """Generate human-readable reasons for the match"""
        reasons = []
        
        # Invoice number
        if self._match_invoice_numbers(current.invoice_number, historical.invoice_number):
            if current.invoice_number == historical.invoice_number:
                reasons.append("Exact invoice number match")
            else:
                reasons.append(f"Similar invoice numbers: {current.invoice_number} ≈ {historical.invoice_number}")
        
        # Vendor
        vendor_sim = self._string_similarity(current.vendor_name or "", historical.vendor_name or "")
        if vendor_sim >= 0.85:
            if vendor_sim == 1.0:
                reasons.append("Same vendor")
            else:
                reasons.append(f"Vendor names {vendor_sim*100:.0f}% similar")
        
        # Amount
        if self._match_amounts(current.total_amount, historical.total_amount):
            if current.total_amount == historical.total_amount:
                reasons.append(f"Exact amount: {current.total_amount} {current.currency}")
            else:
                reasons.append(f"Amounts within tolerance: {current.total_amount} vs {historical.total_amount}")
        
        # Date
        if self._match_dates(current.invoice_date, historical.invoice_date):
            d1 = current.invoice_date
            d2 = historical.invoice_date
            if hasattr(d1, 'date'): d1 = d1.date()
            if hasattr(d2, 'date'): d2 = d2.date()
            date_diff = abs((d1 - d2).days)
            if date_diff == 0:
                reasons.append("Same invoice date")
            else:
                reasons.append(f"Invoices {date_diff} days apart")
        
        # Currency
        if current.currency == historical.currency:
            reasons.append(f"Same currency: {current.currency}")
        
        # Duplicate risk score
        if score >= 90:
            reasons.insert(0, "⚠️ LIKELY DUPLICATE")
        elif score >= 75:
            reasons.insert(0, "⚠️ POSSIBLE DUPLICATE")
        
        return reasons
    
    def get_best_match(self, extracted_data):
        """Get the single best duplicate match"""
        matches = self.detect_duplicates(extracted_data)
        return matches[0] if matches else None
    
    def get_duplicate_score(self, extracted_data):
        """Get best duplicate match score only"""
        best_match = self.get_best_match(extracted_data)
        return best_match.score if best_match else 0


    def find_duplicates(self, new_invoice_data: dict, organization_id: str,
                        exclude_document_id: str = None):
        """
        Find duplicates for a dict-based invoice within *organization_id*.

        Args:
            new_invoice_data:     Dict with keys invoice_number, vendor_name,
                                  total_amount, currency, issue_date.
            organization_id:      UUID string — scopes the search to one org.
            exclude_document_id:  Optional document UUID to exclude from results.

        Returns:
            List of DuplicateMatch objects sorted by score descending.
        """
        from types import SimpleNamespace
        from decimal import Decimal as _D

        # Normalise dict to an attribute-accessible object matching ORM field names
        issue_date = new_invoice_data.get('issue_date')
        current = SimpleNamespace(
            invoice_number=new_invoice_data.get('invoice_number') or '',
            vendor_name=new_invoice_data.get('vendor_name') or '',
            total_amount=new_invoice_data.get('total_amount'),
            invoice_date=issue_date,
            currency=new_invoice_data.get('currency') or '',
        )

        qs = ExtractedData.objects.filter(
            organization_id=organization_id,
            extraction_status='extracted',
            vendor_name__isnull=False,
        )
        if exclude_document_id:
            qs = qs.exclude(document_id=exclude_document_id)
        qs = qs[:500]

        matches = []
        for historical in qs:
            score = self._calculate_duplicate_score(current, historical)
            if score >= 60:
                reasons = self._get_match_reasons(current, historical, score)
                matches.append(DuplicateMatch(historical, score, reasons))

        matches.sort(key=lambda m: m.score, reverse=True)
        return matches

# Singleton instance
invoice_duplicate_detection_service = InvoiceDuplicateDetectionService()

