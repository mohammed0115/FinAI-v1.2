"""
Compliance Views - وجهات الامتثال
"""
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum
from decimal import Decimal
import logging

from core.models import Organization
from compliance.models import (
    AuditFinding, ZATCAInvoice, VATReconciliation, 
    ZakatCalculation, RegulatoryReference, ZATCAVerificationLog
)

logger = logging.getLogger(__name__)


@login_required
def compliance_overview_view(request):
    """صفحة نظرة عامة على الامتثال"""
    user = request.user
    organization = user.organization
    
    # ZATCA Invoices
    zatca_invoices = ZATCAInvoice.objects.filter(organization=organization).order_by('-issue_date')[:10]
    zatca_invoices_count = ZATCAInvoice.objects.filter(organization=organization).count()
    zatca_valid_count = ZATCAInvoice.objects.filter(
        organization=organization, 
        status__in=['validated', 'cleared']
    ).count()
    zatca_score = int((zatca_valid_count / max(zatca_invoices_count, 1)) * 100) if zatca_invoices_count > 0 else 100
    
    # VAT Reconciliations
    vat_reconciliations = VATReconciliation.objects.filter(organization=organization).order_by('-period_end')[:10]
    vat_reconciliations_count = VATReconciliation.objects.filter(organization=organization).count()
    vat_score_sum = VATReconciliation.objects.filter(organization=organization).aggregate(avg=Sum('compliance_score'))['avg']
    vat_score = int(vat_score_sum / max(vat_reconciliations_count, 1)) if vat_score_sum else 100
    
    # Zakat Calculation
    zakat_calcs = ZakatCalculation.objects.filter(organization=organization)
    latest_zakat = zakat_calcs.order_by('-fiscal_year_end').first()
    zakat_due = latest_zakat.zakat_due if latest_zakat else Decimal('0')
    zakat_score_sum = zakat_calcs.aggregate(avg=Sum('compliance_score'))['avg']
    zakat_score = int(zakat_score_sum / max(zakat_calcs.count(), 1)) if zakat_score_sum else 100
    
    # Audit Findings
    total_findings = AuditFinding.objects.filter(organization=organization).count()
    unresolved_findings = AuditFinding.objects.filter(
        organization=organization,
        is_resolved=False
    ).count()
    
    # Overall score
    overall_score = int((zatca_score + vat_score + zakat_score) / 3)
    
    # Regulatory references
    regulatory_references = RegulatoryReference.objects.all()[:10]
    
    context = {
        'organization': organization,
        'overall_score': overall_score,
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
        'regulatory_references': regulatory_references,
    }
    
    return render(request, 'compliance/overview.html', context)


@login_required
def zatca_verification_view(request):
    """
    صفحة التحقق من الفواتير عبر ZATCA API
    ZATCA Invoice Verification Page
    
    SCOPE: VERIFICATION ONLY - No submission, clearance, or signing
    """
    from compliance.zatca_api_service import zatca_api_service
    
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
