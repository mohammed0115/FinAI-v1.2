import logging
from datetime import timedelta
from decimal import Decimal
from django.utils import timezone
from django.db.models import Sum, Count, Q, Avg
from documents.models import ExtractedData, FinancialAlert, AnomalyLog, VendorRisk
from core.models import Organization

logger = logging.getLogger(__name__)


class InvoiceIntelligentAlertsService:
    """
    Phase 5 - Intelligent Alerts Service
    
    Detects anomalies, spending spikes, duplicate risks, and cash flow
    pressure, generating actionable alerts for finance teams.
    """
    
    _instance = None
    
    # Alert thresholds
    SPEND_SPIKE_THRESHOLD = 1.5  # 50% increase
    ANOMALY_CLUSTER_THRESHOLD = 5  # 5+ anomalies in 7 days
    CASH_FLOW_PRESSURE_THRESHOLD = Decimal('1000000')  # 1M
    DUPLICATE_RISK_THRESHOLD = 0.7  # 70+ score
    BUDGET_OVERRUN_THRESHOLD = 0.9  # 90% utilization
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(InvoiceIntelligentAlertsService, cls).__new__(cls)
        return cls._instance
    
    def generate_alerts(self, organization: Organization, 
                       extracted_data: ExtractedData = None) -> dict:
        """
        Generate all relevant alerts for organization or specific invoice.
        
        Returns:
            dict: List of generated alerts with severity and details
        """
        try:
            logger.info(f"Generating alerts for organization {organization.name}")
            
            alerts_created = []
            
            # Check for spend spikes
            spend_spike_alerts = self._check_spend_spikes(organization)
            alerts_created.extend(spend_spike_alerts)
            
            # Check for anomaly clusters
            anomaly_alerts = self._check_anomaly_clusters(organization)
            alerts_created.extend(anomaly_alerts)
            
            # Check for duplicate risks
            if extracted_data:
                duplicate_alerts = self._check_duplicate_risks(extracted_data)
                alerts_created.extend(duplicate_alerts)
            
            # Check for cash flow pressure
            cash_flow_alerts = self._check_cash_flow_pressure(organization)
            alerts_created.extend(cash_flow_alerts)
            
            # Check for budget overruns
            budget_alerts = self._check_budget_overruns(organization)
            alerts_created.extend(budget_alerts)
            
            # Check for vendor risk increases
            vendor_alerts = self._check_vendor_risk_increases(organization)
            alerts_created.extend(vendor_alerts)
            
            return {
                'success': True,
                'alert_count': len(alerts_created),
                'alerts': alerts_created,
            }
        except Exception as e:
            logger.error(f"Error generating alerts: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'alerts': []
            }
    
    def _check_spend_spikes(self, organization: Organization) -> list:
        """
        Detect spending spikes (>50% increase from baseline).
        
        Returns:
            list: Alert records created
        """
        try:
            alerts = []
            today = timezone.now().date()
            
            # Compare current week to previous week
            current_week_start = today - timedelta(days=today.weekday())
            previous_week_start = current_week_start - timedelta(days=7)
            previous_week_end = current_week_start - timedelta(days=1)
            
            current_week_spend = ExtractedData.objects.filter(
                organization=organization,
                invoice_date__gte=current_week_start,
                invoice_date__lte=today
            ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
            
            previous_week_spend = ExtractedData.objects.filter(
                organization=organization,
                invoice_date__gte=previous_week_start,
                invoice_date__lte=previous_week_end
            ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
            
            if previous_week_spend > 0 and current_week_spend > previous_week_spend * Decimal(str(self.SPEND_SPIKE_THRESHOLD)):
                spike_percent = ((current_week_spend - previous_week_spend) / previous_week_spend) * 100
                
                alert = FinancialAlert.objects.create(
                    organization=organization,
                    alert_type='spend_spike',
                    severity='high' if spike_percent > 100 else 'medium',
                    title=f'Spending Spike Detected - {spike_percent:.0f}% Increase',
                    description=f'Weekly spending increased by {spike_percent:.1f}% from {float(previous_week_spend):,.0f} SAR to {float(current_week_spend):,.0f} SAR',
                    trigger_details={
                        'previous_week_spend': float(previous_week_spend),
                        'current_week_spend': float(current_week_spend),
                        'spike_percent': round(float(spike_percent), 2),
                    },
                    affected_amount=current_week_spend,
                    recommended_action='Review recent invoices for unusual vendors, categories, or amounts',
                )
                
                alerts.append({
                    'alert_id': alert.id,
                    'type': alert.alert_type,
                    'severity': alert.severity,
                    'title': alert.title,
                })
            
            return alerts
        except Exception as e:
            logger.warning(f"Error checking spend spikes: {str(e)}")
            return []
    
    def _check_anomaly_clusters(self, organization: Organization) -> list:
        """
        Detect clusters of anomalies (5+ in 7 days).
        
        Returns:
            list: Alert records created
        """
        try:
            alerts = []
            today = timezone.now().date()
            week_ago = today - timedelta(days=7)
            
            # Count anomalies in past 7 days
            recent_anomalies = AnomalyLog.objects.filter(
                created_at__date__gte=week_ago,
                created_at__date__lte=today
            ).count()
            
            if recent_anomalies >= self.ANOMALY_CLUSTER_THRESHOLD:
                alert = FinancialAlert.objects.create(
                    organization=organization,
                    alert_type='anomaly_cluster',
                    severity='high' if recent_anomalies > 10 else 'medium',
                    title=f'Anomaly Cluster Detected - {recent_anomalies} Anomalies',
                    description=f'{recent_anomalies} anomalies detected in the past 7 days. Investigation recommended.',
                    trigger_details={
                        'anomaly_count': recent_anomalies,
                        'period_days': 7,
                    },
                    recommended_action='Review detected anomalies in detail and confirm legitimate invoices',
                )
                
                alerts.append({
                    'alert_id': alert.id,
                    'type': alert.alert_type,
                    'severity': alert.severity,
                    'title': alert.title,
                })
            
            return alerts
        except Exception as e:
            logger.warning(f"Error checking anomaly clusters: {str(e)}")
            return []
    
    def _check_duplicate_risks(self, extracted_data: ExtractedData) -> list:
        """
        Check for duplicate invoice risks.
        
        Returns:
            list: Alert records created
        """
        try:
            alerts = []
            
            if extracted_data.duplicate_score and extracted_data.duplicate_score >= (self.DUPLICATE_RISK_THRESHOLD * 100):
                alert = FinancialAlert.objects.create(
                    organization=extracted_data.organization,
                    extracted_data=extracted_data,
                    alert_type='duplicate_risk',
                    severity='high' if extracted_data.duplicate_score >= 85 else 'medium',
                    title=f'Duplicate Invoice Risk - {extracted_data.invoice_number}',
                    description=f'Invoice {extracted_data.invoice_number} has {extracted_data.duplicate_score:.0f}% likelihood of being a duplicate',
                    trigger_details={
                        'duplicate_score': float(extracted_data.duplicate_score),
                        'invoice_number': extracted_data.invoice_number,
                    },
                    affected_amount=extracted_data.total_amount,
                    recommended_action='Compare with recent invoices from same vendor to confirm legitimacy',
                )
                
                alerts.append({
                    'alert_id': alert.id,
                    'type': alert.alert_type,
                    'severity': alert.severity,
                    'title': alert.title,
                })
            
            return alerts
        except Exception as e:
            logger.warning(f"Error checking duplicate risks: {str(e)}")
            return []
    
    def _check_cash_flow_pressure(self, organization: Organization) -> list:
        """
        Detect upcoming cash flow pressure (high payment obligations).
        
        Returns:
            list: Alert records created
        """
        try:
            alerts = []
            today = timezone.now().date()
            month_ahead = today + timedelta(days=30)
            
            # Get forecasted payments for next month
            forecasted_payments = ExtractedData.objects.filter(
                organization=organization,
                due_date__gte=today,
                due_date__lte=month_ahead,
                status='processed'
            ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
            
            if forecasted_payments > self.CASH_FLOW_PRESSURE_THRESHOLD:
                alert = FinancialAlert.objects.create(
                    organization=organization,
                    alert_type='cash_flow_pressure',
                    severity='high' if forecasted_payments > self.CASH_FLOW_PRESSURE_THRESHOLD * 2 else 'medium',
                    title=f'Cash Flow Pressure - SAR {float(forecasted_payments):,.0f} Due',
                    description=f'Total payments due in next 30 days: SAR {float(forecasted_payments):,.0f}. Ensure sufficient liquidity.',
                    trigger_details={
                        'forecasted_payments': float(forecasted_payments),
                        'period_days': 30,
                    },
                    affected_amount=forecasted_payments,
                    recommended_action='Review payment schedule and ensure adequate cash reserves',
                )
                
                alerts.append({
                    'alert_id': alert.id,
                    'type': alert.alert_type,
                    'severity': alert.severity,
                    'title': alert.title,
                })
            
            return alerts
        except Exception as e:
            logger.warning(f"Error checking cash flow pressure: {str(e)}")
            return []
    
    def _check_budget_overruns(self, organization: Organization) -> list:
        """
        Detect budget overrun risks (>90% utilization).
        
        Returns:
            list: Alert records created
        """
        try:
            from documents.models import FinancialBudget
            
            alerts = []
            today = timezone.now().date()
            
            # Get active budgets
            active_budgets = FinancialBudget.objects.filter(
                organization=organization,
                period_start__lte=today,
                period_end__gte=today
            )
            
            for budget in active_budgets:
                # Calculate actual spend
                actual_spend = ExtractedData.objects.filter(
                    organization=organization,
                    item_category=budget.category,
                    invoice_date__gte=budget.period_start,
                    invoice_date__lte=budget.period_end
                ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
                
                utilization = (actual_spend / budget.budget_amount) * 100 if budget.budget_amount > 0 else 0
                
                if utilization >= (self.BUDGET_OVERRUN_THRESHOLD * 100):
                    alert = FinancialAlert.objects.create(
                        organization=organization,
                        alert_type='budget_overrun',
                        severity='critical' if utilization >= 110 else 'high',
                        title=f'Budget Overrun Risk - {budget.category}',
                        description=f'Category "{budget.category}" is at {utilization:.1f}% of budget (SAR {float(actual_spend):,.0f} of SAR {float(budget.budget_amount):,.0f})',
                        trigger_details={
                            'category': budget.category,
                            'budget_amount': float(budget.budget_amount),
                            'actual_spend': float(actual_spend),
                            'utilization_percent': round(float(utilization), 1),
                        },
                        affected_category=budget.category,
                        affected_amount=actual_spend,
                        recommended_action='Review spending in this category and consider budget revision or spend reduction',
                    )
                    
                    alerts.append({
                        'alert_id': alert.id,
                        'type': alert.alert_type,
                        'severity': alert.severity,
                        'title': alert.title,
                    })
            
            return alerts
        except Exception as e:
            logger.warning(f"Error checking budget overruns: {str(e)}")
            return []
    
    def _check_vendor_risk_increases(self, organization: Organization) -> list:
        """
        Detect vendors with rapidly increasing risk.
        
        Returns:
            list: Alert records created
        """
        try:
            alerts = []
            
            # Get vendors with high anomaly growth
            vendor_risks = VendorRisk.objects.filter(
                organization=organization,
                risk_score__gte=60
            )
            
            for vendor_risk in vendor_risks:
                # Check if risk is increasing
                recent_issues = AnomalyLog.objects.filter(
                    extracted_data__vendor_name__icontains=vendor_risk.vendor_name,
                    created_at__gte=timezone.now() - timedelta(days=30)
                ).count()
                
                if recent_issues > 3:  # 3+ anomalies in past month
                    alert = FinancialAlert.objects.create(
                        organization=organization,
                        alert_type='vendor_risk_increase',
                        severity='high' if vendor_risk.risk_score >= 80 else 'medium',
                        title=f'Vendor Risk Increase - {vendor_risk.vendor_name}',
                        description=f'Vendor "{vendor_risk.vendor_name}" shows increasing risk (score: {vendor_risk.risk_score:.0f}/100) with {recent_issues} recent anomalies',
                        trigger_details={
                            'vendor_name': vendor_risk.vendor_name,
                            'risk_score': vendor_risk.risk_score,
                            'recent_issues': recent_issues,
                        },
                        affected_vendor=vendor_risk.vendor_name,
                        recommended_action='Review vendor communications, terms, and payment history. Consider alternative sources.',
                    )
                    
                    alerts.append({
                        'alert_id': alert.id,
                        'type': alert.alert_type,
                        'severity': alert.severity,
                        'title': alert.title,
                    })
            
            return alerts
        except Exception as e:
            logger.warning(f"Error checking vendor risk increases: {str(e)}")
            return []
    
    def acknowledge_alert(self, alert_id: int, user_name: str) -> dict:
        """
        Mark alert as acknowledged.
        
        Returns:
            dict: Updated alert status
        """
        try:
            alert = FinancialAlert.objects.get(id=alert_id)
            alert.is_acknowledged = True
            alert.acknowledged_by = user_name
            alert.acknowledged_at = timezone.now()
            alert.save()
            
            return {
                'success': True,
                'alert_id': alert.id,
                'acknowledged_at': str(alert.acknowledged_at),
            }
        except Exception as e:
            logger.error(f"Error acknowledging alert: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def resolve_alert(self, alert_id: int, resolution_notes: str = None) -> dict:
        """
        Mark alert as resolved.
        
        Returns:
            dict: Updated alert status
        """
        try:
            alert = FinancialAlert.objects.get(id=alert_id)
            alert.is_resolved = True
            alert.resolved_at = timezone.now()
            alert.resolution_notes = resolution_notes
            alert.save()
            
            return {
                'success': True,
                'alert_id': alert.id,
                'resolved_at': str(alert.resolved_at),
            }
        except Exception as e:
            logger.error(f"Error resolving alert: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def get_active_alerts(self, organization: Organization) -> dict:
        """
        Get all unresolved alerts for organization.
        
        Returns:
            dict: List of active alerts
        """
        try:
            alerts = FinancialAlert.objects.filter(
                organization=organization,
                is_resolved=False
            ).order_by('-severity', '-created_at')
            
            return {
                'success': True,
                'alert_count': alerts.count(),
                'alerts': [
                    {
                        'id': alert.id,
                        'type': alert.alert_type,
                        'severity': alert.severity,
                        'title': alert.title,
                        'description': alert.description,
                        'created_at': str(alert.created_at),
                        'is_acknowledged': alert.is_acknowledged,
                    }
                    for alert in alerts
                ]
            }
        except Exception as e:
            logger.error(f"Error getting active alerts: {str(e)}")
            return {'success': False, 'error': str(e)}


def get_intelligent_alerts_service() -> InvoiceIntelligentAlertsService:
    """Get singleton instance of intelligent alerts service."""
    return InvoiceIntelligentAlertsService()
