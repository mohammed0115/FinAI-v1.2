from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.http import HttpResponse
from django.utils import timezone
from django.db.models import Sum
from datetime import datetime, timedelta
from decimal import Decimal
import logging

from .models import Report, Insight
from .serializers import ReportSerializer, InsightSerializer
from .pdf_generator import arabic_pdf_generator
from documents.models import Transaction
from compliance.models import (
    AuditFinding, ZATCAInvoice, VATReconciliation, ZakatCalculation
)

logger = logging.getLogger(__name__)

class ReportViewSet(viewsets.ModelViewSet):
    queryset = Report.objects.all()
    serializer_class = ReportSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin':
            return Report.objects.all()
        elif user.organization:
            return Report.objects.filter(organization=user.organization)
        return Report.objects.none()
    
    def perform_create(self, serializer):
        serializer.save(generated_by=self.request.user)
    
    @action(detail=False, methods=['post'])
    def generate(self, request):
        """Generate a new financial report"""
        organization_id = request.data.get('organization_id')
        report_type = request.data.get('report_type')
        report_name = request.data.get('report_name')
        period_start = datetime.fromisoformat(request.data.get('period_start'))
        period_end = datetime.fromisoformat(request.data.get('period_end'))
        
        # Get transactions for the period
        transactions = Transaction.objects.filter(
            organization_id=organization_id,
            transaction_date__range=[period_start, period_end]
        )
        
        # Generate report data based on type
        report_data = {}
        
        if report_type == 'income_statement':
            income = transactions.filter(transaction_type='income').aggregate(
                total=Sum('amount')
            )['total'] or Decimal('0')
            
            expenses = transactions.filter(transaction_type='expense').aggregate(
                total=Sum('amount')
            )['total'] or Decimal('0')
            
            report_data = {
                'total_revenue': float(income),
                'total_expenses': float(expenses),
                'net_income': float(income - expenses),
                'transactions': transactions.count()
            }
        
        elif report_type == 'cash_flow':
            inflow = transactions.filter(transaction_type='income').aggregate(
                total=Sum('amount')
            )['total'] or Decimal('0')
            
            outflow = transactions.filter(transaction_type='expense').aggregate(
                total=Sum('amount')
            )['total'] or Decimal('0')
            
            report_data = {
                'total_inflow': float(inflow),
                'total_outflow': float(outflow),
                'net_cash_flow': float(inflow - outflow)
            }
        
        # Create report
        report = Report.objects.create(
            organization_id=organization_id,
            report_type=report_type,
            report_name=report_name,
            period_start=period_start,
            period_end=period_end,
            status='generated',
            data_json=report_data,
            generated_by=request.user
        )
        
        serializer = self.get_serializer(report)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        """Update report status"""
        report = self.get_object()
        new_status = request.data.get('status')
        
        report.status = new_status
        
        if new_status == 'reviewed':
            report.reviewed_by = request.user
        elif new_status == 'approved':
            report.approved_by = request.user
        
        report.save()
        
        serializer = self.get_serializer(report)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='download-pdf')
    def download_pdf_report(self, request):
        """
        تحميل تقرير التدقيق بصيغة PDF
        Download Arabic PDF Audit Report (READ-ONLY)
        
        This endpoint generates an immutable PDF audit report from existing verified data.
        It does NOT modify any audit logic, findings, or database records.
        
        Query Parameters:
        - period_start: Start date (YYYY-MM-DD)
        - period_end: End date (YYYY-MM-DD)
        """
        user = request.user
        organization = user.organization
        
        if not organization:
            return Response(
                {'error': 'لا توجد منشأة مرتبطة بالحساب', 'error_en': 'No organization associated'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Parse date parameters
        period_start_str = request.query_params.get('period_start')
        period_end_str = request.query_params.get('period_end')
        
        if period_start_str:
            try:
                period_start = datetime.strptime(period_start_str, '%Y-%m-%d').date()
            except ValueError:
                return Response({'error': 'تنسيق تاريخ البداية غير صحيح'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            period_start = (timezone.now() - timedelta(days=30)).date()
        
        if period_end_str:
            try:
                period_end = datetime.strptime(period_end_str, '%Y-%m-%d').date()
            except ValueError:
                return Response({'error': 'تنسيق تاريخ النهاية غير صحيح'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            period_end = timezone.now().date()
        
        # Gather organization data
        organization_data = {
            'id': str(organization.id),
            'name': organization.name,
            'tax_id': getattr(organization, 'tax_id', None) or '',
        }
        
        # Gather compliance data
        zatca_invoices = ZATCAInvoice.objects.filter(organization=organization)
        zatca_valid = zatca_invoices.filter(status__in=['validated', 'cleared']).count()
        zatca_score = int((zatca_valid / max(zatca_invoices.count(), 1)) * 100) if zatca_invoices.exists() else 100
        
        vat_reconciliations = VATReconciliation.objects.filter(organization=organization)
        vat_total_score = vat_reconciliations.aggregate(total=Sum('compliance_score'))['total']
        vat_score = int(vat_total_score / max(vat_reconciliations.count(), 1)) if vat_total_score else 100
        
        zakat_calcs = ZakatCalculation.objects.filter(organization=organization)
        zakat_total_score = zakat_calcs.aggregate(total=Sum('compliance_score'))['total']
        zakat_score = int(zakat_total_score / max(zakat_calcs.count(), 1)) if zakat_total_score else 100
        
        overall_score = int((zatca_score + vat_score + zakat_score) / 3)
        
        # VAT summary
        latest_vat = vat_reconciliations.order_by('-period_end').first()
        vat_summary = {}
        if latest_vat:
            vat_summary = {
                'collected': float(latest_vat.total_output_vat or 0),
                'paid': float(latest_vat.total_input_vat or 0),
                'net': float(latest_vat.net_vat_due or 0),
            }
        
        # Zakat summary
        latest_zakat = zakat_calcs.order_by('-fiscal_year_end').first()
        zakat_summary = {}
        if latest_zakat:
            zakat_summary = {
                'base': float(latest_zakat.net_zakat_base or 0),
                'due': float(latest_zakat.zakat_due or 0),
            }
        
        compliance_data = {
            'overall_score': overall_score,
            'zatca_score': zatca_score,
            'vat_score': vat_score,
            'zakat_score': zakat_score,
            'vat_summary': vat_summary,
            'zakat_summary': zakat_summary,
        }
        
        # Gather findings data
        findings = AuditFinding.objects.filter(organization=organization)
        findings_data = []
        for f in findings:
            reg_ref = None
            if f.regulatory_reference:
                reg_ref = {
                    'article_number': f.regulatory_reference.article_number,
                    'title_ar': f.regulatory_reference.title_ar,
                }
            
            findings_data.append({
                'finding_number': f.finding_number,
                'title_ar': f.title_ar,
                'description_ar': f.description_ar,
                'impact_ar': f.impact_ar,
                'recommendation_ar': f.recommendation_ar,
                'ai_explanation_ar': f.ai_explanation_ar,
                'risk_level': f.risk_level,
                'financial_impact': float(f.financial_impact) if f.financial_impact else 0,
                'regulatory_reference': reg_ref,
                'is_resolved': f.is_resolved,
            })
        
        # Generate PDF
        try:
            pdf_bytes = arabic_pdf_generator.generate_report(
                organization_data=organization_data,
                compliance_data=compliance_data,
                findings_data=findings_data,
                period_start=period_start,
                period_end=period_end,
                generated_by=user.email,
            )
            
            # Create response with PDF
            response = HttpResponse(pdf_bytes, content_type='application/pdf')
            filename = f"audit_report_{organization.name.replace(' ', '_')}_{period_end.strftime('%Y%m%d')}.pdf"
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            response['X-Report-Type'] = 'READ-ONLY-AUDIT-REPORT'
            response['X-Generated-At'] = timezone.now().isoformat()
            
            logger.info(f"PDF report generated for {organization.name} by {user.email}")
            
            return response
            
        except Exception as e:
            logger.error(f"PDF generation error: {e}")
            return Response(
                {'error': 'خطأ في إنشاء التقرير', 'error_en': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class InsightViewSet(viewsets.ModelViewSet):
    queryset = Insight.objects.all()
    serializer_class = InsightSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        queryset = Insight.objects.all() if user.role == 'admin' else Insight.objects.filter(organization=user.organization)
        
        # Filter by resolved status
        include_resolved = self.request.query_params.get('include_resolved', 'false').lower() == 'true'
        if not include_resolved:
            queryset = queryset.filter(is_resolved=False)
        
        return queryset
    
    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        """Mark insight as resolved"""
        insight = self.get_object()
        insight.is_resolved = True
        insight.resolved_by = request.user
        insight.resolved_at = timezone.now()
        insight.save()
        
        serializer = self.get_serializer(insight)
        return Response(serializer.data)
