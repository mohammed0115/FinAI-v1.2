"""
Compliance Views - عرض الامتثال
Read-only API endpoints for ZATCA, VAT, Zakat, and Audit findings

SCOPE: READ-ONLY VERIFICATION AND AUDIT
This module provides READ-ONLY access to compliance data.
It does NOT generate, submit, or modify invoices.
"""
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import datetime, timedelta
from dataclasses import asdict
import logging

from .models import (
    RegulatoryReference, ZATCAInvoice, ZATCAValidationResult,
    VATReconciliation, VATDiscrepancy, ZakatCalculation,
    ZakatDiscrepancy, AuditFinding, ZATCALiveVerificationReport
)
from .serializers import (
    RegulatoryReferenceSerializer, ZATCAInvoiceSerializer,
    ZATCAInvoiceListSerializer, ZATCAValidationResultSerializer,
    VATReconciliationSerializer, VATReconciliationSummarySerializer,
    VATDiscrepancySerializer, ZakatCalculationSerializer,
    ZakatCalculationSummarySerializer, ZakatDiscrepancySerializer,
    AuditFindingSerializer, AuditFindingListSerializer,
    ArabicAuditReportSerializer
)
from .services import zatca_service, vat_service, zakat_service, arabic_report_service
from .zatca_live_verification import zatca_live_verification_service, ZATCAVerificationResult

logger = logging.getLogger(__name__)


class RegulatoryReferenceViewSet(viewsets.ReadOnlyModelViewSet):
    """
    المراجع التنظيمية - Regulatory References API
    Read-only access to regulatory articles and clauses
    """
    queryset = RegulatoryReference.objects.filter(is_active=True)
    serializer_class = RegulatoryReferenceSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by regulator
        regulator = self.request.query_params.get('regulator')
        if regulator:
            queryset = queryset.filter(regulator=regulator)
        
        # Filter by category
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category=category)
        
        return queryset
    
    @action(detail=False, methods=['get'])
    def by_regulator(self, request):
        """تجميع حسب الجهة التنظيمية"""
        grouped = {}
        for ref in self.get_queryset():
            regulator = ref.get_regulator_display()
            if regulator not in grouped:
                grouped[regulator] = []
            grouped[regulator].append(RegulatoryReferenceSerializer(ref).data)
        return Response(grouped)


class ZATCAInvoiceViewSet(viewsets.ReadOnlyModelViewSet):
    """
    الفواتير الإلكترونية - ZATCA E-Invoices API
    Read-only access with validation capabilities
    """
    queryset = ZATCAInvoice.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ZATCAInvoiceListSerializer
        return ZATCAInvoiceSerializer
    
    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin':
            queryset = ZATCAInvoice.objects.all()
        elif user.organization:
            queryset = ZATCAInvoice.objects.filter(organization=user.organization)
        else:
            queryset = ZATCAInvoice.objects.none()
        
        # Filter by status
        invoice_status = self.request.query_params.get('status')
        if invoice_status:
            queryset = queryset.filter(status=invoice_status)
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date and end_date:
            queryset = queryset.filter(issue_date__range=[start_date, end_date])
        
        return queryset
    
    @action(detail=True, methods=['get'])
    def validate(self, request, pk=None):
        """
        التحقق من صحة الفاتورة
        Validate invoice against ZATCA requirements
        """
        invoice = self.get_object()
        
        # Prepare invoice data for validation
        invoice_data = {
            'invoice_number': invoice.invoice_number,
            'uuid': str(invoice.uuid),
            'invoice_subtype': invoice.invoice_subtype,
            'issue_date': invoice.issue_date,
            'seller_name': invoice.seller_name,
            'seller_vat_number': invoice.seller_vat_number,
            'buyer_name': invoice.buyer_name,
            'total_excluding_vat': invoice.total_excluding_vat,
            'total_vat': invoice.total_vat,
            'total_including_vat': invoice.total_including_vat,
        }
        
        # Run validation
        validation_results = zatca_service.validate_invoice(invoice_data)
        overall_status, score = zatca_service.get_overall_status(validation_results)
        
        return Response({
            'invoice_id': str(invoice.id),
            'invoice_number': invoice.invoice_number,
            'validation_status': overall_status,
            'compliance_score': score,
            'total_checks': len(validation_results),
            'passed_checks': sum(1 for r in validation_results if r['is_valid']),
            'failed_checks': sum(1 for r in validation_results if not r['is_valid']),
            'validation_results': validation_results,
        })
    
    @action(detail=False, methods=['get'])
    def compliance_summary(self, request):
        """
        ملخص امتثال الفواتير الإلكترونية
        E-Invoice compliance summary
        """
        queryset = self.get_queryset()
        
        total = queryset.count()
        by_status = queryset.values('status').annotate(count=Count('id'))
        
        return Response({
            'total_invoices': total,
            'by_status': {item['status']: item['count'] for item in by_status},
            'validated_percentage': round(
                queryset.filter(status__in=['validated', 'cleared']).count() / max(total, 1) * 100, 2
            ),
        })


class VATReconciliationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    تسوية ضريبة القيمة المضافة
    VAT Reconciliation API
    """
    queryset = VATReconciliation.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'list':
            return VATReconciliationSummarySerializer
        return VATReconciliationSerializer
    
    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin':
            queryset = VATReconciliation.objects.all()
        elif user.organization:
            queryset = VATReconciliation.objects.filter(organization=user.organization)
        else:
            queryset = VATReconciliation.objects.none()
        
        return queryset
    
    @action(detail=False, methods=['post'])
    def calculate(self, request):
        """
        حساب تسوية ضريبة القيمة المضافة
        Calculate VAT reconciliation for a period
        """
        organization_id = request.data.get('organization_id')
        period_start = datetime.strptime(request.data.get('period_start'), '%Y-%m-%d').date()
        period_end = datetime.strptime(request.data.get('period_end'), '%Y-%m-%d').date()
        
        result = vat_service.reconcile_vat(organization_id, period_start, period_end)
        
        return Response(result)
    
    @action(detail=False, methods=['get'])
    def variance_report(self, request):
        """
        تقرير التفاوتات
        VAT variance report
        """
        organization_id = request.query_params.get('organization_id')
        queryset = self.get_queryset()
        
        if organization_id:
            queryset = queryset.filter(organization_id=organization_id)
        
        # Get reconciliations with variance
        with_variance = queryset.filter(~Q(total_variance=0))
        
        return Response({
            'total_reconciliations': queryset.count(),
            'with_variance': with_variance.count(),
            'total_positive_variance': with_variance.filter(total_variance__gt=0).aggregate(
                total=Sum('total_variance')
            )['total'] or 0,
            'total_negative_variance': with_variance.filter(total_variance__lt=0).aggregate(
                total=Sum('total_variance')
            )['total'] or 0,
            'average_compliance_score': queryset.aggregate(avg=Sum('compliance_score'))['avg'] or 0,
        })


class ZakatCalculationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    حساب الزكاة
    Zakat Calculation API
    """
    queryset = ZakatCalculation.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ZakatCalculationSummarySerializer
        return ZakatCalculationSerializer
    
    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin':
            queryset = ZakatCalculation.objects.all()
        elif user.organization:
            queryset = ZakatCalculation.objects.filter(organization=user.organization)
        else:
            queryset = ZakatCalculation.objects.none()
        
        return queryset
    
    @action(detail=False, methods=['post'])
    def calculate(self, request):
        """
        حساب الزكاة للسنة المالية
        Calculate Zakat for fiscal year
        """
        organization_id = request.data.get('organization_id')
        fiscal_year_end = datetime.strptime(request.data.get('fiscal_year_end'), '%Y-%m-%d').date()
        
        result = zakat_service.calculate_zakat(organization_id, fiscal_year_end)
        
        return Response(result)
    
    @action(detail=True, methods=['get'])
    def comparison(self, request, pk=None):
        """
        مقارنة الزكاة مع ضريبة الدخل
        Compare Zakat vs Income Tax
        """
        zakat_calc = self.get_object()
        
        comparison = zakat_service.compare_zakat_vs_tax(
            zakat_calc.zakat_due,
            zakat_calc.income_tax_due
        )
        
        return Response(comparison)


class AuditFindingViewSet(viewsets.ReadOnlyModelViewSet):
    """
    نتائج التدقيق
    Audit Findings API
    """
    queryset = AuditFinding.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'list':
            return AuditFindingListSerializer
        return AuditFindingSerializer
    
    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin':
            queryset = AuditFinding.objects.all()
        elif user.organization:
            queryset = AuditFinding.objects.filter(organization=user.organization)
        else:
            queryset = AuditFinding.objects.none()
        
        # Filter by risk level
        risk_level = self.request.query_params.get('risk_level')
        if risk_level:
            queryset = queryset.filter(risk_level=risk_level)
        
        # Filter by type
        finding_type = self.request.query_params.get('finding_type')
        if finding_type:
            queryset = queryset.filter(finding_type=finding_type)
        
        # Filter by resolution status
        is_resolved = self.request.query_params.get('is_resolved')
        if is_resolved is not None:
            queryset = queryset.filter(is_resolved=is_resolved.lower() == 'true')
        
        return queryset
    
    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        """
        لوحة معلومات نتائج التدقيق
        Audit findings dashboard
        """
        queryset = self.get_queryset()
        
        by_risk = queryset.values('risk_level').annotate(count=Count('id'))
        by_type = queryset.values('finding_type').annotate(count=Count('id'))
        
        unresolved = queryset.filter(is_resolved=False)
        
        return Response({
            'total_findings': queryset.count(),
            'unresolved_findings': unresolved.count(),
            'by_risk_level': {item['risk_level']: item['count'] for item in by_risk},
            'by_finding_type': {item['finding_type']: item['count'] for item in by_type},
            'total_financial_impact': queryset.aggregate(
                total=Sum('financial_impact')
            )['total'] or 0,
            'critical_unresolved': unresolved.filter(risk_level='critical').count(),
            'high_unresolved': unresolved.filter(risk_level='high').count(),
        })
    
    @action(detail=False, methods=['get'])
    def generate_report_ar(self, request):
        """
        توليد تقرير التدقيق بالعربية
        Generate Arabic audit report
        """
        organization_id = request.query_params.get('organization_id')
        period_start = datetime.strptime(
            request.query_params.get('period_start', (timezone.now() - timedelta(days=365)).strftime('%Y-%m-%d')),
            '%Y-%m-%d'
        ).date()
        period_end = datetime.strptime(
            request.query_params.get('period_end', timezone.now().strftime('%Y-%m-%d')),
            '%Y-%m-%d'
        ).date()
        
        # Get findings
        findings = list(self.get_queryset().filter(
            organization_id=organization_id,
            created_at__gte=period_start,
            created_at__lte=period_end
        ).values())
        
        # Generate report
        report = arabic_report_service.generate_audit_report_ar(
            organization_id, findings, period_start, period_end
        )
        
        return Response(report)


class ComplianceDashboardViewSet(viewsets.ViewSet):
    """
    لوحة معلومات الامتثال الشاملة
    Comprehensive Compliance Dashboard
    """
    permission_classes = [permissions.IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def overview(self, request):
        """
        نظرة عامة على الامتثال
        Compliance overview for organization
        """
        user = request.user
        org_id = request.query_params.get('organization_id') or (
            str(user.organization.id) if user.organization else None
        )
        
        if not org_id:
            return Response({'error': 'Organization ID required'}, status=400)
        
        # VAT Compliance
        vat_reconciliations = VATReconciliation.objects.filter(organization_id=org_id)
        vat_score = vat_reconciliations.aggregate(avg=Sum('compliance_score'))['avg'] or 0
        
        # Zakat Compliance
        zakat_calculations = ZakatCalculation.objects.filter(organization_id=org_id)
        zakat_score = zakat_calculations.aggregate(avg=Sum('compliance_score'))['avg'] or 0
        
        # ZATCA Compliance
        zatca_invoices = ZATCAInvoice.objects.filter(organization_id=org_id)
        zatca_validated = zatca_invoices.filter(status__in=['validated', 'cleared']).count()
        zatca_total = zatca_invoices.count()
        zatca_score = int((zatca_validated / max(zatca_total, 1)) * 100)
        
        # Audit Findings
        findings = AuditFinding.objects.filter(organization_id=org_id)
        unresolved_critical = findings.filter(risk_level='critical', is_resolved=False).count()
        unresolved_high = findings.filter(risk_level='high', is_resolved=False).count()
        
        # Overall score
        overall_score = int((vat_score + zakat_score + zatca_score) / 3)
        
        return Response({
            'organization_id': org_id,
            'overall_compliance_score': overall_score,
            'vat_compliance': {
                'score': vat_score,
                'reconciliations': vat_reconciliations.count(),
                'with_variance': vat_reconciliations.filter(~Q(total_variance=0)).count(),
            },
            'zakat_compliance': {
                'score': zakat_score,
                'calculations': zakat_calculations.count(),
            },
            'zatca_compliance': {
                'score': zatca_score,
                'total_invoices': zatca_total,
                'validated': zatca_validated,
            },
            'audit_findings': {
                'total': findings.count(),
                'unresolved': findings.filter(is_resolved=False).count(),
                'critical_unresolved': unresolved_critical,
                'high_unresolved': unresolved_high,
            },
            'risk_level': self._calculate_risk_level(overall_score, unresolved_critical, unresolved_high),
        })
    
    def _calculate_risk_level(self, score: int, critical: int, high: int) -> dict:
        """حساب مستوى المخاطر"""
        if critical > 0 or score < 50:
            return {'level': 'critical', 'level_ar': 'حرج', 'color': 'red'}
        elif high > 2 or score < 70:
            return {'level': 'high', 'level_ar': 'مرتفع', 'color': 'orange'}
        elif score < 85:
            return {'level': 'medium', 'level_ar': 'متوسط', 'color': 'yellow'}
        else:
            return {'level': 'low', 'level_ar': 'منخفض', 'color': 'green'}



class ZATCALiveVerificationViewSet(viewsets.ViewSet):
    """
    التحقق المباشر من ZATCA - ZATCA Live Verification API
    
    ╔═══════════════════════════════════════════════════════════════╗
    ║                  SCOPE LIMITATION NOTICE                      ║
    ╠═══════════════════════════════════════════════════════════════╣
    ║  This is a READ-ONLY verification service.                    ║
    ║                                                               ║
    ║  ✓ DOES: Verify existing invoice data                         ║
    ║  ✓ DOES: Check VAT number format                              ║
    ║  ✓ DOES: Validate UUID correctness                            ║
    ║  ✓ DOES: Verify hash chain integrity                          ║
    ║  ✓ DOES: Store results as audit evidence                      ║
    ║                                                               ║
    ║  ✗ DOES NOT: Generate invoices                                ║
    ║  ✗ DOES NOT: Submit invoices to ZATCA                         ║
    ║  ✗ DOES NOT: Sign invoices                                    ║
    ║  ✗ DOES NOT: Modify invoice data                              ║
    ║  ✗ DOES NOT: Act on behalf of taxpayers                       ║
    ╚═══════════════════════════════════════════════════════════════╝
    """
    permission_classes = [permissions.IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def scope_declaration(self, request):
        """
        إعلان النطاق - Scope Declaration
        Returns official scope documentation for regulatory purposes
        """
        return Response(ZATCALiveVerificationReport.get_scope_documentation())
    
    @action(detail=True, methods=['get'], url_path='verify')
    def verify_invoice(self, request, pk=None):
        """
        التحقق من فاتورة واحدة
        Verify a single invoice (READ-ONLY)
        
        This endpoint performs post-transaction, read-only verification.
        It does NOT submit, sign, or modify the invoice.
        """
        try:
            invoice = ZATCAInvoice.objects.get(id=pk)
        except ZATCAInvoice.DoesNotExist:
            return Response(
                {'error': 'الفاتورة غير موجودة', 'error_en': 'Invoice not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check organization access
        user = request.user
        if user.role != 'admin' and invoice.organization != user.organization:
            return Response(
                {'error': 'غير مصرح بالوصول', 'error_en': 'Access denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Prepare invoice data for verification
        invoice_data = {
            'id': str(invoice.id),
            'invoice_number': invoice.invoice_number,
            'uuid': str(invoice.uuid),
            'invoice_type_code': invoice.invoice_type_code,
            'invoice_subtype': invoice.invoice_subtype,
            'issue_date': invoice.issue_date,
            'seller_name': invoice.seller_name,
            'seller_vat_number': invoice.seller_vat_number,
            'buyer_name': invoice.buyer_name,
            'buyer_vat_number': invoice.buyer_vat_number,
            'total_excluding_vat': invoice.total_excluding_vat,
            'total_vat': invoice.total_vat,
            'total_including_vat': invoice.total_including_vat,
            'currency_code': invoice.currency_code,
            'invoice_hash': invoice.invoice_hash,
            'previous_invoice_hash': invoice.previous_invoice_hash,
            'qr_code': invoice.qr_code,
        }
        
        # Perform READ-ONLY verification
        report = zatca_live_verification_service.verify_invoice(invoice_data)
        
        # Store as audit evidence
        verification_results = []
        critical_errors = []
        for r in report.results:
            result_dict = {
                'check_type': r.check_type,
                'field_name': r.field_name,
                'is_valid': r.is_valid,
                'error_code': r.error_code,
                'message_ar': r.message_ar,
                'message_en': r.message_en,
                'expected_value': r.expected_value,
                'actual_value': r.actual_value,
                'regulatory_article': r.regulatory_article,
            }
            verification_results.append(result_dict)
            if not r.is_valid and r.check_type in ['mandatory_field', 'calculation']:
                critical_errors.append(result_dict)
        
        # Create audit evidence record
        evidence = ZATCALiveVerificationReport.objects.create(
            invoice=invoice,
            organization=invoice.organization,
            verification_timestamp=report.verification_timestamp,
            verification_type='post_transaction',
            overall_status=report.overall_status,
            compliance_score=report.compliance_score,
            total_checks=report.total_checks,
            passed_checks=report.passed_checks,
            failed_checks=report.failed_checks,
            warning_checks=report.warning_checks,
            verification_results_json=verification_results,
            hash_verification_json=report.hash_verification,
            summary_ar=report.summary_ar,
            summary_en=report.summary_en,
            critical_errors_json=critical_errors if critical_errors else None,
            verified_by=request.user,
            scope_declaration='READ-ONLY POST-TRANSACTION VERIFICATION',
        )
        
        logger.info(f"ZATCA Live Verification completed for invoice {invoice.invoice_number} - Status: {report.overall_status}")
        
        return Response({
            'scope_notice': {
                'ar': 'هذا تحقق للقراءة فقط - لا يتم إرسال أو تعديل الفاتورة',
                'en': 'This is READ-ONLY verification - invoice is not submitted or modified',
            },
            'evidence_id': str(evidence.id),
            'invoice_id': str(invoice.id),
            'invoice_number': invoice.invoice_number,
            'verification_timestamp': report.verification_timestamp.isoformat(),
            'overall_status': report.overall_status,
            'overall_status_ar': {
                'passed': 'ناجح',
                'warning': 'تحذير',
                'failed': 'فشل'
            }.get(report.overall_status, report.overall_status),
            'compliance_score': report.compliance_score,
            'total_checks': report.total_checks,
            'passed_checks': report.passed_checks,
            'failed_checks': report.failed_checks,
            'warning_checks': report.warning_checks,
            'verification_results': verification_results,
            'hash_verification': report.hash_verification,
            'summary_ar': report.summary_ar,
            'summary_en': report.summary_en,
            'critical_errors': critical_errors,
        })
    
    @action(detail=False, methods=['post'], url_path='verify-batch')
    def verify_batch(self, request):
        """
        التحقق من مجموعة فواتير
        Verify a batch of invoices (READ-ONLY)
        """
        invoice_ids = request.data.get('invoice_ids', [])
        
        if not invoice_ids:
            return Response(
                {'error': 'قائمة الفواتير مطلوبة', 'error_en': 'Invoice IDs required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user = request.user
        results = []
        
        for invoice_id in invoice_ids:
            try:
                invoice = ZATCAInvoice.objects.get(id=invoice_id)
                
                # Check access
                if user.role != 'admin' and invoice.organization != user.organization:
                    results.append({
                        'invoice_id': invoice_id,
                        'error': 'غير مصرح بالوصول',
                        'error_en': 'Access denied',
                    })
                    continue
                
                # Prepare invoice data
                invoice_data = {
                    'id': str(invoice.id),
                    'invoice_number': invoice.invoice_number,
                    'uuid': str(invoice.uuid),
                    'invoice_type_code': invoice.invoice_type_code,
                    'invoice_subtype': invoice.invoice_subtype,
                    'issue_date': invoice.issue_date,
                    'seller_name': invoice.seller_name,
                    'seller_vat_number': invoice.seller_vat_number,
                    'buyer_name': invoice.buyer_name,
                    'buyer_vat_number': invoice.buyer_vat_number,
                    'total_excluding_vat': invoice.total_excluding_vat,
                    'total_vat': invoice.total_vat,
                    'total_including_vat': invoice.total_including_vat,
                    'invoice_hash': invoice.invoice_hash,
                    'previous_invoice_hash': invoice.previous_invoice_hash,
                }
                
                # Verify
                report = zatca_live_verification_service.verify_invoice(invoice_data)
                
                results.append({
                    'invoice_id': str(invoice.id),
                    'invoice_number': invoice.invoice_number,
                    'overall_status': report.overall_status,
                    'compliance_score': report.compliance_score,
                    'passed_checks': report.passed_checks,
                    'failed_checks': report.failed_checks,
                })
                
            except ZATCAInvoice.DoesNotExist:
                results.append({
                    'invoice_id': invoice_id,
                    'error': 'الفاتورة غير موجودة',
                    'error_en': 'Invoice not found',
                })
        
        return Response({
            'scope_notice': {
                'ar': 'هذا تحقق للقراءة فقط - لا يتم إرسال أو تعديل الفواتير',
                'en': 'This is READ-ONLY verification - invoices are not submitted or modified',
            },
            'total_invoices': len(invoice_ids),
            'results': results,
        })
    
    @action(detail=False, methods=['post'], url_path='verify-vat-number')
    def verify_vat_number(self, request):
        """
        التحقق من الرقم الضريبي
        Verify VAT number format (READ-ONLY)
        
        Note: This validates format only.
        Actual registration status requires ZATCA portal access.
        """
        vat_number = request.data.get('vat_number', '')
        
        if not vat_number:
            return Response(
                {'error': 'الرقم الضريبي مطلوب', 'error_en': 'VAT number required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        result = zatca_live_verification_service.verify_vat_number(vat_number)
        
        return Response(result)
    
    @action(detail=False, methods=['get'], url_path='verification-history')
    def verification_history(self, request):
        """
        سجل التحققات السابقة
        Get verification history (audit trail)
        """
        user = request.user
        
        if user.role == 'admin':
            reports = ZATCALiveVerificationReport.objects.all()
        elif user.organization:
            reports = ZATCALiveVerificationReport.objects.filter(
                organization=user.organization
            )
        else:
            reports = ZATCALiveVerificationReport.objects.none()
        
        # Filters
        invoice_id = request.query_params.get('invoice_id')
        if invoice_id:
            reports = reports.filter(invoice_id=invoice_id)
        
        status_filter = request.query_params.get('status')
        if status_filter:
            reports = reports.filter(overall_status=status_filter)
        
        # Limit results
        reports = reports[:100]
        
        results = []
        for report in reports:
            results.append({
                'id': str(report.id),
                'invoice_id': str(report.invoice.id),
                'invoice_number': report.invoice.invoice_number,
                'verification_timestamp': report.verification_timestamp.isoformat(),
                'overall_status': report.overall_status,
                'compliance_score': report.compliance_score,
                'total_checks': report.total_checks,
                'passed_checks': report.passed_checks,
                'failed_checks': report.failed_checks,
                'verified_by': report.verified_by.email,
                'scope': report.scope_declaration,
            })
        
        return Response({
            'scope_notice': 'All verifications are READ-ONLY post-transaction checks',
            'total_records': len(results),
            'records': results,
        })
    
    @action(detail=True, methods=['get'], url_path='evidence')
    def get_evidence(self, request, pk=None):
        """
        الحصول على دليل التحقق
        Get verification evidence for audit purposes
        """
        try:
            evidence = ZATCALiveVerificationReport.objects.get(id=pk)
        except ZATCALiveVerificationReport.DoesNotExist:
            return Response(
                {'error': 'الدليل غير موجود', 'error_en': 'Evidence not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check access
        user = request.user
        if user.role != 'admin' and evidence.organization != user.organization:
            return Response(
                {'error': 'غير مصرح بالوصول', 'error_en': 'Access denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        return Response({
            'evidence_id': str(evidence.id),
            'scope_declaration': evidence.scope_declaration,
            'invoice': {
                'id': str(evidence.invoice.id),
                'invoice_number': evidence.invoice.invoice_number,
                'issue_date': str(evidence.invoice.issue_date),
                'seller_name': evidence.invoice.seller_name,
                'seller_vat_number': evidence.invoice.seller_vat_number,
                'total_including_vat': str(evidence.invoice.total_including_vat),
            },
            'verification': {
                'timestamp': evidence.verification_timestamp.isoformat(),
                'type': evidence.verification_type,
                'overall_status': evidence.overall_status,
                'compliance_score': evidence.compliance_score,
                'total_checks': evidence.total_checks,
                'passed_checks': evidence.passed_checks,
                'failed_checks': evidence.failed_checks,
            },
            'results': evidence.verification_results_json,
            'hash_verification': evidence.hash_verification_json,
            'summary_ar': evidence.summary_ar,
            'summary_en': evidence.summary_en,
            'critical_errors': evidence.critical_errors_json,
            'audit_trail': {
                'verified_by': evidence.verified_by.email,
                'created_at': evidence.created_at.isoformat(),
            },
            'regulatory_note': {
                'ar': 'هذا دليل تدقيق على التحقق للقراءة فقط. لا يمثل إرسال الفاتورة إلى هيئة الزكاة والضريبة والجمارك.',
                'en': 'This is audit evidence of READ-ONLY verification. It does not represent invoice submission to ZATCA.',
            },
        })
