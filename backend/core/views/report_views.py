"""
Report Views - وجهات التقارير
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from django.db.models import Sum
from decimal import Decimal

from core.models import Organization
from documents.models import Transaction
from reports.models import Report, Insight
from reports.pdf_generator import arabic_pdf_generator
from compliance.models import (
    AuditFinding, ZATCAInvoice, VATReconciliation, ZakatCalculation
)


@login_required
def arabic_report_view(request):
    """صفحة التقرير العربي"""
    user = request.user
    organization = user.organization
    
    # Get all data for report
    findings = AuditFinding.objects.filter(organization=organization)
    zatca_invoices = ZATCAInvoice.objects.filter(organization=organization)
    vat_reconciliations = VATReconciliation.objects.filter(organization=organization)
    zakat_calcs = ZakatCalculation.objects.filter(organization=organization)
    transactions = Transaction.objects.filter(organization=organization)
    
    # Calculate scores
    zatca_valid = zatca_invoices.filter(status__in=['validated', 'cleared']).count()
    zatca_score = int((zatca_valid / max(zatca_invoices.count(), 1)) * 100) if zatca_invoices.exists() else 100
    
    vat_score = vat_reconciliations.aggregate(avg=Sum('compliance_score'))['avg']
    vat_score = int(vat_score / max(vat_reconciliations.count(), 1)) if vat_score else 100
    
    zakat_score = zakat_calcs.aggregate(avg=Sum('compliance_score'))['avg']
    zakat_score = int(zakat_score / max(zakat_calcs.count(), 1)) if zakat_score else 100
    
    overall_score = int((zatca_score + vat_score + zakat_score) / 3)
    
    # Financial summary
    income = transactions.filter(transaction_type='income').aggregate(total=Sum('amount'))['total'] or Decimal('0')
    expenses = transactions.filter(transaction_type='expense').aggregate(total=Sum('amount'))['total'] or Decimal('0')
    
    context = {
        'organization': organization,
        'findings': findings,
        'findings_critical': findings.filter(risk_level='critical'),
        'findings_high': findings.filter(risk_level='high'),
        'findings_medium': findings.filter(risk_level='medium'),
        'findings_low': findings.filter(risk_level='low'),
        'zatca_score': zatca_score,
        'vat_score': vat_score,
        'zakat_score': zakat_score,
        'overall_score': overall_score,
        'income': income,
        'expenses': expenses,
        'net': income - expenses,
    }
    
    return render(request, 'reports/arabic_report.html', context)


@login_required
def download_pdf_report_view(request):
    """
    تحميل تقرير PDF بالعربية
    Download Arabic PDF Audit Report
    """
    from datetime import date, timedelta
    
    user = request.user
    organization = user.organization
    
    try:
        # Get all data for report
        findings = AuditFinding.objects.filter(organization=organization)
        zatca_invoices = ZATCAInvoice.objects.filter(organization=organization)
        vat_reconciliations = VATReconciliation.objects.filter(organization=organization)
        zakat_calcs = ZakatCalculation.objects.filter(organization=organization)
        
        # Calculate scores
        zatca_valid = zatca_invoices.filter(status__in=['validated', 'cleared']).count()
        zatca_score = int((zatca_valid / max(zatca_invoices.count(), 1)) * 100) if zatca_invoices.exists() else 100
        
        vat_score = vat_reconciliations.aggregate(avg=Sum('compliance_score'))['avg']
        vat_score = int(vat_score / max(vat_reconciliations.count(), 1)) if vat_score else 100
        
        zakat_score = zakat_calcs.aggregate(avg=Sum('compliance_score'))['avg']
        zakat_score = int(zakat_score / max(zakat_calcs.count(), 1)) if zakat_score else 100
        
        overall_score = int((zatca_score + vat_score + zakat_score) / 3)
        
        # Prepare data for PDF generator
        organization_data = {
            'name': organization.name,
            'name_ar': organization.name_ar or organization.name,
            'vat_number': organization.vat_number or 'غير متوفر',
            'country': organization.country,
        }
        
        compliance_data = {
            'overall_score': overall_score,
            'zatca_score': zatca_score,
            'vat_score': vat_score,
            'zakat_score': zakat_score,
        }
        
        findings_data = [
            {
                'finding_number': f.finding_number,
                'title_ar': f.title_ar,
                'risk_level': f.risk_level,
                'description_ar': f.description_ar,
                'recommendation_ar': f.recommendation_ar,
            }
            for f in findings
        ]
        
        period_end = date.today()
        period_start = period_end - timedelta(days=365)
        
        # Generate PDF
        pdf_bytes = arabic_pdf_generator.generate_report(
            organization_data=organization_data,
            compliance_data=compliance_data,
            findings_data=findings_data,
            period_start=period_start,
            period_end=period_end,
            generated_by=user.email
        )
        
        # Create response - handle both bytes and BytesIO
        pdf_content = pdf_bytes if isinstance(pdf_bytes, bytes) else pdf_bytes.getvalue()
        response = HttpResponse(pdf_content, content_type='application/pdf')
        filename = f'audit_report_{organization.name.replace(" ", "_")}_{period_end.strftime("%Y%m%d")}.pdf'
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response
        
    except Exception as e:
        messages.error(request, f'خطأ في توليد التقرير: {str(e)}')
        return redirect('arabic_report')


@login_required
def reports_list_view(request):
    """قائمة التقارير"""
    user = request.user
    organization = user.organization
    
    reports = Report.objects.filter(organization=organization).order_by('-created_at')[:20]
    
    context = {
        'reports': reports,
    }
    
    return render(request, 'reports/list.html', context)


@login_required
def analytics_dashboard_view(request):
    """لوحة التحليلات"""
    user = request.user
    organization = user.organization
    
    # Get insights
    insights = Insight.objects.filter(organization=organization).order_by('-created_at')[:20]
    
    # Financial summary
    transactions = Transaction.objects.filter(organization=organization)
    income = transactions.filter(transaction_type='income').aggregate(total=Sum('amount'))['total'] or 0
    expenses = transactions.filter(transaction_type='expense').aggregate(total=Sum('amount'))['total'] or 0
    
    context = {
        'insights': insights,
        'income': income,
        'expenses': expenses,
        'net': income - expenses,
    }
    
    return render(request, 'analytics/dashboard.html', context)


@login_required
def resolve_insight_view(request, insight_id):
    """حل الملاحظة"""
    user = request.user
    organization = user.organization
    
    insight = get_object_or_404(Insight, id=insight_id, organization=organization)
    
    if request.method == 'POST':
        insight.is_resolved = True
        insight.save()
        messages.success(request, 'تم حل الملاحظة بنجاح')
    
    return redirect('analytics_dashboard')
