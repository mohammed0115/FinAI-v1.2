"""
Invoice Analysis Dashboard Views
Displays results from all 5 phases of the invoice processing pipeline
"""

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.db.models import Count, Avg, Sum, Q
from decimal import Decimal
import json
from datetime import datetime, timedelta

from documents.models import ExtractedData, Document


@login_required
@require_http_methods(["GET"])
def invoice_analysis_dashboard(request):
    """
    Display comprehensive invoice analysis dashboard with all 5 phase results
    """
    user = request.user
    org = user.organization
    
    if not org:
        return redirect('login')
    
    # All extracted data for this organization
    all_invoices = ExtractedData.objects.filter(
        organization=org
    ).select_related('document').order_by('-document__uploaded_at')
    
    # Calculate statistics for each phase
    
    # Phase 1: Extraction
    total_invoices = all_invoices.filter(extraction_status='extracted').count()
    extracted_with_confidence = all_invoices.filter(
        extraction_status='extracted',
        confidence__gt=0
    ).aggregate(avg=Avg('confidence'))
    avg_confidence = extracted_with_confidence['avg'] or 0
    
    extracted_with_amounts = all_invoices.filter(
        extraction_status='extracted',
        total_amount__isnull=False
    )
    total_spend = extracted_with_amounts.aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
    avg_amount = extracted_with_amounts.aggregate(avg=Avg('total_amount'))['avg'] or Decimal('0')
    
    extraction_error_count = all_invoices.filter(
        extraction_status='failed'
    ).count()
    
    # Phase 2: Validation
    valid_count = all_invoices.filter(is_valid=True).count()
    invalid_count = all_invoices.filter(is_valid=False).count()
    validation_rate = (valid_count / total_invoices * 100) if total_invoices > 0 else 0
    
    # Count warnings
    total_warnings = 0
    for invoice in all_invoices:
        if invoice.validation_warnings:
            try:
                warnings = invoice.validation_warnings
                if isinstance(warnings, str):
                    warnings = json.loads(warnings)
                if isinstance(warnings, list):
                    total_warnings += len(warnings)
            except:
                pass
    
    # Phase 3: Compliance
    compliance_scores = []
    critical_count = 0
    high_count = 0
    medium_count = 0
    low_count = 0
    
    for invoice in all_invoices:
        if invoice.risk_score:
            compliance_scores.append(invoice.risk_score)
            if invoice.risk_score >= 75:
                critical_count += 1
            elif invoice.risk_score >= 50:
                high_count += 1
            elif invoice.risk_score >= 25:
                medium_count += 1
            else:
                low_count += 1
    
    avg_risk_score = sum(compliance_scores) / len(compliance_scores) if compliance_scores else 0
    compliance_score = 100 - avg_risk_score  # Convert risk to compliance score
    high_risk_count = critical_count + high_count
    
    # Phase 4: Cross-Document Intelligence
    exact_duplicates = 0
    anomalies_detected = 0
    high_vendor_risk = 0
    
    for invoice in all_invoices:
        if invoice.duplicate_score and invoice.duplicate_score > 85:
            exact_duplicates += 1
        if invoice.anomaly_flags:
            try:
                flags = invoice.anomaly_flags
                if isinstance(flags, str):
                    flags = json.loads(flags)
                if isinstance(flags, list) and len(flags) > 0:
                    anomalies_detected += 1
            except:
                pass
        if invoice.vendor_risk_score and invoice.vendor_risk_score > 50:
            high_vendor_risk += 1
    
    # Phase 5: Financial Intelligence
    # Calculate 90-day forecast
    recent_invoices = all_invoices.filter(extraction_status='extracted')[:30]
    forecast_amount = Decimal('0')
    if recent_invoices.exists():
        avg_per_invoice = recent_invoices.aggregate(avg=Avg('total_amount'))['avg'] or Decimal('0')
        # Assume invoices come roughly every 7 days
        forecast_amount = avg_per_invoice * 13  # 13 weeks = 91 days
    
    # Get top vendor
    top_vendor_data = all_invoices.values('vendor_name').annotate(
        count=Count('id')
    ).order_by('-count').first()
    top_vendor = top_vendor_data['vendor_name'] if top_vendor_data else 'N/A'
    
    # Determine spending trend
    this_month = all_invoices.filter(
        document__uploaded_at__gte=datetime.now() - timedelta(days=30)
    ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
    
    last_month = all_invoices.filter(
        document__uploaded_at__gte=datetime.now() - timedelta(days=60),
        document__uploaded_at__lt=datetime.now() - timedelta(days=30)
    ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
    
    if last_month and this_month > last_month * Decimal('1.1'):
        spending_trend = 'up'
    elif last_month and this_month < last_month * Decimal('0.9'):
        spending_trend = 'down'
    else:
        spending_trend = 'stable'
    
    # Determine overall risk level
    if critical_count > 0:
        overall_risk_level = 'critical'
    elif high_count > 0:
        overall_risk_level = 'high'
    elif medium_count > 0:
        overall_risk_level = 'medium'
    else:
        overall_risk_level = 'low'
    
    # Recent invoices for table
    recent_invoices_list = all_invoices.filter(
        extraction_status='extracted'
    )[:10]
    
    context = {
        # Phase 1 stats
        'total_invoices': total_invoices,
        'avg_confidence': avg_confidence,
        'avg_amount': avg_amount,
        'extraction_count': total_invoices,
        'extraction_error_count': extraction_error_count,
        
        # Phase 2 stats
        'valid_count': valid_count,
        'invalid_count': invalid_count,
        'validation_rate': validation_rate,
        'total_warnings': total_warnings,
        
        # Phase 3 stats
        'compliance_score': compliance_score,
        'compliance_checks_count': 6,  # Number of compliance checks
        'critical_count': critical_count,
        'high_count': high_count,
        'medium_count': medium_count,
        'low_count': low_count,
        'high_risk_count': high_risk_count,
        'avg_risk_score': avg_risk_score,
        
        # Phase 4 stats
        'exact_duplicates': exact_duplicates,
        'anomalies_detected': anomalies_detected,
        'high_vendor_risk': high_vendor_risk,
        
        # Phase 5 stats
        'forecast_amount': forecast_amount,
        'top_vendor': top_vendor,
        'spending_trend': spending_trend,
        'total_spend': total_spend,
        
        # Overall
        'overall_risk_level': overall_risk_level,
        'currency': 'SAR',
        'recent_invoices': recent_invoices_list,
        'now': datetime.now(),
    }
    
    return render(request, 'invoice_analysis_dashboard.html', context)


@login_required
@require_http_methods(["GET"])
def invoice_detail(request, invoice_id):
    """
    Display detailed analysis for a single invoice
    """
    user = request.user
    org = user.organization
    
    if not org:
        return redirect('login')
    
    try:
        invoice = ExtractedData.objects.get(id=invoice_id, organization=org)
    except ExtractedData.DoesNotExist:
        return redirect('invoice_analysis_dashboard')
    
    # Parse JSON fields
    extracted_data = invoice.normalized_json
    if isinstance(extracted_data, str):
        try:
            extracted_data = json.loads(extracted_data)
        except:
            extracted_data = {}
    
    validation_errors = invoice.validation_errors or []
    validation_warnings = invoice.validation_warnings or []
    
    compliance_checks = invoice.compliance_checks
    if isinstance(compliance_checks, str):
        try:
            compliance_checks = json.loads(compliance_checks)
        except:
            compliance_checks = {}
    
    anomaly_flags = invoice.anomaly_flags or []
    if isinstance(anomaly_flags, str):
        try:
            anomaly_flags = json.loads(anomaly_flags)
        except:
            anomaly_flags = []
    
    audit_summary = invoice.audit_summary
    if audit_summary and isinstance(audit_summary, str):
        try:
            audit_summary = json.loads(audit_summary)
        except:
            audit_summary = None
    
    context = {
        'invoice': invoice,
        'extracted_data': extracted_data,
        'validation_errors': validation_errors,
        'validation_warnings': validation_warnings,
        'compliance_checks': compliance_checks,
        'anomaly_flags': anomaly_flags,
        'audit_summary': audit_summary,
        'currency': invoice.currency or 'SAR',
    }
    
    return render(request, 'invoice_detail.html', context)


@login_required
@require_http_methods(["GET"])
def audit_report_detail(request, report_id):
    """
    Display comprehensive audit report with all 11 sections:
    1. Document Information
    2. Invoice Data Extraction
    3. Line Items Details
    4. Financial Totals
    5. Validation Results
    6. Compliance Checks
    7. Duplicate Detection
    8. Anomaly Detection
    9. Risk Assessment
    10. AI Summary & Recommendations
    11. Audit Trail
    """
    from documents.models import InvoiceAuditReport
    
    user = request.user
    org = user.organization
    
    if not org:
        return redirect('login')
    
    try:
        report = InvoiceAuditReport.objects.get(id=report_id, organization=org)
    except InvoiceAuditReport.DoesNotExist:
        return redirect('invoice_analysis_dashboard')
    
    # Parse JSON fields for display
    validation_results = report.validation_results_json or {}
    if isinstance(validation_results, str):
        try:
            validation_results = json.loads(validation_results)
        except:
            validation_results = {}
    
    compliance_checks = report.compliance_checks_json or {}
    if isinstance(compliance_checks, str):
        try:
            compliance_checks = json.loads(compliance_checks)
        except:
            compliance_checks = {}
    
    duplicate_matched_docs = report.duplicate_matched_documents_json or []
    if isinstance(duplicate_matched_docs, str):
        try:
            duplicate_matched_docs = json.loads(duplicate_matched_docs)
        except:
            duplicate_matched_docs = []
    
    anomaly_reasons = report.anomaly_reasons_json or []
    if isinstance(anomaly_reasons, str):
        try:
            anomaly_reasons = json.loads(anomaly_reasons)
        except:
            anomaly_reasons = []
    
    risk_factors = report.risk_factors_json or []
    if isinstance(risk_factors, str):
        try:
            risk_factors = json.loads(risk_factors)
        except:
            risk_factors = []
    
    line_items = report.line_items_json or []
    if isinstance(line_items, str):
        try:
            line_items = json.loads(line_items)
        except:
            line_items = []
    
    audit_trail = report.audit_trail_json or []
    if isinstance(audit_trail, str):
        try:
            audit_trail = json.loads(audit_trail)
        except:
            audit_trail = []
    
    context = {
        'report': report,
        'validation_results': validation_results,
        'compliance_checks': compliance_checks,
        'duplicate_matched_documents': duplicate_matched_docs,
        'anomaly_reasons': anomaly_reasons,
        'risk_factors': risk_factors,
        'line_items': line_items,
        'audit_trail': audit_trail,
    }
    
    return render(request, 'documents/comprehensive_audit_report.html', context)
