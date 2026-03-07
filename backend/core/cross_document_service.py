"""
Cross-Document Intelligence Service - Phase 4
خدمة الذكاء عبر الوثائق

Performs cross-document analysis to detect:
- Duplicate or near-duplicate invoices
- Suspicious patterns and anomalies
- Vendor risk assessment from historical data
- Invoice timing anomalies
- Amount anomalies
"""

import logging
from decimal import Decimal
from typing import Dict, List, Tuple, Any, Optional
from datetime import datetime, timedelta
import json
from collections import defaultdict
import hashlib

logger = logging.getLogger(__name__)


class DuplicateDetectionService:
    """Service for detecting duplicate and near-duplicate invoices"""
    
    # Similarity thresholds
    EXACT_MATCH_THRESHOLD = 0.99
    HIGH_SIMILARITY_THRESHOLD = 0.85
    MEDIUM_SIMILARITY_THRESHOLD = 0.70
    
    @staticmethod
    def detect_duplicates(current_invoice: Dict[str, Any],
                          historical_invoices: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Detect duplicates by comparing with historical invoices
        
        Args:
            current_invoice: Current invoice data
            historical_invoices: List of historical invoice data
        
        Returns:
            Dictionary with duplicate detection results
        """
        exact_match = None
        high_similarity_matches = []
        
        for historical in historical_invoices:
            similarity = DuplicateDetectionService._calculate_similarity(
                current_invoice, historical
            )
            
            if similarity >= DuplicateDetectionService.EXACT_MATCH_THRESHOLD:
                exact_match = {
                    'invoice_number': historical.get('invoice_number'),
                    'vendor_name': historical.get('vendor_name'),
                    'total_amount': historical.get('total_amount'),
                    'issue_date': historical.get('issue_date'),
                    'similarity': similarity,
                }
                break
            
            elif similarity >= DuplicateDetectionService.HIGH_SIMILARITY_THRESHOLD:
                high_similarity_matches.append({
                    'invoice_number': historical.get('invoice_number'),
                    'vendor_name': historical.get('vendor_name'),
                    'total_amount': historical.get('total_amount'),
                    'issue_date': historical.get('issue_date'),
                    'similarity': similarity,
                })
        
        # Sort by similarity descending
        high_similarity_matches.sort(key=lambda x: x['similarity'], reverse=True)
        
        result = {
            'is_exact_duplicate': exact_match is not None,
            'exact_match_details': exact_match,
            'high_similarity_matches': high_similarity_matches,
            'duplicate_risk_score': 0,
            'duplicate_status': 'clear',
        }
        
        if exact_match:
            result['duplicate_status'] = 'EXACT_DUPLICATE'
            result['duplicate_risk_score'] = 95
        elif high_similarity_matches:
            result['duplicate_status'] = 'SUSPECTED_DUPLICATE'
            result['duplicate_risk_score'] = 70 + (len(high_similarity_matches) * 5)
        
        return result
    
    @staticmethod
    def _calculate_similarity(invoice1: Dict[str, Any],
                             invoice2: Dict[str, Any]) -> float:
        """
        Calculate similarity score between two invoices (0-1)
        
        Compares:
        - Invoice number (exact match worth 30%)
        - Vendor name (fuzzy match worth 20%)
        - Total amount (close match worth 25%)
        - Items (content similarity worth 25%)
        """
        scores = {}
        
        # Invoice number exact match (30%)
        if invoice1.get('invoice_number') == invoice2.get('invoice_number'):
            scores['invoice_number'] = 1.0
        else:
            scores['invoice_number'] = 0.0
        
        # Vendor name similarity (20%)
        vendor1 = invoice1.get('vendor_name', '').lower().strip()
        vendor2 = invoice2.get('vendor_name', '').lower().strip()
        if vendor1 and vendor2:
            # Simple string similarity
            vendor_sim = DuplicateDetectionService._string_similarity(vendor1, vendor2)
            scores['vendor_name'] = vendor_sim
        else:
            scores['vendor_name'] = 0.0
        
        # Total amount similarity (25%)
        amount1 = invoice1.get('total_amount')
        amount2 = invoice2.get('total_amount')
        if amount1 and amount2:
            # Allow 1% variance
            diff_ratio = abs(amount1 - amount2) / max(amount1, amount2)
            amount_sim = max(0, 1.0 - diff_ratio)
            scores['total_amount'] = amount_sim
        else:
            scores['total_amount'] = 0.0
        
        # Items similarity (25%)
        items1 = invoice1.get('items', [])
        items2 = invoice2.get('items', [])
        if items1 and items2:
            items_sim = DuplicateDetectionService._items_similarity(items1, items2)
            scores['items'] = items_sim
        else:
            scores['items'] = 0.0
        
        # Weighted average
        weights = {
            'invoice_number': 0.30,
            'vendor_name': 0.20,
            'total_amount': 0.25,
            'items': 0.25,
        }
        
        similarity = sum(
            scores.get(key, 0) * weight
            for key, weight in weights.items()
        )
        
        return min(1.0, max(0.0, similarity))
    
    @staticmethod
    def _string_similarity(s1: str, s2: str) -> float:
        """Calculate string similarity (0-1) using simple overlap"""
        if not s1 or not s2:
            return 0.0
        
        # Convert to sets of characters
        set1 = set(s1)
        set2 = set(s2)
        
        if not set1 or not set2:
            return 0.0
        
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        
        return intersection / union if union > 0 else 0.0
    
    @staticmethod
    def _items_similarity(items1: List[Dict], items2: List[Dict]) -> float:
        """Calculate similarity between line items"""
        if not items1 or not items2:
            return 0.0
        
        # Compare sum of line totals
        total1 = sum(item.get('line_total', Decimal('0')) for item in items1)
        total2 = sum(item.get('line_total', Decimal('0')) for item in items2)
        
        if total1 == 0 and total2 == 0:
            return 0.5
        
        diff_ratio = abs(total1 - total2) / max(total1, total2) if max(total1, total2) > 0 else 0
        
        # Also compare item count
        count_ratio = min(len(items1), len(items2)) / max(len(items1), len(items2))
        
        return (1.0 - min(diff_ratio, 1.0)) * 0.6 + count_ratio * 0.4


class AnomalyDetectionService:
    """Service for detecting anomalous patterns in invoices"""
    
    # Amount thresholds
    LARGE_AMOUNT_THRESHOLD = Decimal('500000')
    SUDDEN_SPIKE_RATIO = 2.0  # 200% increase
    
    @staticmethod
    def detect_anomalies(current_invoice: Dict[str, Any],
                        vendor_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Detect anomalies in current invoice compared to vendor history
        
        Args:
            current_invoice: Current invoice data
            vendor_history: Historical invoices from same vendor
        
        Returns:
            Dictionary with anomaly detection results
        """
        anomalies = []
        anomaly_risk_score = 0
        
        # Check amount anomaly
        amount_anomaly = AnomalyDetectionService._detect_amount_anomaly(
            current_invoice, vendor_history
        )
        if amount_anomaly['detected']:
            anomalies.append(amount_anomaly)
            anomaly_risk_score += 15
        
        # Check timing anomaly
        timing_anomaly = AnomalyDetectionService._detect_timing_anomaly(
            current_invoice, vendor_history
        )
        if timing_anomaly['detected']:
            anomalies.append(timing_anomaly)
            anomaly_risk_score += 10
        
        # Check frequency anomaly
        frequency_anomaly = AnomalyDetectionService._detect_frequency_anomaly(
            current_invoice, vendor_history
        )
        if frequency_anomaly['detected']:
            anomalies.append(frequency_anomaly)
            anomaly_risk_score += 10
        
        # Check line item anomaly
        items_anomaly = AnomalyDetectionService._detect_items_anomaly(
            current_invoice, vendor_history
        )
        if items_anomaly['detected']:
            anomalies.append(items_anomaly)
            anomaly_risk_score += 10
        
        return {
            'anomalies_detected': len(anomalies) > 0,
            'anomalies': anomalies,
            'anomaly_risk_score': min(50, anomaly_risk_score),
            'anomaly_flags': [a['flag'] for a in anomalies],
        }
    
    @staticmethod
    def _detect_amount_anomaly(current: Dict[str, Any],
                               history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Detect if amount is anomalously high"""
        if not history:
            return {'detected': False}
        
        current_amount = current.get('total_amount', Decimal('0'))
        historical_amounts = [
            inv.get('total_amount', Decimal('0'))
            for inv in history
            if inv.get('total_amount')
        ]
        
        if not historical_amounts:
            return {'detected': False}
        
        avg_amount = sum(historical_amounts) / len(historical_amounts)
        max_amount = max(historical_amounts)
        
        # Check if current is more than 2x the average
        if current_amount > avg_amount * AnomalyDetectionService.SUDDEN_SPIKE_RATIO:
            return {
                'detected': True,
                'flag': f'AMOUNT_SPIKE',
                'description': (
                    f"Amount ({current_amount}) is {current_amount/avg_amount:.1f}x "
                    f"the average ({avg_amount})"
                ),
                'severity': 'high',
            }
        
        if current_amount > AnomalyDetectionService.LARGE_AMOUNT_THRESHOLD:
            return {
                'detected': True,
                'flag': f'LARGE_AMOUNT',
                'description': f"Very large amount: {current_amount}",
                'severity': 'medium',
            }
        
        return {'detected': False}
    
    @staticmethod
    def _detect_timing_anomaly(current: Dict[str, Any],
                               history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Detect if invoice date is anomalous"""
        if not history:
            return {'detected': False}
        
        try:
            current_date = datetime.strptime(current.get('issue_date', ''), '%Y-%m-%d')
        except (ValueError, TypeError):
            return {'detected': False}
        
        today = datetime.now()
        
        # Check if it's a very old invoice
        if (today - current_date).days > 180:
            return {
                'detected': True,
                'flag': 'STALE_INVOICE',
                'description': f"Invoice is {(today - current_date).days} days old",
                'severity': 'medium',
            }
        
        # Check if it's future-dated
        if current_date > today:
            return {
                'detected': True,
                'flag': 'FUTURE_DATE',
                'description': "Invoice date is in the future",
                'severity': 'high',
            }
        
        return {'detected': False}
    
    @staticmethod
    def _detect_frequency_anomaly(current: Dict[str, Any],
                                  history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Detect if invoices are arriving at unusual frequency"""
        if len(history) < 3:
            return {'detected': False}
        
        try:
            current_date = datetime.strptime(current.get('issue_date', ''), '%Y-%m-%d')
        except (ValueError, TypeError):
            return {'detected': False}
        
        # Get dates from history
        dates = []
        for inv in history:
            try:
                date = datetime.strptime(inv.get('issue_date', ''), '%Y-%m-%d')
                dates.append(date)
            except (ValueError, TypeError):
                continue
        
        if len(dates) < 2:
            return {'detected': False}
        
        # Sort dates
        dates.sort()
        
        # Calculate average gap between invoices
        gaps = []
        for i in range(1, len(dates)):
            gaps.append((dates[i] - dates[i-1]).days)
        
        avg_gap = sum(gaps) / len(gaps)
        
        # Check if current invoice comes too soon
        last_date = dates[-1] if dates else None
        if last_date:
            days_since_last = (current_date - last_date).days
            if days_since_last < avg_gap * 0.5:
                return {
                    'detected': True,
                    'flag': 'RAPID_INVOICING',
                    'description': (
                        f"Invoice received {days_since_last} days after previous; "
                        f"average gap is {avg_gap:.0f} days"
                    ),
                    'severity': 'low',
                }
        
        return {'detected': False}
    
    @staticmethod
    def _detect_items_anomaly(current: Dict[str, Any],
                              history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Detect if line items are anomalous"""
        current_items = current.get('items', [])
        
        if not current_items or not history:
            return {'detected': False}
        
        # Check for unusually large number of items
        historical_item_counts = [
            len(inv.get('items', []))
            for inv in history
            if inv.get('items')
        ]
        
        if historical_item_counts:
            avg_items = sum(historical_item_counts) / len(historical_item_counts)
            if len(current_items) > avg_items * 2:
                return {
                    'detected': True,
                    'flag': 'UNUSUAL_ITEM_COUNT',
                    'description': (
                        f"Unusual number of items ({len(current_items)}); "
                        f"average: {avg_items:.0f}"
                    ),
                    'severity': 'low',
                }
        
        return {'detected': False}


class VendorRiskService:
    """Service for assessing vendor risk based on historical patterns"""
    
    @staticmethod
    def calculate_vendor_risk(vendor_name: str,
                             vendor_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate vendor risk score based on historical invoicing patterns
        
        Args:
            vendor_name: Vendor name
            vendor_history: List of historical invoices from vendor
        
        Returns:
            Dictionary with vendor risk assessment
        """
        if not vendor_history:
            return {
                'vendor_name': vendor_name,
                'vendor_risk_score': 0,
                'risk_level': 'unknown',
                'risk_factors': [],
                'positive_factors': [],
            }
        
        risk_factors = []
        positive_factors = []
        risk_score = 0
        
        # Factor 1: Invoice history length
        if len(vendor_history) < 3:
            risk_factors.append(f"Limited history ({len(vendor_history)} invoices)")
            risk_score += 10
        else:
            positive_factors.append(f"Established history ({len(vendor_history)} invoices)")
        
        # Factor 2: Consistency of amounts
        amounts = [
            inv.get('total_amount', Decimal('0'))
            for inv in vendor_history
            if inv.get('total_amount')
        ]
        
        if amounts and len(amounts) > 2:
            avg_amount = sum(amounts) / len(amounts)
            variance = sum((amt - avg_amount) ** 2 for amt in amounts) / len(amounts)
            std_dev = variance ** 0.5 if variance else 0
            
            # High variance indicates inconsistent invoicing
            if std_dev > avg_amount * 0.5:
                risk_factors.append(f"Highly variable invoice amounts (std dev: {std_dev:.0f})")
                risk_score += 15
            else:
                positive_factors.append("Consistent invoice amounts")
        
        # Factor 3: Payment compliance (if we have that data)
        # This would require additional data we might not have in this phase
        
        # Factor 4: Invoice frequency
        if len(vendor_history) >= 2:
            dates = []
            for inv in vendor_history:
                try:
                    date = datetime.strptime(inv.get('issue_date', ''), '%Y-%m-%d')
                    dates.append(date)
                except (ValueError, TypeError):
                    continue
            
            if len(dates) >= 2:
                dates.sort()
                gaps = [(dates[i] - dates[i-1]).days for i in range(1, len(dates))]
                
                # Invoices should have regular gaps
                if gaps:
                    avg_gap = sum(gaps) / len(gaps)
                    if 20 <= avg_gap <= 90:
                        positive_factors.append(f"Regular invoicing schedule (~{avg_gap:.0f} days)")
                    elif avg_gap < 10:
                        risk_factors.append(f"Very frequent invoicing (~{avg_gap:.0f} days)")
                        risk_score += 5
        
        # Determine risk level
        if risk_score >= 50:
            risk_level = 'high'
        elif risk_score >= 25:
            risk_level = 'medium'
        elif risk_score >= 10:
            risk_level = 'low'
        else:
            risk_level = 'very_low'
        
        return {
            'vendor_name': vendor_name,
            'vendor_risk_score': min(100, risk_score),
            'risk_level': risk_level,
            'risk_factors': risk_factors,
            'positive_factors': positive_factors,
            'invoice_count': len(vendor_history),
        }


def get_cross_document_service():
    """Factory for cross-document services"""
    return {
        'duplicate': DuplicateDetectionService,
        'anomaly': AnomalyDetectionService,
        'vendor_risk': VendorRiskService,
    }
