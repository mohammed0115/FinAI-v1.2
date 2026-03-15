from datetime import date, timedelta
from decimal import Decimal

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from compliance.models import AuditFinding, VATReconciliation, ZATCAInvoice, ZakatCalculation
from core.views.base import OrganizationActionView, OrganizationTemplateView
from documents.models import ExtractedData, OCREvidence, Transaction
from reports.models import Insight, Report


def get_arabic_pdf_generator():
    from reports.pdf_generator import arabic_pdf_generator

    return arabic_pdf_generator


class ArabicReportPageView(OrganizationTemplateView):
    template_name = 'reports/arabic_report.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        organization = self.get_organization()
        findings = AuditFinding.objects.filter(organization=organization)
        zatca_invoices = ZATCAInvoice.objects.filter(organization=organization)
        vat_reconciliations = VATReconciliation.objects.filter(organization=organization)
        zakat_calcs = ZakatCalculation.objects.filter(organization=organization)
        transactions = Transaction.objects.filter(organization=organization)

        zatca_valid = zatca_invoices.filter(status__in=['validated', 'cleared']).count()
        zatca_score = int((zatca_valid / max(zatca_invoices.count(), 1)) * 100) if zatca_invoices.exists() else 100

        vat_score = vat_reconciliations.aggregate(avg=Sum('compliance_score'))['avg']
        vat_score = int(vat_score / max(vat_reconciliations.count(), 1)) if vat_score else 100

        zakat_score = zakat_calcs.aggregate(avg=Sum('compliance_score'))['avg']
        zakat_score = int(zakat_score / max(zakat_calcs.count(), 1)) if zakat_score else 100

        income = transactions.filter(transaction_type='income').aggregate(total=Sum('amount'))['total'] or Decimal('0')
        expenses = transactions.filter(transaction_type='expense').aggregate(total=Sum('amount'))['total'] or Decimal('0')

        context.update(
            {
                'findings': findings,
                'findings_critical': findings.filter(risk_level='critical'),
                'findings_high': findings.filter(risk_level='high'),
                'findings_medium': findings.filter(risk_level='medium'),
                'findings_low': findings.filter(risk_level='low'),
                'zatca_score': zatca_score,
                'vat_score': vat_score,
                'zakat_score': zakat_score,
                'overall_score': int((zatca_score + vat_score + zakat_score) / 3),
                'income': income,
                'expenses': expenses,
                'net': income - expenses,
            }
        )
        return context


class DownloadPdfReportView(OrganizationActionView):
    def get(self, request, *args, **kwargs):
        organization = self.get_organization()

        try:
            findings = AuditFinding.objects.filter(organization=organization)
            zatca_invoices = ZATCAInvoice.objects.filter(organization=organization)
            vat_reconciliations = VATReconciliation.objects.filter(organization=organization)
            zakat_calcs = ZakatCalculation.objects.filter(organization=organization)

            zatca_valid = zatca_invoices.filter(status__in=['validated', 'cleared']).count()
            zatca_score = int((zatca_valid / max(zatca_invoices.count(), 1)) * 100) if zatca_invoices.exists() else 100

            vat_score = vat_reconciliations.aggregate(avg=Sum('compliance_score'))['avg']
            vat_score = int(vat_score / max(vat_reconciliations.count(), 1)) if vat_score else 100

            zakat_score = zakat_calcs.aggregate(avg=Sum('compliance_score'))['avg']
            zakat_score = int(zakat_score / max(zakat_calcs.count(), 1)) if zakat_score else 100

            period_end = date.today()
            organization_data = {
                'name': organization.name,
                'name_ar': organization.name_ar or organization.name,
                'vat_number': organization.vat_number or 'غير متوفر',
                'country': organization.country,
            }
            compliance_data = {
                'overall_score': int((zatca_score + vat_score + zakat_score) / 3),
                'zatca_score': zatca_score,
                'vat_score': vat_score,
                'zakat_score': zakat_score,
            }
            findings_data = [
                {
                    'finding_number': finding.finding_number,
                    'title_ar': finding.title_ar,
                    'risk_level': finding.risk_level,
                    'description_ar': finding.description_ar,
                    'recommendation_ar': finding.recommendation_ar,
                }
                for finding in findings
            ]

            arabic_pdf_generator = get_arabic_pdf_generator()
            pdf_bytes = arabic_pdf_generator.generate_report(
                organization_data=organization_data,
                compliance_data=compliance_data,
                findings_data=findings_data,
                period_start=period_end - timedelta(days=365),
                period_end=period_end,
                generated_by=request.user.email,
            )

            pdf_content = pdf_bytes if isinstance(pdf_bytes, bytes) else pdf_bytes.getvalue()
            response = HttpResponse(pdf_content, content_type='application/pdf')
            filename = f'audit_report_{organization.name.replace(" ", "_")}_{period_end.strftime("%Y%m%d")}.pdf'
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
        except Exception as exc:
            messages.error(request, f'خطأ في توليد التقرير: {exc}')
            return redirect('arabic_report')


class ReportsListPageView(OrganizationTemplateView):
    template_name = 'reports/list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['reports'] = Report.objects.filter(organization=self.get_organization()).order_by('-created_at')[:20]
        return context


class AnalyticsDashboardPageView(OrganizationTemplateView):
    template_name = 'analytics/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        organization = self.get_organization()
        transactions = Transaction.objects.filter(organization=organization)
        income = transactions.filter(transaction_type='income').aggregate(total=Sum('amount'))['total'] or 0
        expenses = transactions.filter(transaction_type='expense').aggregate(total=Sum('amount'))['total'] or 0
        context.update(
            {
                'insights': Insight.objects.filter(organization=organization).order_by('-created_at')[:20],
                'income': income,
                'expenses': expenses,
                'net': income - expenses,
            }
        )
        return context


class ResolveInsightActionView(OrganizationActionView):
    def get(self, request, *args, **kwargs):
        return redirect('analytics_dashboard')

    def post(self, request, *args, **kwargs):
        insight = get_object_or_404(Insight, id=kwargs['insight_id'], organization=self.get_organization())
        insight.is_resolved = True
        insight.save()
        messages.success(request, 'تم حل الملاحظة بنجاح')
        return redirect('analytics_dashboard')


class AIAuditReportsPageView(OrganizationTemplateView):
    template_name = 'documents/ai_audit_reports.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        organization = self.get_organization()
        reports = ExtractedData.objects.filter(organization=organization, audit_summary__isnull=False).exclude(audit_summary__exact='')

        risk_filter = self.request.GET.get('risk_level')
        if risk_filter:
            reports = reports.filter(risk_level=risk_filter)
        reports = reports.order_by('-extracted_at')

        approved_count = 0
        review_count = 0
        for report in reports:
            if report.audit_summary.get('final_status') == 'approved':
                approved_count += 1
            elif report.audit_summary.get('final_status') == 'review':
                review_count += 1

        page_obj = Paginator(reports, 20).get_page(self.request.GET.get('page'))

        context.update(
            {
                'extracted_data_list': page_obj,
                'page_obj': page_obj,
                'is_paginated': page_obj.has_other_pages(),
                'total_count': reports.count(),
                'critical_count': reports.filter(risk_level='critical').count(),
                'high_count': reports.filter(risk_level='high').count(),
                'approved_count': approved_count,
                'review_count': review_count,
            }
        )
        return context


class InvoiceAuditReportPageView(OrganizationTemplateView):
    template_name = 'documents/invoice_audit_report.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        organization = self.get_organization()
        extracted_data = get_object_or_404(
            ExtractedData,
            id=self.kwargs['extracted_data_id'],
            organization=organization,
            document__organization=organization,
        )
        context.update(
            {
                'extracted_data': extracted_data,
                'ocr_evidence': OCREvidence.objects.filter(document=extracted_data.document).first(),
                'now': timezone.now(),
            }
        )
        return context


arabic_report_view = ArabicReportPageView.as_view()
download_pdf_report_view = DownloadPdfReportView.as_view()
reports_list_view = ReportsListPageView.as_view()
analytics_dashboard_view = AnalyticsDashboardPageView.as_view()
resolve_insight_view = ResolveInsightActionView.as_view()
ai_audit_reports_view = AIAuditReportsPageView.as_view()
invoice_audit_report_view = InvoiceAuditReportPageView.as_view()


__all__ = [
    'ArabicReportPageView',
    'DownloadPdfReportView',
    'ReportsListPageView',
    'AnalyticsDashboardPageView',
    'ResolveInsightActionView',
    'AIAuditReportsPageView',
    'InvoiceAuditReportPageView',
    'arabic_report_view',
    'download_pdf_report_view',
    'reports_list_view',
    'analytics_dashboard_view',
    'resolve_insight_view',
    'ai_audit_reports_view',
    'invoice_audit_report_view',
]
