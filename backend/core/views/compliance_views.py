import logging
from decimal import Decimal

from django.contrib import messages
from django.db.models import Sum
from django.shortcuts import render

from compliance.models import AuditFinding, RegulatoryReference, VATReconciliation, ZATCAInvoice, ZATCAVerificationLog, ZakatCalculation
from core.views.base import OrganizationTemplateView

logger = logging.getLogger(__name__)


class ComplianceOverviewPageView(OrganizationTemplateView):
    template_name = 'compliance/overview.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        organization = self.get_organization()

        zatca_invoices = ZATCAInvoice.objects.filter(organization=organization).order_by('-issue_date')[:10]
        zatca_invoices_count = ZATCAInvoice.objects.filter(organization=organization).count()
        zatca_valid_count = ZATCAInvoice.objects.filter(
            organization=organization,
            status__in=['validated', 'cleared'],
        ).count()
        zatca_score = int((zatca_valid_count / max(zatca_invoices_count, 1)) * 100) if zatca_invoices_count > 0 else 100

        vat_reconciliations = VATReconciliation.objects.filter(organization=organization).order_by('-period_end')[:10]
        vat_reconciliations_count = VATReconciliation.objects.filter(organization=organization).count()
        vat_score_sum = VATReconciliation.objects.filter(organization=organization).aggregate(avg=Sum('compliance_score'))['avg']
        vat_score = int(vat_score_sum / max(vat_reconciliations_count, 1)) if vat_score_sum else 100

        zakat_calcs = ZakatCalculation.objects.filter(organization=organization)
        latest_zakat = zakat_calcs.order_by('-fiscal_year_end').first()
        zakat_due = latest_zakat.zakat_due if latest_zakat else Decimal('0')
        zakat_score_sum = zakat_calcs.aggregate(avg=Sum('compliance_score'))['avg']
        zakat_score = int(zakat_score_sum / max(zakat_calcs.count(), 1)) if zakat_score_sum else 100

        total_findings = AuditFinding.objects.filter(organization=organization).count()
        unresolved_findings = AuditFinding.objects.filter(organization=organization, is_resolved=False).count()

        context.update(
            {
                'overall_score': int((zatca_score + vat_score + zakat_score) / 3),
                'zatca_score': zatca_score,
                'zatca_invoices_count': zatca_invoices_count,
                'zatca_invoices': zatca_invoices,
                'vat_score': vat_score,
                'vat_reconciliations_count': vat_reconciliations_count,
                'vat_reconciliations': vat_reconciliations,
                'zakat_score': zakat_score,
                'zakat_due': zakat_due,
                'latest_zakat': latest_zakat,
                'total_findings': total_findings,
                'unresolved_findings': unresolved_findings,
                'regulatory_references': RegulatoryReference.objects.all()[:10],
            }
        )
        return context


class ZATCAVerificationPageView(OrganizationTemplateView):
    template_name = 'compliance/zatca_verification.html'

    def build_context(self, verification_result=None):
        from compliance.zatca_api_service import zatca_api_service

        organization = self.get_organization()
        return self.get_context_data(
            verification_result=verification_result,
            recent_verifications=ZATCAVerificationLog.objects.filter(organization=organization).order_by('-created_at')[:10],
            scope_docs=zatca_api_service.get_scope_documentation(),
        )

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name, self.build_context())

    def post(self, request, *args, **kwargs):
        from compliance.zatca_api_service import zatca_api_service

        organization = self.get_organization()
        user = request.user
        verification_result = None
        verification_type = request.POST.get('verification_type', 'vat')

        if verification_type == 'vat':
            vat_number = request.POST.get('vat_number', '').strip()
            if vat_number:
                verification_result = zatca_api_service.verify_vat_number(vat_number)
                ZATCAVerificationLog.objects.create(
                    organization=organization,
                    verification_type='vat_number',
                    input_identifier=vat_number,
                    is_valid=verification_result.get('valid', False),
                    compliance_score=100 if verification_result.get('valid') else 0,
                    passed_checks=1 if verification_result.get('valid') else 0,
                    failed_checks=0 if verification_result.get('valid') else 1,
                    message_ar=verification_result.get('message_ar') or verification_result.get('error_message_ar'),
                    message_en=verification_result.get('message_en'),
                    error_code=verification_result.get('error_code'),
                    response_json=verification_result,
                    processing_time_ms=verification_result.get('processing_time_ms', 0),
                    audit_hash=verification_result.get('audit_hash', ''),
                    verified_by=user,
                )
                if verification_result.get('valid'):
                    messages.success(request, verification_result.get('message_ar', 'تم التحقق بنجاح'))
                else:
                    messages.error(request, verification_result.get('error_message_ar', 'فشل التحقق'))

        elif verification_type == 'invoice':
            invoice_xml = request.POST.get('invoice_xml', '')
            invoice_hash = request.POST.get('invoice_hash', '')
            invoice_uuid = request.POST.get('invoice_uuid', '')
            if invoice_xml and invoice_uuid:
                verification_result = zatca_api_service.verify_invoice_structure(invoice_xml, invoice_hash, invoice_uuid)
                ZATCAVerificationLog.objects.create(
                    organization=organization,
                    verification_type='invoice_structure',
                    input_identifier=invoice_uuid,
                    is_valid=verification_result.get('valid', False),
                    compliance_score=verification_result.get('compliance_score', 0),
                    passed_checks=verification_result.get('passed_count', 0),
                    failed_checks=verification_result.get('failed_count', 0),
                    message_ar=verification_result.get('message_ar'),
                    message_en=verification_result.get('message_en'),
                    response_json=verification_result,
                    processing_time_ms=verification_result.get('processing_time_ms', 0),
                    audit_hash=verification_result.get('audit_hash', ''),
                    verified_by=user,
                )
                if verification_result.get('valid'):
                    messages.success(request, verification_result.get('message_ar', 'تم التحقق بنجاح'))
                else:
                    messages.error(request, verification_result.get('message_ar', 'فشل التحقق'))

        return render(request, self.template_name, self.build_context(verification_result=verification_result))


compliance_overview_view = ComplianceOverviewPageView.as_view()
zatca_verification_view = ZATCAVerificationPageView.as_view()


__all__ = [
    'ComplianceOverviewPageView',
    'ZATCAVerificationPageView',
    'compliance_overview_view',
    'zatca_verification_view',
]
