#!/usr/bin/env python3
"""
FinAI Backend API Testing Suite
Tests all API endpoints for the Django REST API backend
"""

import requests
import sys
import json
from datetime import datetime, timedelta
from decimal import Decimal

class FinAIAPITester:
    def __init__(self, base_url="http://localhost:8001"):
        self.base_url = base_url
        self.token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.failed_tests = []
        self.organization_id = None

    def log_result(self, test_name, success, response_data=None, error_msg=None):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {test_name} - PASSED")
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
            return None

    def test_health_check(self):
        """Test health check endpoint"""
        print("\n🔍 Testing Health Check...")
        response = self.make_request('GET', '/health')
        
        if response and response.status_code == 200:
            self.log_result("Health Check", True)
            return True
        else:
            error_msg = f"Status: {response.status_code if response else 'No response'}"
            self.log_result("Health Check", False, error_msg=error_msg)
            return False

    def test_jwt_authentication(self):
        """Test JWT authentication"""
        print("\n🔍 Testing JWT Authentication...")
        
        # Test login
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
                    self.log_result("JWT Authentication - Login", True)
                    return True
                else:
                    self.log_result("JWT Authentication - Login", False, 
                                  error_msg="No access token in response")
                    return False
            except json.JSONDecodeError:
                self.log_result("JWT Authentication - Login", False, 
                              error_msg="Invalid JSON response")
                return False
        else:
            error_msg = f"Status: {response.status_code if response else 'No response'}"
            if response:
                try:
                    error_msg += f", Response: {response.text}"
                except:
                    pass
            self.log_result("JWT Authentication - Login", False, error_msg=error_msg)
            return False

    def test_organizations_api(self):
        """Test Organizations API"""
        print("\n🔍 Testing Organizations API...")
        
        # Test list organizations
        response = self.make_request('GET', '/api/core/organizations/')
        
        if response and response.status_code == 200:
            try:
                data = response.json()
                # Handle paginated response
                if isinstance(data, dict) and 'results' in data and len(data['results']) > 0:
                    self.organization_id = data['results'][0].get('id')
                    self.log_result("Organizations - List", True)
                    
                    # Test organization stats
                    if self.organization_id:
                        stats_response = self.make_request('GET', f'/api/core/organizations/{self.organization_id}/stats/')
                        if stats_response and stats_response.status_code == 200:
                            self.log_result("Organizations - Stats", True)
                        else:
                            error_msg = f"Stats Status: {stats_response.status_code if stats_response else 'No response'}"
                            self.log_result("Organizations - Stats", False, error_msg=error_msg)
                    
                    return True
                elif isinstance(data, list) and len(data) > 0:
                    # Handle direct array response
                    self.organization_id = data[0].get('id')
                    self.log_result("Organizations - List", True)
                    return True
                else:
                    self.log_result("Organizations - List", False, 
                                  error_msg="Empty or invalid response")
                    return False
            except json.JSONDecodeError:
                self.log_result("Organizations - List", False, 
                              error_msg="Invalid JSON response")
                return False
        else:
            error_msg = f"Status: {response.status_code if response else 'No response'}"
            self.log_result("Organizations - List", False, error_msg=error_msg)
            return False

    def test_accounts_api(self):
        """Test Accounts API"""
        print("\n🔍 Testing Accounts API...")
        
        # Test list accounts
        response = self.make_request('GET', '/api/documents/accounts/')
        
        if response and response.status_code == 200:
            self.log_result("Accounts - List", True)
            
            # Test trial balance
            trial_response = self.make_request('GET', '/api/documents/accounts/trial_balance/')
            if trial_response and trial_response.status_code == 200:
                self.log_result("Accounts - Trial Balance", True)
            else:
                error_msg = f"Trial Balance Status: {trial_response.status_code if trial_response else 'No response'}"
                self.log_result("Accounts - Trial Balance", False, error_msg=error_msg)
            
            # Test accounts by type
            by_type_response = self.make_request('GET', '/api/documents/accounts/by_type/')
            if by_type_response and by_type_response.status_code == 200:
                self.log_result("Accounts - By Type", True)
            else:
                error_msg = f"By Type Status: {by_type_response.status_code if by_type_response else 'No response'}"
                self.log_result("Accounts - By Type", False, error_msg=error_msg)
            
            return True
        else:
            error_msg = f"Status: {response.status_code if response else 'No response'}"
            self.log_result("Accounts - List", False, error_msg=error_msg)
            return False

    def test_transactions_api(self):
        """Test Transactions API"""
        print("\n🔍 Testing Transactions API...")
        
        # Test list transactions
        response = self.make_request('GET', '/api/documents/transactions/')
        
        if response and response.status_code == 200:
            self.log_result("Transactions - List", True)
            
            # Test filter by type
            type_response = self.make_request('GET', '/api/documents/transactions/', 
                                            params={'type': 'income'})
            if type_response and type_response.status_code == 200:
                self.log_result("Transactions - Filter by Type", True)
            else:
                error_msg = f"Filter Type Status: {type_response.status_code if type_response else 'No response'}"
                self.log_result("Transactions - Filter by Type", False, error_msg=error_msg)
            
            # Test anomalies only filter
            anomaly_response = self.make_request('GET', '/api/documents/transactions/', 
                                               params={'anomalies_only': 'true'})
            if anomaly_response and anomaly_response.status_code == 200:
                self.log_result("Transactions - Anomalies Filter", True)
            else:
                error_msg = f"Anomalies Status: {anomaly_response.status_code if anomaly_response else 'No response'}"
                self.log_result("Transactions - Anomalies Filter", False, error_msg=error_msg)
            
            # Test summary endpoint
            summary_response = self.make_request('GET', '/api/documents/transactions/summary/')
            if summary_response and summary_response.status_code == 200:
                self.log_result("Transactions - Summary", True)
            else:
                error_msg = f"Summary Status: {summary_response.status_code if summary_response else 'No response'}"
                self.log_result("Transactions - Summary", False, error_msg=error_msg)
            
            return True
        else:
            error_msg = f"Status: {response.status_code if response else 'No response'}"
            self.log_result("Transactions - List", False, error_msg=error_msg)
            return False

    def test_journal_entries_api(self):
        """Test Journal Entries API"""
        print("\n🔍 Testing Journal Entries API...")
        
        response = self.make_request('GET', '/api/documents/journal-entries/')
        
        if response and response.status_code == 200:
            self.log_result("Journal Entries - List", True)
            return True
        else:
            error_msg = f"Status: {response.status_code if response else 'No response'}"
            self.log_result("Journal Entries - List", False, error_msg=error_msg)
            return False

    def test_compliance_checks_api(self):
        """Test Compliance Checks API"""
        print("\n🔍 Testing Compliance Checks API...")
        
        # Test list compliance checks
        response = self.make_request('GET', '/api/documents/compliance-checks/')
        
        if response and response.status_code == 200:
            self.log_result("Compliance Checks - List", True)
            
            # Test score summary
            summary_response = self.make_request('GET', '/api/documents/compliance-checks/score_summary/')
            if summary_response and summary_response.status_code == 200:
                self.log_result("Compliance Checks - Score Summary", True)
            else:
                error_msg = f"Score Summary Status: {summary_response.status_code if summary_response else 'No response'}"
                self.log_result("Compliance Checks - Score Summary", False, error_msg=error_msg)
            
            return True
        else:
            error_msg = f"Status: {response.status_code if response else 'No response'}"
            self.log_result("Compliance Checks - List", False, error_msg=error_msg)
            return False

    def test_audit_flags_api(self):
        """Test Audit Flags API"""
        print("\n🔍 Testing Audit Flags API...")
        
        # Test list audit flags
        response = self.make_request('GET', '/api/documents/audit-flags/')
        
        if response and response.status_code == 200:
            self.log_result("Audit Flags - List", True)
            
            # Test dashboard endpoint
            dashboard_response = self.make_request('GET', '/api/documents/audit-flags/dashboard/')
            if dashboard_response and dashboard_response.status_code == 200:
                self.log_result("Audit Flags - Dashboard", True)
            else:
                error_msg = f"Dashboard Status: {dashboard_response.status_code if dashboard_response else 'No response'}"
                self.log_result("Audit Flags - Dashboard", False, error_msg=error_msg)
            
            # Test filter by priority
            priority_response = self.make_request('GET', '/api/documents/audit-flags/', 
                                                params={'priority': 'high'})
            if priority_response and priority_response.status_code == 200:
                self.log_result("Audit Flags - Priority Filter", True)
            else:
                error_msg = f"Priority Filter Status: {priority_response.status_code if priority_response else 'No response'}"
                self.log_result("Audit Flags - Priority Filter", False, error_msg=error_msg)
            
            return True
        else:
            error_msg = f"Status: {response.status_code if response else 'No response'}"
            self.log_result("Audit Flags - List", False, error_msg=error_msg)
            return False

    def test_insights_api(self):
        """Test Insights API"""
        print("\n🔍 Testing Insights API...")
        
        response = self.make_request('GET', '/api/reports/insights/')
        
        if response and response.status_code == 200:
            self.log_result("Insights - List", True)
            return True
        else:
            error_msg = f"Status: {response.status_code if response else 'No response'}"
            self.log_result("Insights - List", False, error_msg=error_msg)
            return False

    def test_reports_api(self):
        """Test Reports API"""
        print("\n🔍 Testing Reports API...")
        
        response = self.make_request('GET', '/api/reports/reports/')
        
        if response and response.status_code == 200:
            self.log_result("Reports - List", True)
            return True
        else:
            error_msg = f"Status: {response.status_code if response else 'No response'}"
            self.log_result("Reports - List", False, error_msg=error_msg)
            return False

    def test_analytics_api(self):
        """Test Analytics API"""
        print("\n🔍 Testing Analytics API...")
        
        # Test KPIs endpoint
        params = {}
        if self.organization_id:
            params['organization_id'] = self.organization_id
        
        response = self.make_request('GET', '/api/analytics/kpis/', params=params)
        
        if response and response.status_code == 200:
            self.log_result("Analytics - KPIs", True)
            return True
        else:
            error_msg = f"Status: {response.status_code if response else 'No response'}"
            self.log_result("Analytics - KPIs", False, error_msg=error_msg)
            return False

    def run_all_tests(self):
        """Run all API tests"""
        print("🚀 Starting FinAI Backend API Tests")
        print("=" * 50)
        
        # Test health check first
        if not self.test_health_check():
            print("❌ Health check failed - backend may not be running")
            return False
        
        # Test authentication
        if not self.test_jwt_authentication():
            print("❌ Authentication failed - cannot proceed with other tests")
            return False
        
        # Test all API endpoints
        self.test_organizations_api()
        self.test_accounts_api()
        self.test_transactions_api()
        self.test_journal_entries_api()
        self.test_compliance_checks_api()
        self.test_audit_flags_api()
        self.test_insights_api()
        self.test_reports_api()
        self.test_analytics_api()
        
        # Print summary
        print("\n" + "=" * 50)
        print(f"📊 Test Summary: {self.tests_passed}/{self.tests_run} tests passed")
        
        if self.failed_tests:
            print("\n❌ Failed Tests:")
            for failed in self.failed_tests:
                print(f"  - {failed['test']}: {failed['error']}")
        
        success_rate = (self.tests_passed / self.tests_run * 100) if self.tests_run > 0 else 0
        print(f"✅ Success Rate: {success_rate:.1f}%")
        
        return success_rate > 80

def main():
    """Main test execution"""
    tester = FinAIAPITester()
    success = tester.run_all_tests()
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())