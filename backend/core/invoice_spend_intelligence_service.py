import logging
from datetime import timedelta, datetime
from decimal import Decimal
from django.utils import timezone
from django.db.models import Sum, Count, Avg, Q
from documents.models import ExtractedData, SpendCategory
from core.models import Organization

logger = logging.getLogger(__name__)


class InvoiceSpendIntelligenceService:
    """
    Phase 5 - Spend Intelligence Service
    
    Analyzes vendor spending patterns, category trends, and spending velocity.
    Identifies top vendors, spending trends, and category distribution.
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(InvoiceSpendIntelligenceService, cls).__new__(cls)
        return cls._instance
    
    def analyze_spending_patterns(self, organization: Organization, extracted_data: ExtractedData) -> dict:
        """
        Analyze spending patterns for an organization based on new invoice data.
        
        Returns:
            dict: Spending analysis including top vendors, categories, and trends
        """
        try:
            logger.info(f"Analyzing spending patterns for invoice {extracted_data.invoice_number}")
            
            # Get all invoices for this organization
            all_invoices = ExtractedData.objects.filter(
                organization=organization,
                status='processed'
            ).order_by('-invoice_date')
            
            if not all_invoices.exists():
                logger.warning(f"No processed invoices found for organization {organization.name}")
                return self._empty_spending_analysis()
            
            # Get current month's invoices
            today = timezone.now().date()
            current_month_start = today.replace(day=1)
            current_month_invoices = all_invoices.filter(
                invoice_date__gte=current_month_start
            )
            
            # Get previous month for comparison
            if current_month_start.month == 1:
                prev_month_start = current_month_start.replace(year=current_month_start.year - 1, month=12)
            else:
                prev_month_start = current_month_start.replace(month=current_month_start.month - 1)
            
            prev_month_end = current_month_start - timedelta(days=1)
            prev_month_invoices = all_invoices.filter(
                invoice_date__gte=prev_month_start,
                invoice_date__lte=prev_month_end
            )
            
            # Calculate spending metrics
            current_month_spend = self._calculate_total_spend(current_month_invoices)
            prev_month_spend = self._calculate_total_spend(prev_month_invoices)
            trend_percent = self._calculate_trend(current_month_spend, prev_month_spend)
            
            # Get top vendors
            top_vendors = self._get_top_vendors(all_invoices, limit=10)
            
            # Get spending by category
            categories = self._get_category_breakdown(all_invoices)
            
            # Create SpendCategory records for current period
            for category_name, amount in categories.items():
                self._create_or_update_spend_category(
                    organization, category_name, current_month_start, 
                    amount, current_month_invoices
                )
            
            # Get high-cost items
            high_cost_items = self._get_high_cost_items(all_invoices, limit=5)
            
            # Calculate YTD metrics
            ytd_start = today.replace(month=1, day=1)
            ytd_invoices = all_invoices.filter(invoice_date__gte=ytd_start)
            ytd_spend = self._calculate_total_spend(ytd_invoices)
            
            return {
                'success': True,
                'analysis': {
                    'period': {
                        'current_month': str(current_month_start),
                        'previous_month': str(prev_month_start),
                    },
                    'spending': {
                        'current_month_total': float(current_month_spend),
                        'previous_month_total': float(prev_month_spend),
                        'trend_percent': round(trend_percent, 2),
                        'ytd_total': float(ytd_spend),
                        'invoice_count_current_month': current_month_invoices.count(),
                        'invoice_count_ytd': ytd_invoices.count(),
                    },
                    'top_vendors': top_vendors,
                    'category_breakdown': categories,
                    'high_cost_items': high_cost_items,
                    'vendor_count': all_invoices.values('vendor_name').distinct().count(),
                }
            }
            
        except Exception as e:
            logger.error(f"Error in spend analysis: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'analysis': {}
            }
    
    def _calculate_total_spend(self, invoices) -> Decimal:
        """Calculate total spending from set of invoices (in SAR equivalent)."""
        try:
            total = Decimal('0')
            for invoice in invoices:
                amount = invoice.total_amount or Decimal('0')
                total += amount
            return total
        except Exception as e:
            logger.warning(f"Error calculating spend total: {str(e)}")
            return Decimal('0')
    
    def _calculate_trend(self, current: Decimal, previous: Decimal) -> float:
        """Calculate month-over-month trend percentage."""
        try:
            if previous == 0:
                return 100.0 if current > 0 else 0.0
            trend = ((current - previous) / previous) * 100
            return float(trend)
        except Exception as e:
            logger.warning(f"Error calculating trend: {str(e)}")
            return 0.0
    
    def _get_top_vendors(self, invoices, limit: int = 10) -> list:
        """Get top vendors by total spending."""
        try:
            vendor_spend = {}
            for invoice in invoices:
                vendor = invoice.vendor_name or 'Unknown'
                amount = invoice.total_amount or Decimal('0')
                
                if vendor not in vendor_spend:
                    vendor_spend[vendor] = Decimal('0')
                vendor_spend[vendor] += amount
            
            # Sort by spend descending
            sorted_vendors = sorted(vendor_spend.items(), key=lambda x: x[1], reverse=True)[:limit]
            
            return [
                {
                    'vendor_name': vendor,
                    'total_spend': float(amount),
                    'invoice_count': invoices.filter(vendor_name=vendor).count(),
                }
                for vendor, amount in sorted_vendors
            ]
        except Exception as e:
            logger.warning(f"Error getting top vendors: {str(e)}")
            return []
    
    def _get_category_breakdown(self, invoices) -> dict:
        """Get spending breakdown by item category."""
        try:
            category_spend = {}
            
            for invoice in invoices:
                category = invoice.item_category or 'Uncategorized'
                amount = invoice.total_amount or Decimal('0')
                
                if category not in category_spend:
                    category_spend[category] = Decimal('0')
                category_spend[category] += amount
            
            # Convert to dict with float values and percentages
            result = {}
            total_spend = sum(category_spend.values())
            
            for category, amount in sorted(category_spend.items(), key=lambda x: x[1], reverse=True):
                percent = (float(amount) / float(total_spend) * 100) if total_spend > 0 else 0
                result[category] = {
                    'amount': float(amount),
                    'percent': round(percent, 2)
                }
            
            return result
        except Exception as e:
            logger.warning(f"Error getting category breakdown: {str(e)}")
            return {}
    
    def _create_or_update_spend_category(self, organization: Organization, category: str,
                                        month_start: datetime.date, amount: Decimal, invoices):
        """Create or update SpendCategory record."""
        try:
            previous_record = SpendCategory.objects.filter(
                organization=organization,
                category=category,
                month=month_start
            ).first()
            
            if previous_record and previous_record.month < month_start:
                prev_amount = previous_record.monthly_amount
            else:
                prev_amount = Decimal('0')
            
            trend_percent = self._calculate_trend(amount, prev_amount)
            
            top_vendor = None
            vendor_amount = Decimal('0')
            vendor_invoices = invoices.filter(item_category=category)
            if vendor_invoices.exists():
                vendor_data = self._get_top_vendors(vendor_invoices, limit=1)
                if vendor_data:
                    top_vendor = vendor_data[0]['vendor_name']
                    vendor_amount = Decimal(str(vendor_data[0]['total_spend']))
            
            SpendCategory.objects.update_or_create(
                organization=organization,
                category=category,
                month=month_start,
                defaults={
                    'monthly_amount': amount,
                    'invoice_count': invoices.filter(item_category=category).count(),
                    'vendor_count': invoices.filter(item_category=category).values('vendor_name').distinct().count(),
                    'previous_month_amount': prev_amount,
                    'trend_percent': trend_percent,
                    'top_vendor': top_vendor,
                    'top_vendor_amount': vendor_amount,
                }
            )
        except Exception as e:
            logger.warning(f"Error creating/updating spend category record: {str(e)}")
    
    def _get_high_cost_items(self, invoices, limit: int = 5) -> list:
        """Get highest single invoices (high-cost items)."""
        try:
            high_cost = invoices.order_by('-total_amount')[:limit].values(
                'invoice_number', 'vendor_name', 'total_amount', 'invoice_date', 'item_category'
            )
            
            return [
                {
                    'invoice_number': item['invoice_number'],
                    'vendor': item['vendor_name'],
                    'amount': float(item['total_amount']),
                    'date': str(item['invoice_date']),
                    'category': item['item_category'],
                }
                for item in high_cost
            ]
        except Exception as e:
            logger.warning(f"Error getting high-cost items: {str(e)}")
            return []
    
    def _empty_spending_analysis(self) -> dict:
        """Return empty spending analysis structure."""
        return {
            'success': False,
            'error': 'No data available',
            'analysis': {
                'spending': {
                    'current_month_total': 0,
                    'previous_month_total': 0,
                    'trend_percent': 0,
                    'ytd_total': 0,
                    'invoice_count_current_month': 0,
                    'invoice_count_ytd': 0,
                },
                'top_vendors': [],
                'category_breakdown': {},
                'high_cost_items': [],
                'vendor_count': 0,
            }
        }
    
    def get_vendor_spend_trends(self, organization: Organization, vendor_name: str,
                               num_months: int = 12) -> dict:
        """
        Get historical spending trends for a specific vendor.
        
        Returns:
            dict: Monthly spending data and trends
        """
        try:
            today = timezone.now().date()
            vendor_invoices = ExtractedData.objects.filter(
                organization=organization,
                vendor_name__icontains=vendor_name if vendor_name else '',
                status='processed'
            ).order_by('-invoice_date')
            
            # Get monthly aggregates
            monthly_data = {}
            for i in range(num_months):
                month_start = (today.replace(day=1) - timedelta(days=30*i)).replace(day=1)
                month_invoices = vendor_invoices.filter(
                    invoice_date__gte=month_start,
                    invoice_date__lt=month_start + timedelta(days=32)
                )
                
                month_spend = self._calculate_total_spend(month_invoices)
                monthly_data[str(month_start)] = {
                    'amount': float(month_spend),
                    'invoice_count': month_invoices.count(),
                }
            
            return {
                'success': True,
                'vendor': vendor_name,
                'monthly_trends': monthly_data,
                'total_invoices': vendor_invoices.count(),
                'total_spend': float(self._calculate_total_spend(vendor_invoices)),
            }
        except Exception as e:
            logger.error(f"Error getting vendor trends: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def identify_spending_anomalies(self, organization: Organization) -> dict:
        """
        Identify unusual spending patterns (spikes, new vendors, category shifts).
        
        Returns:
            dict: Anomalies detected with severity and details
        """
        try:
            today = timezone.now().date()
            current_month_start = today.replace(day=1)
            
            if current_month_start.month == 1:
                prev_month_start = current_month_start.replace(year=current_month_start.year - 1, month=12)
            else:
                prev_month_start = current_month_start.replace(month=current_month_start.month - 1)
            
            prev_month_end = current_month_start - timedelta(days=1)
            
            current_invoices = ExtractedData.objects.filter(
                organization=organization,
                invoice_date__gte=current_month_start,
                status='processed'
            )
            
            prev_invoices = ExtractedData.objects.filter(
                organization=organization,
                invoice_date__gte=prev_month_start,
                invoice_date__lte=prev_month_end,
                status='processed'
            )
            
            anomalies = []
            
            # Check for spending spikes (>50% increase)
            current_spend = self._calculate_total_spend(current_invoices)
            prev_spend = self._calculate_total_spend(prev_invoices)
            if prev_spend > 0:
                growth_rate = ((current_spend - prev_spend) / prev_spend) * 100
                if growth_rate > 50:
                    anomalies.append({
                        'type': 'spending_spike',
                        'severity': 'high' if growth_rate > 100 else 'medium',
                        'description': f'Spending increased by {round(growth_rate, 1)}%',
                        'value': float(growth_rate),
                    })
            
            # Check for new vendors
            prev_vendors = set(prev_invoices.values_list('vendor_name', flat=True))
            current_vendors = set(current_invoices.values_list('vendor_name', flat=True))
            new_vendors = current_vendors - prev_vendors
            
            if new_vendors:
                anomalies.append({
                    'type': 'new_vendors',
                    'severity': 'medium',
                    'description': f'{len(new_vendors)} new vendors identified',
                    'vendors': list(new_vendors)[:5],  # Top 5
                })
            
            # Check for category shifts
            current_categories = self._get_category_breakdown(current_invoices)
            prev_categories = self._get_category_breakdown(prev_invoices)
            
            for category, current_data in current_categories.items():
                prev_data = prev_categories.get(category, {'amount': 0})
                if prev_data['amount'] > 0:
                    shift = ((current_data['amount'] - prev_data['amount']) / prev_data['amount']) * 100
                    if abs(shift) > 50:
                        anomalies.append({
                            'type': 'category_shift',
                            'severity': 'medium',
                            'category': category,
                            'shift_percent': round(shift, 1),
                        })
            
            return {
                'success': True,
                'anomaly_count': len(anomalies),
                'anomalies': anomalies,
            }
        except Exception as e:
            logger.error(f"Error identifying anomalies: {str(e)}")
            return {'success': False, 'error': str(e)}


def get_spend_intelligence_service() -> InvoiceSpendIntelligenceService:
    """Get singleton instance of spend intelligence service."""
    return InvoiceSpendIntelligenceService()
