"""
Compliance Services - خدمات الامتثال
ZATCA, VAT, and Zakat validation and calculation services
"""
from decimal import Decimal
from datetime import datetime, date
from django.db.models import Sum, Q
from django.utils import timezone
from typing import Dict, List, Optional, Tuple
import uuid
import re

from core.models import Organization
from documents.models import Transaction, Account


class ZATCAValidationService:
    """
    خدمة التحقق من الفواتير الإلكترونية
    ZATCA E-Invoice Validation Service (Pre-integration)
    """
    
    # ZATCA Mandatory Fields for Tax Invoice
    MANDATORY_FIELDS_STANDARD = [
        ('invoice_number', 'رقم الفاتورة', 'Invoice Number'),
        ('uuid', 'المعرف الفريد', 'UUID'),
        ('issue_date', 'تاريخ الإصدار', 'Issue Date'),
        ('seller_name', 'اسم البائع', 'Seller Name'),
        ('seller_vat_number', 'الرقم الضريبي للبائع', 'Seller VAT Number'),
        ('buyer_name', 'اسم المشتري', 'Buyer Name'),
        ('total_excluding_vat', 'المجموع بدون الضريبة', 'Total Excluding VAT'),
        ('total_vat', 'مبلغ الضريبة', 'VAT Amount'),
        ('total_including_vat', 'المجموع شامل الضريبة', 'Total Including VAT'),
    ]
    
    # ZATCA Mandatory Fields for Simplified Invoice
    MANDATORY_FIELDS_SIMPLIFIED = [
        ('invoice_number', 'رقم الفاتورة', 'Invoice Number'),
        ('issue_date', 'تاريخ الإصدار', 'Issue Date'),
        ('seller_name', 'اسم البائع', 'Seller Name'),
        ('seller_vat_number', 'الرقم الضريبي للبائع', 'Seller VAT Number'),
        ('total_including_vat', 'المجموع شامل الضريبة', 'Total Including VAT'),
    ]
    
    # Saudi VAT Number format: 3XXXXXXXXXX00003
    VAT_NUMBER_PATTERN = r'^3\d{13}3$'
    
    def validate_invoice(self, invoice_data: Dict) -> List[Dict]:
        """
        التحقق من صحة الفاتورة
        Validate invoice against ZATCA requirements
        Returns list of validation results
        """
        results = []
        
        # Determine invoice type
        is_simplified = invoice_data.get('invoice_subtype', '0100000') == '0200000'
        mandatory_fields = self.MANDATORY_FIELDS_SIMPLIFIED if is_simplified else self.MANDATORY_FIELDS_STANDARD
        
        # 1. Mandatory Field Checks
        for field_name, field_ar, field_en in mandatory_fields:
            value = invoice_data.get(field_name)
            is_valid = bool(value) and str(value).strip() != ''
            
            results.append({
                'check_type': 'mandatory_field',
                'field_name': field_name,
                'is_valid': is_valid,
                'error_code': 'ZATCA-001' if not is_valid else None,
                'message_ar': f'الحقل الإلزامي "{field_ar}" {"موجود" if is_valid else "مفقود أو فارغ"}',
                'message_en': f'Mandatory field "{field_en}" is {"present" if is_valid else "missing or empty"}',
            })
        
        # 2. VAT Number Format Validation
        seller_vat = invoice_data.get('seller_vat_number', '')
        vat_valid = bool(re.match(self.VAT_NUMBER_PATTERN, seller_vat))
        results.append({
            'check_type': 'format',
            'field_name': 'seller_vat_number',
            'is_valid': vat_valid,
            'error_code': 'ZATCA-002' if not vat_valid else None,
            'message_ar': f'تنسيق الرقم الضريبي للبائع {"صحيح" if vat_valid else "غير صحيح - يجب أن يكون 15 رقم يبدأ بـ 3 وينتهي بـ 3"}',
            'message_en': f'Seller VAT number format is {"valid" if vat_valid else "invalid - must be 15 digits starting and ending with 3"}',
        })
        
        # 3. UUID Format Validation
        invoice_uuid = invoice_data.get('uuid', '')
        try:
            uuid.UUID(str(invoice_uuid))
            uuid_valid = True
        except (ValueError, AttributeError):
            uuid_valid = False
        
        results.append({
            'check_type': 'format',
            'field_name': 'uuid',
            'is_valid': uuid_valid,
            'error_code': 'ZATCA-003' if not uuid_valid else None,
            'message_ar': f'تنسيق المعرف الفريد (UUID) {"صحيح" if uuid_valid else "غير صحيح"}',
            'message_en': f'UUID format is {"valid" if uuid_valid else "invalid"}',
        })
        
        # 4. VAT Calculation Validation
        total_ex_vat = Decimal(str(invoice_data.get('total_excluding_vat', 0)))
        total_vat = Decimal(str(invoice_data.get('total_vat', 0)))
        total_inc_vat = Decimal(str(invoice_data.get('total_including_vat', 0)))
        
        expected_total = total_ex_vat + total_vat
        calc_valid = abs(expected_total - total_inc_vat) < Decimal('0.01')
        
        results.append({
            'check_type': 'calculation',
            'field_name': 'total_including_vat',
            'is_valid': calc_valid,
            'error_code': 'ZATCA-004' if not calc_valid else None,
            'message_ar': f'حساب المجموع شامل الضريبة {"صحيح" if calc_valid else f"غير صحيح - المتوقع {expected_total} والفعلي {total_inc_vat}"}',
            'message_en': f'Total including VAT calculation is {"correct" if calc_valid else f"incorrect - expected {expected_total}, got {total_inc_vat}"}',
        })
        
        # 5. VAT Rate Validation (15% for Saudi Arabia)
        if total_ex_vat > 0:
            calculated_rate = (total_vat / total_ex_vat * 100).quantize(Decimal('0.01'))
            rate_valid = calculated_rate == Decimal('15.00') or total_vat == Decimal('0')  # 0 for exempt
            
            results.append({
                'check_type': 'business_rule',
                'field_name': 'vat_rate',
                'is_valid': rate_valid,
                'error_code': 'ZATCA-005' if not rate_valid else None,
                'message_ar': f'نسبة ضريبة القيمة المضافة {"15% صحيحة" if rate_valid else f"غير صحيحة - النسبة المحسوبة {calculated_rate}%"}',
                'message_en': f'VAT rate is {"correct at 15%" if rate_valid else f"incorrect - calculated rate is {calculated_rate}%"}',
            })
        
        # 6. Invoice Date Validation (not future dated)
        issue_date = invoice_data.get('issue_date')
        if issue_date:
            if isinstance(issue_date, str):
                issue_date = datetime.strptime(issue_date, '%Y-%m-%d').date()
            date_valid = issue_date <= date.today()
            
            results.append({
                'check_type': 'business_rule',
                'field_name': 'issue_date',
                'is_valid': date_valid,
                'error_code': 'ZATCA-006' if not date_valid else None,
                'message_ar': f'تاريخ الفاتورة {"صحيح" if date_valid else "لا يمكن أن يكون في المستقبل"}',
                'message_en': f'Invoice date is {"valid" if date_valid else "cannot be in the future"}',
            })
        
        # 7. Invoice Number Sequential Check (conceptual)
        invoice_number = invoice_data.get('invoice_number', '')
        number_valid = bool(invoice_number) and len(invoice_number) <= 127
        
        results.append({
            'check_type': 'format',
            'field_name': 'invoice_number',
            'is_valid': number_valid,
            'error_code': 'ZATCA-007' if not number_valid else None,
            'message_ar': f'رقم الفاتورة {"صحيح" if number_valid else "يجب ألا يتجاوز 127 حرف"}',
            'message_en': f'Invoice number is {"valid" if number_valid else "must not exceed 127 characters"}',
        })
        
        return results
    
    def get_overall_status(self, validation_results: List[Dict]) -> Tuple[str, int]:
        """
        حساب الحالة الإجمالية للتحقق
        Calculate overall validation status and score
        """
        total = len(validation_results)
        passed = sum(1 for r in validation_results if r['is_valid'])
        
        score = int((passed / total) * 100) if total > 0 else 0
        
        if score == 100:
            status = 'validated'
        elif score >= 80:
            status = 'warning'
        else:
            status = 'rejected'
        
        return status, score


class VATReconciliationService:
    """
    خدمة تسوية ضريبة القيمة المضافة
    VAT Reconciliation Service
    """
    
    def reconcile_vat(self, organization_id: str, period_start: date, period_end: date) -> Dict:
        """
        تسوية ضريبة القيمة المضافة لفترة محددة
        Reconcile VAT for a specific period
        """
        from documents.models import Transaction, Account
        
        # Get all transactions in period
        transactions = Transaction.objects.filter(
            organization_id=organization_id,
            transaction_date__gte=period_start,
            transaction_date__lte=period_end
        )
        
        # Calculate Output VAT (Sales)
        sales_transactions = transactions.filter(transaction_type='income')
        output_vat_sales = sales_transactions.aggregate(
            total=Sum('vat_amount')
        )['total'] or Decimal('0')
        
        # Calculate Input VAT (Purchases)
        purchase_transactions = transactions.filter(transaction_type='expense')
        input_vat_purchases = purchase_transactions.aggregate(
            total=Sum('vat_amount')
        )['total'] or Decimal('0')
        
        # Get VAT account balances from GL
        try:
            vat_payable_account = Account.objects.get(
                organization_id=organization_id,
                account_subtype='vat_payable'
            )
            gl_vat_payable = vat_payable_account.current_balance
        except Account.DoesNotExist:
            gl_vat_payable = Decimal('0')
        
        # Calculate net VAT
        net_vat_due = output_vat_sales - input_vat_purchases
        
        # Calculate variance
        variance = net_vat_due - gl_vat_payable
        
        # Find discrepancies
        discrepancies = self._find_discrepancies(transactions, organization_id)
        
        # Calculate compliance score
        compliance_score = self._calculate_compliance_score(variance, discrepancies)
        
        return {
            'period_start': period_start,
            'period_end': period_end,
            'output_vat_sales': output_vat_sales,
            'input_vat_purchases': input_vat_purchases,
            'net_vat_due': net_vat_due,
            'gl_vat_payable': gl_vat_payable,
            'variance': variance,
            'discrepancies': discrepancies,
            'compliance_score': compliance_score,
            'variance_explanation_ar': self._generate_variance_explanation_ar(variance, discrepancies),
        }
    
    def _find_discrepancies(self, transactions, organization_id: str) -> List[Dict]:
        """
        البحث عن التفاوتات
        Find VAT discrepancies in transactions
        """
        discrepancies = []
        
        for txn in transactions:
            # Check for missing VAT
            if txn.amount > 0 and (txn.vat_amount is None or txn.vat_amount == 0):
                if txn.vat_rate and txn.vat_rate > 0:
                    expected_vat = txn.amount * txn.vat_rate / 100
                    discrepancies.append({
                        'transaction_id': str(txn.id),
                        'discrepancy_type': 'missing_invoice',
                        'expected_vat': expected_vat,
                        'actual_vat': Decimal('0'),
                        'variance': expected_vat,
                        'description_ar': f'ضريبة القيمة المضافة مفقودة للمعاملة {txn.reference_number}',
                        'description_en': f'VAT missing for transaction {txn.reference_number}',
                    })
            
            # Check for rate errors
            if txn.amount > 0 and txn.vat_amount and txn.vat_amount > 0:
                expected_vat = txn.amount * Decimal('0.15')  # 15% SA rate
                if abs(txn.vat_amount - expected_vat) > Decimal('0.01'):
                    discrepancies.append({
                        'transaction_id': str(txn.id),
                        'discrepancy_type': 'rate_error',
                        'expected_vat': expected_vat,
                        'actual_vat': txn.vat_amount,
                        'variance': txn.vat_amount - expected_vat,
                        'description_ar': f'خطأ في حساب الضريبة للمعاملة {txn.reference_number}',
                        'description_en': f'VAT calculation error for transaction {txn.reference_number}',
                    })
        
        return discrepancies
    
    def _calculate_compliance_score(self, variance: Decimal, discrepancies: List) -> int:
        """حساب درجة الامتثال"""
        score = 100
        
        # Deduct for variance
        if abs(variance) > Decimal('10000'):
            score -= 30
        elif abs(variance) > Decimal('1000'):
            score -= 15
        elif abs(variance) > Decimal('100'):
            score -= 5
        
        # Deduct for discrepancies
        score -= min(len(discrepancies) * 5, 40)
        
        return max(score, 0)
    
    def _generate_variance_explanation_ar(self, variance: Decimal, discrepancies: List) -> str:
        """توليد شرح التفاوت بالعربية"""
        if abs(variance) < Decimal('1'):
            return "لا يوجد فرق جوهري بين ضريبة القيمة المضافة المحسوبة والمسجلة في الدفاتر"
        
        explanation = f"يوجد فرق قدره {abs(variance):,.2f} ريال سعودي "
        
        if variance > 0:
            explanation += "(ضريبة مستحقة أكثر من المسجل) "
        else:
            explanation += "(ضريبة مسجلة أكثر من المستحق) "
        
        if discrepancies:
            explanation += f"بسبب {len(discrepancies)} تفاوت في المعاملات."
        
        return explanation


class ZakatCalculationService:
    """
    خدمة حساب الزكاة
    Zakat Calculation Service for Saudi Organizations
    """
    
    ZAKAT_RATE = Decimal('0.025')  # 2.5%
    
    def calculate_zakat(self, organization_id: str, fiscal_year_end: date) -> Dict:
        """
        حساب الزكاة للسنة المالية
        Calculate Zakat for fiscal year
        """
        from documents.models import Account
        
        # Get accounts by type
        accounts = Account.objects.filter(organization_id=organization_id)
        
        # Calculate positive Zakat base components
        equity_accounts = accounts.filter(account_type='equity')
        total_equity = equity_accounts.aggregate(total=Sum('current_balance'))['total'] or Decimal('0')
        
        liability_accounts = accounts.filter(account_type='liability', account_subtype='loans')
        long_term_liabilities = liability_accounts.aggregate(total=Sum('current_balance'))['total'] or Decimal('0')
        
        # Get provisions (accrued liabilities)
        provision_accounts = accounts.filter(account_type='liability', account_subtype='accrued')
        provisions = provision_accounts.aggregate(total=Sum('current_balance'))['total'] or Decimal('0')
        
        # Calculate adjusted net profit
        revenue_accounts = accounts.filter(account_type='revenue')
        total_revenue = revenue_accounts.aggregate(total=Sum('current_balance'))['total'] or Decimal('0')
        
        expense_accounts = accounts.filter(account_type='expense')
        total_expenses = expense_accounts.aggregate(total=Sum('current_balance'))['total'] or Decimal('0')
        
        adjusted_net_profit = total_revenue - total_expenses
        
        # Positive base
        positive_zakat_base = total_equity + long_term_liabilities + provisions + adjusted_net_profit
        
        # Calculate deductions
        fixed_asset_accounts = accounts.filter(account_type='asset', account_subtype='fixed_assets')
        fixed_assets = fixed_asset_accounts.aggregate(total=Sum('current_balance'))['total'] or Decimal('0')
        
        # Accumulated losses (negative retained earnings)
        retained_earnings = accounts.filter(account_subtype='retained_earnings')
        accumulated_losses = abs(min(
            retained_earnings.aggregate(total=Sum('current_balance'))['total'] or Decimal('0'),
            Decimal('0')
        ))
        
        total_deductions = fixed_assets + accumulated_losses
        
        # Net Zakat base
        net_zakat_base = max(positive_zakat_base - total_deductions, Decimal('0'))
        
        # Zakat due
        zakat_due = net_zakat_base * self.ZAKAT_RATE
        
        # Find discrepancies
        discrepancies = self._find_discrepancies(accounts, organization_id)
        
        return {
            'fiscal_year_end': fiscal_year_end,
            'total_equity': total_equity,
            'long_term_liabilities': long_term_liabilities,
            'provisions': provisions,
            'adjusted_net_profit': adjusted_net_profit,
            'positive_zakat_base': positive_zakat_base,
            'fixed_assets': fixed_assets,
            'accumulated_losses': accumulated_losses,
            'total_deductions': total_deductions,
            'net_zakat_base': net_zakat_base,
            'zakat_rate': self.ZAKAT_RATE,
            'zakat_due': zakat_due,
            'discrepancies': discrepancies,
            'calculation_details': {
                'equity_breakdown': list(equity_accounts.values('account_name', 'current_balance')),
                'liability_breakdown': list(liability_accounts.values('account_name', 'current_balance')),
            }
        }
    
    def _find_discrepancies(self, accounts, organization_id: str) -> List[Dict]:
        """البحث عن تفاوتات الزكاة"""
        discrepancies = []
        
        # Check for missing account classifications
        unclassified = accounts.filter(account_subtype__isnull=True)
        for acc in unclassified:
            discrepancies.append({
                'discrepancy_type': 'classification_error',
                'field_name': 'account_subtype',
                'description_ar': f'الحساب {acc.account_code} - {acc.account_name} غير مصنف بشكل صحيح',
                'description_en': f'Account {acc.account_code} - {acc.account_name} is not properly classified',
                'risk_level': 'medium',
                'impact_on_zakat': Decimal('0'),
            })
        
        return discrepancies
    
    def compare_zakat_vs_tax(self, zakat_due: Decimal, income_tax_due: Decimal) -> Dict:
        """
        مقارنة الزكاة مع ضريبة الدخل
        Compare Zakat with Income Tax
        """
        difference = zakat_due - income_tax_due
        
        if difference > 0:
            explanation_ar = f"الزكاة المستحقة أعلى من ضريبة الدخل بمبلغ {abs(difference):,.2f} ريال"
        elif difference < 0:
            explanation_ar = f"ضريبة الدخل أعلى من الزكاة بمبلغ {abs(difference):,.2f} ريال"
        else:
            explanation_ar = "الزكاة وضريبة الدخل متساويتان"
        
        return {
            'zakat_due': zakat_due,
            'income_tax_due': income_tax_due,
            'difference': difference,
            'explanation_ar': explanation_ar,
        }


class ArabicReportService:
    """
    خدمة التقارير العربية
    Arabic Report Generation Service
    """
    
    def generate_audit_report_ar(self, organization_id: str, findings: List, period_start: date, period_end: date) -> Dict:
        """
        توليد تقرير التدقيق باللغة العربية
        Generate Arabic Audit Report
        """
        from core.models import Organization
        
        org = Organization.objects.get(id=organization_id)
        
        # Categorize findings by risk
        critical = [f for f in findings if f.get('risk_level') == 'critical']
        high = [f for f in findings if f.get('risk_level') == 'high']
        medium = [f for f in findings if f.get('risk_level') == 'medium']
        low = [f for f in findings if f.get('risk_level') == 'low']
        
        # Calculate overall risk rating
        if critical:
            risk_rating = 'حرج'
            risk_rating_en = 'Critical'
        elif high:
            risk_rating = 'مرتفع'
            risk_rating_en = 'High'
        elif medium:
            risk_rating = 'متوسط'
            risk_rating_en = 'Medium'
        else:
            risk_rating = 'منخفض'
            risk_rating_en = 'Low'
        
        # Calculate compliance score
        total_findings = len(findings)
        resolved = len([f for f in findings if f.get('is_resolved', False)])
        compliance_score = int((1 - (total_findings - resolved) / max(total_findings, 1)) * 100)
        
        # Calculate financial impact
        total_financial_impact = sum(
            Decimal(str(f.get('financial_impact', 0) or 0)) for f in findings
        )
        
        # Generate executive summary
        executive_summary_ar = self._generate_executive_summary_ar(
            org.name, period_start, period_end, total_findings, risk_rating, compliance_score
        )
        
        # Generate recommendations
        recommendations_ar = self._generate_recommendations_ar(findings)
        
        # Generate conclusion
        conclusion_ar = self._generate_conclusion_ar(risk_rating, compliance_score)
        
        return {
            'report_number': f'AUD-{org.country}-{timezone.now().strftime("%Y%m%d")}',
            'report_date': timezone.now().date(),
            'report_title_ar': f'تقرير التدقيق المالي - {org.name}',
            'organization_name': org.name,
            'organization_tax_id': org.tax_id,
            'period_start': period_start,
            'period_end': period_end,
            'executive_summary_ar': executive_summary_ar,
            'overall_compliance_score': compliance_score,
            'risk_rating': risk_rating,
            'risk_rating_en': risk_rating_en,
            'total_findings': total_findings,
            'critical_findings': len(critical),
            'high_risk_findings': len(high),
            'medium_risk_findings': len(medium),
            'low_risk_findings': len(low),
            'total_financial_impact': total_financial_impact,
            'findings': findings,
            'recommendations_ar': recommendations_ar,
            'conclusion_ar': conclusion_ar,
        }
    
    def _generate_executive_summary_ar(self, org_name: str, period_start: date, period_end: date,
                                        total_findings: int, risk_rating: str, compliance_score: int) -> str:
        """توليد الملخص التنفيذي"""
        return f"""
الملخص التنفيذي

تم إجراء تدقيق مالي شامل لمنشأة {org_name} للفترة من {period_start.strftime('%Y/%m/%d')} إلى {period_end.strftime('%Y/%m/%d')}.

نتائج التدقيق الرئيسية:
• إجمالي الملاحظات: {total_findings} ملاحظة
• مستوى المخاطر العام: {risk_rating}
• درجة الامتثال: {compliance_score}%

يهدف هذا التقرير إلى تقديم تقييم مستقل لمدى التزام المنشأة بالمتطلبات التنظيمية والمعايير المحاسبية المعتمدة.
"""
    
    def _generate_recommendations_ar(self, findings: List) -> List[str]:
        """توليد التوصيات"""
        recommendations = []
        
        # Group by finding type
        finding_types = set(f.get('finding_type') for f in findings)
        
        if 'compliance' in finding_types:
            recommendations.append("تعزيز إجراءات الامتثال للمتطلبات التنظيمية وتحديث السياسات الداخلية")
        
        if 'accuracy' in finding_types:
            recommendations.append("مراجعة وتحسين إجراءات التحقق من دقة البيانات المالية")
        
        if 'documentation' in finding_types:
            recommendations.append("تعزيز إجراءات التوثيق والاحتفاظ بالمستندات الداعمة")
        
        if 'internal_control' in finding_types:
            recommendations.append("تقييم وتحسين نظام الرقابة الداخلية")
        
        # Add general recommendation
        recommendations.append("إجراء تدقيق دوري للتأكد من استمرارية الامتثال")
        
        return recommendations
    
    def _generate_conclusion_ar(self, risk_rating: str, compliance_score: int) -> str:
        """توليد الخلاصة"""
        if compliance_score >= 90:
            opinion = "رأي غير متحفظ - المنشأة تلتزم بشكل جيد بالمتطلبات التنظيمية"
        elif compliance_score >= 70:
            opinion = "رأي متحفظ - يوجد بعض الملاحظات التي تتطلب معالجة"
        else:
            opinion = "رأي سلبي - يوجد ملاحظات جوهرية تتطلب معالجة فورية"
        
        return f"""
الخلاصة

بناءً على إجراءات التدقيق المنفذة والأدلة التي تم الحصول عليها، فإن رأينا هو:

{opinion}

مستوى المخاطر: {risk_rating}
درجة الامتثال: {compliance_score}%

ننصح الإدارة بمراجعة الملاحظات الواردة في هذا التقرير واتخاذ الإجراءات التصحيحية اللازمة.
"""


# Singleton instances
zatca_service = ZATCAValidationService()
vat_service = VATReconciliationService()
zakat_service = ZakatCalculationService()
arabic_report_service = ArabicReportService()
