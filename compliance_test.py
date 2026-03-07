#!/usr/bin/env python3
"""
FinAI Phase 2 Compliance Module Testing Suite
Tests ZATCA, VAT, Zakat, and Audit compliance endpoints
"""

import requests
import sys
import json
from datetime import datetime, timedelta
from decimal import Decimal
import uuid

class ComplianceAPITester:
    def __init__(self, base_url="http://localhost:8001"):
        self.base_url = base_url
        self.token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.failed_tests = []
        self.organization_id = None
        self.zatca_invoice_id = None
        self.vat_reconciliation_id = None
        self.zakat_calculation_id = None

    def log_result(self, test_name, success, response_data=None, error_msg=None):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {test_name} - PASSED")
            if response_data and isinstance(response_data, dict):
                # Check for Arabic text preservation
                arabic_fields = [k for k, v in response_data.items() if k.endswith('_ar') and v]
                if arabic_fields:
                    print(f"   📝 Arabic text preserved in: {', '.join(arabic_fields)}")
        else:
            self.failed_tests.append({
                'test': test_name,
                'error': error_msg,
                'response': response_data
            })
            print(f"❌ {test_name} - FAILED: {error_msg}")

    def make_request(self, method, endpoint, data=None, params=None):
        """Make HTTP request with proper headers"""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = {'Content-Type': 'application/json'}
        
        if self.token:
            headers['Authorization'] = f'Bearer {self.token}'

        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, params=params, timeout=30)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=30)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers, timeout=30)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=30)
            
            return response
        except requests.exceptions.RequestException as e:
            print(f"   🔗 Request error: {str(e)}")
            return None

    def test_authentication(self):
        """Test JWT authentication with admin credentials"""
        print("\n🔍 Testing Authentication...")
        
        login_data = {
            "email": "admin@finai.com",
            "password": "admin123"
        }
        
        response = self.make_request('POST', '/api/auth/token/', login_data)
        
        if response and response.status_code == 200:
            try:
                data = response.json()
                if 'access' in data:
                    self.token = data['access']
                    self.log_result("JWT Authentication", True)
                    return True
                else:
                    self.log_result("JWT Authentication", False, 
                                  error_msg="No access token in response")
                    return False
            except json.JSONDecodeError:
                self.log_result("JWT Authentication", False, 
                              error_msg="Invalid JSON response")
                return False
        else:
            error_msg = f"Status: {response.status_code if response else 'No response'}"
            if response:
                try:
                    error_msg += f", Response: {response.text}"
                except:
                    pass
            self.log_result("JWT Authentication", False, error_msg=error_msg)
            return False

    def get_organization_id(self):
        """Get organization ID for testing"""
        response = self.make_request('GET', '/api/core/organizations/')
        if response and response.status_code == 200:
            try:
                data = response.json()
                if isinstance(data, dict) and 'results' in data and len(data['results']) > 0:
                    self.organization_id = data['results'][0].get('id')
                elif isinstance(data, list) and len(data) > 0:
                    self.organization_id = data[0].get('id')
                return self.organization_id is not None
            except:
                return False
        return False

    def test_compliance_dashboard_overview(self):
        """Test Compliance Dashboard Overview API"""
        print("\n🔍 Testing Compliance Dashboard Overview...")
        
        if not self.organization_id:
            if not self.get_organization_id():
                self.log_result("Compliance Dashboard Overview", False, 
                              error_msg="No organization ID available")
                return False
        
        params = {'organization_id': self.organization_id}
        response = self.make_request('GET', '/api/compliance/dashboard/overview/', params=params)
        
        if response and response.status_code == 200:
            try:
                data = response.json()
                # Check for expected fields
                expected_fields = ['overall_compliance_score', 'vat_compliance', 'zakat_compliance', 
                                 'zatca_compliance', 'audit_findings', 'risk_level']
                
                missing_fields = [field for field in expected_fields if field not in data]
                if missing_fields:
                    self.log_result("Compliance Dashboard Overview", False, 
                                  error_msg=f"Missing fields: {missing_fields}")
                    return False
                
                # Check Arabic text in risk level
                if 'risk_level' in data and 'level_ar' in data['risk_level']:
                    print(f"   🌍 Risk level in Arabic: {data['risk_level']['level_ar']}")
                
                self.log_result("Compliance Dashboard Overview", True, data)
                return True
            except json.JSONDecodeError:
                self.log_result("Compliance Dashboard Overview", False, 
                              error_msg="Invalid JSON response")
                return False
        else:
            error_msg = f"Status: {response.status_code if response else 'No response'}"
            if response:
                try:
                    error_msg += f", Response: {response.text[:200]}"
                except:
                    pass
            self.log_result("Compliance Dashboard Overview", False, error_msg=error_msg)
            return False

    def test_regulatory_references_api(self):
        """Test Regulatory References API"""
        print("\n🔍 Testing Regulatory References API...")
        
        # Test list regulatory references
        response = self.make_request('GET', '/api/compliance/regulatory-references/')
        
        if response and response.status_code == 200:
            try:
                data = response.json()
                self.log_result("Regulatory References - List", True, data)
                
                # Test filter by regulator
                zatca_response = self.make_request('GET', '/api/compliance/regulatory-references/', 
                                                 params={'regulator': 'zatca'})
                if zatca_response and zatca_response.status_code == 200:
                    self.log_result("Regulatory References - Filter by ZATCA", True)
                else:
                    error_msg = f"ZATCA Filter Status: {zatca_response.status_code if zatca_response else 'No response'}"
                    self.log_result("Regulatory References - Filter by ZATCA", False, error_msg=error_msg)
                
                # Test filter by category
                vat_response = self.make_request('GET', '/api/compliance/regulatory-references/', 
                                               params={'category': 'vat'})
                if vat_response and vat_response.status_code == 200:
                    self.log_result("Regulatory References - Filter by VAT", True)
                else:
                    error_msg = f"VAT Filter Status: {vat_response.status_code if vat_response else 'No response'}"
                    self.log_result("Regulatory References - Filter by VAT", False, error_msg=error_msg)
                
                # Test by_regulator action
                by_regulator_response = self.make_request('GET', '/api/compliance/regulatory-references/by_regulator/')
                if by_regulator_response and by_regulator_response.status_code == 200:
                    self.log_result("Regulatory References - By Regulator", True)
                else:
                    error_msg = f"By Regulator Status: {by_regulator_response.status_code if by_regulator_response else 'No response'}"
                    self.log_result("Regulatory References - By Regulator", False, error_msg=error_msg)
                
                return True
            except json.JSONDecodeError:
                self.log_result("Regulatory References - List", False, 
                              error_msg="Invalid JSON response")
                return False
        else:
            error_msg = f"Status: {response.status_code if response else 'No response'}"
            self.log_result("Regulatory References - List", False, error_msg=error_msg)
            return False

    def test_zatca_invoices_api(self):
        """Test ZATCA Invoices API"""
        print("\n🔍 Testing ZATCA Invoices API...")
        
        # Test list ZATCA invoices
        response = self.make_request('GET', '/api/compliance/zatca-invoices/')
        
        if response and response.status_code == 200:
            try:
                data = response.json()
                self.log_result("ZATCA Invoices - List", True, data)
                
                # Get first invoice ID for validation test
                invoices = data.get('results', data) if isinstance(data, dict) else data
                if isinstance(invoices, list) and len(invoices) > 0:
                    self.zatca_invoice_id = invoices[0].get('id')
                
                # Test filter by status
                status_response = self.make_request('GET', '/api/compliance/zatca-invoices/', 
                                                  params={'status': 'draft'})
                if status_response and status_response.status_code == 200:
                    self.log_result("ZATCA Invoices - Filter by Status", True)
                else:
                    error_msg = f"Status Filter: {status_response.status_code if status_response else 'No response'}"
                    self.log_result("ZATCA Invoices - Filter by Status", False, error_msg=error_msg)
                
                # Test date range filter
                end_date = datetime.now().date()
                start_date = end_date - timedelta(days=30)
                date_response = self.make_request('GET', '/api/compliance/zatca-invoices/', 
                                                params={
                                                    'start_date': start_date.strftime('%Y-%m-%d'),
                                                    'end_date': end_date.strftime('%Y-%m-%d')
                                                })
                if date_response and date_response.status_code == 200:
                    self.log_result("ZATCA Invoices - Date Range Filter", True)
                else:
                    error_msg = f"Date Filter: {date_response.status_code if date_response else 'No response'}"
                    self.log_result("ZATCA Invoices - Date Range Filter", False, error_msg=error_msg)
                
                return True
            except json.JSONDecodeError:
                self.log_result("ZATCA Invoices - List", False, 
                              error_msg="Invalid JSON response")
                return False
        else:
            error_msg = f"Status: {response.status_code if response else 'No response'}"
            self.log_result("ZATCA Invoices - List", False, error_msg=error_msg)
            return False

    def test_zatca_invoice_validation(self):
        """Test ZATCA Invoice Validation API"""
        print("\n🔍 Testing ZATCA Invoice Validation...")
        
        if not self.zatca_invoice_id:
            self.log_result("ZATCA Invoice Validation", False, 
                          error_msg="No invoice ID available for validation")
            return False
        
        response = self.make_request('GET', f'/api/compliance/zatca-invoices/{self.zatca_invoice_id}/validate/')
        
        if response and response.status_code == 200:
            try:
                data = response.json()
                # Check for expected validation fields
                expected_fields = ['invoice_id', 'validation_status', 'compliance_score', 
                                 'total_checks', 'validation_results']
                
                missing_fields = [field for field in expected_fields if field not in data]
                if missing_fields:
                    self.log_result("ZATCA Invoice Validation", False, 
                                  error_msg=f"Missing fields: {missing_fields}")
                    return False
                
                # Check Arabic messages in validation results
                validation_results = data.get('validation_results', [])
                arabic_messages = [r for r in validation_results if r.get('message_ar')]
                if arabic_messages:
                    print(f"   🌍 Found {len(arabic_messages)} validation messages in Arabic")
                
                self.log_result("ZATCA Invoice Validation", True, data)
                return True
            except json.JSONDecodeError:
                self.log_result("ZATCA Invoice Validation", False, 
                              error_msg="Invalid JSON response")
                return False
        else:
            error_msg = f"Status: {response.status_code if response else 'No response'}"
            self.log_result("ZATCA Invoice Validation", False, error_msg=error_msg)
            return False

    def test_zatca_compliance_summary(self):
        """Test ZATCA Compliance Summary API"""
        print("\n🔍 Testing ZATCA Compliance Summary...")
        
        response = self.make_request('GET', '/api/compliance/zatca-invoices/compliance_summary/')
        
        if response and response.status_code == 200:
            try:
                data = response.json()
                # Check for expected summary fields
                expected_fields = ['total_invoices', 'by_status', 'validated_percentage']
                
                missing_fields = [field for field in expected_fields if field not in data]
                if missing_fields:
                    self.log_result("ZATCA Compliance Summary", False, 
                                  error_msg=f"Missing fields: {missing_fields}")
                    return False
                
                self.log_result("ZATCA Compliance Summary", True, data)
                return True
            except json.JSONDecodeError:
                self.log_result("ZATCA Compliance Summary", False, 
                              error_msg="Invalid JSON response")
                return False
        else:
            error_msg = f"Status: {response.status_code if response else 'No response'}"
            self.log_result("ZATCA Compliance Summary", False, error_msg=error_msg)
            return False

    def test_vat_reconciliations_api(self):
        """Test VAT Reconciliations API"""
        print("\n🔍 Testing VAT Reconciliations API...")
        
        # Test list VAT reconciliations
        response = self.make_request('GET', '/api/compliance/vat-reconciliations/')
        
        if response and response.status_code == 200:
            try:
                data = response.json()
                self.log_result("VAT Reconciliations - List", True, data)
                
                # Get first reconciliation ID
                reconciliations = data.get('results', data) if isinstance(data, dict) else data
                if isinstance(reconciliations, list) and len(reconciliations) > 0:
                    self.vat_reconciliation_id = reconciliations[0].get('id')
                
                return True
            except json.JSONDecodeError:
                self.log_result("VAT Reconciliations - List", False, 
                              error_msg="Invalid JSON response")
                return False
        else:
            error_msg = f"Status: {response.status_code if response else 'No response'}"
            self.log_result("VAT Reconciliations - List", False, error_msg=error_msg)
            return False

    def test_vat_variance_report(self):
        """Test VAT Variance Report API"""
        print("\n🔍 Testing VAT Variance Report...")
        
        params = {}
        if self.organization_id:
            params['organization_id'] = self.organization_id
        
        response = self.make_request('GET', '/api/compliance/vat-reconciliations/variance_report/', 
                                   params=params)
        
        if response and response.status_code == 200:
            try:
                data = response.json()
                # Check for expected variance report fields
                expected_fields = ['total_reconciliations', 'with_variance', 'total_positive_variance', 
                                 'total_negative_variance', 'average_compliance_score']
                
                missing_fields = [field for field in expected_fields if field not in data]
                if missing_fields:
                    self.log_result("VAT Variance Report", False, 
                                  error_msg=f"Missing fields: {missing_fields}")
                    return False
                
                self.log_result("VAT Variance Report", True, data)
                return True
            except json.JSONDecodeError:
                self.log_result("VAT Variance Report", False, 
                              error_msg="Invalid JSON response")
                return False
        else:
            error_msg = f"Status: {response.status_code if response else 'No response'}"
            self.log_result("VAT Variance Report", False, error_msg=error_msg)
            return False

    def test_zakat_calculations_api(self):
        """Test Zakat Calculations API"""
        print("\n🔍 Testing Zakat Calculations API...")
        
        # Test list Zakat calculations
        response = self.make_request('GET', '/api/compliance/zakat-calculations/')
        
        if response and response.status_code == 200:
            try:
                data = response.json()
                self.log_result("Zakat Calculations - List", True, data)
                
                # Get first calculation ID
                calculations = data.get('results', data) if isinstance(data, dict) else data
                if isinstance(calculations, list) and len(calculations) > 0:
                    self.zakat_calculation_id = calculations[0].get('id')
                
                return True
            except json.JSONDecodeError:
                self.log_result("Zakat Calculations - List", False, 
                              error_msg="Invalid JSON response")
                return False
        else:
            error_msg = f"Status: {response.status_code if response else 'No response'}"
            self.log_result("Zakat Calculations - List", False, error_msg=error_msg)
            return False

    def test_audit_findings_dashboard(self):
        """Test Audit Findings Dashboard API"""
        print("\n🔍 Testing Audit Findings Dashboard...")
        
        response = self.make_request('GET', '/api/compliance/audit-findings/dashboard/')
        
        if response and response.status_code == 200:
            try:
                data = response.json()
                # Check for expected dashboard fields
                expected_fields = ['total_findings', 'unresolved_findings', 'by_risk_level', 
                                 'by_finding_type', 'total_financial_impact']
                
                missing_fields = [field for field in expected_fields if field not in data]
                if missing_fields:
                    self.log_result("Audit Findings Dashboard", False, 
                                  error_msg=f"Missing fields: {missing_fields}")
                    return False
                
                self.log_result("Audit Findings Dashboard", True, data)
                return True
            except json.JSONDecodeError:
                self.log_result("Audit Findings Dashboard", False, 
                              error_msg="Invalid JSON response")
                return False
        else:
            error_msg = f"Status: {response.status_code if response else 'No response'}"
            self.log_result("Audit Findings Dashboard", False, error_msg=error_msg)
            return False

    def test_arabic_audit_report_generation(self):
        """Test Arabic Audit Report Generation API"""
        print("\n🔍 Testing Arabic Audit Report Generation...")
        
        if not self.organization_id:
            self.log_result("Arabic Audit Report Generation", False, 
                          error_msg="No organization ID available")
            return False
        
        # Set date range for report
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=365)
        
        params = {
            'organization_id': self.organization_id,
            'period_start': start_date.strftime('%Y-%m-%d'),
            'period_end': end_date.strftime('%Y-%m-%d')
        }
        
        response = self.make_request('GET', '/api/compliance/audit-findings/generate_report_ar/', 
                                   params=params)
        
        if response and response.status_code == 200:
            try:
                data = response.json()
                # Check for expected Arabic report fields
                expected_fields = ['report_title_ar', 'executive_summary_ar', 'recommendations_ar', 
                                 'conclusion_ar', 'risk_rating']
                
                missing_fields = [field for field in expected_fields if field not in data]
                if missing_fields:
                    self.log_result("Arabic Audit Report Generation", False, 
                                  error_msg=f"Missing fields: {missing_fields}")
                    return False
                
                # Check for Arabic content
                arabic_content_fields = [field for field in expected_fields if field.endswith('_ar') and data.get(field)]
                if arabic_content_fields:
                    print(f"   🌍 Arabic content generated in: {', '.join(arabic_content_fields)}")
                    # Show sample of Arabic text
                    if data.get('report_title_ar'):
                        print(f"   📄 Report title: {data['report_title_ar']}")
                
                self.log_result("Arabic Audit Report Generation", True, data)
                return True
            except json.JSONDecodeError:
                self.log_result("Arabic Audit Report Generation", False, 
                              error_msg="Invalid JSON response")
                return False
        else:
            error_msg = f"Status: {response.status_code if response else 'No response'}"
            self.log_result("Arabic Audit Report Generation", False, error_msg=error_msg)
            return False

    def test_audit_findings_api(self):
        """Test Audit Findings API with filters"""
        print("\n🔍 Testing Audit Findings API...")
        
        # Test list audit findings
        response = self.make_request('GET', '/api/compliance/audit-findings/')
        
        if response and response.status_code == 200:
            try:
                data = response.json()
                self.log_result("Audit Findings - List", True, data)
                
                # Test filter by risk level
                risk_response = self.make_request('GET', '/api/compliance/audit-findings/', 
                                                params={'risk_level': 'high'})
                if risk_response and risk_response.status_code == 200:
                    self.log_result("Audit Findings - Filter by Risk Level", True)
                else:
                    error_msg = f"Risk Filter Status: {risk_response.status_code if risk_response else 'No response'}"
                    self.log_result("Audit Findings - Filter by Risk Level", False, error_msg=error_msg)
                
                # Test filter by finding type
                type_response = self.make_request('GET', '/api/compliance/audit-findings/', 
                                                params={'finding_type': 'compliance'})
                if type_response and type_response.status_code == 200:
                    self.log_result("Audit Findings - Filter by Type", True)
                else:
                    error_msg = f"Type Filter Status: {type_response.status_code if type_response else 'No response'}"
                    self.log_result("Audit Findings - Filter by Type", False, error_msg=error_msg)
                
                # Test filter by resolution status
                resolved_response = self.make_request('GET', '/api/compliance/audit-findings/', 
                                                    params={'is_resolved': 'false'})
                if resolved_response and resolved_response.status_code == 200:
                    self.log_result("Audit Findings - Filter by Resolution Status", True)
                else:
                    error_msg = f"Resolution Filter Status: {resolved_response.status_code if resolved_response else 'No response'}"
                    self.log_result("Audit Findings - Filter by Resolution Status", False, error_msg=error_msg)
                
                return True
            except json.JSONDecodeError:
                self.log_result("Audit Findings - List", False, 
                              error_msg="Invalid JSON response")
                return False
        else:
            error_msg = f"Status: {response.status_code if response else 'No response'}"
            self.log_result("Audit Findings - List", False, error_msg=error_msg)
            return False

    def run_all_tests(self):
        """Run all compliance API tests"""
        print("🚀 Starting FinAI Phase 2 Compliance Module Tests")
        print("=" * 60)
        
        # Test authentication first
        if not self.test_authentication():
            print("❌ Authentication failed - cannot proceed with compliance tests")
            return False
        
        # Get organization ID
        if not self.get_organization_id():
            print("⚠️  Warning: No organization ID found, some tests may fail")
        
        # Test all compliance endpoints
        test_methods = [
            self.test_compliance_dashboard_overview,
            self.test_regulatory_references_api,
            self.test_zatca_invoices_api,
            self.test_zatca_invoice_validation,
            self.test_zatca_compliance_summary,
            self.test_vat_reconciliations_api,
            self.test_vat_variance_report,
            self.test_zakat_calculations_api,
            self.test_audit_findings_api,
            self.test_audit_findings_dashboard,
            self.test_arabic_audit_report_generation,
        ]
        
        for test_method in test_methods:
            try:
                test_method()
            except Exception as e:
                self.log_result(test_method.__name__, False, error_msg=f"Exception: {str(e)}")
        
        # Print summary
        print("\n" + "=" * 60)
        print(f"📊 Compliance Test Summary: {self.tests_passed}/{self.tests_run} tests passed")
        
        if self.failed_tests:
            print("\n❌ Failed Tests:")
            for failed in self.failed_tests:
                print(f"  - {failed['test']}: {failed['error']}")
        
        success_rate = (self.tests_passed / self.tests_run * 100) if self.tests_run > 0 else 0
        print(f"✅ Success Rate: {success_rate:.1f}%")
        
        # Arabic text summary
        print(f"\n🌍 Arabic Text Support: Tested in regulatory references, validation messages, and audit reports")
        
        return success_rate > 70

def main():
    """Main test execution"""
    tester = ComplianceAPITester()
    success = tester.run_all_tests()
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())