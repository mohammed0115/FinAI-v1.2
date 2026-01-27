from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from django.utils import timezone
from django.core.paginator import Paginator
from django.db.models import Sum, Count, Q
from decimal import Decimal
from datetime import datetime, timedelta
import logging

from core.models import User, Organization
from documents.models import Document, Transaction, Account
from reports.models import Report, Insight
from reports.pdf_generator import arabic_pdf_generator
from compliance.models import (
    AuditFinding, ZATCAInvoice, VATReconciliation, 
    ZakatCalculation, RegulatoryReference
)
from compliance.services import arabic_report_service

logger = logging.getLogger(__name__)


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        user = authenticate(request, email=email, password=password)
        
        if user is not None:
            auth_login(request, user)
            return redirect('dashboard')
        else:
            messages.error(request, 'البريد الإلكتروني أو كلمة المرور غير صحيحة')
    
    return render(request, 'login.html')


def logout_view(request):
    auth_logout(request)
    return redirect('login')


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
    
    context = {
        'stats': stats,
        'compliance_summary': compliance_summary,
        'recent_findings': recent_findings,
        'anomalous_transactions': anomalous_transactions,
        'recent_transactions': recent_transactions,
        'now': timezone.now(),
    }
    
    return render(request, 'dashboard.html', context)


@login_required
def compliance_overview_view(request):
    user = request.user
    organization = user.organization
    
    if not organization:
        return render(request, 'no_organization.html')
    
    # Calculate scores
    zatca_invoices = ZATCAInvoice.objects.filter(organization=organization)
    zatca_valid = zatca_invoices.filter(status__in=['validated', 'cleared']).count()
    zatca_score = int((zatca_valid / max(zatca_invoices.count(), 1)) * 100) if zatca_invoices.exists() else 100
    
    vat_reconciliations = VATReconciliation.objects.filter(organization=organization)
    vat_score = vat_reconciliations.aggregate(avg=Sum('compliance_score'))['avg']
    vat_score = int(vat_score / max(vat_reconciliations.count(), 1)) if vat_score else 100
    
    zakat_calcs = ZakatCalculation.objects.filter(organization=organization)
    zakat_score = zakat_calcs.aggregate(avg=Sum('compliance_score'))['avg']
    zakat_score = int(zakat_score / max(zakat_calcs.count(), 1)) if zakat_score else 100
    
    # Overall score
    overall_score = int((zatca_score + vat_score + zakat_score) / 3)
    
    # Audit findings
    findings = AuditFinding.objects.filter(organization=organization)
    total_findings = findings.count()
    unresolved_findings = findings.filter(is_resolved=False).count()
    
    # Latest zakat
    latest_zakat = ZakatCalculation.objects.filter(organization=organization).order_by('-fiscal_year_end').first()
    
    # Regulatory references
    regulatory_references = RegulatoryReference.objects.filter(is_active=True)[:10]
    
    context = {
        'organization': organization,
        'overall_score': overall_score,
        'zatca_score': zatca_score,
        'vat_score': vat_score,
        'zakat_score': zakat_score,
        'zatca_invoices_count': zatca_invoices.count(),
        'vat_reconciliations_count': vat_reconciliations.count(),
        'zakat_due': latest_zakat.zakat_due if latest_zakat else Decimal('0'),
        'total_findings': total_findings,
        'unresolved_findings': unresolved_findings,
        'zatca_invoices': zatca_invoices[:10],
        'vat_reconciliations': vat_reconciliations[:5],
        'latest_zakat': latest_zakat,
        'regulatory_references': regulatory_references,
    }
    
    return render(request, 'compliance/overview.html', context)


@login_required
def audit_findings_list_view(request):
    user = request.user
    organization = user.organization
    
    if not organization:
        return render(request, 'no_organization.html')
    
    findings = AuditFinding.objects.filter(organization=organization)
    
    # Apply filters
    risk_level = request.GET.get('risk_level')
    finding_type = request.GET.get('finding_type')
    status = request.GET.get('status')
    
    if risk_level:
        findings = findings.filter(risk_level=risk_level)
    if finding_type:
        findings = findings.filter(finding_type=finding_type)
    if status == 'resolved':
        findings = findings.filter(is_resolved=True)
    elif status == 'unresolved':
        findings = findings.filter(is_resolved=False)
    
    findings = findings.order_by('-created_at')
    
    # Count by risk level
    all_findings = AuditFinding.objects.filter(organization=organization)
    findings_by_risk = {
        'critical': all_findings.filter(risk_level='critical').count(),
        'high': all_findings.filter(risk_level='high').count(),
        'medium': all_findings.filter(risk_level='medium').count(),
        'low': all_findings.filter(risk_level='low').count(),
    }
    
    # Pagination
    paginator = Paginator(findings, 20)
    page_number = request.GET.get('page')
    findings_page = paginator.get_page(page_number)
    
    context = {
        'findings': findings_page,
        'findings_by_risk': findings_by_risk,
    }
    
    return render(request, 'findings/list.html', context)


@login_required
def audit_finding_detail_view(request, finding_id):
    user = request.user
    organization = user.organization
    
    finding = get_object_or_404(AuditFinding, id=finding_id, organization=organization)
    
    context = {
        'finding': finding,
    }
    
    return render(request, 'findings/detail.html', context)


@login_required
def transactions_view(request):
    user = request.user
    organization = user.organization
    
    if not organization:
        return render(request, 'no_organization.html')
    
    transactions = Transaction.objects.filter(organization=organization)
    
    # Apply filters
    txn_type = request.GET.get('type')
    anomaly = request.GET.get('anomaly')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    if txn_type:
        transactions = transactions.filter(transaction_type=txn_type)
    if anomaly == '1':
        transactions = transactions.filter(is_anomaly=True)
    elif anomaly == '0':
        transactions = transactions.filter(is_anomaly=False)
    if date_from:
        transactions = transactions.filter(transaction_date__gte=date_from)
    if date_to:
        transactions = transactions.filter(transaction_date__lte=date_to)
    
    transactions = transactions.order_by('-transaction_date')
    
    # Calculate totals
    all_txns = Transaction.objects.filter(organization=organization)
    income_total = all_txns.filter(transaction_type='income').aggregate(total=Sum('amount'))['total'] or Decimal('0')
    expense_total = all_txns.filter(transaction_type='expense').aggregate(total=Sum('amount'))['total'] or Decimal('0')
    anomaly_count = all_txns.filter(is_anomaly=True).count()
    total_count = all_txns.count()
    
    # Pagination
    paginator = Paginator(transactions, 50)
    page_number = request.GET.get('page')
    transactions_page = paginator.get_page(page_number)
    
    context = {
        'transactions': transactions_page,
        'total_count': total_count,
        'anomaly_count': anomaly_count,
        'income_total': income_total,
        'expense_total': expense_total,
    }
    
    return render(request, 'transactions.html', context)


@login_required
def transaction_detail_view(request, transaction_id):
    user = request.user
    organization = user.organization
    
    transaction = get_object_or_404(Transaction, id=transaction_id, organization=organization)
    
    # Get related audit findings
    audit_findings = AuditFinding.objects.filter(
        organization=organization,
        related_entity_type='Transaction',
        related_entity_id=transaction.id
    )
    
    context = {
        'transaction': transaction,
        'audit_findings': audit_findings,
    }
    
    return render(request, 'transactions_detail.html', context)


@login_required
def accounts_list_view(request):
    user = request.user
    organization = user.organization
    
    if not organization:
        return render(request, 'no_organization.html')
    
    accounts = Account.objects.filter(organization=organization)
    
    # Apply filters
    account_type = request.GET.get('type')
    search = request.GET.get('search')
    
    if account_type:
        accounts = accounts.filter(account_type=account_type)
    if search:
        accounts = accounts.filter(
            Q(account_name__icontains=search) | 
            Q(account_code__icontains=search) |
            Q(account_name_ar__icontains=search)
        )
    
    accounts = accounts.order_by('account_code')
    
    # Calculate summary by type
    all_accounts = Account.objects.filter(organization=organization)
    summary = {
        'asset': all_accounts.filter(account_type='asset').aggregate(total=Sum('current_balance'))['total'] or Decimal('0'),
        'liability': all_accounts.filter(account_type='liability').aggregate(total=Sum('current_balance'))['total'] or Decimal('0'),
        'equity': all_accounts.filter(account_type='equity').aggregate(total=Sum('current_balance'))['total'] or Decimal('0'),
        'revenue': all_accounts.filter(account_type='revenue').aggregate(total=Sum('current_balance'))['total'] or Decimal('0'),
        'expense': all_accounts.filter(account_type='expense').aggregate(total=Sum('current_balance'))['total'] or Decimal('0'),
    }
    
    # Pagination
    paginator = Paginator(accounts, 50)
    page_number = request.GET.get('page')
    accounts_page = paginator.get_page(page_number)
    
    context = {
        'accounts': accounts_page,
        'accounts_count': all_accounts.count(),
        'summary': summary,
    }
    
    return render(request, 'accounts/list.html', context)


@login_required
def account_detail_view(request, account_id):
    user = request.user
    organization = user.organization
    
    account = get_object_or_404(Account, id=account_id, organization=organization)
    
    # Get sub-accounts
    sub_accounts = Account.objects.filter(parent_account=account)
    
    # Get recent transactions for this account
    recent_transactions = Transaction.objects.filter(
        organization=organization,
        account=account
    ).order_by('-transaction_date')[:20]
    
    transactions_count = Transaction.objects.filter(
        organization=organization,
        account=account
    ).count()
    
    context = {
        'account': account,
        'sub_accounts': sub_accounts,
        'recent_transactions': recent_transactions,
        'transactions_count': transactions_count,
    }
    
    return render(request, 'accounts/detail.html', context)


@login_required
def arabic_report_view(request):
    user = request.user
    organization = user.organization
    
    if not organization:
        return render(request, 'no_organization.html')
    
    # Get all findings for the report
    findings = AuditFinding.objects.filter(organization=organization)
    findings_data = []
    for f in findings:
        findings_data.append({
            'finding_number': f.finding_number,
            'finding_type': f.finding_type,
            'risk_level': f.risk_level,
            'title_ar': f.title_ar,
            'description_ar': f.description_ar,
            'impact_ar': f.impact_ar,
            'recommendation_ar': f.recommendation_ar,
            'financial_impact': f.financial_impact,
            'is_resolved': f.is_resolved,
        })
    
    # Generate report
    thirty_days_ago = timezone.now().date() - timedelta(days=30)
    today = timezone.now().date()
    
    report = arabic_report_service.generate_audit_report_ar(
        organization_id=str(organization.id),
        findings=findings_data,
        period_start=thirty_days_ago,
        period_end=today
    )
    
    context = {
        'organization': organization,
        'report': report,
    }
    
    return render(request, 'reports/arabic_report.html', context)


@login_required
def documents_view(request):
    user = request.user
    organization = user.organization
    
    documents = Document.objects.filter(organization=organization).order_by('-uploaded_at')[:100]
    
    context = {
        'documents': documents,
    }
    
    return render(request, 'documents.html', context)


@login_required
def reports_list_view(request):
    user = request.user
    organization = user.organization
    
    reports = Report.objects.filter(organization=organization).order_by('-created_at')
    
    context = {
        'reports': reports,
    }
    
    return render(request, 'reports.html', context)


@login_required
def analytics_dashboard_view(request):
    user = request.user
    organization = user.organization
    
    thirty_days_ago = timezone.now() - timedelta(days=30)
    
    transactions = Transaction.objects.filter(
        organization=organization,
        transaction_date__gte=thirty_days_ago
    )
    
    income = transactions.filter(transaction_type='income').aggregate(
        total=Sum('amount')
    )['total'] or Decimal('0')
    
    expenses = transactions.filter(transaction_type='expense').aggregate(
        total=Sum('amount')
    )['total'] or Decimal('0')
    
    insights = Insight.objects.filter(organization=organization, is_resolved=False)
    
    context = {
        'total_income': float(income),
        'total_expenses': float(expenses),
        'net_profit': float(income - expenses),
        'insights': insights,
    }
    
    return render(request, 'analytics.html', context)


@login_required
def resolve_insight_view(request, insight_id):
    insight = get_object_or_404(Insight, id=insight_id, organization=request.user.organization)
    
    if request.method == 'POST':
        insight.is_resolved = True
        insight.resolved_by = request.user
        insight.resolved_at = timezone.now()
        insight.save()
        messages.success(request, 'تم حل الملاحظة بنجاح')
    
    return redirect('dashboard')



@login_required
def download_pdf_report_view(request):
    """
    تحميل تقرير التدقيق بصيغة PDF
    Download Arabic PDF Audit Report (READ-ONLY)
    """
    user = request.user
    organization = user.organization
    
    if not organization:
        messages.error(request, 'لا توجد منشأة مرتبطة بالحساب')
        return redirect('dashboard')
    
    # Get date parameters
    period_start_str = request.GET.get('period_start')
    period_end_str = request.GET.get('period_end')
    
    if period_start_str:
        try:
            period_start = datetime.strptime(period_start_str, '%Y-%m-%d').date()
        except ValueError:
            period_start = (timezone.now() - timedelta(days=30)).date()
    else:
        period_start = (timezone.now() - timedelta(days=30)).date()
    
    if period_end_str:
        try:
            period_end = datetime.strptime(period_end_str, '%Y-%m-%d').date()
        except ValueError:
            period_end = timezone.now().date()
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
    
    # VAT/Zakat summaries
    latest_vat = vat_reconciliations.order_by('-period_end').first()
    vat_summary = {}
    if latest_vat:
        vat_summary = {
            'collected': float(latest_vat.total_output_vat or 0),
            'paid': float(latest_vat.total_input_vat or 0),
            'net': float(latest_vat.net_vat_due or 0),
        }
    
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
    
    # Gather findings
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
        
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        filename = f"audit_report_{organization.name.replace(' ', '_')}_{period_end.strftime('%Y%m%d')}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        logger.info(f"PDF report downloaded by {user.email} for {organization.name}")
        
        return response
        
    except Exception as e:
        logger.error(f"PDF generation error: {e}")
        messages.error(request, f'خطأ في إنشاء التقرير: {str(e)}')
        return redirect('arabic_report')
