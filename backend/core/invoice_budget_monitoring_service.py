import logging
from datetime import timedelta
from decimal import Decimal
from django.utils import timezone
from django.db.models import Sum, Count
from documents.models import ExtractedData, FinancialBudget
from core.models import Organization

logger = logging.getLogger(__name__)


class InvoiceBudgetMonitoringService:
    """
    Phase 5 - Budget Monitoring Service
    
    Tracks spending against budgets, calculates utilization,
    and predicts budget overrun risks.
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(InvoiceBudgetMonitoringService, cls).__new__(cls)
        return cls._instance
    
    def monitor_budget_status(self, organization: Organization, 
                             budget: FinancialBudget = None) -> dict:
        """
        Monitor budget status and calculate utilization metrics.
        
        Returns:
            dict: Budget status with utilization, variance, and projections
        """
        try:
            logger.info(f"Monitoring budget status for organization {organization.name}")
            
            # If no specific budget provided, analyze all current period budgets
            if budget:
                budgets = [budget]
            else:
                today = timezone.now().date()
                budgets = FinancialBudget.objects.filter(
                    organization=organization,
                    period_start__lte=today,
                    period_end__gte=today
                )
            
            if not budgets:
                logger.warning(f"No active budgets found for organization {organization.name}")
                return self._empty_budget_status()
            
            budget_results = []
            
            for budget_item in budgets:
                # Calculate actual spend for the budget period
                actual_spend = self._calculate_actual_spend(
                    organization, budget_item.category,
                    budget_item.period_start, budget_item.period_end
                )
                
                # Calculate metrics
                utilization_percent = (float(actual_spend) / float(budget_item.budget_amount) * 100) if budget_item.budget_amount > 0 else 0
                variance_amount = actual_spend - budget_item.budget_amount
                variance_percent = (float(variance_amount) / float(budget_item.budget_amount) * 100) if budget_item.budget_amount > 0 else 0
                
                # Determine status
                if actual_spend > budget_item.budget_amount:
                    status = 'overrun'
                elif utilization_percent >= 90:
                    status = 'at_risk'
                elif utilization_percent < 30:
                    status = 'underutilized'
                else:
                    status = 'on_track'
                
                # Project final spend
                days_elapsed = (budget_item.period_end - budget_item.period_start).days
                days_remaining = (budget_item.period_end - timezone.now().date()).days
                
                if days_elapsed > 0:
                    daily_burn_rate = float(actual_spend) / (days_elapsed - days_remaining) if days_elapsed > days_remaining else 0
                    projected_final_spend = Decimal(str(actual_spend + (daily_burn_rate * days_remaining)))
                else:
                    projected_final_spend = actual_spend
                
                # Calculate overrun risk
                overrun_risk_percent = max(0, ((float(projected_final_spend) - float(budget_item.budget_amount)) / float(budget_item.budget_amount) * 100)) if budget_item.budget_amount > 0 else 0
                
                # Update budget record
                budget_item.actual_spend = actual_spend
                budget_item.utilization_percent = utilization_percent
                budget_item.variance_amount = variance_amount
                budget_item.variance_percent = variance_percent
                budget_item.status = status
                budget_item.projected_final_spend = projected_final_spend
                budget_item.overrun_risk_percent = overrun_risk_percent
                budget_item.save()
                
                budget_results.append({
                    'category': budget_item.category,
                    'period': f"{budget_item.period_start} to {budget_item.period_end}",
                    'budget_amount': float(budget_item.budget_amount),
                    'actual_spend': float(actual_spend),
                    'utilization_percent': round(utilization_percent, 1),
                    'variance_amount': float(variance_amount),
                    'variance_percent': round(variance_percent, 1),
                    'status': status,
                    'projected_final_spend': float(projected_final_spend),
                    'overrun_risk_percent': round(overrun_risk_percent, 1),
                    'days_remaining': days_remaining,
                })
            
            return {
                'success': True,
                'budgets': budget_results,
                'overall_status': self._calculate_overall_status(budget_results),
            }
        except Exception as e:
            logger.error(f"Error monitoring budget: {str(e)}", exc_info=True)
            return self._empty_budget_status()
    
    def _calculate_actual_spend(self, organization: Organization, category: str,
                               period_start, period_end) -> Decimal:
        """
        Calculate actual spending for a category in a period.
        
        Returns:
            Decimal: Total spend in SAR equivalent
        """
        try:
            invoices = ExtractedData.objects.filter(
                organization=organization,
                item_category=category,
                invoice_date__gte=period_start,
                invoice_date__lte=period_end,
                status='processed'
            )
            
            total = Decimal('0')
            for invoice in invoices:
                amount = invoice.total_amount or Decimal('0')
                total += amount
            
            return total
        except Exception as e:
            logger.warning(f"Error calculating actual spend: {str(e)}")
            return Decimal('0')
    
    def _calculate_overall_status(self, budget_results: list) -> str:
        """Calculate overall budget health status."""
        if not budget_results:
            return 'unknown'
        
        statuses = [b['status'] for b in budget_results]
        
        if 'overrun' in statuses:
            return 'critical'
        elif 'at_risk' in statuses:
            return 'at_risk'
        elif any(s == 'on_track' for s in statuses):
            return 'on_track'
        else:
            return 'underutilized'
    
    def _empty_budget_status(self) -> dict:
        """Return empty budget status."""
        return {
            'success': False,
            'error': 'No budget data available',
            'budgets': [],
            'overall_status': 'unknown',
        }
    
    def create_budget(self, organization: Organization, category: str, 
                     budget_amount: Decimal, period_start, period_end,
                     currency: str = 'SAR') -> dict:
        """
        Create a new budget for an organization and category.
        
        Returns:
            dict: Created budget details
        """
        try:
            budget = FinancialBudget.objects.create(
                organization=organization,
                category=category,
                budget_amount=budget_amount,
                period_start=period_start,
                period_end=period_end,
                currency=currency,
                status='on_track'
            )
            
            logger.info(f"Created budget for {category}: {currency} {budget_amount}")
            
            return {
                'success': True,
                'budget_id': budget.id,
                'category': category,
                'budget_amount': float(budget_amount),
                'period': f"{period_start} to {period_end}",
            }
        except Exception as e:
            logger.error(f"Error creating budget: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def identify_budget_risks(self, organization: Organization) -> dict:
        """
        Identify budgets at risk of overrun and recommend actions.
        
        Returns:
            dict: Budget risks with recommendations
        """
        try:
            today = timezone.now().date()
            
            # Get active budgets
            active_budgets = FinancialBudget.objects.filter(
                organization=organization,
                period_start__lte=today,
                period_end__gte=today
            )
            
            risks = []
            
            for budget in active_budgets:
                # Calculate current spend
                actual_spend = self._calculate_actual_spend(
                    organization, budget.category,
                    budget.period_start, budget.period_end
                )
                
                utilization = (float(actual_spend) / float(budget.budget_amount) * 100) if budget.budget_amount > 0 else 0
                
                # Check for risks
                if utilization >= 90:
                    days_remaining = (budget.period_end - today).days
                    recommendation = f"Spending is at {utilization:.1f}% of budget with {days_remaining} days remaining. Consider reducing spend or revising budget."
                    
                    risks.append({
                        'category': budget.category,
                        'current_utilization': round(utilization, 1),
                        'budget_amount': float(budget.budget_amount),
                        'actual_spend': float(actual_spend),
                        'days_remaining': days_remaining,
                        'severity': 'critical' if utilization >= 110 else 'high' if utilization >= 100 else 'medium',
                        'recommendation': recommendation,
                    })
            
            return {
                'success': True,
                'risk_count': len(risks),
                'risks': sorted(risks, key=lambda x: x['current_utilization'], reverse=True),
            }
        except Exception as e:
            logger.error(f"Error identifying budget risks: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def project_budget_utilization(self, budget: FinancialBudget, 
                                  organization: Organization) -> dict:
        """
        Project final budget utilization based on current spend rate.
        
        Returns:
            dict: Projection with confidence and recommendations
        """
        try:
            today = timezone.now().date()
            
            # Calculate actual spend to date
            actual_spend = self._calculate_actual_spend(
                organization, budget.category,
                budget.period_start, today
            )
            
            # Calculate daily burn rate
            days_elapsed = (today - budget.period_start).days
            if days_elapsed > 0:
                daily_burn = float(actual_spend) / days_elapsed
            else:
                daily_burn = 0
            
            # Project final spend
            days_remaining = (budget.period_end - today).days
            projected_remaining_spend = Decimal(str(daily_burn * days_remaining))
            projected_final_spend = actual_spend + projected_remaining_spend
            
            # Calculate confidence
            if days_elapsed < 7:
                confidence = 0.3
            elif days_elapsed < 14:
                confidence = 0.5
            else:
                confidence = 0.8
            
            # Calculate projected utilization
            projected_utilization = (float(projected_final_spend) / float(budget.budget_amount) * 100) if budget.budget_amount > 0 else 0
            variance_projection = projected_final_spend - budget.budget_amount
            
            # Determine risk level
            if projected_utilization >= 110:
                risk_level = 'critical'
                recommendation = f"Budget will be overrun by {float(variance_projection):,.0f}. Immediate action required."
            elif projected_utilization >= 95:
                risk_level = 'high'
                recommendation = f"Projected to use {projected_utilization:.1f}% of budget. Monitor closely."
            elif projected_utilization >= 85:
                risk_level = 'medium'
                recommendation = f"Projected to use {projected_utilization:.1f}% of budget. Consider optimization."
            else:
                risk_level = 'low'
                recommendation = f"Budget projection is healthy at {projected_utilization:.1f}% utilization."
            
            return {
                'success': True,
                'projection': {
                    'budget_amount': float(budget.budget_amount),
                    'actual_spend_to_date': float(actual_spend),
                    'daily_burn_rate': round(daily_burn, 2),
                    'days_elapsed': days_elapsed,
                    'days_remaining': days_remaining,
                    'projected_remaining_spend': float(projected_remaining_spend),
                    'projected_final_spend': float(projected_final_spend),
                    'projected_utilization_percent': round(projected_utilization, 1),
                    'confidence': round(confidence, 2),
                    'variance_projection': float(variance_projection),
                    'risk_level': risk_level,
                    'recommendation': recommendation,
                }
            }
        except Exception as e:
            logger.error(f"Error projecting budget utilization: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def compare_budgets(self, organization: Organization, period_num_months: int = 3) -> dict:
        """
        Compare budget performance across periods.
        
        Returns:
            dict: Budget comparison with trends and insights
        """
        try:
            today = timezone.now().date()
            comparisons = []
            
            for i in range(period_num_months):
                period_start = (today.replace(day=1) - timedelta(days=30*i)).replace(day=1)
                if period_start.month == 12:
                    period_end = period_start.replace(year=period_start.year + 1, month=1, day=1) - timedelta(days=1)
                else:
                    period_end = period_start.replace(month=period_start.month + 1, day=1) - timedelta(days=1)
                
                period_label = period_start.strftime('%B %Y')
                
                # Get budgets for this period
                period_budgets = FinancialBudget.objects.filter(
                    organization=organization,
                    period_start__gte=period_start,
                    period_end__lte=period_end
                )
                
                total_budget = sum(b.budget_amount for b in period_budgets)
                total_actual = sum(self._calculate_actual_spend(organization, b.category, period_start, period_end) for b in period_budgets)
                utilization = (float(total_actual) / float(total_budget) * 100) if total_budget > 0 else 0
                
                comparisons.append({
                    'period': period_label,
                    'total_budget': float(total_budget),
                    'total_actual': float(total_actual),
                    'utilization_percent': round(utilization, 1),
                    'variance': float(total_actual - total_budget),
                })
            
            return {
                'success': True,
                'comparison_periods': period_num_months,
                'period_comparison': sorted(comparisons, key=lambda x: x['period']),
            }
        except Exception as e:
            logger.error(f"Error comparing budgets: {str(e)}")
            return {'success': False, 'error': str(e)}


def get_budget_monitoring_service() -> InvoiceBudgetMonitoringService:
    """Get singleton instance of budget monitoring service."""
    return InvoiceBudgetMonitoringService()
