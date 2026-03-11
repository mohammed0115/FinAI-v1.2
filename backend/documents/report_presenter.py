import json
import re
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List


LABELS = {
    'title': {'ar': 'تقرير التدقيق الشامل', 'en': 'Comprehensive Audit Report'},
    'subtitle': {'ar': 'تقرير تدقيق مالي شامل للفاتورة المرفوعة', 'en': 'Comprehensive financial audit report for the uploaded invoice'},
    'download_pdf': {'ar': 'تنزيل PDF', 'en': 'Download PDF'},
    'back': {'ar': 'رجوع', 'en': 'Back'},
    'report_number': {'ar': 'رقم التقرير', 'en': 'Report #'},
    'generated': {'ar': 'تاريخ الإنشاء', 'en': 'Generated'},
    'risk_level': {'ar': 'مستوى المخاطر', 'en': 'Risk Level'},
    'risk_score': {'ar': 'درجة المخاطر', 'en': 'Risk Score'},
    'document_information': {'ar': 'معلومات المستند', 'en': 'Document Information'},
    'invoice_information': {'ar': 'بيانات الفاتورة', 'en': 'Invoice Information'},
    'vendor_information': {'ar': 'بيانات المورد', 'en': 'Vendor Information'},
    'customer_information': {'ar': 'بيانات العميل', 'en': 'Customer Information'},
    'financial_totals': {'ar': 'الإجماليات المالية', 'en': 'Financial Totals'},
    'line_items': {'ar': 'بنود الفاتورة', 'en': 'Line Items'},
    'validation_checklist': {'ar': 'جدول التحقق', 'en': 'Validation Checklist'},
    'analysis_summary': {'ar': 'ملخص التحليل', 'en': 'Analysis Summary'},
    'duplicate_detection': {'ar': 'فحص التكرار', 'en': 'Duplicate Detection'},
    'anomaly_detection': {'ar': 'فحص الشذوذ', 'en': 'Anomaly Detection'},
    'risk_factors': {'ar': 'عوامل المخاطر', 'en': 'Risk Factors'},
    'ai_analysis': {'ar': 'تحليل الذكاء الاصطناعي', 'en': 'AI Analysis'},
    'recommendation': {'ar': 'التوصية', 'en': 'Recommendation'},
    'recommendation_reason': {'ar': 'سبب التوصية', 'en': 'Recommendation Reason'},
    'audit_trail': {'ar': 'سجل التدقيق', 'en': 'Audit Trail'},
    'document_id': {'ar': 'معرّف المستند', 'en': 'Document ID'},
    'file_name': {'ar': 'اسم الملف', 'en': 'File Name'},
    'upload_date': {'ar': 'تاريخ الرفع', 'en': 'Upload Date'},
    'ocr_engine': {'ar': 'محرك OCR', 'en': 'OCR Engine'},
    'ocr_confidence': {'ar': 'دقة OCR', 'en': 'OCR Confidence'},
    'processing_status': {'ar': 'حالة المعالجة', 'en': 'Processing Status'},
    'invoice_number': {'ar': 'رقم الفاتورة', 'en': 'Invoice Number'},
    'issue_date': {'ar': 'تاريخ الإصدار', 'en': 'Issue Date'},
    'due_date': {'ar': 'تاريخ الاستحقاق', 'en': 'Due Date'},
    'currency': {'ar': 'العملة', 'en': 'Currency'},
    'name': {'ar': 'الاسم', 'en': 'Name'},
    'address': {'ar': 'العنوان', 'en': 'Address'},
    'tin': {'ar': 'الرقم الضريبي', 'en': 'Tax ID'},
    'subtotal': {'ar': 'الإجمالي قبل الضريبة', 'en': 'Subtotal'},
    'vat': {'ar': 'ضريبة القيمة المضافة', 'en': 'VAT'},
    'total_amount': {'ar': 'إجمالي الفاتورة', 'en': 'Total Amount'},
    'description': {'ar': 'الوصف', 'en': 'Description'},
    'quantity': {'ar': 'الكمية', 'en': 'Quantity'},
    'unit_price': {'ar': 'سعر الوحدة', 'en': 'Unit Price'},
    'discount': {'ar': 'الخصم', 'en': 'Discount'},
    'total': {'ar': 'الإجمالي', 'en': 'Total'},
    'check': {'ar': 'التحقق', 'en': 'Check'},
    'checklist': {'ar': 'تم', 'en': 'Checklist'},
    'status': {'ar': 'الحالة', 'en': 'Status'},
    'notes': {'ar': 'الملاحظات', 'en': 'Notes'},
    'timestamp': {'ar': 'الوقت', 'en': 'Timestamp'},
    'event': {'ar': 'الحدث', 'en': 'Event'},
    'details': {'ar': 'التفاصيل', 'en': 'Details'},
    'no_data': {'ar': 'غير متاح', 'en': 'N/A'},
    'no_items': {'ar': 'لا توجد بنود مسجلة', 'en': 'No line items found'},
    'no_notes': {'ar': 'لا توجد ملاحظات', 'en': 'No issues noted'},
    'no_findings': {'ar': 'لم يتم رصد مشكلات جوهرية.', 'en': 'No significant issues were detected.'},
    'no_risk_factors': {'ar': 'لا توجد عوامل مخاطر إضافية.', 'en': 'No additional risk factors.'},
    'no_audit_events': {'ar': 'لا توجد أحداث في سجل التدقيق.', 'en': 'No audit trail events available.'},
    'duplicate_score': {'ar': 'درجة التكرار', 'en': 'Duplicate Score'},
    'anomaly_score': {'ar': 'درجة الشذوذ', 'en': 'Anomaly Score'},
}


RISK_LEVELS = {
    'low': {'ar': 'منخفض', 'en': 'Low'},
    'medium': {'ar': 'متوسط', 'en': 'Medium'},
    'high': {'ar': 'مرتفع', 'en': 'High'},
    'critical': {'ar': 'حرج', 'en': 'Critical'},
}


RECOMMENDATIONS = {
    'approve': {'ar': 'اعتماد', 'en': 'Approve'},
    'manual_review': {'ar': 'مراجعة يدوية', 'en': 'Manual Review'},
    'reject': {'ar': 'رفض', 'en': 'Reject'},
}


DOCUMENT_STATUSES = {
    'pending': {'ar': 'قيد الانتظار', 'en': 'Pending'},
    'processing': {'ar': 'قيد المعالجة', 'en': 'Processing'},
    'completed': {'ar': 'مكتمل', 'en': 'Completed'},
    'failed': {'ar': 'فشل', 'en': 'Failed'},
    'success': {'ar': 'ناجح', 'en': 'Success'},
    'warning': {'ar': 'تحذير', 'en': 'Warning'},
    'info': {'ar': 'معلومة', 'en': 'Info'},
    'validated': {'ar': 'تم التحقق', 'en': 'Validated'},
    'pending_review': {'ar': 'بانتظار المراجعة', 'en': 'Pending Review'},
    'generated': {'ar': 'تم الإنشاء', 'en': 'Generated'},
    'reviewed': {'ar': 'تمت المراجعة', 'en': 'Reviewed'},
    'approved': {'ar': 'معتمد', 'en': 'Approved'},
    'rejected': {'ar': 'مرفوض', 'en': 'Rejected'},
}


DUPLICATE_STATUSES = {
    'no_duplicate': {'ar': 'لا يوجد تكرار', 'en': 'No duplicate detected'},
    'low_risk': {'ar': 'احتمال تكرار منخفض', 'en': 'Low duplicate risk'},
    'medium_risk': {'ar': 'احتمال تكرار متوسط', 'en': 'Medium duplicate risk'},
    'high_risk': {'ar': 'احتمال تكرار مرتفع', 'en': 'High duplicate risk'},
    'confirmed_duplicate': {'ar': 'تكرار مؤكد', 'en': 'Confirmed duplicate'},
}


ANOMALY_STATUSES = {
    'no_anomaly': {'ar': 'لا يوجد شذوذ', 'en': 'No anomaly'},
    'low_anomaly': {'ar': 'شذوذ منخفض', 'en': 'Low anomaly'},
    'medium_anomaly': {'ar': 'شذوذ متوسط', 'en': 'Medium anomaly'},
    'high_anomaly': {'ar': 'شذوذ مرتفع', 'en': 'High anomaly'},
    'critical_anomaly': {'ar': 'شذوذ حرج', 'en': 'Critical anomaly'},
}


CHECK_LABELS = {
    'invoice_number': {'ar': 'رقم الفاتورة', 'en': 'Invoice Number'},
    'vendor': {'ar': 'بيانات المورد', 'en': 'Vendor Details'},
    'customer': {'ar': 'بيانات العميل', 'en': 'Customer Details'},
    'items': {'ar': 'بنود الفاتورة', 'en': 'Line Items'},
    'total_match': {'ar': 'مطابقة الإجماليات', 'en': 'Totals Match'},
    'vat': {'ar': 'ضريبة القيمة المضافة', 'en': 'VAT Validation'},
    'duplicate_screening': {'ar': 'فحص التكرار', 'en': 'Duplicate Screening'},
    'anomaly_screening': {'ar': 'فحص الشذوذ', 'en': 'Anomaly Screening'},
}


CHECK_ORDER = [
    'invoice_number',
    'vendor',
    'customer',
    'items',
    'total_match',
    'vat',
]


STATUS_META = {
    'pass': {
        'badge': 'success',
        'label': {'ar': 'مكتمل', 'en': 'Passed'},
        'completion': {'ar': 'نعم', 'en': 'Yes'},
    },
    'warning': {
        'badge': 'warning',
        'label': {'ar': 'بحاجة مراجعة', 'en': 'Warning'},
        'completion': {'ar': 'جزئي', 'en': 'Partial'},
    },
    'fail': {
        'badge': 'danger',
        'label': {'ar': 'غير مجتاز', 'en': 'Failed'},
        'completion': {'ar': 'لا', 'en': 'No'},
    },
}


EXACT_ISSUE_TRANSLATIONS = {
    'Invoice number is missing': 'رقم الفاتورة مفقود',
    'Invoice number is unusually short': 'رقم الفاتورة قصير بشكل غير معتاد',
    'Vendor name is missing': 'اسم المورد مفقود',
    'Vendor TIN appears to be invalid format': 'تنسيق الرقم الضريبي للمورد غير صحيح',
    'Vendor TIN is missing': 'الرقم الضريبي للمورد مفقود',
    'Customer name is missing': 'اسم العميل مفقود',
    'Customer TIN appears to be invalid format': 'تنسيق الرقم الضريبي للعميل غير صحيح',
    'Customer TIN is missing': 'الرقم الضريبي للعميل مفقود',
    'No line items found on invoice': 'لا توجد بنود مستخرجة من الفاتورة',
    'Cannot verify totals without line items': 'تعذر التحقق من الإجماليات لعدم وجود بنود',
    'VAT amount is missing or zero': 'مبلغ ضريبة القيمة المضافة مفقود أو يساوي صفراً',
    'Due date is before invoice date': 'تاريخ الاستحقاق أسبق من تاريخ الفاتورة',
    'Due date is in the past': 'تاريخ الاستحقاق في الماضي',
    'No line items extracted from invoice': 'لم يتم استخراج بنود من الفاتورة',
    'Likely duplicate invoice': 'يُحتمل أن الفاتورة مكررة',
    'Review for potential duplicates': 'مطلوب مراجعة لاحتمال وجود تكرار',
    'All validations passed': 'جميع عناصر التحقق الأساسية مجتازة',
    'Low risk detected (0/100)': 'تم رصد مخاطر منخفضة (0/100)',
    'No anomalies detected': 'لم يتم رصد أي شذوذ',
    'Missing vendor information': 'بيانات المورد مفقودة',
    'Missing invoice number': 'رقم الفاتورة مفقود',
    'Missing customer information': 'بيانات العميل مفقودة',
}


def get_labels(lang: str = 'ar') -> Dict[str, str]:
    return {key: value.get(lang, value['en']) for key, value in LABELS.items()}


def _coerce_dict(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}
    return {}


def _coerce_list(value: Any) -> List[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, list) else []
        except Exception:
            return []
    return []


def _localize_choice(mapping: Dict[str, Dict[str, str]], key: str, lang: str, fallback: str = '') -> str:
    item = mapping.get((key or '').lower())
    if item:
        return item.get(lang, item.get('en', fallback))
    return fallback or (key or '')


def localize_risk_level(level: str, lang: str = 'ar') -> str:
    return _localize_choice(RISK_LEVELS, level, lang, level or '')


def localize_recommendation(recommendation: str, lang: str = 'ar') -> str:
    return _localize_choice(RECOMMENDATIONS, recommendation, lang, recommendation or '')


def localize_processing_status(status: str, lang: str = 'ar') -> str:
    return _localize_choice(DOCUMENT_STATUSES, status, lang, status or '')


def localize_duplicate_status(status: str, lang: str = 'ar') -> str:
    return _localize_choice(DUPLICATE_STATUSES, status, lang, status or '')


def localize_anomaly_status(status: str, lang: str = 'ar') -> str:
    return _localize_choice(ANOMALY_STATUSES, status, lang, status or '')


def localize_check_label(check_key: str, lang: str = 'ar') -> str:
    return _localize_choice(CHECK_LABELS, check_key, lang, check_key or '')


def format_amount(value: Any) -> str:
    if value in (None, ''):
        return '-'
    try:
        numeric_value = Decimal(str(value))
        return f'{numeric_value:,.2f}'
    except (InvalidOperation, ValueError, TypeError):
        return str(value)


def normalize_line_items(raw_items: Any) -> List[Dict[str, Any]]:
    normalized_items = []
    for item in _coerce_list(raw_items):
        if not isinstance(item, dict):
            continue
        normalized_items.append(
            {
                'description': item.get('description') or item.get('name') or item.get('product') or '-',
                'quantity': item.get('quantity', item.get('qty', '0')),
                'unit_price': item.get('unit_price', item.get('price', '0')),
                'discount': item.get('discount', '0'),
                'total': item.get('total', item.get('line_total', item.get('amount', '0'))),
            }
        )
    return normalized_items


def localize_issue(issue: Any, lang: str = 'ar') -> str:
    issue_text = str(issue or '').strip()
    if not issue_text or lang != 'ar':
        return issue_text

    if issue_text in EXACT_ISSUE_TRANSLATIONS:
        return EXACT_ISSUE_TRANSLATIONS[issue_text]

    line_total_match = re.match(
        r'^Line (\d+): Calculated total \(([^)]+)\) does not match stated total \(([^)]+)\)$',
        issue_text,
    )
    if line_total_match:
        line_no, calculated_total, stated_total = line_total_match.groups()
        return (
            f'البند {line_no}: الإجمالي المحتسب ({calculated_total}) '
            f'لا يطابق الإجمالي المذكور ({stated_total})'
        )

    invalid_numeric_match = re.match(r'^Line (\d+): Invalid numeric value - (.+)$', issue_text)
    if invalid_numeric_match:
        line_no, reason = invalid_numeric_match.groups()
        return f'البند {line_no}: قيمة رقمية غير صالحة - {reason}'

    subtotal_mismatch = re.match(r'^Subtotal mismatch: Calculated (.+), but invoice shows (.+)$', issue_text)
    if subtotal_mismatch:
        calculated_total, invoice_total = subtotal_mismatch.groups()
        return f'يوجد اختلاف في الإجمالي قبل الضريبة: المحتسب {calculated_total} بينما الفاتورة تعرض {invoice_total}'

    total_mismatch = re.match(r'^Total mismatch: Calculated (.+), but invoice shows (.+)$', issue_text)
    if total_mismatch:
        calculated_total, invoice_total = total_mismatch.groups()
        return f'يوجد اختلاف في الإجمالي النهائي: المحتسب {calculated_total} بينما الفاتورة تعرض {invoice_total}'

    vat_rate_match = re.match(r'^VAT rate appears unusual: ([0-9.]+)% \(typically 5-15%\)$', issue_text)
    if vat_rate_match:
        vat_rate = vat_rate_match.group(1)
        return f'نسبة ضريبة القيمة المضافة غير معتادة: {vat_rate}% (المتوقع عادة بين 5% و15%)'

    unusual_amount_high = re.match(
        r'^Invoice amount \((.+)\) is 3x higher than average from this vendor \((.+)\)$',
        issue_text,
    )
    if unusual_amount_high:
        current_amount, average_amount = unusual_amount_high.groups()
        return f'قيمة الفاتورة ({current_amount}) أعلى بثلاث مرات من متوسط هذا المورد ({average_amount})'

    unusual_amount_low = re.match(
        r'^Invoice amount \((.+)\) is significantly lower than average from this vendor \((.+)\)$',
        issue_text,
    )
    if unusual_amount_low:
        current_amount, average_amount = unusual_amount_low.groups()
        return f'قيمة الفاتورة ({current_amount}) أقل بشكل ملحوظ من متوسط هذا المورد ({average_amount})'

    payment_terms_match = re.match(r'^Unusual payment terms: (\d+) days$', issue_text)
    if payment_terms_match:
        days_to_pay = payment_terms_match.group(1)
        return f'شروط السداد غير معتادة: {days_to_pay} يوم'

    confidence_match = re.match(r'^Low OCR confidence: (\d+)%$', issue_text)
    if confidence_match:
        score = confidence_match.group(1)
        return f'دقة OCR منخفضة: {score}%'

    duplicate_factor_match = re.match(r'^Potential duplicate detected \(score: (\d+)\)$', issue_text)
    if duplicate_factor_match:
        score = duplicate_factor_match.group(1)
        return f'تم رصد احتمال تكرار (الدرجة: {score})'

    anomalies_score_match = re.match(r'^Anomalies detected \(score: (\d+)\)$', issue_text)
    if anomalies_score_match:
        score = anomalies_score_match.group(1)
        return f'تم رصد شذوذات (الدرجة: {score})'

    critical_risk_match = re.match(r'^Critical risk detected \((\d+)/100\)$', issue_text)
    if critical_risk_match:
        score = critical_risk_match.group(1)
        return f'تم رصد مخاطر حرجة ({score})'

    high_risk_match = re.match(r'^High risk level \((\d+)/100\)$', issue_text)
    if high_risk_match:
        score = high_risk_match.group(1)
        return f'مستوى المخاطر مرتفع ({score})'

    medium_risk_match = re.match(r'^Medium risk level \((\d+)/100\)$', issue_text)
    if medium_risk_match:
        score = medium_risk_match.group(1)
        return f'مستوى المخاطر متوسط ({score})'

    low_risk_match = re.match(r'^Low risk detected \((\d+)/100\)$', issue_text)
    if low_risk_match:
        score = low_risk_match.group(1)
        return f'تم رصد مخاطر منخفضة ({score})'

    validation_failed_match = re.match(r'^([a-z_]+) validation failed$', issue_text)
    if validation_failed_match:
        check_key = validation_failed_match.group(1)
        return f'فشل التحقق: {localize_check_label(check_key, lang)}'

    failed_validation_match = re.match(r'^Failed ([a-z_]+) validation$', issue_text)
    if failed_validation_match:
        check_key = failed_validation_match.group(1)
        return f'فشل في تحقق {localize_check_label(check_key, lang)}'

    warning_validation_match = re.match(r'^Warning in ([a-z_]+) validation$', issue_text)
    if warning_validation_match:
        check_key = warning_validation_match.group(1)
        return f'تحذير في تحقق {localize_check_label(check_key, lang)}'

    return issue_text


def localize_audit_message(message: Any, lang: str = 'ar') -> str:
    message_text = str(message or '').strip()
    if not message_text or lang != 'ar':
        return message_text

    exact_messages = {
        'Invoice persisted to ingestion layer': 'تم حفظ الفاتورة في طبقة الإدخال',
        'Vendor, invoice header, and line items were saved for audit readiness.': 'تم حفظ بيانات المورد ورأس الفاتورة والبنود لتهيئة التدقيق.',
        'Initial audit procedures completed': 'اكتملت إجراءات التدقيق الأولية',
        'Deterministic invoice audit checks were executed after persistence.': 'تم تنفيذ فحوصات التدقيق الحتمية بعد حفظ البيانات.',
        'Audit Report Generated': 'تم إنشاء تقرير التدقيق',
    }
    if message_text in exact_messages:
        return exact_messages[message_text]

    generated_report_match = re.match(r'^Comprehensive audit report generated: (.+)$', message_text)
    if generated_report_match:
        report_number = generated_report_match.group(1)
        return f'تم إنشاء تقرير التدقيق الشامل: {report_number}'

    risk_summary_match = re.match(r'^Risk Level: (.+), Recommendation: (.+)$', message_text)
    if risk_summary_match:
        risk_level, recommendation = risk_summary_match.groups()
        return (
            f'مستوى المخاطر: {localize_risk_level(risk_level, lang)}، '
            f'التوصية: {localize_recommendation(recommendation, lang)}'
        )

    return localize_issue(message_text, lang)


def _status_payload(status_key: str, lang: str) -> Dict[str, str]:
    return {
        'status_key': status_key,
        'status_label': STATUS_META[status_key]['label'][lang],
        'completion_label': STATUS_META[status_key]['completion'][lang],
        'badge': STATUS_META[status_key]['badge'],
    }


def build_checklist_rows(
    validation_results: Any,
    duplicate_score: int,
    duplicate_status: str,
    anomaly_score: int,
    anomaly_reasons: Any,
    lang: str = 'ar',
) -> List[Dict[str, Any]]:
    validation_map = _coerce_dict(validation_results)
    rows: List[Dict[str, Any]] = []

    for check_key in CHECK_ORDER:
        raw_result = validation_map.get(check_key, {})
        status_key = raw_result.get('status', 'warning')
        if status_key not in STATUS_META:
            status_key = 'warning'

        issues = [localize_issue(issue, lang) for issue in _coerce_list(raw_result.get('issues'))]
        row = {
            'key': check_key,
            'label': localize_check_label(check_key, lang),
            'notes': issues,
        }
        row.update(_status_payload(status_key, lang))
        rows.append(row)

    duplicate_notes: List[str] = []
    if duplicate_score >= 80:
        duplicate_status_key = 'fail'
        duplicate_notes.append(
            'احتمال التكرار مرتفع جداً.' if lang == 'ar' else 'Duplicate probability is very high.'
        )
    elif duplicate_score >= 30:
        duplicate_status_key = 'warning'
        duplicate_notes.append(
            'توجد مؤشرات تحتاج مراجعة لاحتمال وجود تكرار.' if lang == 'ar' else 'Potential duplicate indicators require review.'
        )
    else:
        duplicate_status_key = 'pass'
        duplicate_notes.append(
            'لم يتم رصد مؤشرات قوية على التكرار.' if lang == 'ar' else 'No strong duplicate indicators were found.'
        )

    duplicate_notes.append(
        (
            f'الحالة: {localize_duplicate_status(duplicate_status, lang)} - الدرجة: {duplicate_score}/100'
            if lang == 'ar'
            else f'Status: {localize_duplicate_status(duplicate_status, lang)} - Score: {duplicate_score}/100'
        )
    )

    duplicate_row = {
        'key': 'duplicate_screening',
        'label': localize_check_label('duplicate_screening', lang),
        'notes': duplicate_notes,
    }
    duplicate_row.update(_status_payload(duplicate_status_key, lang))
    rows.append(duplicate_row)

    localized_anomalies = [
        localize_issue(reason.get('reason') if isinstance(reason, dict) else reason, lang)
        for reason in _coerce_list(anomaly_reasons)
    ]
    localized_anomalies = [reason for reason in localized_anomalies if reason]

    if anomaly_score >= 70:
        anomaly_status_key = 'fail'
    elif anomaly_score >= 30 or localized_anomalies:
        anomaly_status_key = 'warning'
    else:
        anomaly_status_key = 'pass'

    anomaly_notes = localized_anomalies[:]
    if not anomaly_notes:
        anomaly_notes.append(
            'لم يتم رصد شذوذات مؤثرة.' if lang == 'ar' else 'No material anomalies were detected.'
        )
    anomaly_notes.append(
        f"{'درجة الشذوذ' if lang == 'ar' else 'Anomaly score'}: {anomaly_score}/100"
    )

    anomaly_row = {
        'key': 'anomaly_screening',
        'label': localize_check_label('anomaly_screening', lang),
        'notes': anomaly_notes,
    }
    anomaly_row.update(_status_payload(anomaly_status_key, lang))
    rows.append(anomaly_row)

    return rows


def build_ai_summary(report, lang: str = 'ar', checklist_rows: List[Dict[str, Any]] | None = None) -> str:
    if lang == 'ar' and getattr(report, 'ai_summary_ar', None):
        return report.ai_summary_ar.strip()
    if lang == 'en' and getattr(report, 'ai_summary', None):
        return report.ai_summary.strip()

    checklist_rows = checklist_rows or []
    failed_checks = [row['label'] for row in checklist_rows if row['status_key'] == 'fail']
    warning_checks = [row['label'] for row in checklist_rows if row['status_key'] == 'warning']
    amount_display = format_amount(report.total_amount)
    risk_label = localize_risk_level(report.risk_level, lang)
    recommendation_label = localize_recommendation(report.recommendation, lang)

    if lang == 'ar':
        summary_parts = [
            (
                f'الفاتورة رقم {report.extracted_invoice_number or "-"} للمورد '
                f'{report.extracted_vendor_name or "-"} بقيمة {amount_display} {report.currency or "SAR"} '
                f'تم تصنيفها ضمن مستوى مخاطر {risk_label}.'
            )
        ]

        if failed_checks:
            summary_parts.append(f'هناك عناصر تحقق غير مجتازة: {"، ".join(failed_checks)}.')
        elif warning_checks:
            summary_parts.append(f'توجد ملاحظات تحتاج متابعة في: {"، ".join(warning_checks)}.')
        else:
            summary_parts.append('جميع عناصر التحقق الأساسية في وضع جيد.')

        summary_parts.append(f'التوصية الحالية للنظام: {recommendation_label}.')
        return '\n\n'.join(summary_parts)

    summary_parts = [
        (
            f'Invoice {report.extracted_invoice_number or "-"} from '
            f'{report.extracted_vendor_name or "-"} for {amount_display} {report.currency or "SAR"} '
            f'is currently classified as {risk_label} risk.'
        )
    ]
    if failed_checks:
        summary_parts.append(f'Failed checks were detected in: {", ".join(failed_checks)}.')
    elif warning_checks:
        summary_parts.append(f'Follow-up is recommended for: {", ".join(warning_checks)}.')
    else:
        summary_parts.append('Core validation checks are in good standing.')
    summary_parts.append(f'The current system recommendation is: {recommendation_label}.')
    return '\n\n'.join(summary_parts)


def build_ai_findings(
    report,
    lang: str = 'ar',
    checklist_rows: List[Dict[str, Any]] | None = None,
    anomaly_reasons: List[str] | None = None,
    risk_factors: List[str] | None = None,
) -> str:
    if lang == 'ar' and getattr(report, 'ai_findings_ar', None):
        return report.ai_findings_ar.strip()
    if lang == 'en' and getattr(report, 'ai_findings', None):
        return report.ai_findings.strip()

    checklist_rows = checklist_rows or []
    anomaly_reasons = anomaly_reasons or []
    risk_factors = risk_factors or []

    failed_checks = [row['label'] for row in checklist_rows if row['status_key'] == 'fail']
    warning_checks = [row['label'] for row in checklist_rows if row['status_key'] == 'warning']

    findings: List[str] = []

    if lang == 'ar':
        if failed_checks:
            findings.append(f'الفحوصات غير المجتازة: {"، ".join(failed_checks)}.')
        if warning_checks:
            findings.append(f'العناصر التي تحتاج مراجعة إضافية: {"، ".join(warning_checks)}.')
        if report.duplicate_score:
            findings.append(
                f'نتيجة فحص التكرار: {report.duplicate_score}/100 ({localize_duplicate_status(report.duplicate_status, lang)}).'
            )
        if anomaly_reasons:
            findings.append(f'أبرز الشذوذات المرصودة: {"، ".join(anomaly_reasons[:3])}.')
        if risk_factors:
            findings.append(f'عوامل المخاطر: {"، ".join(risk_factors[:3])}.')
        return '\n'.join(f'• {finding}' for finding in findings) if findings else get_labels(lang)['no_findings']

    if failed_checks:
        findings.append(f'Failed checks: {", ".join(failed_checks)}.')
    if warning_checks:
        findings.append(f'Checks requiring follow-up: {", ".join(warning_checks)}.')
    if report.duplicate_score:
        findings.append(
            f'Duplicate review score: {report.duplicate_score}/100 ({localize_duplicate_status(report.duplicate_status, lang)}).'
        )
    if anomaly_reasons:
        findings.append(f'Key anomalies: {", ".join(anomaly_reasons[:3])}.')
    if risk_factors:
        findings.append(f'Risk factors: {", ".join(risk_factors[:3])}.')
    return '\n'.join(f'• {finding}' for finding in findings) if findings else get_labels(lang)['no_findings']


def build_recommendation_reason(
    report,
    lang: str = 'ar',
    checklist_rows: List[Dict[str, Any]] | None = None,
) -> str:
    if lang == 'ar' and getattr(report, 'recommendation_reason_ar', None):
        return report.recommendation_reason_ar.strip()
    if lang == 'en' and getattr(report, 'recommendation_reason', None):
        return report.recommendation_reason.strip()

    checklist_rows = checklist_rows or []
    failed_checks = [row['label'] for row in checklist_rows if row['status_key'] == 'fail']
    warning_checks = [row['label'] for row in checklist_rows if row['status_key'] == 'warning']

    if lang == 'ar':
        reason_parts: List[str] = []
        if report.recommendation == 'reject':
            reason_parts.append('تم التوصية بالرفض بسبب ارتفاع المخاطر أو وجود مخالفات غير مجتازة.')
        elif report.recommendation == 'manual_review':
            reason_parts.append('تمت التوصية بالمراجعة اليدوية بسبب وجود مؤشرات تحتاج تدقيقاً إضافياً.')
        else:
            reason_parts.append('تمت التوصية بالاعتماد لأن نتائج التحقق الأساسية ضمن الحدود المقبولة.')

        if failed_checks:
            reason_parts.append(f'العناصر المؤثرة: {"، ".join(failed_checks)}.')
        elif warning_checks:
            reason_parts.append(f'العناصر التي تستلزم متابعة: {"، ".join(warning_checks)}.')

        if report.duplicate_score >= 80:
            reason_parts.append('كما أن احتمال التكرار مرتفع جداً.')
        return ' '.join(reason_parts).strip()

    reason_parts = []
    if report.recommendation == 'reject':
        reason_parts.append('The invoice is recommended for rejection because risk is high or failed checks were identified.')
    elif report.recommendation == 'manual_review':
        reason_parts.append('Manual review is recommended because additional verification is required.')
    else:
        reason_parts.append('Approval is recommended because core validation checks are within acceptable limits.')

    if failed_checks:
        reason_parts.append(f'Key failed checks: {", ".join(failed_checks)}.')
    elif warning_checks:
        reason_parts.append(f'Checks needing follow-up: {", ".join(warning_checks)}.')

    if report.duplicate_score >= 80:
        reason_parts.append('Duplicate probability is also very high.')
    return ' '.join(reason_parts).strip()


def build_audit_trail_entries(audit_trail: Any, lang: str = 'ar') -> List[Dict[str, str]]:
    localized_entries = []
    for entry in _coerce_list(audit_trail):
        if not isinstance(entry, dict):
            continue
        localized_entries.append(
            {
                'timestamp': entry.get('timestamp', ''),
                'status': localize_processing_status(entry.get('status', ''), lang),
                'event': localize_audit_message(entry.get('title') or entry.get('event') or '', lang),
                'details': localize_audit_message(entry.get('description') or entry.get('result_summary') or '', lang),
            }
        )
    return localized_entries


def build_report_presentation(report, lang: str = 'ar') -> Dict[str, Any]:
    labels = get_labels(lang)
    validation_results = _coerce_dict(report.validation_results_json)
    anomaly_reasons_raw = _coerce_list(report.anomaly_reasons_json)
    risk_factors_raw = _coerce_list(report.risk_factors_json)

    anomaly_reasons = [
        localize_issue(item.get('reason') if isinstance(item, dict) else item, lang)
        for item in anomaly_reasons_raw
    ]
    anomaly_reasons = [reason for reason in anomaly_reasons if reason]

    risk_factors = [
        localize_issue(item.get('reason') if isinstance(item, dict) else item, lang)
        for item in risk_factors_raw
    ]
    risk_factors = [factor for factor in risk_factors if factor]

    checklist_rows = build_checklist_rows(
        validation_results=validation_results,
        duplicate_score=report.duplicate_score or 0,
        duplicate_status=report.duplicate_status or 'no_duplicate',
        anomaly_score=report.anomaly_score or 0,
        anomaly_reasons=anomaly_reasons_raw,
        lang=lang,
    )

    return {
        'lang': lang,
        'is_arabic': lang == 'ar',
        'labels': labels,
        'line_items': normalize_line_items(report.line_items_json),
        'checklist_rows': checklist_rows,
        'anomaly_reasons': anomaly_reasons,
        'risk_factors': risk_factors,
        'risk_level_label': localize_risk_level(report.risk_level, lang),
        'recommendation_label': localize_recommendation(report.recommendation, lang),
        'duplicate_status_label': localize_duplicate_status(report.duplicate_status, lang),
        'anomaly_status_label': localize_anomaly_status(report.anomaly_status, lang),
        'processing_status_label': localize_processing_status(report.processing_status, lang),
        'ai_summary_display': build_ai_summary(report, lang=lang, checklist_rows=checklist_rows),
        'ai_findings_display': build_ai_findings(
            report,
            lang=lang,
            checklist_rows=checklist_rows,
            anomaly_reasons=anomaly_reasons,
            risk_factors=risk_factors,
        ),
        'recommendation_reason_display': build_recommendation_reason(
            report,
            lang=lang,
            checklist_rows=checklist_rows,
        ),
        'audit_trail': build_audit_trail_entries(report.audit_trail_json, lang),
    }
