"""
Phase 4: Anomaly Detection Service

Aggregates anomalies from all detection sources:
- Duplicate detection anomalies
- Cross-document validation anomalies  
- Statistical anomalies
- Rule-based anomalies

Calculates composite anomaly score and severity.
"""

import logging
from documents.models import ExtractedData, AnomalyLog

logger = logging.getLogger(__name__)


class InvoiceAnomalyDetectionService:
    """Service for comprehensive anomaly detection"""
    
    # Anomaly severity scale
    SEVERITY_SCORES = {
        'info': 10,
        'warning': 30,
        'high': 65,
        'critical': 90,
    }
    
    # Anomaly weighting
    DUPLICATE_WEIGHT = 40        # Duplicates are high priority
    AMOUNT_ANOMALY_WEIGHT = 25   # Amount spikes/drops
    DISCOUNT_ANOMALY_WEIGHT = 20 # Unusual discounts
    VAT_ANOMALY_WEIGHT = 30      # VAT inconsistencies  
    FREQUENCY_ANOMALY_WEIGHT = 15 # Frequency spikes
    
    def detect_all_anomalies(self, extracted_data, duplicate_matches=None, cross_doc_anomalies=None):
        """
        Aggregate all anomalies and calculate composite score
        
        Args:
            extracted_data: ExtractedData instance
            duplicate_matches: List of DuplicateMatch objects (optional)
            cross_doc_anomalies: List of CrossDocumentAnomaly objects (optional)
        
        Returns:
            dict with anomaly_score, anomaly_flags, severity_breakdown
        """
        
        anomaly_flags = []
        severity_counts = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0}
        weighted_scores = []
        
        try:
            # Process duplicate matches
            if duplicate_matches:
                for match in duplicate_matches:
                    if match.score >= 75:  # Likely or higher
                        anomaly_flags.append({
                            'type': 'potential_duplicate',
                            'severity': 'critical' if match.score >= 90 else 'high',
                            'score': match.score,
                            'reasons': match.match_reasons[:3],  # Top 3 reasons
                            'matched_invoice': str(match.matched_document.id),
                        })
                        severity_counts[
                            'critical' if match.score >= 90 else 'high'
                        ] += 1
                        weighted_scores.append((self.DUPLICATE_WEIGHT, match.score))
            
            # Process cross-document anomalies
            if cross_doc_anomalies:
                anomaly_type_counts = {}
                for anomaly in cross_doc_anomalies:
                    # Track anomaly type
                    atype = anomaly.anomaly_type
                    anomaly_type_counts[atype] = anomaly_type_counts.get(atype, 0) + 1
                    
                    # Map anomaly type to weight
                    weight = self._get_anomaly_weight(atype)
                    
                    anomaly_flags.append({
                        'type': atype,
                        'severity': anomaly.severity,
                        'score': anomaly.score,
                        'description': anomaly.description,
                        'context': anomaly.context,
                    })
                    
                    # Track by severity
                    if anomaly.severity == 'critical':
                        severity_counts['critical'] += 1
                    elif anomaly.severity == 'high':
                        severity_counts['high'] += 1
                    elif anomaly.severity == 'medium':
                        severity_counts['medium'] += 1
                    else:
                        severity_counts['low'] += 1
                    
                    weighted_scores.append((weight, anomaly.score))
            
            # Calculate composite anomaly score
            anomaly_score = self._calculate_composite_score(weighted_scores)
            
            # Log anomalies
            self._log_anomalies(extracted_data, anomaly_flags)
            
            # Determine overall severity level
            overall_severity = self._determine_overall_severity(severity_counts)
            
            result = {
                'anomaly_score': anomaly_score,
                'anomaly_flags': anomaly_flags,
                'severity_breakdown': severity_counts,
                'overall_severity': overall_severity,
                'has_critical': severity_counts['critical'] > 0,
                'has_high': severity_counts['high'] > 0,
                'total_anomalies': len(anomaly_flags),
            }
            
            logger.info(f"Anomaly detection for {extracted_data.invoice_number}: score={anomaly_score}, anomalies={len(anomaly_flags)}")
            return result
            
        except Exception as e:
            logger.error(f"Error detecting anomalies for {extracted_data.id}: {str(e)}")
            return {
                'anomaly_score': 0,
                'anomaly_flags': [],
                'severity_breakdown': {'critical': 0, 'high': 0, 'medium': 0, 'low': 0},
                'overall_severity': 'info',
                'has_critical': False,
                'has_high': False,
                'total_anomalies': 0,
            }
    
    def _get_anomaly_weight(self, anomaly_type):
        """Get weight multiplier for anomaly type"""
        weights = {
            'potential_duplicate': self.DUPLICATE_WEIGHT,
            'amount_spike': self.AMOUNT_ANOMALY_WEIGHT,
            'amount_drop': self.AMOUNT_ANOMALY_WEIGHT,
            'suspicious_discount': self.DISCOUNT_ANOMALY_WEIGHT,
            'vat_inconsistency': self.VAT_ANOMALY_WEIGHT,
            'frequency_anomaly': self.FREQUENCY_ANOMALY_WEIGHT,
            'unusual_amount': self.AMOUNT_ANOMALY_WEIGHT,
            'vendor_pattern_break': 25,
            'cross_vendor_match': 35,
        }
        return weights.get(anomaly_type, 20)
    
    def _calculate_composite_score(self, weighted_scores):
        """
        Calculate composite anomaly score from weighted individual scores
        
        Returns:
            int: 0-100 composite score
        """
        if not weighted_scores:
            return 0
        
        # Weighted average approach
        total_weight = sum(w for w, _ in weighted_scores)
        weighted_sum = sum(w * s for w, s in weighted_scores)
        
        if total_weight == 0:
            return 0
        
        composite = (weighted_sum / total_weight)
        
        # Apply non-linear scaling - anomalies compound
        # Higher anomaly score should be weighted more heavily
        if composite > 50:
            composite = composite * 1.2  # Boost high anomalies
        
        composite = min(100, composite)
        
        return int(composite)
    
    def _determine_overall_severity(self, severity_counts):
        """Determine overall severity level"""
        if severity_counts['critical'] > 0:
            return 'critical'
        elif severity_counts['high'] > 1:
            return 'high'
        elif severity_counts['high'] > 0 or severity_counts['medium'] > 2:
            return 'high'
        elif severity_counts['medium'] > 0:
            return 'medium'
        elif severity_counts['low'] > 0:
            return 'low'
        else:
            return 'info'
    
    def _log_anomalies(self, extracted_data, anomaly_flags):
        """Create AnomalyLog entries for each anomaly"""
        try:
            for flag in anomaly_flags:
                AnomalyLog.objects.create(
                    extracted_data=extracted_data,
                    organization=extracted_data.organization,
                    anomaly_type=flag['type'],
                    description=flag.get('description', ''),
                    detected_value=str(flag.get('value', '')),
                    confidence_score=flag.get('score', 50),
                    severity=flag.get('severity', 'warning'),
                    context_data=flag.get('context', {}),
                    detection_method='cross_document',
                    is_confirmed=False,
                )
        except Exception as e:
            logger.warning(f"Error logging anomalies: {str(e)}")
    
    def get_anomaly_summary(self, anomaly_detection_result):
        """Generate human-readable summary of anomalies"""
        flags = anomaly_detection_result['anomaly_flags']
        
        if not flags:
            return "No anomalies detected"
        
        # Group by type
        by_type = {}
        for flag in flags:
            atype = flag['type']
            by_type[atype] = by_type.get(atype, 0) + 1
        
        # Build summary
        summary_parts = []
        
        if by_type.get('potential_duplicate', 0) > 0:
            summary_parts.append(f"{by_type['potential_duplicate']} potential duplicate(s)")
        
        if by_type.get('amount_spike', 0) > 0:
            summary_parts.append("amount spike")
        
        if by_type.get('vat_inconsistency', 0) > 0:
            summary_parts.append("VAT inconsistency")
        
        if by_type.get('suspicious_discount', 0) > 0:
            summary_parts.append("unusual discount")
        
        if by_type.get('frequency_anomaly', 0) > 0:
            summary_parts.append("frequency spike")
        
        if summary_parts:
            return "Detected: " + ", ".join(summary_parts)
        
        return f"{len(flags)} anomalies detected"


# Singleton instance
invoice_anomaly_detection_service = InvoiceAnomalyDetectionService()

