import logging
from datetime import timedelta
from decimal import Decimal
from django.utils import timezone
from django.db.models import Count, Avg, Q, Sum
from documents.models import ExtractedData, VendorRisk, VendorSpendMetrics, AnomalyLog
from core.models import Organization

logger = logging.getLogger(__name__)


class InvoiceVendorRiskForecastService:
    """
    Phase 5 - Vendor Risk Forecasting Service
    
    Projects vendor risk forward using anomaly detection trends.
    Identifies vendors with increasing risk patterns and forecasts risk growth.
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(InvoiceVendorRiskForecastService, cls).__new__(cls)
        return cls._instance
    
    def forecast_vendor_risk(self, vendor_risk: VendorRisk, organization: Organization) -> dict:
        """
        Forecast vendor risk trajectory over 30/60/90 days.
        
        Returns:
            dict: Risk forecast with velocity, trend, and projected scores
        """
        try:
            logger.info(f"Forecasting risk for vendor {vendor_risk.vendor_name}")
            
            # Get recent anomaly history for this vendor
            anomaly_history = self._get_vendor_anomaly_history(vendor_risk, days_back=90)
            
            if not anomaly_history:
                logger.info(f"No anomaly history for vendor {vendor_risk.vendor_name}")
                return {
                    'success': True,
                    'forecast': {
                        'vendor_name': vendor_risk.vendor_name,
                        'current_risk_score': vendor_risk.risk_score,
                        'risk_trajectory': 'stable',
                        'projected_risk_30d': vendor_risk.risk_score,
                        'projected_risk_60d': vendor_risk.risk_score,
                        'projected_risk_90d': vendor_risk.risk_score,
                        'anomaly_growth_rate': 0.0,
                        'forecast_confidence': 0.5,
                    }
                }
            
            # Calculate anomaly growth rate (velocity)
            anomaly_growth_rate = self._calculate_anomaly_growth_rate(anomaly_history)
            
            # Project future risk scores
            current_risk = vendor_risk.risk_score
            projected_30d = self._project_risk_score(current_risk, anomaly_growth_rate, days=30)
            projected_60d = self._project_risk_score(current_risk, anomaly_growth_rate, days=60)
            projected_90d = self._project_risk_score(current_risk, anomaly_growth_rate, days=90)
            
            # Determine risk trajectory
            risk_trajectory = self._determine_risk_trajectory(anomaly_growth_rate, current_risk)
            
            # Calculate forecast confidence
            forecast_confidence = self._calculate_forecast_confidence(anomaly_history)
            
            # Update VendorSpendMetrics with forecast data
            self._update_vendor_spend_metrics(vendor_risk, anomaly_growth_rate, current_risk)
            
            return {
                'success': True,
                'forecast': {
                    'vendor_name': vendor_risk.vendor_name,
                    'vendor_country': vendor_risk.vendor_country,
                    'current_risk_score': current_risk,
                    'risk_trajectory': risk_trajectory,
                    'projected_risk_30d': round(projected_30d, 1),
                    'projected_risk_60d': round(projected_60d, 1),
                    'projected_risk_90d': round(projected_90d, 1),
                    'anomaly_growth_rate': round(anomaly_growth_rate, 2),
                    'forecast_confidence': round(forecast_confidence, 2),
                    'anomaly_history': {
                        'month_1_count': anomaly_history.get('month_1_count', 0),
                        'month_2_count': anomaly_history.get('month_2_count', 0),
                        'month_3_count': anomaly_history.get('month_3_count', 0),
                    }
                }
            }
            
        except Exception as e:
            logger.error(f"Error forecasting vendor risk: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'forecast': {}
            }
    
    def _get_vendor_anomaly_history(self, vendor_risk: VendorRisk, days_back: int = 90) -> dict:
        """
        Get historical anomaly counts by month for the vendor.
        
        Returns:
            dict: Anomaly counts for recent months
        """
        try:
            today = timezone.now().date()
            cutoff_date = today - timedelta(days=days_back)
            
            # Get anomalies from all invoices for this vendor in past 90 days
            vendor_invoices = ExtractedData.objects.filter(
                vendor_name__icontains=vendor_risk.vendor_name,
                invoice_date__gte=cutoff_date
            )
            
            # Count anomalies by month
            month_1_start = (today.replace(day=1) - timedelta(days=30)).replace(day=1)
            month_2_start = (today.replace(day=1) - timedelta(days=60)).replace(day=1)
            month_3_start = (today.replace(day=1) - timedelta(days=90)).replace(day=1)
            
            month_1_end = today.replace(day=1) - timedelta(days=1)
            month_2_end = month_1_start - timedelta(days=1)
            month_3_end = month_2_start - timedelta(days=1)
            
            # Query anomaly logs
            month_1_anomalies = AnomalyLog.objects.filter(
                extracted_data__vendor_name__icontains=vendor_risk.vendor_name,
                created_at__date__gte=month_1_start,
                created_at__date__lte=month_1_end
            ).count()
            
            month_2_anomalies = AnomalyLog.objects.filter(
                extracted_data__vendor_name__icontains=vendor_risk.vendor_name,
                created_at__date__gte=month_2_start,
                created_at__date__lte=month_2_end
            ).count()
            
            month_3_anomalies = AnomalyLog.objects.filter(
                extracted_data__vendor_name__icontains=vendor_risk.vendor_name,
                created_at__date__gte=month_3_start,
                created_at__date__lte=month_3_end
            ).count()
            
            return {
                'month_1_count': month_1_anomalies,
                'month_2_count': month_2_anomalies,
                'month_3_count': month_3_anomalies,
            }
        except Exception as e:
            logger.warning(f"Error getting anomaly history: {str(e)}")
            return {}
    
    def _calculate_anomaly_growth_rate(self, anomaly_history: dict) -> float:
        """
        Calculate the rate of anomaly growth over time.
        
        Returns:
            float: Growth rate (positive = increasing anomalies, negative = decreasing)
        """
        try:
            month_1 = anomaly_history.get('month_1_count', 0)
            month_2 = anomaly_history.get('month_2_count', 0)
            month_3 = anomaly_history.get('month_3_count', 0)
            
            # Calculate month-over-month growth
            if month_2 > 0:
                m1_m2_growth = ((month_1 - month_2) / month_2) * 100
            else:
                m1_m2_growth = 100.0 if month_1 > 0 else 0.0
            
            if month_3 > 0:
                m2_m3_growth = ((month_2 - month_3) / month_3) * 100
            else:
                m2_m3_growth = 0.0
            
            # Average growth rate
            avg_growth = (m1_m2_growth + m2_m3_growth) / 2
            
            return avg_growth
        except Exception as e:
            logger.warning(f"Error calculating anomaly growth: {str(e)}")
            return 0.0
    
    def _project_risk_score(self, current_score: float, growth_rate: float, days: int = 30) -> float:
        """
        Project future risk score based on growth rate.
        
        Args:
            current_score: Current risk score (0-100)
            growth_rate: Monthly growth rate (%)
            days: Days to project forward
        
        Returns:
            float: Projected risk score (capped at 100)
        """
        try:
            # Convert daily growth rate
            monthly_multiplier = 1 + (growth_rate / 100)
            periods = days / 30  # Convert days to months
            
            projected = current_score * (monthly_multiplier ** periods)
            
            # Cap at 100 (maximum risk)
            return min(100.0, max(0.0, projected))
        except Exception as e:
            logger.warning(f"Error projecting risk score: {str(e)}")
            return current_score
    
    def _determine_risk_trajectory(self, growth_rate: float, current_score: float) -> str:
        """
        Determine if vendor risk is trending up, down, or stable.
        
        Returns:
            str: 'increasing', 'decreasing', 'stable', or 'critical'
        """
        if current_score >= 75:
            return 'critical'
        elif growth_rate > 15:
            return 'increasing'
        elif growth_rate < -15:
            return 'decreasing'
        else:
            return 'stable'
    
    def _calculate_forecast_confidence(self, anomaly_history: dict) -> float:
        """
        Calculate confidence in the risk forecast (0-1 scale).
        
        Higher if we have consistent anomaly data, lower if inconsistent.
        """
        try:
            month_1 = anomaly_history.get('month_1_count', 0)
            month_2 = anomaly_history.get('month_2_count', 0)
            month_3 = anomaly_history.get('month_3_count', 0)
            
            # Base confidence is 0.5
            confidence = 0.5
            
            # Increase confidence if we have data from all months
            data_points = sum(1 for count in [month_1, month_2, month_3] if count > 0)
            confidence += data_points * 0.1  # Each month adds 10%
            
            # Check for consistency (low variance = higher confidence)
            if data_points >= 2:
                counts = [c for c in [month_1, month_2, month_3] if c > 0]
                avg = sum(counts) / len(counts)
                variance = sum((c - avg) ** 2 for c in counts) / len(counts)
                consistency = 1.0 / (1.0 + (variance / avg if avg > 0 else 1))
                confidence += consistency * 0.2
            
            return min(1.0, max(0.0, confidence))
        except Exception as e:
            logger.warning(f"Error calculating forecast confidence: {str(e)}")
            return 0.5
    
    def _update_vendor_spend_metrics(self, vendor_risk: VendorRisk, 
                                    anomaly_growth_rate: float, current_risk: float):
        """Update VendorSpendMetrics with forecast data."""
        try:
            spend_metrics, created = VendorSpendMetrics.objects.get_or_create(
                vendor_risk=vendor_risk
            )
            
            spend_metrics.anomaly_growth_rate = anomaly_growth_rate
            
            # Determine spending velocity based on growth
            if anomaly_growth_rate > 20:
                spend_metrics.spending_velocity = 'volatile'
            elif anomaly_growth_rate > 10:
                spend_metrics.spending_velocity = 'growing'
            elif anomaly_growth_rate < -10:
                spend_metrics.spending_velocity = 'declining'
            else:
                spend_metrics.spending_velocity = 'stable'
            
            spend_metrics.save()
            logger.info(f"Updated spend metrics for {vendor_risk.vendor_name}")
        except Exception as e:
            logger.warning(f"Error updating spend metrics: {str(e)}")
    
    def get_high_risk_vendors(self, organization: Organization, 
                             risk_threshold: float = 60.0) -> dict:
        """
        Identify vendors with high risk and increasing risk trajectory.
        
        Returns:
            dict: List of high-risk vendors with forecast data
        """
        try:
            high_risk_vendors = VendorRisk.objects.filter(
                organization=organization,
                risk_score__gte=risk_threshold
            ).select_related('organization').prefetch_related('spend_metrics')
            
            risk_forecasts = []
            for vendor_risk in high_risk_vendors:
                try:
                    anomaly_history = self._get_vendor_anomaly_history(vendor_risk)
                    growth_rate = self._calculate_anomaly_growth_rate(anomaly_history)
                    projected_90d = self._project_risk_score(vendor_risk.risk_score, growth_rate, days=90)
                    trajectory = self._determine_risk_trajectory(growth_rate, vendor_risk.risk_score)
                    
                    risk_forecasts.append({
                        'vendor_name': vendor_risk.vendor_name,
                        'vendor_country': vendor_risk.vendor_country,
                        'current_risk_score': vendor_risk.risk_score,
                        'projected_risk_90d': round(projected_90d, 1),
                        'risk_trajectory': trajectory,
                        'anomaly_growth_rate': round(growth_rate, 2),
                        'issues_count': vendor_risk.issues_count,
                        'last_issue_date': str(vendor_risk.last_issue_date) if vendor_risk.last_issue_date else None,
                    })
                except Exception as e:
                    logger.warning(f"Error forecasting individual vendor {vendor_risk.vendor_name}: {str(e)}")
                    continue
            
            # Sort by projected risk descending
            risk_forecasts.sort(key=lambda x: x['projected_risk_90d'], reverse=True)
            
            return {
                'success': True,
                'threshold': risk_threshold,
                'vendor_count': len(risk_forecasts),
                'vendors': risk_forecasts,
            }
        except Exception as e:
            logger.error(f"Error getting high-risk vendors: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def detect_emerging_vendor_risks(self, organization: Organization, 
                                     growth_threshold: float = 50.0) -> dict:
        """
        Detect vendors with rapidly increasing risk (emerging risks).
        
        Returns:
            dict: List of emerging risk vendors with growth metrics
        """
        try:
            all_vendors = VendorRisk.objects.filter(organization=organization)
            
            emerging_risks = []
            for vendor_risk in all_vendors:
                try:
                    anomaly_history = self._get_vendor_anomaly_history(vendor_risk)
                    growth_rate = self._calculate_anomaly_growth_rate(anomaly_history)
                    
                    if growth_rate >= growth_threshold:
                        emerging_risks.append({
                            'vendor_name': vendor_risk.vendor_name,
                            'current_risk_score': vendor_risk.risk_score,
                            'anomaly_growth_rate': round(growth_rate, 2),
                            'recent_anomalies': anomaly_history.get('month_1_count', 0),
                            'trajectory': 'increasing',
                        })
                except Exception as e:
                    logger.warning(f"Error checking vendor {vendor_risk.vendor_name}: {str(e)}")
                    continue
            
            # Sort by growth rate descending
            emerging_risks.sort(key=lambda x: x['anomaly_growth_rate'], reverse=True)
            
            return {
                'success': True,
                'growth_threshold': growth_threshold,
                'emerging_risk_count': len(emerging_risks),
                'vendors': emerging_risks,
            }
        except Exception as e:
            logger.error(f"Error detecting emerging risks: {str(e)}")
            return {'success': False, 'error': str(e)}


def get_vendor_risk_forecast_service() -> InvoiceVendorRiskForecastService:
    """Get singleton instance of vendor risk forecast service."""
    return InvoiceVendorRiskForecastService()
