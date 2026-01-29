from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from django.utils import timezone
from django.core.paginator import Paginator
from django.db.models import Sum, Count, Q
from django.conf import settings
from django.views.decorators.http import require_POST
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
    
    # Get AI explanation logs for this finding
    ai_logs = finding.ai_explanation_logs.all().order_by('-generated_at')[:5]
    
    context = {
        'finding': finding,
        'ai_explanation_logs': ai_logs,
    }
    
    return render(request, 'findings/detail.html', context)


@login_required
def generate_ai_explanation_view(request, finding_id):
    """
    توليد شرح ذكي لنتيجة التدقيق
    Generate AI Explanation for Audit Finding
    
    COMPLIANCE:
    - Output is ADVISORY ONLY
    - Human review is REQUIRED
    - Full audit trail maintained
    """
    import asyncio
    from compliance.ai_explanation_service import ai_explanation_service
    from compliance.models import AuditFinding, AIExplanationLog
    
    user = request.user
    organization = user.organization
    
    finding = get_object_or_404(AuditFinding, id=finding_id, organization=organization)
    
    if request.method == 'POST':
        try:
            # Get regulatory reference if available
            reg_ref = None
            if finding.regulatory_reference:
                reg_ref = f"{finding.regulatory_reference.article_number}: {finding.regulatory_reference.title_ar}"
            
            # Generate explanation asynchronously
            result = ai_explanation_service.generate_explanation_sync(
                finding_id=str(finding.id),
                title_ar=finding.title_ar,
                description_ar=finding.description_ar,
                risk_level=finding.risk_level,
                finding_type=finding.finding_type,
                financial_impact=finding.financial_impact,
                regulatory_reference=reg_ref,
            )
            
            if result.get('success'):
                # Store in audit log
                ai_log = AIExplanationLog.objects.create(
                    finding=finding,
                    organization=organization,
                    explanation_ar=result['explanation_ar'],
                    confidence_score=result['confidence_score'],
                    confidence_level=result['confidence_level'],
                    model_used=result['model_used'],
                    provider=result['provider'],
                    session_id=result['session_id'],
                    processing_time_ms=result['processing_time_ms'],
                    audit_hash=result['audit_hash'],
                    is_advisory=True,
                    requires_human_review=True,
                    generated_by=user,
                )
                
                # Update finding with new explanation (but keep human review required)
                finding.ai_explanation_ar = result['explanation_ar']
                finding.ai_confidence = result['confidence_score']
                finding.save()
                
                messages.success(
                    request, 
                    f'تم توليد الشرح الذكي بنجاح (درجة الثقة: {result["confidence_score"]}%). يرجى مراجعة الشرح قبل الاعتماد.'
                )
                
                logger.info(
                    f"AI explanation generated for finding {finding.finding_number} by {user.email}"
                )
            else:
                messages.error(
                    request, 
                    f'فشل في توليد الشرح الذكي: {result.get("error", "خطأ غير معروف")}'
                )
                
        except Exception as e:
            logger.error(f"AI explanation generation error: {e}")
            messages.error(request, f'خطأ في توليد الشرح الذكي: {str(e)}')
    
    return redirect('audit_finding_detail', finding_id=finding_id)


@login_required
@require_POST
def review_ai_explanation_view(request, log_id):
    """
    مراجعة واعتماد/رفض/تعديل الشرح الذكي
    Review and Approve/Reject/Modify AI Explanation
    
    COMPLIANCE:
    - All actions are logged
    - No automatic approval
    - No auto-override of audit findings
    - Preserves AIExplanationLog integrity
    """
    from compliance.models import AIExplanationLog
    
    user = request.user
    organization = user.organization
    
    # Get the AI explanation log
    ai_log = get_object_or_404(AIExplanationLog, id=log_id, organization=organization)
    
    # Only pending logs can be reviewed
    if ai_log.approval_status != 'pending':
        messages.error(request, 'هذا الشرح تمت مراجعته مسبقاً')
        return redirect('audit_finding_detail', finding_id=ai_log.finding.id)
    
    action = request.POST.get('action', '')
    
    if action == 'approve':
        ai_log.approval_status = 'approved'
        ai_log.human_reviewed = True
        ai_log.reviewed_by = user
        ai_log.reviewed_at = timezone.now()
        ai_log.save()
        
        messages.success(request, 'تم اعتماد الشرح الذكي بنجاح')
        logger.info(f"AI explanation approved: {ai_log.id} by {user.email}")
        
    elif action == 'reject':
        ai_log.approval_status = 'rejected'
        ai_log.human_reviewed = True
        ai_log.reviewed_by = user
        ai_log.reviewed_at = timezone.now()
        ai_log.review_notes = request.POST.get('review_notes', 'رفض بدون ملاحظات')
        ai_log.save()
        
        messages.warning(request, 'تم رفض الشرح الذكي')
        logger.info(f"AI explanation rejected: {ai_log.id} by {user.email}")
        
    elif action == 'modify':
        modified_text = request.POST.get('modified_text', '').strip()
        review_notes = request.POST.get('review_notes', '').strip()
        
        if not modified_text:
            messages.error(request, 'يرجى إدخال النص المعدّل')
            return redirect('audit_finding_detail', finding_id=ai_log.finding.id)
        
        ai_log.approval_status = 'modified'
        ai_log.human_reviewed = True
        ai_log.reviewed_by = user
        ai_log.reviewed_at = timezone.now()
        ai_log.review_notes = review_notes or 'تم التعديل بواسطة المدقق'
        ai_log.explanation_ar = modified_text
        ai_log.save()
        
        # Update the finding with modified explanation
        ai_log.finding.ai_explanation_ar = modified_text
        ai_log.finding.save()
        
        messages.success(request, 'تم تعديل واعتماد الشرح الذكي')
        logger.info(f"AI explanation modified: {ai_log.id} by {user.email}")
    
    else:
        messages.error(request, 'إجراء غير صالح')
    
    return redirect('audit_finding_detail', finding_id=ai_log.finding.id)


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



@login_required
def document_upload_view(request):
    """
    رفع المستندات للتعرف الضوئي
    Document Upload for OCR Processing
    
    READ-ONLY FLOW: Upload → OCR → Store as Evidence
    """
    from documents.models import Document, OCREvidence
    from documents.ocr_service import document_ocr_service
    import os
    import tempfile
    
    user = request.user
    organization = user.organization
    
    if not organization:
        messages.error(request, 'لا توجد منشأة مرتبطة بالحساب')
        return redirect('dashboard')
    
    if request.method == 'POST':
        uploaded_file = request.FILES.get('document')
        
        if not uploaded_file:
            messages.error(request, 'الرجاء اختيار ملف للرفع')
            return redirect('document_upload')
        
        # Validate file type
        file_ext = os.path.splitext(uploaded_file.name)[1].lower()
        allowed_types = ['.pdf', '.jpg', '.jpeg', '.png', '.tiff', '.bmp']
        
        if file_ext not in allowed_types:
            messages.error(request, f'نوع الملف غير مدعوم. الأنواع المدعومة: {", ".join(allowed_types)}')
            return redirect('document_upload')
        
        # Get form data
        document_type = request.POST.get('document_type', 'other')
        language = request.POST.get('language', 'mixed')
        is_handwritten = request.POST.get('is_handwritten') == 'on'
        
        try:
            # Save uploaded file temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp_file:
                for chunk in uploaded_file.chunks():
                    tmp_file.write(chunk)
                tmp_path = tmp_file.name
            
            # Create document record
            upload_dir = os.path.join(settings.MEDIA_ROOT, 'uploads', str(organization.id))
            os.makedirs(upload_dir, exist_ok=True)
            
            storage_key = f"{timezone.now().strftime('%Y%m%d_%H%M%S')}_{uploaded_file.name}"
            storage_path = os.path.join(upload_dir, storage_key)
            
            # Copy to permanent storage
            import shutil
            shutil.copy(tmp_path, storage_path)
            
            document = Document.objects.create(
                organization=organization,
                uploaded_by=user,
                file_name=uploaded_file.name,
                file_type=file_ext,
                file_size=uploaded_file.size,
                storage_key=storage_key,
                storage_url=storage_path,
                document_type=document_type,
                status='processing',
                language=language,
                is_handwritten=is_handwritten,
            )
            
            # Process OCR
            ocr_result = document_ocr_service.process_document(
                file_path=tmp_path,
                file_type=file_ext,
                language=language,
                is_handwritten=is_handwritten,
            )
            
            # Extract structured data
            structured = document_ocr_service.extract_structured_data(
                ocr_result.get('text', ''),
                document_type
            )
            
            # Get JSON-serializable version for storage
            structured_json = document_ocr_service.get_json_serializable_data(structured)
            
            # Determine confidence level
            confidence = ocr_result.get('confidence', 0)
            if confidence >= 80:
                confidence_level = 'high'
            elif confidence >= 60:
                confidence_level = 'medium'
            elif confidence >= 40:
                confidence_level = 'low'
            else:
                confidence_level = 'very_low'
            
            # Create OCR evidence record
            ocr_evidence = OCREvidence.objects.create(
                document=document,
                organization=organization,
                raw_text=ocr_result.get('text', ''),
                text_ar=ocr_result.get('text_ar', ''),
                text_en=ocr_result.get('text_en', ''),
                confidence_score=confidence,
                confidence_level=confidence_level,
                page_count=ocr_result.get('page_count', 1),
                word_count=len(ocr_result.get('text', '').split()),
                ocr_engine=ocr_result.get('ocr_engine', 'tesseract'),
                ocr_version=ocr_result.get('ocr_version', ''),
                language_used=language,
                is_handwritten=is_handwritten,
                processing_time_ms=ocr_result.get('processing_time_ms', 0),
                extracted_invoice_number=structured.get('invoice_number'),
                extracted_vat_number=structured.get('vat_number'),
                extracted_total=structured.get('total_amount'),
                extracted_tax=structured.get('tax_amount'),
                structured_data_json=structured_json,
                evidence_hash=ocr_result.get('evidence_hash', ''),
                extracted_by=user,
            )
            
            # Update document status
            document.status = 'completed'
            document.processed_at = timezone.now()
            document.save()
            
            # Clean up temp file
            os.unlink(tmp_path)
            
            messages.success(request, f'تم معالجة المستند بنجاح. درجة الثقة: {confidence}%')
            return redirect('ocr_evidence_detail', evidence_id=ocr_evidence.id)
            
        except Exception as e:
            logger.error(f"Document upload error: {e}")
            messages.error(request, f'خطأ في معالجة المستند: {str(e)}')
            return redirect('document_upload')
    
    # GET: Show upload form
    recent_docs = Document.objects.filter(organization=organization).order_by('-uploaded_at')[:10]
    
    context = {
        'recent_documents': recent_docs,
        'document_types': Document.DOCUMENT_TYPE_CHOICES,
        'language_choices': Document.LANGUAGE_CHOICES,
    }
    
    return render(request, 'documents/upload.html', context)


@login_required
def ocr_evidence_list_view(request):
    """
    قائمة أدلة التعرف الضوئي
    List OCR Evidence Records
    """
    from documents.models import OCREvidence
    
    user = request.user
    organization = user.organization
    
    if not organization:
        return render(request, 'no_organization.html')
    
    evidence_records = OCREvidence.objects.filter(organization=organization)
    
    # Apply filters
    confidence = request.GET.get('confidence')
    if confidence:
        evidence_records = evidence_records.filter(confidence_level=confidence)
    
    evidence_records = evidence_records.order_by('-extracted_at')
    
    # Pagination
    paginator = Paginator(evidence_records, 20)
    page_number = request.GET.get('page')
    evidence_page = paginator.get_page(page_number)
    
    context = {
        'evidence_records': evidence_page,
        'total_count': OCREvidence.objects.filter(organization=organization).count(),
    }
    
    return render(request, 'documents/ocr_list.html', context)


@require_POST
def toggle_language_view(request):
    """
    Toggle between Arabic and English UI language.
    
    NOTE: This is UI-level only. Audit logic remains unchanged.
    Arabic is the primary language.
    """
    current_lang = request.session.get('language', 'ar')
    new_lang = 'en' if current_lang == 'ar' else 'ar'
    request.session['language'] = new_lang
    
    # Get the referring page or default to dashboard
    referer = request.META.get('HTTP_REFERER', '/')
    return redirect(referer)


@login_required
def zatca_verification_view(request):
    """
    صفحة التحقق من الفواتير عبر ZATCA API
    ZATCA Invoice Verification Page
    
    SCOPE: VERIFICATION ONLY - No submission, clearance, or signing
    """
    from compliance.zatca_api_service import zatca_api_service
    from compliance.models import ZATCAVerificationLog
    
    user = request.user
    organization = user.organization
    
    verification_result = None
    
    if request.method == 'POST':
        verification_type = request.POST.get('verification_type', 'vat')
        
        if verification_type == 'vat':
            vat_number = request.POST.get('vat_number', '').strip()
            if vat_number:
                verification_result = zatca_api_service.verify_vat_number(vat_number)
                
                # Store as audit evidence
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
                verification_result = zatca_api_service.verify_invoice_structure(
                    invoice_xml, invoice_hash, invoice_uuid
                )
                
                # Store as audit evidence
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
    
    # Get recent verifications
    recent_verifications = ZATCAVerificationLog.objects.filter(
        organization=organization
    ).order_by('-created_at')[:10]
    
    context = {
        'verification_result': verification_result,
        'recent_verifications': recent_verifications,
        'scope_docs': zatca_api_service.get_scope_documentation(),
    }
    
    return render(request, 'compliance/zatca_verification.html', context)

    
    # Get the referring page or default to dashboard
    referer = request.META.get('HTTP_REFERER', '/')
    return redirect(referer)



@login_required
def ocr_evidence_detail_view(request, evidence_id):
    """
    تفاصيل دليل التعرف الضوئي
    OCR Evidence Detail View
    """
    from documents.models import OCREvidence
    
    user = request.user
    organization = user.organization
    
    evidence = get_object_or_404(OCREvidence, id=evidence_id, organization=organization)
    
    context = {
        'evidence': evidence,
        'scope_docs': OCREvidence.get_scope_documentation(),
    }
    
    return render(request, 'documents/ocr_detail.html', context)


@login_required
def organization_settings_view(request):
    """
    إعدادات الشركة / المنظمة
    Company / Organization Settings
    
    VAT HANDLING LOGIC:
    - Saudi Arabia (SA): VAT number REQUIRED, validated against ZATCA format
    - Other GCC countries: VAT number OPTIONAL
    - Validation only - no ERP behavior
    """
    from core.vat_validation_service import vat_validation_service
    
    user = request.user
    organization = user.organization
    
    if not organization:
        messages.error(request, 'لا توجد شركة مرتبطة بحسابك')
        return redirect('dashboard')
    
    vat_requirements = vat_validation_service.get_country_vat_requirements(organization.country)
    validation_result = None
    
    if request.method == 'POST':
        # Get form data
        name = request.POST.get('name', '').strip()
        name_ar = request.POST.get('name_ar', '').strip()
        country = request.POST.get('country', organization.country)
        vat_number = request.POST.get('vat_number', '').strip()
        company_type = request.POST.get('company_type', '')
        industry = request.POST.get('industry', '').strip()
        
        # Get language for error messages
        lang = request.session.get('language', 'ar')
        
        # Validate VAT number
        validation_result = vat_validation_service.validate_vat_number(
            vat_number=vat_number,
            country=country,
            lang=lang
        )
        
        if validation_result['valid']:
            # Update organization
            organization.name = name or organization.name
            organization.name_ar = name_ar
            organization.country = country
            organization.vat_number = vat_number if vat_number else None
            organization.vat_applicable = validation_result['vat_applicable']
            organization.zatca_enabled = validation_result['zatca_enabled']
            organization.company_type = company_type or None
            organization.industry = industry or None
            
            # Update VAT validation status
            if vat_number:
                organization.vat_validation_status = 'valid'
                organization.vat_validation_message = validation_result['validation_details'].get('message_ar', '')
            elif country == 'SA':
                organization.vat_validation_status = 'invalid'
                organization.vat_validation_message = 'رقم ضريبة القيمة المضافة مطلوب'
            else:
                organization.vat_validation_status = 'not_required'
                organization.vat_validation_message = 'رقم ضريبة القيمة المضافة غير مطلوب لهذا البلد'
            
            organization.vat_validated_at = timezone.now()
            
            # Update ZATCA scope based on VAT validation
            if organization.zatca_enabled:
                organization.zatca_verification_scope = 'verification_only'
            else:
                organization.zatca_verification_scope = 'disabled'
            
            organization.save()
            
            messages.success(request, 'تم حفظ إعدادات الشركة بنجاح')
            logger.info(f"Organization settings updated: {organization.name} by {user.email}")
            
            return redirect('organization_settings')
        else:
            # Validation failed - show error
            messages.error(request, validation_result['error_message'])
    
    # Get all country requirements for UI
    all_country_requirements = {
        code: vat_validation_service.get_country_vat_requirements(code)
        for code, _ in Organization.COUNTRY_CHOICES
    }
    
    context = {
        'organization': organization,
        'vat_requirements': vat_requirements,
        'all_country_requirements': all_country_requirements,
        'validation_result': validation_result,
        'country_choices': Organization.COUNTRY_CHOICES,
        'company_type_choices': Organization.COMPANY_TYPE_CHOICES,
    }
    
    return render(request, 'settings/organization.html', context)

