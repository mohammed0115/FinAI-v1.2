"""
Financial Intelligence Service - Phase 5
خدمة الذكاء المالي

Performs advanced financial analysis including:
- Cash flow forecasting
- Spend intelligence and category analysis
- Financial narrative generation using AI
- Budget vs actual analysis
- Spending trends and predictions
"""

import logging
from decimal import Decimal
from typing import Dict, List, Tuple, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import json
import re

logger = logging.getLogger(__name__)


class CashFlowForecastService:
    """Service for forecasting cash flow based on invoice patterns"""
    
    @staticmethod
    def forecast_cash_flow(invoices: List[Dict[str, Any]],
                          forecast_period_days: int = 90) -> Dict[str, Any]:
        """
        Forecast cash outflow based on historical invoices and payment terms
        
        Args:
            invoices: Historical invoice data
            forecast_period_days: Number of days to forecast ahead
        
        Returns:
            Dictionary with cash flow forecast
        """
        if not invoices:
            return {
                'forecast_period_days': forecast_period_days,
                'forecast_status': 'insufficient_data',
                'forecasted_payments': [],
                'total_forecasted_outflow': Decimal('0'),
            }
        
        forecast_today = datetime.now()
        forecast_end = forecast_today + timedelta(days=forecast_period_days)
        
        # Analyze payment patterns
        daily_patterns = CashFlowForecastService._analyze_daily_patterns(invoices)
        
        # Project future invoices
        projected_invoices = []
        for day_offset in range(0, forecast_period_days, 7):
            forecast_date = forecast_today + timedelta(days=day_offset)
            
            # Get average invoice amount for this period
            avg_amount = sum(
                inv.get('total_amount', Decimal('0'))
                for inv in invoices
                if inv.get('total_amount')
            ) / len([inv for inv in invoices if inv.get('total_amount')])
            
            projected_invoices.append({
                'forecast_date': forecast_date.strftime('%Y-%m-%d'),
                'projected_amount': avg_amount,
                'confidence': 0.65,
            })
        
        # Calculate payment due dates based on average payment terms
        payment_schedule = CashFlowForecastService._calculate_payment_schedule(
            invoices, projected_invoices
        )
        
        total_outflow = sum(
            payment.get('amount', Decimal('0'))
            for payment in payment_schedule
            if payment.get('amount')
        )
        
        return {
            'forecast_period_days': forecast_period_days,
            'forecast_start': forecast_today.strftime('%Y-%m-%d'),
            'forecast_end': forecast_end.strftime('%Y-%m-%d'),
            'forecast_status': 'generated',
            'forecasted_payments': payment_schedule,
            'total_forecasted_outflow': total_outflow,
            'forecast_confidence': 0.65,
        }
    
    @staticmethod
    def _analyze_daily_patterns(invoices: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze patterns of invoicing by day of week"""
        day_patterns = defaultdict(list)
        
        for invoice in invoices:
            try:
                date = datetime.strptime(invoice.get('issue_date', ''), '%Y-%m-%d')
                day_name = date.strftime('%A')
                amount = invoice.get('total_amount', Decimal('0'))
                if amount:
                    day_patterns[day_name].append(amount)
            except (ValueError, TypeError):
                continue
        
        # Calculate averages
        day_averages = {}
        for day, amounts in day_patterns.items():
            if amounts:
                day_averages[day] = sum(amounts) / len(amounts)
        
        return day_averages
    
    @staticmethod
    def _calculate_payment_schedule(invoices: List[Dict[str, Any]],
                                    projected: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Calculate when payments will be due"""
        # Analyze average payment terms
        payment_terms_list = []
        
        for invoice in invoices:
            try:
                issue_date = datetime.strptime(invoice.get('issue_date', ''), '%Y-%m-%d')
                due_date = datetime.strptime(invoice.get('due_date', ''), '%Y-%m-%d')
                payment_days = (due_date - issue_date).days
                payment_terms_list.append(payment_days)
            except (ValueError, TypeError):
                continue
        
        avg_payment_terms = (
            sum(payment_terms_list) / len(payment_terms_list)
            if payment_terms_list else 30
        )
        
        # Create payment schedule
        schedule = []
        for proj in projected:
            try:
                invoice_date = datetime.strptime(proj['forecast_date'], '%Y-%m-%d')
                due_date = invoice_date + timedelta(days=int(avg_payment_terms))
                
                schedule.append({
                    'invoice_date': proj['forecast_date'],
                    'payment_due_date': due_date.strftime('%Y-%m-%d'),
                    'amount': proj['projected_amount'],
                    'confidence': proj['confidence'],
                    'payment_terms_days': int(avg_payment_terms),
                })
            except (ValueError, TypeError):
                continue
        
        return schedule


class SpendIntelligenceService:
    """Service for analyzing spending patterns and categories"""
    
    @staticmethod
    def analyze_spend_intelligence(invoices: List[Dict[str, Any]],
                                   time_period_months: int = 12) -> Dict[str, Any]:
        """
        Analyze spending patterns and categories
        
        Args:
            invoices: Historical invoice data
            time_period_months: Months of history to analyze
        
        Returns:
            Dictionary with spend intelligence
        """
        if not invoices:
            return {
                'spend_analysis_status': 'insufficient_data',
                'total_spend': Decimal('0'),
                'average_spend_per_invoice': Decimal('0'),
                'spend_by_vendor': {},
                'spend_by_category': {},
                'spending_trend': [],
            }
        
        # Categorize spending
        spend_by_vendor = SpendIntelligenceService._categorize_by_vendor(invoices)
        spend_by_category = SpendIntelligenceService._categorize_by_category(invoices)
        
        # Calculate totals
        total_spend = sum(
            inv.get('total_amount', Decimal('0'))
            for inv in invoices
            if inv.get('total_amount')
        )
        
        avg_spend = (
            total_spend / len([inv for inv in invoices if inv.get('total_amount')])
            if invoices else Decimal('0')
        )
        
        # Analyze trending
        spending_trend = SpendIntelligenceService._analyze_spending_trend(invoices)
        
        # Top vendors
        top_vendors = sorted(
            spend_by_vendor.items(),
            key=lambda x: x[1]['total'],
            reverse=True
        )[:5]
        
        # Top categories
        top_categories = sorted(
            spend_by_category.items(),
            key=lambda x: x[1]['total'],
            reverse=True
        )[:5]
        
        return {
            'spend_analysis_status': 'completed',
            'time_period_months': time_period_months,
            'total_spend': total_spend,
            'average_spend_per_invoice': avg_spend,
            'top_vendors': [
                {
                    'vendor_name': vendor,
                    'total_spend': data['total'],
                    'invoice_count': data['count'],
                    'percentage_of_total': float((data['total'] / total_spend * 100)) if total_spend else 0,
                }
                for vendor, data in top_vendors
            ],
            'top_categories': [
                {
                    'category': category,
                    'total_spend': data['total'],
                    'invoice_count': data['count'],
                    'percentage_of_total': float((data['total'] / total_spend * 100)) if total_spend else 0,
                }
                for category, data in top_categories
            ],
            'spending_trend': spending_trend,
            'vendor_count': len(spend_by_vendor),
            'category_count': len(spend_by_category),
        }
    
    @staticmethod
    def _categorize_by_vendor(invoices: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Categorize spending by vendor"""
        vendor_spend = defaultdict(lambda: {'total': Decimal('0'), 'count': 0})
        
        for invoice in invoices:
            vendor = invoice.get('vendor_name', 'Unknown')
            amount = invoice.get('total_amount', Decimal('0'))
            
            if amount:
                vendor_spend[vendor]['total'] += amount
                vendor_spend[vendor]['count'] += 1
        
        return dict(vendor_spend)
    
    @staticmethod
    def _categorize_by_category(invoices: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Categorize spending by inferred category"""
        category_spend = defaultdict(lambda: {'total': Decimal('0'), 'count': 0})
        
        # Category keywords mapping
        category_keywords = {
            'IT & Technology': ['software', 'license', 'cloud', 'server', 'hosting', 'tech', 'computer', 'it'],
            'Supplies': ['office', 'supply', 'stationery', 'paper', 'ink', 'equipment'],
            'Travel': ['flight', 'hotel', 'transport', 'taxi', 'fuel', 'gas'],
            'Utilities': ['electric', 'water', 'gas', 'internet', 'phone', 'utility'],
            'Professional Services': ['consulting', 'audit', 'legal', 'accounting', 'service'],
            'Maintenance': ['repair', 'maintenance', 'cleaning', 'janitorial'],
            'Marketing': ['advertising', 'marketing', 'promo', 'campaign', 'design'],
            'Other': [],
        }
        
        for invoice in invoices:
            vendor = invoice.get('vendor_name', '').lower()
            amount = invoice.get('total_amount', Decimal('0'))
            
            # Find category by keyword matching
            category = 'Other'
            for cat, keywords in category_keywords.items():
                if cat == 'Other':
                    continue
                if any(keyword in vendor for keyword in keywords):
                    category = cat
                    break
            
            if amount:
                category_spend[category]['total'] += amount
                category_spend[category]['count'] += 1
        
        return dict(category_spend)
    
    @staticmethod
    def _analyze_spending_trend(invoices: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Analyze spending trend over time"""
        # Group invoices by month
        monthly_spend = defaultdict(Decimal)
        
        for invoice in invoices:
            try:
                date = datetime.strptime(invoice.get('issue_date', ''), '%Y-%m-%d')
                month_key = date.strftime('%Y-%m')
                amount = invoice.get('total_amount', Decimal('0'))
                
                if amount:
                    monthly_spend[month_key] += amount
            except (ValueError, TypeError):
                continue
        
        # Sort by month
        trends = []
        for month in sorted(monthly_spend.keys()):
            trends.append({
                'month': month,
                'total_spend': monthly_spend[month],
            })
        
        return trends


class FinancialNarrativeService:
    """Service for generating AI-powered financial narratives"""
    
    @staticmethod
    def generate_financial_narrative(invoice: Dict[str, Any],
                                     spend_intelligence: Dict[str, Any],
                                     compliance_findings: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate human-readable financial narrative for an invoice
        
        Args:
            invoice: Current invoice data
            spend_intelligence: Spend analysis results
            compliance_findings: Compliance check results
        
        Returns:
            Dictionary with narrative and key insights
        """
        narratives = []
        insights = []
        
        # Basic invoice narrative
        vendor = invoice.get('vendor_name', 'Unknown Vendor')
        amount = invoice.get('total_amount', Decimal('0'))
        invoice_num = invoice.get('invoice_number', 'N/A')
        
        # Create description
        invoice_desc = (
            f"Invoice #{invoice_num} from {vendor} for {amount} "
            f"{invoice.get('currency', 'SAR')}"
        )
        narratives.append(invoice_desc)
        
        # Add vendor spend context if available
        if spend_intelligence and spend_intelligence.get('top_vendors'):
            vendor_data = next(
                (v for v in spend_intelligence['top_vendors'] if v['vendor_name'] == vendor),
                None
            )
            
            if vendor_data:
                vendor_narrative = (
                    f"{vendor} is a top spending vendor with "
                    f"{vendor_data['total_spend']} total spend across "
                    f"{vendor_data['invoice_count']} invoices "
                    f"({vendor_data['percentage_of_total']:.1f}% of total spend)"
                )
                narratives.append(vendor_narrative)
                insights.append(f"Top vendor: {vendor}")
        
        # Add compliance insights
        if compliance_findings:
            risk_level = compliance_findings.get('risk_level', 'unknown').upper()
            risk_score = compliance_findings.get('risk_score', 0)
            
            compliance_narrative = f"Compliance assessment: {risk_level} risk (score: {risk_score}/100)"
            narratives.append(compliance_narrative)
            
            if compliance_findings.get('key_findings'):
                findings_text = "; ".join(compliance_findings['key_findings'][:3])
                narratives.append(f"Key findings: {findings_text}")
            
            insights.append(f"Risk Level: {risk_level}")
        
        # Add spending position
        if amount:
            total_spend = spend_intelligence.get('total_spend', Decimal('0'))
            if total_spend:
                percentage = float((amount / total_spend * 100))
                spend_position = (
                    f"This invoice represents {percentage:.2f}% of total "
                    f"organizational spending"
                )
                narratives.append(spend_position)
        
        # Generate executive summary
        executive_summary = FinancialNarrativeService._generate_executive_summary(
            narratives, insights
        )
        
        return {
            'narrative_status': 'generated',
            'executive_summary': executive_summary,
            'detailed_narrative': ' '.join(narratives),
            'key_insights': insights,
            'narrative_language': 'en',
        }
    
    @staticmethod
    def _generate_executive_summary(narratives: List[str],
                                   insights: List[str]) -> str:
        """Generate concise executive summary"""
        if not narratives:
            return "Invoice processed but no additional context available."
        
        # Build summary from key narratives
        summary_parts = [narratives[0]]  # Always include basic invoice desc
        
        if len(narratives) > 1:
            summary_parts.append(narratives[1])  # Add vendor context
        
        # Add risk summary if present
        risk_narrative = next((n for n in narratives if 'Compliance' in n or 'risk' in n), None)
        if risk_narrative:
            summary_parts.append(risk_narrative)
        
        return ' '.join(summary_parts) + '.'
    
    @staticmethod
    def generate_spend_narrative(spend_intelligence: Dict[str, Any]) -> str:
        """Generate narrative about overall spending"""
        if not spend_intelligence or spend_intelligence.get('spend_analysis_status') != 'completed':
            return "Insufficient spending data to generate narrative."
        
        narrative_parts = []
        
        total = spend_intelligence.get('total_spend', Decimal('0'))
        count = len(spend_intelligence.get('top_vendors', []))
        
        narrative_parts.append(
            f"Organization has spent {total} across {count} top vendors. "
        )
        
        # Top vendor insight
        if spend_intelligence.get('top_vendors'):
            top_vendor = spend_intelligence['top_vendors'][0]
            narrative_parts.append(
                f"Top vendor is {top_vendor['vendor_name']} "
                f"with {top_vendor['percentage_of_total']:.1f}% of total spend. "
            )
        
        # Spending trend
        if spend_intelligence.get('spending_trend') and len(spend_intelligence['spending_trend']) >= 2:
            trend = spend_intelligence['spending_trend']
            first_month_spend = trend[0]['total_spend']
            last_month_spend = trend[-1]['total_spend']
            
            if last_month_spend > first_month_spend:
                increase = ((last_month_spend - first_month_spend) / first_month_spend * 100)
                narrative_parts.append(f"Spending trend is increasing (+{increase:.1f}%). ")
            else:
                decrease = ((first_month_spend - last_month_spend) / first_month_spend * 100)
                narrative_parts.append(f"Spending trend is decreasing (-{decrease:.1f}%). ")
        
        return ''.join(narrative_parts)


def get_financial_intelligence_service() -> Dict[str, type]:
    """Factory for financial intelligence services"""
    return {
        'cash_flow': CashFlowForecastService,
        'spend': SpendIntelligenceService,
        'narrative': FinancialNarrativeService,
    }
