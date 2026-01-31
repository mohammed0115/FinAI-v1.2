# accounting_summary.py
# خدمة تحليل ملفات السنة المحاسبية واستخراج دفتر الأستاذ، المركز المالي، والأرباح والخسائر
from typing import List, Dict, Any
from collections import defaultdict

def summarize_accounting_year(entries: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    تحليل قيود السنة المحاسبية واستخراج دفتر الأستاذ، المركز المالي، والأرباح والخسائر.
    الإدخال:
        entries: قائمة من القيد المحاسبي، كل قيد dict فيه 'account', 'debit', 'credit', 'type' (اختياري: 'asset', 'liability', 'equity', 'revenue', 'expense'), 'description'.
    الإخراج:
        dict فيه دفتر الأستاذ، المركز المالي، الأرباح والخسائر.
    """
    ledger = defaultdict(lambda: {'debit': 0, 'credit': 0, 'balance': 0, 'type': None})
    for entry in entries:
        acc = entry['account']
        ledger[acc]['debit'] += entry.get('debit', 0)
        ledger[acc]['credit'] += entry.get('credit', 0)
        ledger[acc]['balance'] = ledger[acc]['debit'] - ledger[acc]['credit']
        if entry.get('type'):
            ledger[acc]['type'] = entry['type']
    # دفتر الأستاذ
    general_ledger = dict(ledger)
    # المركز المالي
    balance_sheet = {'assets': {}, 'liabilities': {}, 'equity': {}}
    for acc, data in ledger.items():
        acc_type = data.get('type')
        if acc_type == 'asset':
            balance_sheet['assets'][acc] = data['balance']
        elif acc_type == 'liability':
            balance_sheet['liabilities'][acc] = data['balance']
        elif acc_type == 'equity':
            balance_sheet['equity'][acc] = data['balance']
    # الأرباح والخسائر
    income_statement = {'revenue': 0, 'expense': 0, 'profit_loss': 0}
    for acc, data in ledger.items():
        acc_type = data.get('type')
        if acc_type == 'revenue':
            income_statement['revenue'] += data['balance']
        elif acc_type == 'expense':
            income_statement['expense'] += data['balance']
    income_statement['profit_loss'] = income_statement['revenue'] - income_statement['expense']
    return {
        'general_ledger': general_ledger,
        'balance_sheet': balance_sheet,
        'income_statement': income_statement
    }

# مثال استخدام
if __name__ == "__main__":
    sample_entries = [
        {'account': 'الصندوق', 'debit': 10000, 'credit': 0, 'type': 'asset', 'description': 'إيداع نقدي'},
        {'account': 'الموردين', 'debit': 0, 'credit': 3000, 'type': 'liability', 'description': 'شراء آجل'},
        {'account': 'رأس المال', 'debit': 0, 'credit': 7000, 'type': 'equity', 'description': 'تأسيس الشركة'},
        {'account': 'المبيعات', 'debit': 0, 'credit': 5000, 'type': 'revenue', 'description': 'بيع بضاعة'},
        {'account': 'المشتريات', 'debit': 2000, 'credit': 0, 'type': 'expense', 'description': 'شراء بضاعة'},
    ]
    result = summarize_accounting_year(sample_entries)
    import json
    print(json.dumps(result, ensure_ascii=False, indent=2))
