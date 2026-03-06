import logging
from datetime import timedelta
from decimal import Decimal
from django.utils import timezone
from django.db import models
from django.db.models import Avg, Count, Q, Sum
from documents.models import ExtractedData, CashFlowForecast
from core.models import Organization

logger = logging.getLogger(__name__)


class InvoiceCashFlowService:
    """
    Phase 5 - Cash Flow Forecasting Service
    
    Analyzes vendor payment patterns and generates 30/60/90 day cash flow forecasts.
    Uses historical payment data to predict when invoices will likely be paid.
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(InvoiceCashFlowService, cls).__new__(cls)
        return cls._instance
    
    def generate_cash_flow_forecast(self, extracted_data: ExtractedData, organization: Organization) -> dict:
        """
        Generate cash flow forecast for an invoice based on vendor payment history.
        
        Returns:
            dict: Forecast data with 30/60/90 day projections and confidence metrics
        """
        try:
            logger.info(f"Generating cash flow forecast for invoice {extracted_data.invoice_number}")
            
            # Extract invoice payment terms
            invoice_date = extracted_data.invoice_date
            due_date = extracted_data.due_date
            invoice_amount = extracted_data.total_amount
            currency = extracted_data.currency or 'SAR'
            
            # Analyze vendor payment history
            vendor_name = extracted_data.vendor_name
            payment_history = self._analyze_vendor_payment_history(
                organization, vendor_name, vendor_country=extracted_data.vendor_country
            )
            
            # Calculate average payment delay
            avg_delay_days = payment_history['avg_payment_delay_days']
            payment_consistency = payment_history['payment_consistency']
            on_time_rate = payment_history['on_time_rate']
            
            # Project payment dates (30/60/90 days from invoice date)
            projected_30d = self._calculate_projected_payment(
                due_date, avg_delay_days, confidence=payment_consistency
            )
            projected_60d = projected_30d + timedelta(days=30) if projected_30d else None
            projected_90d = projected_60d + timedelta(days=30) if projected_60d else None
            
            # Determine forecast method confidence
            confidence_score = self._calculate_confidence_score(
                payment_history, payment_consistency, on_time_rate
            )
            forecast_method = self._select_forecast_method(payment_history)
            
            # Create cash flow forecast record
            forecast_data = {
                'extracted_data': extracted_data,
                'organization': organization,
                'invoice_date': invoice_date,
                'due_date': due_date,
                'invoice_amount': invoice_amount,
                'currency': currency,
                'projected_payment_30d': projected_30d,
                'projected_payment_60d': projected_60d,
                'projected_payment_90d': projected_90d,
                'payment_status': 'pending',
                'confidence_score': confidence_score,
                'forecast_method': forecast_method,
            }
            
            # Save forecast record
            cash_flow_forecast = CashFlowForecast.objects.create(**forecast_data)
            
            return {
                'success': True,
                'forecast': {
                    'invoice_number': extracted_data.invoice_number,
                    'vendor_name': vendor_name,
                    'invoice_amount': float(invoice_amount),
                    'currency': currency,
                    'due_date': str(due_date),
                    'projected_payment_30d': str(projected_30d) if projected_30d else None,
                    'projected_payment_60d': str(projected_60d) if projected_60d else None,
                    'projected_payment_90d': str(projected_90d) if projected_90d else None,
                    'confidence_score': confidence_score,
                    'forecast_method': forecast_method,
                    'payment_history': {
                        'avg_delay_days': avg_delay_days,
                        'on_time_rate': round(on_time_rate, 2),
                        'consistency_score': round(payment_consistency, 2),
                        'total_invoices_analyzed': payment_history['invoice_count'],
                    },
                },
                'workflow': {
                    'forecast_created': True,
                    'record_id': cash_flow_forecast.id,
                }
            }
            
        except Exception as e:
            logger.error(f"Error in cash flow forecasting: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'forecast': {
                    'invoice_number': extracted_data.invoice_number,
                    'projected_payment_30d': None,
                    'projected_payment_60d': None,
                    'projected_payment_90d': None,
                    'confidence_score': 0.0,
                    'payment_status': 'pending',
                }
            }
    
    def _analyze_vendor_payment_history(self, organization: Organization, vendor_name: str, 
                                       vendor_country: str = None) -> dict:
        """
        Analyze historical payment behavior for a vendor.
        
        Returns:
            dict: Payment metrics including average delay, consistency, and on-time rate
        """
        try:
            # Find all previous invoices from this vendor
            vendor_invoices = ExtractedData.objects.filter(
                organization=organization,
                vendor_name__icontains=vendor_name if vendor_name else '',
                actual_payment_date__isnull=False  # Only paid invoices
            ).order_by('-invoice_date')[:50]  # Last 50 invoices
            
            if not vendor_invoices.exists():
                # No payment history - use industry defaults
                logger.info(f"No payment history for vendor {vendor_name}, using industry defaults")
                return self._get_industry_default_values()
            
            # Calculate payment metrics
            delays = []
            on_time_count = 0
            
            for invoice in vendor_invoices:
                if invoice.due_date and invoice.actual_payment_date:
                    delay = (invoice.actual_payment_date - invoice.due_date).days
                    delays.append(delay)
                    
                    if delay <= 0:  # Paid on time or early
                        on_time_count += 1
            
            if not delays:
                # Invoices have no due/payment dates
                return self._get_industry_default_values()
            
            avg_delay = sum(delays) / len(delays)
            payment_consistency = 1.0 - (sum(abs(d - avg_delay) for d in delays) / len(delays) / 30)
            payment_consistency = max(0.0, min(1.0, payment_consistency))  # Clamp 0-1
            on_time_rate = on_time_count / len(delays) if delays else 0.5
            
            return {
                'avg_payment_delay_days': round(avg_delay),
                'payment_consistency': payment_consistency,
                'on_time_rate': on_time_rate,
                'invoice_count': len(vendor_invoices),
                'has_history': True,
            }
            
        except Exception as e:
            logger.warning(f"Error analyzing vendor payment history: {str(e)}")
            return self._get_industry_default_values()
    
    def _get_industry_default_values(self) -> dict:
        """
        Return default payment metrics when vendor history is unavailable.
        Based on typical Middle East payment patterns (30-45 day terms).
        """
        return {
            'avg_payment_delay_days': 15,  # Assume 15 days after due date
            'payment_consistency': 0.6,  # Moderate consistency
            'on_time_rate': 0.4,  # 40% on-time payment typical
            'invoice_count': 0,
            'has_history': False,
        }
    
    def _calculate_projected_payment(self, due_date, avg_delay_days: int, confidence: float = 0.8) -> object:
        """
        Calculate projected payment date based on due date and historical delay.
        
        Args:
            due_date: Invoice due date
            avg_delay_days: Average payment delay from historical data
            confidence: Confidence in prediction (higher = more trust in history)
        
        Returns:
            date: Projected payment date
        """
        if not due_date:
            return None
        
        # Adjust delay based on confidence
        adjusted_delay = int(avg_delay_days * (1 + (1 - confidence)))
        
        # Project 30 days from invoice date as baseline
        projected_date = due_date + timedelta(days=adjusted_delay)
        
        return projected_date
    
    def _calculate_confidence_score(self, payment_history: dict, consistency: float, on_time_rate: float) -> float:
        """
        Calculate confidence score for the forecast (0-1 scale).
        
        Factors:
        - Payment history availability (has_history)
        - Consistency of vendor payments
        - On-time payment rate
        """
        base_score = 0.5  # Base confidence
        
        if payment_history.get('has_history'):
            base_score += 0.2  # Boost for having history
        
        base_score += consistency * 0.2  # Add consistency factor
        base_score += on_time_rate * 0.1  # Add on-time payment factor
        
        return min(1.0, max(0.0, base_score))
    
    def _select_forecast_method(self, payment_history: dict) -> str:
        """
        Select the forecast method based on available data.
        
        Methods:
        - historical_avg: Based on vendor payment history
        - vendor_profile: Based on vendor risk profile
        - industry_standard: Using industry averages
        - manual: Requires manual entry
        """
        if payment_history.get('has_history'):
            return 'historical_avg'
        return 'industry_standard'
    
    def aggregate_cash_flow_by_currency(self, organization: Organization, 
                                      num_days: int = 30) -> dict:
        """
        Aggregate cash flow forecasts by currency for a given period.
        
        Returns:
            dict: Aggregated cash flow by currency with totals and counts
        """
        try:
            cutoff_date = timezone.now().date() + timedelta(days=num_days)
            
            forecasts = CashFlowForecast.objects.filter(
                organization=organization,
                projected_payment_30d__lte=cutoff_date,
                payment_status__in=['pending', 'scheduled']
            ).values('currency').annotate(
                total_amount=Sum('invoice_amount'),
                invoice_count=Count('id'),
                avg_amount=Avg('invoice_amount')
            )
            
            result = {
                'period_days': num_days,
                'cutoff_date': str(cutoff_date),
                'currency_summary': {}
            }
            
            for forecast in forecasts:
                currency = forecast['currency']
                result['currency_summary'][currency] = {
                    'total_amount': float(forecast['total_amount'] or 0),
                    'invoice_count': forecast['invoice_count'],
                    'average_invoice': float(forecast['avg_amount'] or 0),
                }
            
            return result
            
        except Exception as e:
            logger.error(f"Error aggregating cash flow: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def get_cash_flow_pressure_indicators(self, organization: Organization) -> dict:
        """
        Identify cash flow pressure points in upcoming periods.
        
        Returns:
            dict: Risk indicators and high-pressure dates
        """
        try:
            today = timezone.now().date()
            
            # Check 30, 60, 90 day windows
            windows = {
                '30_days': (today, today + timedelta(days=30)),
                '60_days': (today + timedelta(days=30), today + timedelta(days=60)),
                '90_days': (today + timedelta(days=60), today + timedelta(days=90)),
            }
            
            result = {'pressure_by_window': {}}
            
            for window_name, (start_date, end_date) in windows.items():
                forecast_data = CashFlowForecast.objects.filter(
                    organization=organization,
                    projected_payment_30d__gte=start_date,
                    projected_payment_30d__lte=end_date
                ).aggregate(
                    total_amount=Sum('invoice_amount'),
                    invoice_count=Count('id')
                )
                
                total_amount = forecast_data['total_amount'] or Decimal('0')
                invoice_count = forecast_data['invoice_count'] or 0
                
                # Pressure indicator: total above threshold (e.g., 1M)
                pressure_threshold = Decimal('1000000')
                pressure_risk = 'high' if total_amount > pressure_threshold else 'medium' if total_amount > pressure_threshold / 2 else 'low'
                
                result['pressure_by_window'][window_name] = {
                    'period': f"{start_date} to {end_date}",
                    'total_forecasted_payment': float(total_amount),
                    'invoice_count': invoice_count,
                    'pressure_risk': pressure_risk,
                }
            
            return result
            
        except Exception as e:
            logger.error(f"Error calculating cash flow pressure: {str(e)}")
            return {'success': False, 'error': str(e)}


def get_cash_flow_service() -> InvoiceCashFlowService:
    """Get singleton instance of cash flow service."""
    return InvoiceCashFlowService()
