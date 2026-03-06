import logging
import json
import os
from datetime import timedelta
from decimal import Decimal
from django.utils import timezone
from django.db.models import Sum, Count, Avg
from documents.models import ExtractedData, FinancialNarrative
from core.models import Organization

logger = logging.getLogger(__name__)

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("OpenAI library not available, narrative generation will use rule-based approach")


class InvoiceFinancialNarrativeService:
    """
    Phase 5 - Financial Narrative Service
    
    Generates AI-powered financial summaries with spending insights,
    risk highlights, and recommendations. Falls back to rule-based
    templates if OpenAI is unavailable.
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(InvoiceFinancialNarrativeService, cls).__new__(cls)
            self._setup_openai()
        return cls._instance
    
    def _setup_openai(self):
        """Configure OpenAI if available."""
        try:
            if OPENAI_AVAILABLE:
                self.api_key = os.getenv('OPENAI_API_KEY')
                if self.api_key:
                    openai.api_key = self.api_key
                    self.openai_ready = True
                else:
                    self.openai_ready = False
                    logger.warning("OpenAI API key not configured")
            else:
                self.openai_ready = False
        except Exception as e:
            logger.warning(f"Error setting up OpenAI: {str(e)}")
            self.openai_ready = False
    
    def generate_financial_narrative(self, organization: Organization,
                                    period_start, period_end) -> dict:
        """
        Generate comprehensive financial narrative for a period.
        
        Returns:
            dict: Generated narrative with insights and recommendations
        """
        try:
            logger.info(f"Generating financial narrative for {organization.name}")
            
            # Gather financial data
            financial_data = self._gather_financial_data(organization, period_start, period_end)
            
            # Try OpenAI first, fallback to rule-based
            if self.openai_ready:
                narrative_text, trends, risks, recommendations = self._generate_openai_narrative(
                    organization, financial_data
                )
                generation_method = 'openai'
            else:
                narrative_text, trends, risks, recommendations = self._generate_rule_based_narrative(
                    financial_data
                )
                generation_method = 'rule_based'
            
            # Determine narrative type
            days_diff = (period_end - period_start).days
            if days_diff <= 31:
                narrative_type = 'monthly'
            elif days_diff <= 95:
                narrative_type = 'quarterly'
            else:
                narrative_type = 'custom'
            
            # Create narrative record
            narrative = FinancialNarrative.objects.create(
                organization=organization,
                period_start=period_start,
                period_end=period_end,
                narrative_type=narrative_type,
                narrative_text=narrative_text,
                trends=trends,
                risks=risks,
                recommendations=recommendations,
                total_spend=financial_data['total_spend'],
                invoice_count=financial_data['invoice_count'],
                vendor_count=financial_data['vendor_count'],
                top_categories=financial_data['top_categories'],
                top_vendors=financial_data['top_vendors'],
                overall_risk_score=financial_data['overall_risk_score'],
                anomaly_count=financial_data['anomaly_count'],
                duplicate_risk_count=financial_data['duplicate_risk_count'],
                generation_method=generation_method,
            )
            
            return {
                'success': True,
                'narrative_id': narrative.id,
                'narrative': {
                    'period': f"{period_start} to {period_end}",
                    'type': narrative_type,
                    'summary': narrative_text[:500] if narrative_text else '',
                    'generation_method': generation_method,
                    'metrics': {
                        'total_spend': float(financial_data['total_spend']),
                        'invoice_count': financial_data['invoice_count'],
                        'vendor_count': financial_data['vendor_count'],
                    },
                }
            }
        except Exception as e:
            logger.error(f"Error generating narrative: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
            }
    
    def _gather_financial_data(self, organization: Organization, 
                               period_start, period_end) -> dict:
        """Gather all financial data for the period."""
        try:
            invoices = ExtractedData.objects.filter(
                organization=organization,
                invoice_date__gte=period_start,
                invoice_date__lte=period_end,
                status='processed'
            ).order_by('-invoice_date')
            
            # Basic metrics
            total_spend = Decimal('0')
            vendor_dict = {}
            category_dict = {}
            
            for invoice in invoices:
                amount = invoice.total_amount or Decimal('0')
                total_spend += amount
                
                vendor = invoice.vendor_name or 'Unknown'
                if vendor not in vendor_dict:
                    vendor_dict[vendor] = Decimal('0')
                vendor_dict[vendor] += amount
                
                category = invoice.item_category or 'Uncategorized'
                if category not in category_dict:
                    category_dict[category] = Decimal('0')
                category_dict[category] += amount
            
            # Top vendors and categories
            top_vendors = dict(sorted(vendor_dict.items(), key=lambda x: x[1], reverse=True)[:5])
            top_categories = dict(sorted(category_dict.items(), key=lambda x: x[1], reverse=True)[:5])
            
            # Risk metrics
            overall_risk_score = invoices.aggregate(Avg('risk_score'))['risk_score__avg'] or 0
            anomaly_count = invoices.filter(anomaly_flags__isnull=False).count()
            duplicate_risk_count = invoices.filter(duplicate_score__gt=50).count()
            
            return {
                'total_spend': total_spend,
                'invoice_count': invoices.count(),
                'vendor_count': len(vendor_dict),
                'top_vendors': {k: float(v) for k, v in top_vendors.items()},
                'top_categories': {k: float(v) for k, v in top_categories.items()},
                'overall_risk_score': round(float(overall_risk_score), 1),
                'anomaly_count': anomaly_count,
                'duplicate_risk_count': duplicate_risk_count,
                'invoices': invoices,
            }
        except Exception as e:
            logger.error(f"Error gathering financial data: {str(e)}")
            return {
                'total_spend': Decimal('0'),
                'invoice_count': 0,
                'vendor_count': 0,
                'top_vendors': {},
                'top_categories': {},
                'overall_risk_score': 0,
                'anomaly_count': 0,
                'duplicate_risk_count': 0,
                'invoices': [],
            }
    
    def _generate_openai_narrative(self, organization: Organization, 
                                  financial_data: dict) -> tuple:
        """Generate narrative using OpenAI GPT."""
        try:
            # Prepare context for OpenAI
            context = f"""
Organization: {organization.name}
Total Spend: {financial_data['total_spend']:,.0f} SAR
Invoice Count: {financial_data['invoice_count']}
Vendor Count: {financial_data['vendor_count']}
Top Vendors: {json.dumps(financial_data['top_vendors'], default=str)}
Top Categories: {json.dumps(financial_data['top_categories'], default=str)}
Overall Risk Score: {financial_data['overall_risk_score']}/100
Anomalies: {financial_data['anomaly_count']}
Duplicate Risk Items: {financial_data['duplicate_risk_count']}

Generate a concise financial narrative (2-3 paragraphs) that:
1. Summarizes the spending activity
2. Highlights key trends and risks
3. Identifies top vendors and categories
4. Provides actionable recommendations
Format as a professional financial summary.
            """
            
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a financial analyst writing brief summaries of spending patterns."},
                    {"role": "user", "content": context}
                ],
                temperature=0.7,
                max_tokens=800,
            )
            
            narrative_text = response.choices[0].message.content
            
            # Extract structured insights
            trends = self._extract_trends(financial_data, narrative_text)
            risks = self._extract_risks(financial_data, narrative_text)
            recommendations = self._extract_recommendations(financial_data, narrative_text)
            
            return narrative_text, trends, risks, recommendations
            
        except Exception as e:
            logger.warning(f"OpenAI generation failed, falling back to rule-based: {str(e)}")
            return self._generate_rule_based_narrative(financial_data)
    
    def _generate_rule_based_narrative(self, financial_data: dict) -> tuple:
        """Generate narrative using rule-based templates."""
        try:
            # Build narrative from templates
            total_spend = float(financial_data['total_spend'])
            invoice_count = financial_data['invoice_count']
            vendor_count = financial_data['vendor_count']
            risk_score = financial_data['overall_risk_score']
            
            # Opening
            narrative = f"During this period, total spending reached SAR {total_spend:,.0f} across {invoice_count} invoices from {vendor_count} vendors. "
            
            # Spending analysis
            if invoice_count > 0:
                avg_invoice = total_spend / invoice_count
                narrative += f"The average invoice value was SAR {avg_invoice:,.0f}. "
            
            # Risk analysis
            if risk_score > 70:
                narrative += f"Overall risk assessment is high ({risk_score:.0f}/100), requiring increased monitoring. "
            elif risk_score > 40:
                narrative += f"Overall risk assessment is moderate ({risk_score:.0f}/100). Some attention recommended. "
            else:
                narrative += f"Overall risk assessment is low ({risk_score:.0f}/100). Normal monitoring sufficient. "
            
            # Anomalies
            if financial_data['anomaly_count'] > 0:
                narrative += f"{financial_data['anomaly_count']} anomalies were detected. "
            
            if financial_data['duplicate_risk_count'] > 0:
                narrative += f"{financial_data['duplicate_risk_count']} invoices have duplicate risk. "
            
            # Recommendations
            narrative += "Recommended actions: "
            recommendations_list = []
            
            if risk_score > 70:
                recommendations_list.append("Conduct immediate risk review")
            if financial_data['anomaly_count'] > 5:
                recommendations_list.append("Investigate detected anomalies")
            if financial_data['duplicate_risk_count'] > 0:
                recommendations_list.append("Review and reconcile potential duplicates")
            
            narrative += "; ".join(recommendations_list) + "."
            
            # Extract structured data
            trends = {
                'total_spend': float(financial_data['total_spend']),
                'invoice_count': financial_data['invoice_count'],
                'vendor_count': financial_data['vendor_count'],
            }
            
            risks = {
                'overall_risk_score': financial_data['overall_risk_score'],
                'anomaly_count': financial_data['anomaly_count'],
                'duplicate_risk_count': financial_data['duplicate_risk_count'],
            }
            
            recommendations = {
                'actions': recommendations_list,
                'priority': 'high' if risk_score > 70 else 'medium' if risk_score > 40 else 'low',
            }
            
            return narrative, trends, risks, recommendations
            
        except Exception as e:
            logger.error(f"Error generating rule-based narrative: {str(e)}")
            return "", {}, {}, {}
    
    def _extract_trends(self, financial_data: dict, narrative: str) -> dict:
        """Extract trend insights from narrative."""
        return {
            'total_spend': float(financial_data['total_spend']),
            'invoice_count': financial_data['invoice_count'],
            'vendor_count': financial_data['vendor_count'],
            'top_vendors': financial_data['top_vendors'],
            'top_categories': financial_data['top_categories'],
        }
    
    def _extract_risks(self, financial_data: dict, narrative: str) -> dict:
        """Extract risk information from narrative."""
        return {
            'overall_risk_score': financial_data['overall_risk_score'],
            'anomaly_count': financial_data['anomaly_count'],
            'duplicate_risk_count': financial_data['duplicate_risk_count'],
            'risk_level': 'high' if financial_data['overall_risk_score'] > 70 else 'medium' if financial_data['overall_risk_score'] > 40 else 'low',
        }
    
    def _extract_recommendations(self, financial_data: dict, narrative: str) -> dict:
        """Extract recommendations from narrative."""
        actions = []
        
        if financial_data['overall_risk_score'] > 70:
            actions.append('Conduct immediate risk review')
        if financial_data['anomaly_count'] > 5:
            actions.append('Investigate anomalies')
        if financial_data['duplicate_risk_count'] > 0:
            actions.append('Review potential duplicates')
        if financial_data['vendor_count'] > 50:
            actions.append('Consolidate vendor relationships')
        
        return {
            'actions': actions,
            'priority': 'high' if financial_data['overall_risk_score'] > 70 else 'medium',
        }
    
    def get_narrative(self, narrative_id: int) -> dict:
        """Retrieve generated narrative by ID."""
        try:
            narrative = FinancialNarrative.objects.get(id=narrative_id)
            return {
                'success': True,
                'narrative': {
                    'id': narrative.id,
                    'period': f"{narrative.period_start} to {narrative.period_end}",
                    'type': narrative.get_narrative_type_display(),
                    'text': narrative.narrative_text,
                    'summary': narrative.executive_summary,
                    'trends': narrative.trends,
                    'risks': narrative.risks,
                    'recommendations': narrative.recommendations,
                    'generation_method': narrative.generation_method,
                    'created_at': str(narrative.created_at),
                }
            }
        except FinancialNarrative.DoesNotExist:
            return {'success': False, 'error': 'Narrative not found'}
        except Exception as e:
            logger.error(f"Error retrieving narrative: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def publish_narrative(self, narrative_id: int, email_recipients: list = None) -> dict:
        """Publish narrative and send notifications."""
        try:
            narrative = FinancialNarrative.objects.get(id=narrative_id)
            narrative.is_published = True
            narrative.published_at = timezone.now()
            
            if email_recipients:
                narrative.published_to = ','.join(email_recipients)
                # TODO: Implement email sending here
                logger.info(f"Would send narrative to: {email_recipients}")
            
            narrative.save()
            
            return {
                'success': True,
                'narrative_id': narrative.id,
                'published_at': str(narrative.published_at),
                'message': 'Narrative published successfully',
            }
        except Exception as e:
            logger.error(f"Error publishing narrative: {str(e)}")
            return {'success': False, 'error': str(e)}


def get_financial_narrative_service() -> InvoiceFinancialNarrativeService:
    """Get singleton instance of financial narrative service."""
    return InvoiceFinancialNarrativeService()
