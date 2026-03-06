"""
Phase 4: Cross-Document Validation Service

Compares current invoice against historical invoices to detect:
- Unusual amount changes (spikes, drops)
- Unusual discounts
- Inconsistent VAT behavior
- Suspicious frequency spikes
"""

import logging
from datetime import timedelta, datetime
from decimal import Decimal, InvalidOperation
from django.db.models import Avg, Min, Max, Count, Q

from documents.models import ExtractedData

logger = logging.getLogger(__name__)


class CrossDocumentAnomaly:
    """Result object for a detected anomaly"""
    
    def __init__(self, anomaly_type, description, severity, score, context):
        self.anomaly_type = anomaly_type  # Type of anomaly
        self.description = description    # Human-readable description
        self.severity = severity          # low, medium, high, critical
        self.score = score                # 0-100 confidence
        self.context = context            # Additional details


class InvoiceCrossDocumentValidationService:
    """Service for cross-document validation and anomaly detection"""
    
    # Thresholds for anomaly detection
    AMOUNT_SPIKE_THRESHOLD = 1.5  # 50% increase is suspicious
    AMOUNT_DROP_THRESHOLD = 0.5   # 50% decrease is suspicious
    DISCOUNT_THRESHOLD_PCT = 20    # >20% discount is big
    VAT_INCONSISTENCY_THRESHOLD = 0.05  # 5% difference in VAT rate
    FREQUENCY_SPIKE_THRESHOLD = 3       # 3x normal frequency
    
    def validate_against_history(self, extracted_data):
        """
        Validate invoice against historical data from same vendor/customer
        
        Returns:
            list of CrossDocumentAnomaly objects
        """
        anomalies = []
        
        try:
            # Get historical invoices
            vendor_history = self._get_vendor_history(extracted_data)
            
            if not vendor_history.exists():
                logger.info(f"No vendor history for {extracted_data.vendor_name}")
                return anomalies
            
            # Check for amount anomalies
            anomalies.extend(self._check_amount_anomalies(extracted_data, vendor_history))
            
            # Check for discount anomalies
            anomalies.extend(self._check_discount_anomalies(extracted_data, vendor_history))
            
            # Check for VAT anomalies
            anomalies.extend(self._check_vat_anomalies(extracted_data, vendor_history))
            
            # Check for frequency anomalies
            anomalies.extend(self._check_frequency_anomalies(extracted_data, vendor_history))
            
            logger.info(f"Cross-document validation for {extracted_data.invoice_number}: found {len(anomalies)} anomalies")
            
        except Exception as e:
            logger.error(f"Error in cross-document validation for {extracted_data.id}: {str(e)}")
        
        return anomalies
    
    def _get_vendor_history(self, extracted_data):
        """Get historical invoices from same vendor"""
        return ExtractedData.objects.filter(
            organization=extracted_data.organization,
            vendor_name__iexact=extracted_data.vendor_name,
            extraction_status='extracted',
            is_valid=True
        ).exclude(
            id=extracted_data.id
        ).order_by('-invoice_date')[0:200]  # Last 200 invoices
    
    def _get_vendor_stats(self, vendor_history):
        """Calculate statistics from vendor history"""
        stats = vendor_history.aggregate(
            avg_amount=Avg('total_amount'),
            min_amount=Min('total_amount'),
            max_amount=Max('total_amount'),
            count=Count('id'),
        )
        
        # Calculate standard deviation manually
        amounts = [inv.total_amount for inv in vendor_history if inv.total_amount]
        if amounts and stats['avg_amount']:
            avg = float(stats['avg_amount'])
            variance = sum((float(a) - avg) ** 2 for a in amounts) / len(amounts)
            stats['std_dev'] = variance ** 0.5
        else:
            stats['std_dev'] = 0
        
        return stats
    
    def _safe_decimal(self, value):
        """Safely convert to Decimal"""
        if value is None:
            return Decimal('0')
        try:
            return Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError):
            return Decimal('0')
    
    def _check_amount_anomalies(self, extracted_data, vendor_history):
        """Check for unusual amount changes"""
        anomalies = []
        
        if not extracted_data.total_amount:
            return anomalies
        
        try:
            stats = self._get_vendor_stats(vendor_history)
            
            if not stats['avg_amount'] or stats['count'] < 3:
                return anomalies  # Need at least 3 historical invoices
            
            current_amt = float(self._safe_decimal(extracted_data.total_amount))
            avg_amt = float(stats['avg_amount'])
            std_dev = float(stats['std_dev'])
            
            # Check for spike
            if current_amt > avg_amt * self.AMOUNT_SPIKE_THRESHOLD:
                spike_pct = ((current_amt - avg_amt) / avg_amt) * 100
                anomalies.append(CrossDocumentAnomaly(
                    anomaly_type='amount_spike',
                    description=f'Invoice amount {spike_pct:.1f}% higher than vendor average',
                    severity='high' if spike_pct > 100 else 'medium',
                    score=min(100, 50 + int(spike_pct / 2)),
                    context={
                        'current': current_amt,
                        'average': avg_amt,
                        'spike_percentage': spike_pct,
                        'historical_count': stats['count'],
                    }
                ))
            
            # Check for drop
            elif current_amt < avg_amt * self.AMOUNT_DROP_THRESHOLD:
                drop_pct = ((avg_amt - current_amt) / avg_amt) * 100
                anomalies.append(CrossDocumentAnomaly(
                    anomaly_type='amount_drop',
                    description=f'Invoice amount {drop_pct:.1f}% lower than vendor average',
                    severity='low' if drop_pct < 50 else 'medium',
                    score=min(100, 30 + int(drop_pct / 3)),
                    context={
                        'current': current_amt,
                        'average': avg_amt,
                        'drop_percentage': drop_pct,
                        'historical_count': stats['count'],
                    }
                ))
            
        except Exception as e:
            logger.warning(f"Error checking amount anomalies: {str(e)}")
        
        return anomalies
    
    def _check_discount_anomalies(self, extracted_data, vendor_history):
        """Check for unusual discounts"""
        anomalies = []
        
        try:
            # Calculate discount if we have items
            items = extracted_data.items_json
            if not items or not isinstance(items, list):
                return anomalies
            
            # Look for line-item discounts
            discount_found = False
            max_discount = 0
            
            for item in items:
                if isinstance(item, dict):
                    # Check for discount field or negative amounts
                    discount_pct = item.get('discount_percent', 0)
                    if discount_pct > self.DISCOUNT_THRESHOLD_PCT:
                        max_discount = max(max_discount, discount_pct)
                        discount_found = True
            
            if discount_found:
                # Check if this vendor usually gives discounts
                vendor_discount_rate = self._get_vendor_discount_rate(vendor_history)
                
                if vendor_discount_rate < 5 and max_discount > 20:  # Unusual for this vendor
                    anomalies.append(CrossDocumentAnomaly(
                        anomaly_type='suspicious_discount',
                        description=f'Unusual {max_discount:.0f}% discount (vendor typically gives <5%)',
                        severity='medium',
                        score=75,
                        context={
                            'discount_percentage': max_discount,
                            'vendor_typical': vendor_discount_rate,
                            'historical_count': vendor_history.count(),
                        }
                    ))
        
        except Exception as e:
            logger.warning(f"Error checking discount anomalies: {str(e)}")
        
        return anomalies
    
    def _get_vendor_discount_rate(self, vendor_history):
        """Calculate average discount rate from vendor history"""
        discount_rates = []
        
        for inv in vendor_history[:20]:  # Sample last 20
            if inv.items_json and isinstance(inv.items_json, list):
                for item in inv.items_json:
                    if isinstance(item, dict):
                        discount = item.get('discount_percent', 0)
                        if discount > 0:
                            discount_rates.append(discount)
        
        if discount_rates:
            return sum(discount_rates) / len(discount_rates)
        return 0
    
    def _check_vat_anomalies(self, extracted_data, vendor_history):
        """Check for VAT inconsistencies"""
        anomalies = []
        
        try:
            if not extracted_data.total_amount or not extracted_data.tax_amount:
                return anomalies
            
            current_vat_rate = float(self._safe_decimal(extracted_data.tax_amount)) / float(self._safe_decimal(extracted_data.total_amount))
            
            # Get vendor's typical VAT rate
            historical_vat_rates = []
            for inv in vendor_history[:20]:
                if inv.total_amount and inv.tax_amount:
                    vat_rate = float(self._safe_decimal(inv.tax_amount)) / float(self._safe_decimal(inv.total_amount))
                    historical_vat_rates.append(vat_rate)
            
            if not historical_vat_rates or len(historical_vat_rates) < 3:
                return anomalies
            
            avg_vat_rate = sum(historical_vat_rates) / len(historical_vat_rates)
            rate_diff = abs(current_vat_rate - avg_vat_rate)
            
            if rate_diff > self.VAT_INCONSISTENCY_THRESHOLD:
                anomalies.append(CrossDocumentAnomaly(
                    anomaly_type='vat_inconsistency',
                    description=f'VAT rate {current_vat_rate*100:.1f}% differs from vendor norm {avg_vat_rate*100:.1f}%',
                    severity='high',
                    score=80,
                    context={
                        'current_vat_rate': current_vat_rate,
                        'vendor_typical': avg_vat_rate,
                        'difference': rate_diff,
                        'historical_count': len(historical_vat_rates),
                    }
                ))
        
        except Exception as e:
            logger.warning(f"Error checking VAT anomalies: {str(e)}")
        
        return anomalies
    
    def _check_frequency_anomalies(self, extracted_data, vendor_history):
        """Check for suspicious frequency spikes"""
        anomalies = []
        
        try:
            # Count invoices from this vendor in last 30 days
            thirty_days_ago = extracted_data.invoice_date - timedelta(days=30)
            recent_count = vendor_history.filter(
                invoice_date__gte=thirty_days_ago
            ).count()
            
            # Get average frequency
            if vendor_history.count() >= 5:
                # Calculate average invoices per month
                date_range = (vendor_history.first().invoice_date - vendor_history.last().invoice_date).days
                if date_range > 0:
                    months = date_range / 30
                    avg_per_month = vendor_history.count() / months if months > 0 else 0
                    current_monthly_rate = recent_count  # Last 30 days ≈ 1 month
                    
                    if current_monthly_rate > avg_per_month * self.FREQUENCY_SPIKE_THRESHOLD:
                        anomalies.append(CrossDocumentAnomaly(
                            anomaly_type='frequency_anomaly',
                            description=f'Invoice frequency spike: {current_monthly_rate:.0f} in last 30 days vs average {avg_per_month:.1f}/month',
                            severity='medium',
                            score=65,
                            context={
                                'recent_30d_count': recent_count,
                                'typical_monthly': avg_per_month,
                                'spike_ratio': current_monthly_rate / avg_per_month if avg_per_month > 0 else 0,
                            }
                        ))
        
        except Exception as e:
            logger.warning(f"Error checking frequency anomalies: {str(e)}")
        
        return anomalies


# Singleton instance
invoice_cross_document_validation_service = InvoiceCrossDocumentValidationService()

