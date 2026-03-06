"""
Compliance Checks & Audit Findings Service - Phase 3
خدمة الفحوصات الامتثالية والنتائج التدقيقية

Performs compliance checks on invoice data and generates audit findings with risk scoring.

Checks:
- Missing tax information
- Invoice total mismatch
- Suspicious discounts
- Invalid or suspicious dates
- Duplicate risk
- Vendor legitimacy

Risk Scoring:
- Low (0-25)
- Medium (26-50)
- High (51-75)
- Critical (76-100)
"""

import logging
from decimal import Decimal
from typing import Dict, List, Tuple, Any
from datetime import datetime
import json

logger = logging.getLogger(__name__)


class ComplianceCheckService:
    """Service for performing compliance checks and generating audit findings"""
    
    # Risk thresholds
    RISK_LEVELS = {
        'low': (0, 25),
        'medium': (26, 50),
        'high': (51, 75),
        'critical': (76, 100),
    }
    
    # Suspicious discount threshold (%)
    SUSPICIOUS_DISCOUNT_THRESHOLD = 20.0
    
    # Large invoice threshold (SAR)
    LARGE_INVOICE_THRESHOLD = Decimal('100000')
    
    # Very large invoice threshold (SAR)
    VERY_LARGE_INVOICE_THRESHOLD = Decimal('1000000')
    
    @staticmethod
    def perform_compliance_checks(normalized_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform all compliance checks on invoice data
        
        Args:
            normalized_data: Normalized invoice data
        
        Returns:
            Dictionary containing compliance check results
        """
        checks = {
            'tax_information': ComplianceCheckService._check_tax_information(normalized_data),
            'total_mismatch': ComplianceCheckService._check_total_mismatch(normalized_data),
            'suspicious_discount': ComplianceCheckService._check_suspicious_discount(normalized_data),
            'date_validity': ComplianceCheckService._check_date_validity(normalized_data),
            'large_amount': ComplianceCheckService._check_large_amount(normalized_data),
            'vendor_legitimacy': ComplianceCheckService._check_vendor_legitimacy(normalized_data),
        }
        
        return checks
    
    @staticmethod
    def _check_tax_information(data: Dict[str, Any]) -> Dict[str, Any]:
        """Check if tax information is present and valid"""
        check = {
            'check_name': 'Tax Information',
            'passed': True,
            'findings': [],
            'risk_score': 0,
        }
        
        # Check for tax number
        if data.get('vendor_tax_id') or data.get('customer_tax_id'):
            check['findings'].append("Tax IDs present جود معرفات ضريبية")
            check['risk_score'] = 0
        else:
            check['findings'].append("No tax IDs found - may indicate informal vendor")
            check['risk_score'] = 10
        
        # Check for tax amount
        if data.get('tax_amount'):
            check['findings'].append(f"Tax amount declared: {data['tax_amount']}")
            check['risk_score'] = 0
        else:
            check['passed'] = False
            check['findings'].append("No tax amount declared - may be tax-exempt or informal")
            check['risk_score'] = 20
        
        return check
    
    @staticmethod
    def _check_total_mismatch(data: Dict[str, Any]) -> Dict[str, Any]:
        """Check if totals are consistent"""
        check = {
            'check_name': 'Total Mismatch',
            'passed': True,
            'findings': [],
            'risk_score': 0,
        }
        
        total = data.get('total_amount')
        items = data.get('items', [])
        
        if not items:
            check['findings'].append("No line items to verify")
            return check
        
        items_total = Decimal('0')
        for item in items:
            if item.get('line_total'):
                items_total += item['line_total']
        
        if total and items_total:
            difference = abs(total - items_total)
            
            # Allow 1% margin for rounding
            if difference <= (items_total * Decimal('0.01')):
                check['findings'].append(f"Total matches items sum: {items_total}")
                check['risk_score'] = 0
                check['passed'] = True
            else:
                check['findings'].append(
                    f"Significant mismatch: Items {items_total} vs Total {total} "
                    f"(Difference: {difference})"
                )
                check['risk_score'] = 30
                check['passed'] = False
        
        return check
    
    @staticmethod
    def _check_suspicious_discount(data: Dict[str, Any]) -> Dict[str, Any]:
        """Check for suspicious discounts"""
        check = {
            'check_name': 'Suspicious Discount',
            'passed': True,
            'findings': [],
            'risk_score': 0,
        }
        
        discount = data.get('discount_amount')
        subtotal = data.get('subtotal')
        items_total = Decimal('0')
        
        for item in data.get('items', []):
            if item.get('line_total'):
                items_total += item['line_total']
        
        if not discount:
            check['findings'].append("No discount applied")
            return check
        
        # Calculate discount percentage
        base = subtotal or items_total
        if base:
            discount_pct = (discount / base) * 100
            
            if discount_pct > ComplianceCheckService.SUSPICIOUS_DISCOUNT_THRESHOLD:
                check['findings'].append(
                    f"High discount detected: {discount_pct:.1f}% "
                    f"({discount} on {base})"
                )
                check['risk_score'] = 35
                check['passed'] = False
            else:
                check['findings'].append(f"Discount amount: {discount_pct:.1f}%")
                check['risk_score'] = 5
        
        return check
    
    @staticmethod
    def _check_date_validity(data: Dict[str, Any]) -> Dict[str, Any]:
        """Check date validity and reasonableness"""
        check = {
            'check_name': 'Date Validity',
            'passed': True,
            'findings': [],
            'risk_score': 0,
        }
        
        today = datetime.now()
        
        issue_date_str = data.get('issue_date')
        if issue_date_str:
            try:
                issue_date = datetime.strptime(issue_date_str, '%Y-%m-%d')
                
                # Check if issue date is in future
                if issue_date > today:
                    check['findings'].append(f"Issue date is in future: {issue_date_str}")
                    check['risk_score'] = 25
                
                # Check if invoice is very old (> 1 year)
                days_old = (today - issue_date).days
                if days_old > 365:
                    check['findings'].append(
                        f"Invoice is very old ({days_old} days): {issue_date_str}"
                    )
                    check['risk_score'] = 20
            except ValueError:
                check['findings'].append("Could not parse issue date")
                check['risk_score'] = 10
        
        due_date_str = data.get('due_date')
        if due_date_str and issue_date_str:
            try:
                due_date = datetime.strptime(due_date_str, '%Y-%m-%d')
                issue_date = datetime.strptime(issue_date_str, '%Y-%m-%d')
                
                days_to_pay = (due_date - issue_date).days
                
                # Reasonable payment terms are 0-120 days
                if days_to_pay < 0:
                    check['findings'].append("Due date is before issue date")
                    check['risk_score'] = 40
                    check['passed'] = False
                elif days_to_pay > 180:
                    check['findings'].append(
                        f"Unusually long payment terms: {days_to_pay} days"
                    )
                    check['risk_score'] = 15
                else:
                    check['findings'].append(
                        f"Normal payment terms: {days_to_pay} days"
                    )
            except ValueError:
                check['findings'].append("Could not parse due date")
        
        return check
    
    @staticmethod
    def _check_large_amount(data: Dict[str, Any]) -> Dict[str, Any]:
        """Check for unusually large amounts"""
        check = {
            'check_name': 'Large Amount',
            'passed': True,
            'findings': [],
            'risk_score': 0,
        }
        
        total = data.get('total_amount')
        if not total:
            return check
        
        if total > ComplianceCheckService.VERY_LARGE_INVOICE_THRESHOLD:
            check['findings'].append(
                f"Very large invoice: {total} (requires additional review)"
            )
            check['risk_score'] = 15
        elif total > ComplianceCheckService.LARGE_INVOICE_THRESHOLD:
            check['findings'].append(f"Large invoice: {total}")
            check['risk_score'] = 5
        else:
            check['findings'].append(f"Normal amount: {total}")
        
        return check
    
    @staticmethod
    def _check_vendor_legitimacy(data: Dict[str, Any]) -> Dict[str, Any]:
        """Check vendor information for legitimacy"""
        check = {
            'check_name': 'Vendor Legitimacy',
            'passed': True,
            'findings': [],
            'risk_score': 0,
        }
        
        vendor = data.get('vendor_name', '').lower()
        
        # Check for suspicious patterns
        if not vendor:
            check['findings'].append("No vendor name provided")
            check['risk_score'] = 30
            check['passed'] = False
            return check
        
        # Check for very short vendor names (suspicious)
        if len(vendor.strip()) < 3:
            check['findings'].append(f"Suspiciously short vendor name: {vendor}")
            check['risk_score'] = 20
        
        # Check for generic vendor names
        suspicious_names = ['shop', 'store', 'company', 'business', 'trader', 'service']
        if any(name in vendor for name in suspicious_names):
            check['findings'].append(f"Generic vendor name: {vendor}")
            check['risk_score'] = 10
        else:
            check['findings'].append(f"Vendor: {vendor}")
        
        return check
    
    @staticmethod
    def calculate_overall_risk_score(compliance_checks: Dict[str, Any]) -> int:
        """Calculate overall risk score from all compliance checks"""
        total_score = 0
        check_count = len(compliance_checks)
        
        for check_name, check_data in compliance_checks.items():
            total_score += check_data.get('risk_score', 0)
        
        # Average risk across all checks
        overall_score = int(total_score / check_count) if check_count > 0 else 0
        
        # Cap at 100
        return min(100, overall_score)
    
    @staticmethod
    def get_risk_level(risk_score: int) -> str:
        """Convert risk score to risk level"""
        for level, (min_score, max_score) in ComplianceCheckService.RISK_LEVELS.items():
            if min_score <= risk_score <= max_score:
                return level
        return 'critical'
    
    @staticmethod
    def generate_audit_findings(normalized_data: Dict[str, Any], 
                                 compliance_checks: Dict[str, Any],
                                 risk_score: int) -> Dict[str, Any]:
        """
        Generate structured audit findings and summary
        
        Args:
            normalized_data: Normalized invoice data
            compliance_checks: Results of compliance checks
            risk_score: Overall risk score
        
        Returns:
            Dictionary with audit findings and summary
        """
        risk_level = ComplianceCheckService.get_risk_level(risk_score)
        
        # Build key findings
        key_findings = []
        for check_name, check_data in compliance_checks.items():
            if not check_data.get('passed'):
                key_findings.extend(check_data.get('findings', []))
        
        # Generate audit summary
        executive_summary = ComplianceCheckService._generate_executive_summary(
            normalized_data, risk_level, key_findings
        )
        
        recommended_actions = ComplianceCheckService._generate_recommendations(
            risk_level, compliance_checks, normalized_data
        )
        
        return {
            'executive_summary': executive_summary,
            'key_findings': key_findings,
            'risk_level': risk_level,
            'risk_score': risk_score,
            'recommended_actions': recommended_actions,
            'audit_status': 'completed',
            'compliance_checks': compliance_checks,
        }
    
    @staticmethod
    def _generate_executive_summary(data: Dict[str, Any], 
                                     risk_level: str,
                                     findings: List[str]) -> str:
        """Generate executive summary of audit"""
        summary = (
            f"Invoice #{data.get('invoice_number', 'N/A')} from "
            f"{data.get('vendor_name', 'Unknown')} "
            f"for {data.get('total_amount', 'N/A')} {data.get('currency', 'SAR')} "
            f"has been classified as {risk_level.upper()} risk. "
        )
        
        if findings:
            summary += f"Primary issues: {'; '.join(findings[:3])}"
        else:
            summary += "All compliance checks passed."
        
        return summary
    
    @staticmethod
    def _generate_recommendations(risk_level: str,
                                   compliance_checks: Dict[str, Any],
                                   data: Dict[str, Any]) -> List[str]:
        """Generate recommended actions based on risk level"""
        recommendations = []
        
        if risk_level == 'critical':
            recommendations.append("🔴 REJECT: Manual review required before processing")
            recommendations.append("🔴 Escalate to compliance officer immediately")
        
        elif risk_level == 'high':
            recommendations.append("🟠 FLAG: Review before processing")
            recommendations.append("🟠 Request supporting documents from vendor")
        
        elif risk_level == 'medium':
            recommendations.append("🟡 CAUTION: Review additional details if needed")
        
        else:
            recommendations.append("🟢 APPROVE: Normal processing")
        
        # Specific recommendations
        tax_check = compliance_checks.get('tax_information', {})
        if not tax_check.get('passed'):
            recommendations.append("Request tax ID verification from vendor")
        
        total_check = compliance_checks.get('total_mismatch', {})
        if not total_check.get('passed'):
            recommendations.append("Verify invoice calculations with vendor")
        
        discount_check = compliance_checks.get('suspicious_discount', {})
        if not discount_check.get('passed'):
            recommendations.append("Explain discount terms with vendor")
        
        return recommendations


def get_compliance_service() -> ComplianceCheckService:
    """Get compliance check service (stateless, can be instantiated fresh)"""
    return ComplianceCheckService()
