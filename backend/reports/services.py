"""Business logic layer for reports and insights.

This module contains all business logic for report generation
and insight management.
"""
from typing import Dict, Any
from datetime import datetime
from decimal import Decimal
from django.db.models import Sum
from django.utils import timezone

from .models import Report, Insight
from documents.models import Transaction
from core.models import User


class ReportGenerationService:
    """Service for generating financial reports."""
    
    REPORT_GENERATORS = {}
    
    @classmethod
    def register_generator(cls, report_type: str):
        """Decorator to register report generators."""
        def decorator(func):
            cls.REPORT_GENERATORS[report_type] = func
            return func
        return decorator
    
    @staticmethod
    def generate_report(
        organization_id: str,
        report_type: str,
        report_name: str,
        period_start: datetime,
        period_end: datetime,
        generated_by: User
    ) -> Report:
        """Generate a financial report.
        
        Args:
            organization_id: Organization ID
            report_type: Type of report to generate
            report_name: Name of the report
            period_start: Start date of reporting period
            period_end: End date of reporting period
            generated_by: User generating the report
            
        Returns:
            Generated Report instance
        """
        # Get transactions for the period
        transactions = Transaction.objects.filter(
            organization_id=organization_id,
            transaction_date__range=[period_start, period_end]
        )
        
        # Generate report data
        generator = ReportGenerationService.REPORT_GENERATORS.get(
            report_type,
            ReportGenerationService._generate_default_report
        )
        report_data = generator(transactions)
        
        # Create report
        report = Report.objects.create(
            organization_id=organization_id,
            report_type=report_type,
            report_name=report_name,
            period_start=period_start,
            period_end=period_end,
            status='generated',
            data_json=report_data,
            generated_by=generated_by
        )
        
        return report
    
    @staticmethod
    @register_generator('income_statement')
    def _generate_income_statement(transactions) -> Dict[str, Any]:
        """Generate income statement data."""
        income = ReportGenerationService._calculate_total(
            transactions, 'income'
        )
        expenses = ReportGenerationService._calculate_total(
            transactions, 'expense'
        )
        
        return {
            'total_revenue': float(income),
            'total_expenses': float(expenses),
            'net_income': float(income - expenses),
            'transactions': transactions.count()
        }
    
    @staticmethod
    @register_generator('cash_flow')
    def _generate_cash_flow(transactions) -> Dict[str, Any]:
        """Generate cash flow report data."""
        inflow = ReportGenerationService._calculate_total(
            transactions, 'income'
        )
        outflow = ReportGenerationService._calculate_total(
            transactions, 'expense'
        )
        
        return {
            'total_inflow': float(inflow),
            'total_outflow': float(outflow),
            'net_cash_flow': float(inflow - outflow)
        }
    
    @staticmethod
    def _generate_default_report(transactions) -> Dict[str, Any]:
        """Generate default report data."""
        return {
            'transaction_count': transactions.count(),
            'message': 'Report type not implemented'
        }
    
    @staticmethod
    def _calculate_total(queryset, transaction_type: str) -> Decimal:
        """Calculate total amount for a transaction type."""
        result = queryset.filter(
            transaction_type=transaction_type
        ).aggregate(total=Sum('amount'))['total']
        
        return result or Decimal('0')


class ReportStatusService:
    """Service for managing report status."""
    
    STATUS_HANDLERS = {
        'reviewed': lambda report, user: setattr(report, 'reviewed_by', user),
        'approved': lambda report, user: setattr(report, 'approved_by', user),
    }
    
    @staticmethod
    def update_status(
        report: Report,
        new_status: str,
        user: User
    ) -> Report:
        """Update report status with appropriate user assignment.
        
        Args:
            report: Report instance to update
            new_status: New status to set
            user: User updating the status
            
        Returns:
            Updated Report instance
        """
        report.status = new_status
        
        # Handle status-specific logic
        handler = ReportStatusService.STATUS_HANDLERS.get(new_status)
        if handler:
            handler(report, user)
        
        report.save()
        
        return report


class InsightService:
    """Service for managing insights."""
    
    @staticmethod
    def resolve_insight(
        insight: Insight,
        resolved_by: User
    ) -> Insight:
        """Mark an insight as resolved.
        
        Args:
            insight: Insight to resolve
            resolved_by: User resolving the insight
            
        Returns:
            Updated Insight instance
        """
        insight.is_resolved = True
        insight.resolved_by = resolved_by
        insight.resolved_at = timezone.now()
        insight.save()
        
        return insight
    
    @staticmethod
    def create_insight(
        organization_id: str,
        insight_type: str,
        title: str,
        description: str,
        severity: str = 'medium',
        related_entity_type: str = None,
        related_entity_id: str = None,
        data_json: Dict = None
    ) -> Insight:
        """Create a new insight.
        
        Args:
            organization_id: Organization ID
            insight_type: Type of insight
            title: Insight title
            description: Insight description
            severity: Severity level
            related_entity_type: Type of related entity
            related_entity_id: ID of related entity
            data_json: Additional data
            
        Returns:
            Created Insight instance
        """
        insight = Insight.objects.create(
            organization_id=organization_id,
            insight_type=insight_type,
            severity=severity,
            title=title,
            description=description,
            related_entity_type=related_entity_type,
            related_entity_id=related_entity_id,
            data_json=data_json or {}
        )
        
        return insight
