# accounting_rules.py
# خدمة تحليل محاسبي تطبق القوانين المحاسبية وتكشف الخلل دون تخزين
from typing import List, Dict, Any

def analyze_journal_entries(entries: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    تحليل قائمة قيود محاسبية وتطبيق القوانين المحاسبية الأساسية.
    كل قيد يجب أن يكون فيه مجموع المدين = مجموع الدائن.
    الإدخال:
        entries: قائمة من القيد المحاسبي، كل قيد dict فيه 'debit' و 'credit' و 'description'.
    الإخراج:
        dict فيه حالة التوازن وقائمة الأخطاء إن وجدت.
    """
    errors = []
    for idx, entry in enumerate(entries):
        debit = entry.get('debit', 0)
        credit = entry.get('credit', 0)
        if debit < 0 or credit < 0:
            errors.append({
                'index': idx,
                'error': 'Negative value in debit or credit',
                'entry': entry
            })
        if debit == 0 and credit == 0:
            errors.append({
                'index': idx,
                'error': 'Both debit and credit are zero',
                'entry': entry
            })
    total_debit = sum(e.get('debit', 0) for e in entries)
    total_credit = sum(e.get('credit', 0) for e in entries)
    balanced = total_debit == total_credit
    if not balanced:
        errors.append({
            'error': 'Total debit and credit are not equal',
            'total_debit': total_debit,
            'total_credit': total_credit
        })
    return {
        'balanced': balanced,
        'total_debit': total_debit,
        'total_credit': total_credit,
        'errors': errors
    }

# مثال استخدام
if __name__ == "__main__":
    sample_entries = [
        {'debit': 1000, 'credit': 0, 'description': 'شراء'},
        {'debit': 0, 'credit': 1000, 'description': 'دفع نقدي'},
        {'debit': 500, 'credit': 0, 'description': 'شراء إضافي'},
        {'debit': 0, 'credit': 400, 'description': 'دفع جزئي'},
    ]
    result = analyze_journal_entries(sample_entries)
    import json
    print(json.dumps(result, ensure_ascii=False, indent=2))
