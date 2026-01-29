#!/usr/bin/env python3
"""
Hard Rules Engine Backend Testing Suite
Tests all Hard Rules Engine API endpoints for deterministic rule validation
"""

import requests
import sys
import json
import uuid
from datetime import datetime, timedelta
from decimal import Decimal

class HardRulesEngineAPITester:
    def __init__(self, base_url="http://localhost:8001"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.failed_tests = []
        
        print("🔧 Hard Rules Engine API Testing Suite")
        print(f"📡 Base URL: {self.base_url}")
        print("=" * 60)

    def log_result(self, test_name, success, response_data=None, error_msg=None):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {test_name}")
        else:
            self.failed_tests.append({
                'test': test_name,
                'error': error_msg,
                'response': response_data
            })
            print(f"❌ {test_name} - FAILED: {error_msg}")

    def make_request(self, method, endpoint, data=None, params=None):
        """Make HTTP request"""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = {'Content-Type': 'application/json'}

        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, params=params, timeout=30)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=30)
            
            return response
        except requests.exceptions.RequestException as e:
            return None

    def test_governance_status(self):
        """Test GET /api/hard-rules/governance/status/"""
        print("\n🏛️  Testing Governance Status...")
        
        response = self.make_request('GET', '/api/hard-rules/governance/status/')
        
        if not response:
            self.log_result("Governance Status - Connection", False, error_msg="Connection failed")
            return
        
        if response.status_code != 200:
            self.log_result("Governance Status - Status Code", False, 
                          error_msg=f"Expected 200, got {response.status_code}")
            return
        
        try:
            data = response.json()
            
            # Check required fields
            required_fields = ['system_status', 'message', 'hard_rules_engine', 'enforcement_summary']
            for field in required_fields:
                if field not in data:
                    self.log_result(f"Governance Status - {field} field", False, 
                                  error_msg=f"Missing field: {field}")
                    return
            
            # Check system is operational
            if data['system_status'] != 'OPERATIONAL':
                self.log_result("Governance Status - System Operational", False,
                              error_msg=f"System status: {data['system_status']}")
                return
            
            # Check engine details
            engine = data['hard_rules_engine']
            if not engine.get('engine_present'):
                self.log_result("Governance Status - Engine Present", False,
                              error_msg="Engine not present")
                return
            
            # Check rule count
            rules_count = len(engine.get('rules_enforced', []))
            if rules_count != 20:
                self.log_result("Governance Status - Rules Count", False,
                              error_msg=f"Expected 20 rules, got {rules_count}")
                return
            
            self.log_result("Governance Status - Complete", True)
            
        except json.JSONDecodeError:
            self.log_result("Governance Status - JSON Parse", False, error_msg="Invalid JSON response")

    def test_rule_enforcement_summary(self):
        """Test GET /api/hard-rules/governance/rules/"""
        print("\n📋 Testing Rule Enforcement Summary...")
        
        response = self.make_request('GET', '/api/hard-rules/governance/rules/')
        
        if not response:
            self.log_result("Rule Enforcement - Connection", False, error_msg="Connection failed")
            return
        
        if response.status_code != 200:
            self.log_result("Rule Enforcement - Status Code", False,
                          error_msg=f"Expected 200, got {response.status_code}")
            return
        
        try:
            data = response.json()
            
            # Check categories
            expected_categories = ['accounting', 'invoice', 'vat', 'compliance', 'ocr', 'security']
            categories = data.get('categories', {})
            
            for category in expected_categories:
                if category not in categories:
                    self.log_result(f"Rule Enforcement - {category} category", False,
                                  error_msg=f"Missing category: {category}")
                    return
            
            # Check enforcement type
            if data.get('enforcement_type') != 'DETERMINISTIC':
                self.log_result("Rule Enforcement - Deterministic", False,
                              error_msg=f"Expected DETERMINISTIC, got {data.get('enforcement_type')}")
                return
            
            self.log_result("Rule Enforcement Summary - Complete", True)
            
        except json.JSONDecodeError:
            self.log_result("Rule Enforcement - JSON Parse", False, error_msg="Invalid JSON response")

    def test_engine_health(self):
        """Test GET /api/hard-rules/governance/health/"""
        print("\n🏥 Testing Engine Health...")
        
        response = self.make_request('GET', '/api/hard-rules/governance/health/')
        
        if not response:
            self.log_result("Engine Health - Connection", False, error_msg="Connection failed")
            return
        
        if response.status_code != 200:
            self.log_result("Engine Health - Status Code", False,
                          error_msg=f"Expected 200, got {response.status_code}")
            return
        
        try:
            data = response.json()
            
            if not data.get('healthy'):
                self.log_result("Engine Health - Healthy Status", False,
                              error_msg=f"Engine not healthy: {data.get('message')}")
                return
            
            self.log_result("Engine Health Check - Complete", True)
            
        except json.JSONDecodeError:
            self.log_result("Engine Health - JSON Parse", False, error_msg="Invalid JSON response")

    def test_invoice_validation_fail(self):
        """Test POST /api/hard-rules/validate/invoice/ - FAIL case"""
        print("\n📄❌ Testing Invoice Validation (FAIL case)...")
        
        # Invalid invoice data - missing mandatory fields
        invalid_invoice = {
            "invoice_data": {
                "invoice_number": "",  # Missing
                "invoice_date": "2025-01-30",
                "party_name": "",  # Missing
                "total_amount": 0,  # Invalid
                "currency": "INVALID",  # Invalid currency
                "subtotal": 1000,
                "vat_amount": 200,  # Wrong calculation (should be 150 for 15%)
            },
            "country": "SA",
            "organization_id": "test-org"
        }
        
        response = self.make_request('POST', '/api/hard-rules/validate/invoice/', invalid_invoice)
        
        if not response:
            self.log_result("Invoice Validation FAIL - Connection", False, error_msg="Connection failed")
            return
        
        if response.status_code != 200:
            self.log_result("Invoice Validation FAIL - Status Code", False,
                          error_msg=f"Expected 200, got {response.status_code}")
            return
        
        try:
            data = response.json()
            
            # Should NOT be valid
            if data.get('valid'):
                self.log_result("Invoice Validation FAIL - Should Fail", False,
                              error_msg="Invalid invoice was marked as valid")
                return
            
            # Should have FAIL or BLOCKED status
            status = data.get('status')
            if status not in ['FAIL', 'BLOCKED']:
                self.log_result("Invoice Validation FAIL - Status", False,
                              error_msg=f"Expected FAIL/BLOCKED, got {status}")
                return
            
            # Should have blocking message
            if not data.get('message'):
                self.log_result("Invoice Validation FAIL - Message", False,
                              error_msg="No blocking message provided")
                return
            
            self.log_result("Invoice Validation FAIL Case - Complete", True)
            
        except json.JSONDecodeError:
            self.log_result("Invoice Validation FAIL - JSON Parse", False, error_msg="Invalid JSON response")

    def test_invoice_validation_pass(self):
        """Test POST /api/hard-rules/validate/invoice/ - PASS case"""
        print("\n📄✅ Testing Invoice Validation (PASS case)...")
        
        # Valid invoice data with proper user role
        valid_invoice = {
            "invoice_data": {
                "invoice_number": "INV-2025-001",
                "invoice_date": "2025-01-29",
                "party_name": "Test Customer Ltd",
                "total_amount": 1150.00,
                "currency": "SAR",
                "subtotal": 1000.00,
                "vat_amount": 150.00,  # Correct 15% VAT
                "uuid": str(uuid.uuid4()),
                "seller_name": "Test Company",
                "seller_vat_number": "311234567890123",
                "issue_date": "2025-01-29",
                "total_including_vat": 1150.00,
                "total_excluding_vat": 1000.00,
                "total_vat": 150.00,
                "vat_rate": 15,
                "invoice_type_code": "388"
            },
            "country": "SA",
            "organization_id": "test-org",
            "user_role": "accountant"  # Use role with create permission
        }
        
        response = self.make_request('POST', '/api/hard-rules/validate/invoice/', valid_invoice)
        
        if not response:
            self.log_result("Invoice Validation PASS - Connection", False, error_msg="Connection failed")
            return
        
        if response.status_code != 200:
            self.log_result("Invoice Validation PASS - Status Code", False,
                          error_msg=f"Expected 200, got {response.status_code}")
            return
        
        try:
            data = response.json()
            
            # Should be valid
            if not data.get('valid'):
                self.log_result("Invoice Validation PASS - Should Pass", False,
                              error_msg=f"Valid invoice failed: {data.get('message')}")
                return
            
            # Should have PASS status
            status = data.get('status')
            if status != 'PASS':
                self.log_result("Invoice Validation PASS - Status", False,
                              error_msg=f"Expected PASS, got {status}")
                return
            
            self.log_result("Invoice Validation PASS Case - Complete", True)
            
        except json.JSONDecodeError:
            self.log_result("Invoice Validation PASS - JSON Parse", False, error_msg="Invalid JSON response")

    def test_journal_entry_validation_fail(self):
        """Test POST /api/hard-rules/validate/journal-entry/ - FAIL case"""
        print("\n📊❌ Testing Journal Entry Validation (FAIL case)...")
        
        # Invalid journal entry - debit != credit
        invalid_entry = {
            "entry_id": "JE-FAIL-001",
            "debit_amount": 1000.00,
            "credit_amount": 800.00,  # Not equal to debit
            "account_code": "9999",  # Non-existent account
            "transaction_type": "expense",
            "existing_accounts": {
                "1001": {"active": True, "type": "expense"},
                "2001": {"active": True, "type": "liability"}
            }
        }
        
        response = self.make_request('POST', '/api/hard-rules/validate/journal-entry/', invalid_entry)
        
        if not response:
            self.log_result("Journal Entry FAIL - Connection", False, error_msg="Connection failed")
            return
        
        if response.status_code != 200:
            self.log_result("Journal Entry FAIL - Status Code", False,
                          error_msg=f"Expected 200, got {response.status_code}")
            return
        
        try:
            data = response.json()
            
            # Should NOT be valid
            if data.get('valid'):
                self.log_result("Journal Entry FAIL - Should Fail", False,
                              error_msg="Invalid journal entry was marked as valid")
                return
            
            # Should have FAIL status
            status = data.get('status')
            if status != 'FAIL':
                self.log_result("Journal Entry FAIL - Status", False,
                              error_msg=f"Expected FAIL, got {status}")
                return
            
            self.log_result("Journal Entry FAIL Case - Complete", True)
            
        except json.JSONDecodeError:
            self.log_result("Journal Entry FAIL - JSON Parse", False, error_msg="Invalid JSON response")

    def test_journal_entry_validation_pass(self):
        """Test POST /api/hard-rules/validate/journal-entry/ - PASS case"""
        print("\n📊✅ Testing Journal Entry Validation (PASS case)...")
        
        # Valid journal entry - debit = credit
        valid_entry = {
            "entry_id": "JE-PASS-001",
            "debit_amount": 1000.00,
            "credit_amount": 1000.00,  # Equal to debit
            "account_code": "1001",  # Existing account
            "transaction_type": "expense",
            "existing_accounts": {
                "1001": {"active": True, "type": "expense"},
                "2001": {"active": True, "type": "liability"}
            }
        }
        
        response = self.make_request('POST', '/api/hard-rules/validate/journal-entry/', valid_entry)
        
        if not response:
            self.log_result("Journal Entry PASS - Connection", False, error_msg="Connection failed")
            return
        
        if response.status_code != 200:
            self.log_result("Journal Entry PASS - Status Code", False,
                          error_msg=f"Expected 200, got {response.status_code}")
            return
        
        try:
            data = response.json()
            
            # Should be valid
            if not data.get('valid'):
                self.log_result("Journal Entry PASS - Should Pass", False,
                              error_msg=f"Valid journal entry failed: {data.get('message')}")
                return
            
            # Should have PASS status
            status = data.get('status')
            if status != 'PASS':
                self.log_result("Journal Entry PASS - Status", False,
                              error_msg=f"Expected PASS, got {status}")
                return
            
            self.log_result("Journal Entry PASS Case - Complete", True)
            
        except json.JSONDecodeError:
            self.log_result("Journal Entry PASS - JSON Parse", False, error_msg="Invalid JSON response")

    def test_ai_gate_check(self):
        """Test POST /api/hard-rules/gate/check/"""
        print("\n🚪 Testing AI Gate Check...")
        
        gate_request = {
            "ai_function_name": "analyze_invoice",
            "organization_id": "test-org"
        }
        
        response = self.make_request('POST', '/api/hard-rules/gate/check/', gate_request)
        
        if not response:
            self.log_result("AI Gate Check - Connection", False, error_msg="Connection failed")
            return
        
        if response.status_code != 200:
            self.log_result("AI Gate Check - Status Code", False,
                          error_msg=f"Expected 200, got {response.status_code}")
            return
        
        try:
            data = response.json()
            
            # Should have allowed field
            if 'allowed' not in data:
                self.log_result("AI Gate Check - Allowed Field", False,
                              error_msg="Missing 'allowed' field")
                return
            
            # Should be allowed (engine is operational)
            if not data.get('allowed'):
                self.log_result("AI Gate Check - Should Allow", False,
                              error_msg=f"AI gate blocked: {data.get('reason')}")
                return
            
            self.log_result("AI Gate Check - Complete", True)
            
        except json.JSONDecodeError:
            self.log_result("AI Gate Check - JSON Parse", False, error_msg="Invalid JSON response")

    def test_recent_evaluations(self):
        """Test GET /api/hard-rules/evaluations/"""
        print("\n📈 Testing Recent Evaluations...")
        
        response = self.make_request('GET', '/api/hard-rules/evaluations/')
        
        if not response:
            self.log_result("Recent Evaluations - Connection", False, error_msg="Connection failed")
            return
        
        if response.status_code != 200:
            self.log_result("Recent Evaluations - Status Code", False,
                          error_msg=f"Expected 200, got {response.status_code}")
            return
        
        try:
            data = response.json()
            
            # Should have evaluations field
            if 'evaluations' not in data:
                self.log_result("Recent Evaluations - Evaluations Field", False,
                              error_msg="Missing 'evaluations' field")
                return
            
            # Evaluations should be a list
            evaluations = data['evaluations']
            if not isinstance(evaluations, list):
                self.log_result("Recent Evaluations - List Type", False,
                              error_msg="Evaluations should be a list")
                return
            
            self.log_result("Recent Evaluations - Complete", True)
            
        except json.JSONDecodeError:
            self.log_result("Recent Evaluations - JSON Parse", False, error_msg="Invalid JSON response")

    def test_dashboard_accessibility(self):
        """Test Dashboard UI accessibility"""
        print("\n🖥️  Testing Dashboard Accessibility...")
        
        response = self.make_request('GET', '/api/hard-rules/dashboard/')
        
        if not response:
            self.log_result("Dashboard - Connection", False, error_msg="Connection failed")
            return
        
        if response.status_code != 200:
            self.log_result("Dashboard - Status Code", False,
                          error_msg=f"Expected 200, got {response.status_code}")
            return
        
        # Check if it's HTML content
        content_type = response.headers.get('content-type', '')
        if 'text/html' not in content_type:
            self.log_result("Dashboard - Content Type", False,
                          error_msg=f"Expected HTML, got {content_type}")
            return
        
        # Check for key dashboard elements
        html_content = response.text
        required_elements = [
            'Hard Rules Dashboard',  # From title
            'محرك القواعد الصارمة',
            'system-status-badge',
            'ai-gate-status-card'
        ]
        
        for element in required_elements:
            if element not in html_content:
                self.log_result(f"Dashboard - {element}", False,
                              error_msg=f"Missing element: {element}")
                return
        
        self.log_result("Dashboard Accessibility - Complete", True)

    def run_all_tests(self):
        """Run all Hard Rules Engine tests"""
        print("🚀 Starting Hard Rules Engine API Tests...\n")
        
        # Test all endpoints
        self.test_governance_status()
        self.test_rule_enforcement_summary()
        self.test_engine_health()
        self.test_invoice_validation_fail()
        self.test_invoice_validation_pass()
        self.test_journal_entry_validation_fail()
        self.test_journal_entry_validation_pass()
        self.test_ai_gate_check()
        self.test_recent_evaluations()
        self.test_dashboard_accessibility()
        
        # Print summary
        print("\n" + "=" * 60)
        print(f"📊 Test Summary:")
        print(f"   Total Tests: {self.tests_run}")
        print(f"   Passed: {self.tests_passed}")
        print(f"   Failed: {len(self.failed_tests)}")
        print(f"   Success Rate: {(self.tests_passed/self.tests_run*100):.1f}%")
        
        if self.failed_tests:
            print(f"\n❌ Failed Tests:")
            for failure in self.failed_tests:
                print(f"   - {failure['test']}: {failure['error']}")
        
        return len(self.failed_tests) == 0

def main():
    """Main test execution"""
    tester = HardRulesEngineAPITester("http://localhost:8001")
    success = tester.run_all_tests()
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())