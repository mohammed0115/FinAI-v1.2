"""Business logic layer for analytics operations.

This module contains all analytics business logic,
including data aggregation, AI integration, and KPI calculations.
"""
from typing import Dict, List, Any
from datetime import datetime, timedelta
from decimal import Decimal
from django.db.models import Sum, QuerySet

from documents.models import Document, Transaction
from reports.models import Report, Insight
from core.ai_service import (
    CashFlowForecastOperation,
    AnomalyDetectionOperation,
    TrendAnalysisOperation,
    FinancialInsightsOperation
)


class AnalyticsQueryService:
    """Service for analytics data queries."""
    
    @staticmethod
    def get_historical_transactions(
        organization_id: str,
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """Get historical transactions for analysis."""
        transactions = Transaction.objects.filter(
            organization_id=organization_id
        ).order_by('-transaction_date')[:limit].values(
            'transaction_type', 'amount', 'transaction_date', 'currency'
        )
        return list(transactions)
    
    @staticmethod
    def get_recent_transactions_with_details(
        organization_id: str,
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """Get recent transactions with full details for anomaly detection."""
        transactions = Transaction.objects.filter(
            organization_id=organization_id
        ).order_by('-transaction_date')[:limit].values(
            'id', 'transaction_type', 'amount', 'transaction_date',
            'description', 'vendor_customer', 'currency'
        )
        return list(transactions)
    
    @staticmethod
    def get_transactions_for_period(
        organization_id: str,
        days: int = 180,
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """Get transactions for a specific time period."""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        transactions = Transaction.objects.filter(
            organization_id=organization_id,
            transaction_date__gte=cutoff_date
        ).order_by('-transaction_date')[:limit].values(
            'transaction_type', 'amount', 'transaction_date', 'currency'
        )
        return list(transactions)
    
    @staticmethod
    def gather_organization_data(
        organization_id: str,
        months: int = 3
    ) -> Dict[str, List[Dict]]:
        """Gather comprehensive organization data for insights."""
        cutoff_date = datetime.now() - timedelta(days=months * 30)
        
        return {
            'transactions': list(Transaction.objects.filter(
                organization_id=organization_id,
                transaction_date__gte=cutoff_date
            ).order_by('-transaction_date')[:500].values()),
            
            'documents': list(Document.objects.filter(
                organization_id=organization_id,
                uploaded_at__gte=cutoff_date
            ).order_by('-uploaded_at')[:200].values()),
            
            'reports': list(Report.objects.filter(
                organization_id=organization_id,
                created_at__gte=cutoff_date
            ).order_by('-created_at')[:50].values())
        }


class ForecastService:
    """Service for cash flow forecasting (SRP, OCP, LSP)."""
    ai_forecast_operation = CashFlowForecastOperation()

    @classmethod
    def generate_forecast(cls, organization_id: str, periods: int = 6) -> List[Dict[str, Any]]:
        historical_data = AnalyticsQueryService.get_historical_transactions(
            organization_id=organization_id
        )
        forecast = cls.ai_forecast_operation.execute(historical_data, periods)
        return forecast


class AnomalyDetectionService:
    """Service for anomaly detection in transactions (SRP, OCP, LSP)."""
    ai_anomaly_operation = AnomalyDetectionOperation()

    @classmethod
    def detect_and_save_anomalies(cls, organization_id: str) -> List[Dict[str, Any]]:
        transaction_list = AnalyticsQueryService.get_recent_transactions_with_details(
            organization_id=organization_id
        )
        anomalies = cls.ai_anomaly_operation.execute(transaction_list)
        cls._save_critical_anomalies(
            organization_id=organization_id,
            anomalies=anomalies
        )
        return anomalies
    
    @staticmethod
    def _save_critical_anomalies(
        organization_id: str,
        anomalies: List[Dict[str, Any]]
    ) -> None:
        """Save critical anomalies as insights."""
        for anomaly in anomalies:
            if anomaly.get('severity') in ['high', 'critical']:
                Insight.objects.create(
                    organization_id=organization_id,
                    insight_type='anomaly',
                    severity=anomaly.get('severity'),
                    title=anomaly.get('anomalyType'),
                    description=anomaly.get('description'),
                    related_entity_type='transaction',
                    related_entity_id=anomaly.get('transactionId'),
                    data_json=anomaly
                )


class TrendAnalysisService:
    """Service for trend analysis (SRP, OCP, LSP)."""
    ai_trend_operation = TrendAnalysisOperation()

    @classmethod
    def analyze_trends(cls, organization_id: str, metrics: List[str] = None) -> List[Dict[str, Any]]:
        if metrics is None:
            metrics = ['revenue', 'expenses', 'profit']
        financial_data = AnalyticsQueryService.get_transactions_for_period(
            organization_id=organization_id,
            days=180
        )
        trends = cls.ai_trend_operation.execute(financial_data, metrics)
        return trends


class InsightGenerationService:
    """Service for generating comprehensive insights (SRP, OCP, LSP)."""
    ai_insight_operation = FinancialInsightsOperation()

    @classmethod
    def generate_insights(cls, organization_id: str) -> List[str]:
        organization_data = AnalyticsQueryService.gather_organization_data(
            organization_id=organization_id
        )
        insights = cls.ai_insight_operation.execute(organization_data)
        return insights


class KPIService:
    """Service for KPI calculations."""
    
    PERIOD_DAYS = {
        'month': 30,
        'quarter': 90,
        'year': 365
    }
    
    @staticmethod
    def calculate_kpis(
        organization_id: str,
        period: str = 'month'
    ) -> Dict[str, Any]:
        """Calculate financial KPIs for a given period."""
        period_days = KPIService.PERIOD_DAYS.get(period, 30)
        period_start = datetime.now() - timedelta(days=period_days)
        
        transactions = Transaction.objects.filter(
            organization_id=organization_id,
            transaction_date__gte=period_start
        )
        
        # Calculate income and expenses
        income = KPIService._calculate_total_by_type(
            transactions, 'income'
        )
        expenses = KPIService._calculate_total_by_type(
            transactions, 'expense'
        )
        
        # Calculate derived metrics
        profit = income - expenses
        profit_margin = KPIService._calculate_profit_margin(profit, income)
        
        return {
            'period': period,
            'total_income': float(income),
            'total_expenses': float(expenses),
            'net_profit': float(profit),
            'profit_margin': float(profit_margin),
            'transaction_count': transactions.count()
        }
    
    @staticmethod
    def _calculate_total_by_type(
        queryset: QuerySet,
        transaction_type: str
    ) -> Decimal:
        """Calculate total amount for a transaction type."""
        result = queryset.filter(
            transaction_type=transaction_type
        ).aggregate(total=Sum('amount'))['total']
        
        return result or Decimal('0')
    
    @staticmethod
    def _calculate_profit_margin(profit: Decimal, income: Decimal) -> Decimal:
        """Calculate profit margin percentage."""
        if income > 0:
            return (profit / income * 100)
        return Decimal('0')
