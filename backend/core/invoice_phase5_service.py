import logging
from datetime import timedelta
from decimal import Decimal
from django.utils import timezone
from django.db import transaction
from documents.models import ExtractedData, FinancialBudget
from core.models import Organization

logger = logging.getLogger(__name__)


class InvoicePhase5Service:
    """
    Phase 5 - Financial Intelligence & Forecasting Orchestrator
    
    Coordinates all Phase 5 services:
    - Cash flow forecasting (30/60/90 days)
    - Spend intelligence (vendor/category trends)
    - Vendor risk forecasting (anomaly growth detection)
    - Budget monitoring (vs actual spend)
    - Financial narratives (OpenAI summaries)
    - Intelligent alerts (spending spikes, anomalies, etc.)
    
    Processes invoices through all Phase 5 analysis services
    and stores results in dedicated Phase 5 models.
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(InvoicePhase5Service, cls).__new__(cls)
        return cls._instance
    
    @transaction.atomic
    def process_phase5(self, extracted_data: ExtractedData, 
                      organization: Organization) -> dict:
        """
        Process invoice through all Phase 5 analysis services.
        
        This is the main entry point for Phase 5 processing.
        Orchestrates cash flow, spend, vendor risk, budget, narrative, and alert services.
        
        Args:
            extracted_data: ExtractedData record to analyze
            organization: Associated organization
        
        Returns:
            dict: Comprehensive Phase 5 analysis result
        """
        try:
            logger.info(f"Starting Phase 5 processing for invoice {extracted_data.invoice_number}")
            
            phase5_result = {
                'success': True,
                'invoice_number': extracted_data.invoice_number,
                'processing_timestamp': str(timezone.now()),
                'services': {}
            }
            
            # Service 1: Cash Flow Forecasting
            try:
                logger.info("Phase 5.1: Cash flow forecasting")
                from core.invoice_cash_flow_service import get_cash_flow_service
                cash_flow_service = get_cash_flow_service()
                cash_flow_result = cash_flow_service.generate_cash_flow_forecast(
                    extracted_data, organization
                )
                phase5_result['services']['cash_flow_forecast'] = cash_flow_result
                if not cash_flow_result.get('success'):
                    logger.warning(f"Cash flow forecast failed: {cash_flow_result.get('error')}")
            except Exception as e:
                logger.error(f"Error in cash flow forecasting: {str(e)}", exc_info=True)
                phase5_result['services']['cash_flow_forecast'] = {
                    'success': False,
                    'error': str(e)
                }
            
            # Service 2: Spend Intelligence
            try:
                logger.info("Phase 5.2: Spend intelligence analysis")
                from core.invoice_spend_intelligence_service import get_spend_intelligence_service
                spend_service = get_spend_intelligence_service()
                spend_result = spend_service.analyze_spending_patterns(
                    organization, extracted_data
                )
                phase5_result['services']['spend_intelligence'] = spend_result
                if not spend_result.get('success'):
                    logger.warning(f"Spend intelligence failed: {spend_result.get('error')}")
            except Exception as e:
                logger.error(f"Error in spend intelligence: {str(e)}", exc_info=True)
                phase5_result['services']['spend_intelligence'] = {
                    'success': False,
                    'error': str(e)
                }
            
            # Service 3: Vendor Risk Forecasting
            try:
                logger.info("Phase 5.3: Vendor risk forecasting")
                from core.invoice_vendor_risk_forecast_service import get_vendor_risk_forecast_service
                vendor_risk_service = get_vendor_risk_forecast_service()
                # Check if this invoice's vendor has a VendorRisk record
                from documents.models import VendorRisk
                try:
                    vendor_risk = VendorRisk.objects.get(
                        organization=organization,
                        vendor_name=extracted_data.vendor_name
                    )
                    forecast_result = vendor_risk_service.forecast_vendor_risk(
                        vendor_risk, organization
                    )
                    phase5_result['services']['vendor_risk_forecast'] = forecast_result
                except VendorRisk.DoesNotExist:
                    logger.info(f"No vendor risk record for {extracted_data.vendor_name}")
                    phase5_result['services']['vendor_risk_forecast'] = {
                        'success': True,
                        'message': 'No vendor risk record found'
                    }
            except Exception as e:
                logger.error(f"Error in vendor risk forecasting: {str(e)}", exc_info=True)
                phase5_result['services']['vendor_risk_forecast'] = {
                    'success': False,
                    'error': str(e)
                }
            
            # Service 4: Budget Monitoring
            try:
                logger.info("Phase 5.4: Budget monitoring")
                from core.invoice_budget_monitoring_service import get_budget_monitoring_service
                budget_service = get_budget_monitoring_service()
                budget_result = budget_service.monitor_budget_status(organization)
                phase5_result['services']['budget_monitoring'] = budget_result
                if not budget_result.get('success'):
                    logger.warning(f"Budget monitoring had no data: {budget_result.get('error')}")
            except Exception as e:
                logger.error(f"Error in budget monitoring: {str(e)}", exc_info=True)
                phase5_result['services']['budget_monitoring'] = {
                    'success': False,
                    'error': str(e)
                }
            
            # Service 5: Financial Narrative (Monthly only, not per-invoice)
            # This is normally called at end of month
            try:
                logger.info("Phase 5.5: Financial narrative generation (skipped - monthly task)")
                phase5_result['services']['financial_narrative'] = {
                    'success': True,
                    'message': 'Generated at end of period, not per-invoice'
                }
            except Exception as e:
                logger.error(f"Error in financial narrative: {str(e)}", exc_info=True)
                phase5_result['services']['financial_narrative'] = {
                    'success': False,
                    'error': str(e)
                }
            
            # Service 6: Intelligent Alerts
            try:
                logger.info("Phase 5.6: Intelligent alerts generation")
                from core.invoice_intelligent_alerts_service import get_intelligent_alerts_service
                alerts_service = get_intelligent_alerts_service()
                alerts_result = alerts_service.generate_alerts(organization, extracted_data)
                phase5_result['services']['intelligent_alerts'] = alerts_result
                if not alerts_result.get('success'):
                    logger.warning(f"Alert generation failed: {alerts_result.get('error')}")
            except Exception as e:
                logger.error(f"Error in intelligent alerts: {str(e)}", exc_info=True)
                phase5_result['services']['intelligent_alerts'] = {
                    'success': False,
                    'error': str(e)
                }
            
            # Summary statistics
            successful_services = sum(1 for svc in phase5_result['services'].values() if svc.get('success', False))
            phase5_result['services_completed'] = successful_services
            phase5_result['total_services'] = 6
            
            logger.info(f"Phase 5 processing complete for {extracted_data.invoice_number}. " 
                       f"Services completed: {successful_services}/6")
            
            return phase5_result
            
        except Exception as e:
            logger.error(f"Critical error in Phase 5 orchestration: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'invoice_number': extracted_data.invoice_number if extracted_data else 'unknown',
                'services': {}
            }
    
    def generate_monthly_financial_narrative(self, organization: Organization) -> dict:
        """
        Generate monthly financial narrative (call at end of month).
        
        Returns:
            dict: Generated narrative with insights
        """
        try:
            logger.info(f"Generating monthly narrative for {organization.name}")
            
            today = timezone.now().date()
            month_start = today.replace(day=1)
            
            from core.invoice_financial_narrative_service import get_financial_narrative_service
            narrative_service = get_financial_narrative_service()
            result = narrative_service.generate_financial_narrative(
                organization, month_start, today
            )
            
            return result
        except Exception as e:
            logger.error(f"Error generating monthly narrative: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def get_organization_financial_summary(self, organization: Organization, 
                                          days_back: int = 30) -> dict:
        """
        Get comprehensive financial summary for organization.
        
        Returns:
            dict: Aggregated Phase 5 insights
        """
        try:
            logger.info(f"Generating financial summary for {organization.name}")
            
            today = timezone.now().date()
            period_start = today - timedelta(days=days_back)
            
            summary = {
                'success': True,
                'organization': organization.name,
                'period': f"Last {days_back} days",
                'insights': {}
            }
            
            # Get cash flow summary
            try:
                from core.invoice_cash_flow_service import get_cash_flow_service
                cash_flow_service = get_cash_flow_service()
                cash_flow_summary = cash_flow_service.aggregate_cash_flow_by_currency(
                    organization, num_days=30
                )
                pressure = cash_flow_service.get_cash_flow_pressure_indicators(organization)
                
                summary['insights']['cash_flow'] = {
                    'by_currency': cash_flow_summary.get('currency_summary', {}),
                    'pressure': pressure.get('pressure_by_window', {}),
                }
            except Exception as e:
                logger.warning(f"Error getting cash flow summary: {str(e)}")
                summary['insights']['cash_flow'] = {'error': str(e)}
            
            # Get spend summary
            try:
                from core.invoice_spend_intelligence_service import get_spend_intelligence_service
                spend_service = get_spend_intelligence_service()
                anomalies = spend_service.identify_spending_anomalies(organization)
                
                summary['insights']['spending'] = {
                    'anomalies': anomalies.get('anomalies', []),
                    'anomaly_count': anomalies.get('anomaly_count', 0),
                }
            except Exception as e:
                logger.warning(f"Error getting spend summary: {str(e)}")
                summary['insights']['spending'] = {'error': str(e)}
            
            # Get vendor risk summary
            try:
                from core.invoice_vendor_risk_forecast_service import get_vendor_risk_forecast_service
                vendor_service = get_vendor_risk_forecast_service()
                high_risk = vendor_service.get_high_risk_vendors(organization)
                emerging = vendor_service.detect_emerging_vendor_risks(organization)
                
                summary['insights']['vendor_risk'] = {
                    'high_risk_vendors': high_risk.get('vendor_count', 0),
                    'emerging_risks': emerging.get('emerging_risk_count', 0),
                }
            except Exception as e:
                logger.warning(f"Error getting vendor risk summary: {str(e)}")
                summary['insights']['vendor_risk'] = {'error': str(e)}
            
            # Get budget summary
            try:
                from core.invoice_budget_monitoring_service import get_budget_monitoring_service
                budget_service = get_budget_monitoring_service()
                budget_status = budget_service.monitor_budget_status(organization)
                budget_risks = budget_service.identify_budget_risks(organization)
                
                summary['insights']['budget'] = {
                    'overall_status': budget_status.get('overall_status', 'unknown'),
                    'risk_count': budget_risks.get('risk_count', 0),
                }
            except Exception as e:
                logger.warning(f"Error getting budget summary: {str(e)}")
                summary['insights']['budget'] = {'error': str(e)}
            
            # Get active alerts
            try:
                from core.invoice_intelligent_alerts_service import get_intelligent_alerts_service
                alerts_service = get_intelligent_alerts_service()
                active_alerts = alerts_service.get_active_alerts(organization)
                
                summary['insights']['alerts'] = {
                    'active_count': active_alerts.get('alert_count', 0),
                    'by_severity': self._count_alerts_by_severity(active_alerts.get('alerts', [])),
                }
            except Exception as e:
                logger.warning(f"Error getting alerts summary: {str(e)}")
                summary['insights']['alerts'] = {'error': str(e)}
            
            return summary
            
        except Exception as e:
            logger.error(f"Error generating financial summary: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _count_alerts_by_severity(self, alerts: list) -> dict:
        """Count alerts by severity level."""
        counts = {
            'critical': 0,
            'high': 0,
            'medium': 0,
            'low': 0,
        }
        
        for alert in alerts:
            severity = alert.get('severity', 'low')
            if severity in counts:
                counts[severity] += 1
        
        return counts


def get_phase5_service() -> InvoicePhase5Service:
    """Get singleton instance of Phase 5 orchestrator service."""
    return InvoicePhase5Service()
