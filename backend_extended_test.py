#!/usr/bin/env python3
"""
FinAI Backend API Extended Testing Suite
Additional tests for edge cases and detailed functionality
"""

import requests
import sys
import json
from datetime import datetime, timedelta

class FinAIExtendedTester:
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
            
            return response
        except requests.exceptions.RequestException as e:
            return None

    def authenticate(self):
        """Get JWT token"""
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
                    return True
            except json.JSONDecodeError:
                pass
        return False

    def get_organization_id(self):
        """Get first organization ID"""
        response = self.make_request('GET', '/api/core/organizations/')
        if response and response.status_code == 200:
            try:
                data = response.json()
                if isinstance(data, dict) and 'results' in data and len(data['results']) > 0:
                    self.organization_id = data['results'][0].get('id')
                    return True
            except json.JSONDecodeError:
                pass
        return False

    def test_user_endpoints(self):
        """Test user-related endpoints"""
        print("\n🔍 Testing User Endpoints...")
        
        # Test current user info
        response = self.make_request('GET', '/api/core/users/me/')
        if response and response.status_code == 200:
            self.log_result("Users - Current User Info", True)
        else:
            error_msg = f"Status: {response.status_code if response else 'No response'}"
            self.log_result("Users - Current User Info", False, error_msg=error_msg)

    def test_analytics_endpoints(self):
        """Test analytics endpoints with data"""
        print("\n🔍 Testing Analytics Endpoints...")
        
        if not self.organization_id:
            print("⚠️ No organization ID available for analytics tests")
            return
        
        # Test forecast endpoint
        forecast_data = {
            "organization_id": self.organization_id,
            "periods": 3
        }
        response = self.make_request('POST', '/api/analytics/forecast/', forecast_data)
        if response and response.status_code == 200:
            self.log_result("Analytics - Forecast", True)
        else:
            error_msg = f"Status: {response.status_code if response else 'No response'}"
            self.log_result("Analytics - Forecast", False, error_msg=error_msg)
        
        # Test anomaly detection
        anomaly_data = {
            "organization_id": self.organization_id
        }
        response = self.make_request('POST', '/api/analytics/detect-anomalies/', anomaly_data)
        if response and response.status_code == 200:
            self.log_result("Analytics - Anomaly Detection", True)
        else:
            error_msg = f"Status: {response.status_code if response else 'No response'}"
            self.log_result("Analytics - Anomaly Detection", False, error_msg=error_msg)

    def test_reports_generation(self):
        """Test report generation"""
        print("\n🔍 Testing Report Generation...")
        
        if not self.organization_id:
            print("⚠️ No organization ID available for report tests")
            return
        
        # Test report generation
        report_data = {
            "organization_id": self.organization_id,
            "report_type": "income_statement",
            "report_name": "Test Income Statement",
            "period_start": "2024-01-01T00:00:00",
            "period_end": "2024-12-31T23:59:59"
        }
        
        response = self.make_request('POST', '/api/reports/reports/generate/', report_data)
        if response and response.status_code == 201:
            self.log_result("Reports - Generate Income Statement", True)
        else:
            error_msg = f"Status: {response.status_code if response else 'No response'}"
            if response:
                try:
                    error_msg += f", Response: {response.text}"
                except:
                    pass
            self.log_result("Reports - Generate Income Statement", False, error_msg=error_msg)

    def test_error_handling(self):
        """Test error handling"""
        print("\n🔍 Testing Error Handling...")
        
        # Test unauthorized access (without token)
        old_token = self.token
        self.token = None
        
        response = self.make_request('GET', '/api/core/organizations/')
        if response and response.status_code == 401:
            self.log_result("Error Handling - Unauthorized Access", True)
        else:
            error_msg = f"Expected 401, got: {response.status_code if response else 'No response'}"
            self.log_result("Error Handling - Unauthorized Access", False, error_msg=error_msg)
        
        # Restore token
        self.token = old_token
        
        # Test invalid endpoint
        response = self.make_request('GET', '/api/invalid/endpoint/')
        if response and response.status_code == 404:
            self.log_result("Error Handling - Invalid Endpoint", True)
        else:
            error_msg = f"Expected 404, got: {response.status_code if response else 'No response'}"
            self.log_result("Error Handling - Invalid Endpoint", False, error_msg=error_msg)

    def test_data_validation(self):
        """Test data validation"""
        print("\n🔍 Testing Data Validation...")
        
        # Test invalid login credentials
        invalid_login = {
            "email": "invalid@email.com",
            "password": "wrongpassword"
        }
        
        response = self.make_request('POST', '/api/auth/token/', invalid_login)
        if response and response.status_code == 401:
            self.log_result("Data Validation - Invalid Login", True)
        else:
            error_msg = f"Expected 401, got: {response.status_code if response else 'No response'}"
            self.log_result("Data Validation - Invalid Login", False, error_msg=error_msg)

    def run_extended_tests(self):
        """Run all extended tests"""
        print("🚀 Starting FinAI Extended Backend Tests")
        print("=" * 50)
        
        # Authenticate first
        if not self.authenticate():
            print("❌ Authentication failed - cannot proceed")
            return False
        
        # Get organization ID
        if not self.get_organization_id():
            print("⚠️ Could not get organization ID - some tests may be skipped")
        
        # Run extended tests
        self.test_user_endpoints()
        self.test_analytics_endpoints()
        self.test_reports_generation()
        self.test_error_handling()
        self.test_data_validation()
        
        # Print summary
        print("\n" + "=" * 50)
        print(f"📊 Extended Test Summary: {self.tests_passed}/{self.tests_run} tests passed")
        
        if self.failed_tests:
            print("\n❌ Failed Tests:")
            for failed in self.failed_tests:
                print(f"  - {failed['test']}: {failed['error']}")
        
        success_rate = (self.tests_passed / self.tests_run * 100) if self.tests_run > 0 else 0
        print(f"✅ Success Rate: {success_rate:.1f}%")
        
        return success_rate > 70

def main():
    """Main test execution"""
    tester = FinAIExtendedTester()
    success = tester.run_extended_tests()
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())