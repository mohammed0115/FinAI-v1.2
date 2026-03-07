"""
Dashboard Views - وجهات لوحة القيادة
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Sum
from decimal import Decimal

from core.models import User, Organization
from documents.models import Document, Transaction, Account
from compliance.models import (
    AuditFinding, ZATCAInvoice, VATReconciliation, ZakatCalculation
)


@login_required
def dashboard_view(request):
    user = request.user
    organization = user.organization
    
    if not organization:
        return render(request, 'no_organization.html')
    
    # Get basic statistics
    stats = {
        'total_documents': Document.objects.filter(organization=organization).count(),
        'pending_documents': Document.objects.filter(organization=organization, status='pending').count(),
        'total_transactions': Transaction.objects.filter(organization=organization).count(),
        'total_accounts': Account.objects.filter(organization=organization).count(),
        'total_findings': AuditFinding.objects.filter(organization=organization).count(),
        'anomaly_count': Transaction.objects.filter(organization=organization, is_anomaly=True).count(),
    }
    
    # Calculate compliance score
    findings = AuditFinding.objects.filter(organization=organization)
    total_findings = findings.count()
    resolved_findings = findings.filter(is_resolved=True).count()
    stats['compliance_score'] = int((1 - (total_findings - resolved_findings) / max(total_findings, 1)) * 100) if total_findings > 0 else 100
    
    # Get compliance summary
    compliance_summary = {
        'zatca_checks': ZATCAInvoice.objects.filter(organization=organization).count(),
        'zatca_passed': ZATCAInvoice.objects.filter(organization=organization, status='cleared').count() > 0 or ZATCAInvoice.objects.filter(organization=organization).count() == 0,
        'vat_reconciliations': VATReconciliation.objects.filter(organization=organization).count(),
        'vat_variance': VATReconciliation.objects.filter(organization=organization).aggregate(total=Sum('total_variance'))['total'] or Decimal('0'),
        'zakat_calculations': ZakatCalculation.objects.filter(organization=organization).count(),
        'zakat_due': ZakatCalculation.objects.filter(organization=organization).order_by('-fiscal_year_end').first().zakat_due if ZakatCalculation.objects.filter(organization=organization).exists() else Decimal('0'),
    }
    
    # Recent findings (top 5)
    recent_findings = AuditFinding.objects.filter(organization=organization).order_by('-created_at')[:5]
    
    # Anomalous transactions (top 5)
    anomalous_transactions = Transaction.objects.filter(
        organization=organization, 
        is_anomaly=True
    ).order_by('-transaction_date')[:5]
    
    # Recent transactions (top 10)
    recent_transactions = Transaction.objects.filter(organization=organization).order_by('-transaction_date')[:10]
    
    # Chart Data: Compliance scores for ZATCA, VAT, Zakat
    zatca_invoices = ZATCAInvoice.objects.filter(organization=organization)
    zatca_valid = zatca_invoices.filter(status__in=['validated', 'cleared']).count()
    zatca_score = int((zatca_valid / max(zatca_invoices.count(), 1)) * 100) if zatca_invoices.exists() else 100
    
    vat_reconciliations = VATReconciliation.objects.filter(organization=organization)
    vat_score = vat_reconciliations.aggregate(avg=Sum('compliance_score'))['avg']
    vat_score = int(vat_score / max(vat_reconciliations.count(), 1)) if vat_score else 85
    
    zakat_calcs = ZakatCalculation.objects.filter(organization=organization)
    zakat_score = zakat_calcs.aggregate(avg=Sum('compliance_score'))['avg']
    zakat_score = int(zakat_score / max(zakat_calcs.count(), 1)) if zakat_score else 90
    
    chart_data = {
        'compliance_scores': {
            'labels': ['ZATCA', 'ض.ق.م', 'الزكاة'],
            'values': [zatca_score, vat_score, zakat_score],
        },
        'findings_by_risk': {
            'labels': ['حرج', 'مرتفع', 'متوسط', 'منخفض'],
            'values': [
                findings.filter(risk_level='critical').count(),
                findings.filter(risk_level='high').count(),
                findings.filter(risk_level='medium').count(),
                findings.filter(risk_level='low').count(),
            ],
        },
    }
    
    context = {
        'stats': stats,
        'compliance_summary': compliance_summary,
        'recent_findings': recent_findings,
        'anomalous_transactions': anomalous_transactions,
        'recent_transactions': recent_transactions,
        'chart_data': chart_data,
        'now': timezone.now(),
    }
    
    return render(request, 'dashboard.html', context)
