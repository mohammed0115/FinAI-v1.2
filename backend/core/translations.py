"""
Multi-language Support - دعم تعدد اللغات
Arabic (primary) and English (secondary) UI translations

NOTE: This is UI-level translation only.
Audit logic, scoring, and data remain unchanged.
"""

# UI Translations - Arabic is PRIMARY
TRANSLATIONS = {
    # Navigation
    'nav_dashboard': {
        'ar': 'لوحة القيادة',
        'en': 'Dashboard',
    },
    'nav_compliance': {
        'ar': 'الامتثال',
        'en': 'Compliance',
    },
    'nav_findings': {
        'ar': 'نتائج التدقيق',
        'en': 'Audit Findings',
    },
    'nav_transactions': {
        'ar': 'المعاملات',
        'en': 'Transactions',
    },
    'nav_accounts': {
        'ar': 'الحسابات',
        'en': 'Accounts',
    },
    'nav_documents': {
        'ar': 'المستندات',
        'en': 'Documents',
    },
    'nav_reports': {
        'ar': 'التقارير',
        'en': 'Reports',
    },
    'nav_logout': {
        'ar': 'خروج',
        'en': 'Logout',
    },
    
    # Common Labels
    'financial_audit': {
        'ar': 'التدقيق المالي',
        'en': 'Financial Audit',
    },
    'platform_name': {
        'ar': 'منصة التدقيق المالي الذكي',
        'en': 'AI-Powered Financial Audit Platform',
    },
    'risk_level': {
        'ar': 'مستوى المخاطر',
        'en': 'Risk Level',
    },
    'risk_critical': {
        'ar': 'حرج',
        'en': 'Critical',
    },
    'risk_high': {
        'ar': 'مرتفع',
        'en': 'High',
    },
    'risk_medium': {
        'ar': 'متوسط',
        'en': 'Medium',
    },
    'risk_low': {
        'ar': 'منخفض',
        'en': 'Low',
    },
    
    # Status
    'status_resolved': {
        'ar': 'محلول',
        'en': 'Resolved',
    },
    'status_pending': {
        'ar': 'قيد المتابعة',
        'en': 'Pending',
    },
    'status_approved': {
        'ar': 'معتمد',
        'en': 'Approved',
    },
    'status_rejected': {
        'ar': 'مرفوض',
        'en': 'Rejected',
    },
    
    # Finding Types
    'type_compliance': {
        'ar': 'امتثال',
        'en': 'Compliance',
    },
    'type_accuracy': {
        'ar': 'دقة',
        'en': 'Accuracy',
    },
    'type_documentation': {
        'ar': 'توثيق',
        'en': 'Documentation',
    },
    'type_internal_control': {
        'ar': 'رقابة داخلية',
        'en': 'Internal Control',
    },
    
    # Dashboard
    'total_transactions': {
        'ar': 'إجمالي المعاملات',
        'en': 'Total Transactions',
    },
    'total_findings': {
        'ar': 'إجمالي الملاحظات',
        'en': 'Total Findings',
    },
    'compliance_score': {
        'ar': 'درجة الامتثال',
        'en': 'Compliance Score',
    },
    'financial_impact': {
        'ar': 'الأثر المالي',
        'en': 'Financial Impact',
    },
    
    # ZATCA
    'zatca_compliance': {
        'ar': 'امتثال هيئة الزكاة والضريبة والجمارك',
        'en': 'ZATCA Compliance',
    },
    'vat_compliance': {
        'ar': 'امتثال ضريبة القيمة المضافة',
        'en': 'VAT Compliance',
    },
    'zakat_compliance': {
        'ar': 'امتثال الزكاة',
        'en': 'Zakat Compliance',
    },
    
    # Actions
    'action_view': {
        'ar': 'عرض',
        'en': 'View',
    },
    'action_download': {
        'ar': 'تحميل',
        'en': 'Download',
    },
    'action_upload': {
        'ar': 'رفع',
        'en': 'Upload',
    },
    'action_generate': {
        'ar': 'توليد',
        'en': 'Generate',
    },
    'action_verify': {
        'ar': 'تحقق',
        'en': 'Verify',
    },
    
    # AI Explanation
    'ai_analysis': {
        'ar': 'تحليل الذكاء الاصطناعي',
        'en': 'AI Analysis',
    },
    'generate_explanation': {
        'ar': 'توليد شرح جديد',
        'en': 'Generate Explanation',
    },
    'advisory_only': {
        'ar': 'استشاري فقط - يتطلب مراجعة بشرية',
        'en': 'Advisory Only - Requires Human Review',
    },
    'confidence_score': {
        'ar': 'درجة الثقة',
        'en': 'Confidence Score',
    },
    
    # Documents & OCR
    'document_upload': {
        'ar': 'رفع المستندات',
        'en': 'Document Upload',
    },
    'ocr_evidence': {
        'ar': 'أدلة OCR',
        'en': 'OCR Evidence',
    },
    'extracted_text': {
        'ar': 'النص المستخرج',
        'en': 'Extracted Text',
    },
    
    # Common
    'date': {
        'ar': 'التاريخ',
        'en': 'Date',
    },
    'amount': {
        'ar': 'المبلغ',
        'en': 'Amount',
    },
    'currency_sar': {
        'ar': 'ر.س',
        'en': 'SAR',
    },
    'back': {
        'ar': 'العودة',
        'en': 'Back',
    },
    'search': {
        'ar': 'بحث',
        'en': 'Search',
    },
    'filter': {
        'ar': 'تصفية',
        'en': 'Filter',
    },
    'all': {
        'ar': 'الكل',
        'en': 'All',
    },
    
    # Language toggle
    'language': {
        'ar': 'اللغة',
        'en': 'Language',
    },
    'arabic': {
        'ar': 'العربية',
        'en': 'Arabic',
    },
    'english': {
        'ar': 'English',
        'en': 'English',
    },
}


def get_translation(key: str, lang: str = 'ar') -> str:
    """
    Get translation for a key in the specified language.
    Falls back to Arabic if translation not found.
    
    Args:
        key: Translation key
        lang: Language code ('ar' or 'en')
    
    Returns:
        Translated string
    """
    if key in TRANSLATIONS:
        return TRANSLATIONS[key].get(lang, TRANSLATIONS[key].get('ar', key))
    return key


def get_all_translations(lang: str = 'ar') -> dict:
    """
    Get all translations for a language as a flat dictionary.
    
    Args:
        lang: Language code ('ar' or 'en')
    
    Returns:
        Dictionary with all translations
    """
    return {key: get_translation(key, lang) for key in TRANSLATIONS}
