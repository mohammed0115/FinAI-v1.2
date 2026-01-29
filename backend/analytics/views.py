from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from documents.models import Transaction
from reports.models import Insight
from core.ai_service import ai_service
from datetime import datetime, timedelta
from django.db.models import Sum, Count, Q, Avg
from decimal import Decimal

class AnalyticsViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]
    
    @action(detail=False, methods=['post'])
    def forecast(self, request):
        """Generate cash flow forecast"""
        organization_id = request.data.get('organization_id')
        periods = request.data.get('periods', 6)
        
        # Get historical transactions (limited to last 1000 for performance)
        transactions = Transaction.objects.filter(
            organization_id=organization_id
        ).order_by('-transaction_date')[:1000].values(
            'transaction_type', 'amount', 'transaction_date', 'currency'
        )
        
        # Convert to list of dicts
        historical_data = list(transactions)
        
        # Generate forecast using AI
        forecast = ai_service.generate_cash_flow_forecast(historical_data, periods)
        
        return Response({'forecast': forecast})
    
    @action(detail=False, methods=['post'])
    def detect_anomalies(self, request):
        """Detect anomalies in transactions"""
        organization_id = request.data.get('organization_id')
        
        # Get recent transactions
        transactions = Transaction.objects.filter(
            organization_id=organization_id
        ).order_by('-transaction_date')[:1000].values(
            'id', 'transaction_type', 'amount', 'transaction_date', 
            'description', 'vendor_customer', 'currency'
        )
        
        # Convert to list
        transaction_list = list(transactions)
        
        # Detect anomalies using AI
        anomalies = ai_service.detect_anomalies(transaction_list)
        
        # Save critical anomalies as insights
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
        
        return Response({'anomalies': anomalies})
    
    @action(detail=False, methods=['post'])
    def analyze_trends(self, request):
        """Analyze financial trends"""
        organization_id = request.data.get('organization_id')
        metrics = request.data.get('metrics', ['revenue', 'expenses', 'profit'])
        
        # Get transactions for trend analysis (last 6 months, limited to 1000)
        from datetime import datetime, timedelta
        six_months_ago = datetime.now() - timedelta(days=180)
        
        transactions = Transaction.objects.filter(
            organization_id=organization_id,
            transaction_date__gte=six_months_ago
        ).order_by('-transaction_date')[:1000].values(
            'transaction_type', 'amount', 'transaction_date', 'currency'
        )
        
        financial_data = list(transactions)
        
        # Analyze trends using AI
        trends = ai_service.analyze_trends(financial_data, metrics)
        
        return Response({'trends': trends})
    
    @action(detail=False, methods=['post'])
    def generate_insights(self, request):
        """Generate comprehensive financial insights"""
        organization_id = request.data.get('organization_id')
        
        from documents.models import Document
        from reports.models import Report
        from datetime import datetime, timedelta
        
        # Limit data to last 3 months for performance
        three_months_ago = datetime.now() - timedelta(days=90)
        
        # Gather organization data (limited queries)
        transactions = list(Transaction.objects.filter(
            organization_id=organization_id,
            transaction_date__gte=three_months_ago
        ).order_by('-transaction_date')[:500].values())
        
        documents = list(Document.objects.filter(
            organization_id=organization_id,
            uploaded_at__gte=three_months_ago
        ).order_by('-uploaded_at')[:200].values())
        
        reports = list(Report.objects.filter(
            organization_id=organization_id,
            created_at__gte=three_months_ago
        ).order_by('-created_at')[:50].values())
        
        organization_data = {
            'transactions': transactions,
            'documents': documents,
            'reports': reports
        }
        
        # Generate insights using AI
        insights = ai_service.generate_financial_insights(organization_data)
        
        return Response({'insights': insights})
    
    @action(detail=False, methods=['get'])
    def kpis(self, request):
        """Calculate financial KPIs"""
        organization_id = request.query_params.get('organization_id')
        period = request.query_params.get('period', 'month')
        
        # Calculate period start date
        now = datetime.now()
        if period == 'month':
            period_start = now - timedelta(days=30)
        elif period == 'quarter':
            period_start = now - timedelta(days=90)
        elif period == 'year':
            period_start = now - timedelta(days=365)
        else:
            period_start = now - timedelta(days=30)
        
        # Get transactions for the period
        transactions = Transaction.objects.filter(
            organization_id=organization_id,
            transaction_date__gte=period_start
        )
        
        # Calculate KPIs
        income = transactions.filter(transaction_type='income').aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0')
        
        expenses = transactions.filter(transaction_type='expense').aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0')
        
        profit = income - expenses
        profit_margin = (profit / income * 100) if income > 0 else Decimal('0')
        
        kpis = {
            'period': period,
            'total_income': float(income),
            'total_expenses': float(expenses),
            'net_profit': float(profit),
            'profit_margin': float(profit_margin),
            'transaction_count': transactions.count()
        }
        
        return Response(kpis)
