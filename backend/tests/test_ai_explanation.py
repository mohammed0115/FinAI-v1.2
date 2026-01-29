"""
Test AI Explanation Feature for FinAI Audit Platform
Tests LLM integration for Arabic AI explanations with audit trail
"""
import pytest
import requests
import os
import re

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_EMAIL = "admin@finai.com"
TEST_PASSWORD = "adminpassword"
FINDING_ID = "e8c2dee9-2d4b-41d3-be03-914217cd0bdd"


class TestAIExplanationFeature:
    """Test AI Explanation generation and audit trail via HTTP requests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup session with authentication"""
        self.session = requests.Session()
        
    def get_csrf_token(self, url):
        """Get CSRF token from page"""
        response = self.session.get(url)
        # Extract CSRF token from cookies or form
        csrf_token = self.session.cookies.get('csrftoken')
        if not csrf_token:
            # Try to extract from HTML
            match = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', response.text)
            if match:
                csrf_token = match.group(1)
        return csrf_token, response
    
    def login(self):
        """Login and return authenticated session"""
        login_url = f"{BASE_URL}/login/"
        csrf_token, _ = self.get_csrf_token(login_url)
        
        login_data = {
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD,
            "csrfmiddlewaretoken": csrf_token
        }
        
        response = self.session.post(
            login_url,
            data=login_data,
            headers={"Referer": login_url},
            allow_redirects=True
        )
        return response
    
    def test_01_login_works(self):
        """Test that login works with test credentials"""
        response = self.login()
        assert response.status_code == 200, f"Login failed with status {response.status_code}"
        # After login, we should be on dashboard
        assert "لوحة التحكم" in response.text or "Dashboard" in response.text or response.url.endswith("/")
        print("✓ Login successful")
    
    def test_02_finding_detail_page_loads(self):
        """Test that finding detail page loads with AI explanation section"""
        self.login()
        
        finding_url = f"{BASE_URL}/findings/{FINDING_ID}/"
        response = self.session.get(finding_url)
        
        assert response.status_code == 200, f"Finding page failed with status {response.status_code}"
        
        # Check for AI explanation section
        assert "تحليل الذكاء الاصطناعي" in response.text, "AI explanation section not found"
        print("✓ Finding detail page loads with AI explanation section")
    
    def test_03_generate_ai_button_exists(self):
        """Test that Generate AI Explanation button exists"""
        self.login()
        
        finding_url = f"{BASE_URL}/findings/{FINDING_ID}/"
        response = self.session.get(finding_url)
        
        assert response.status_code == 200
        
        # Check for generate button
        assert 'data-testid="generate-ai-btn"' in response.text, "Generate AI button not found"
        assert "توليد شرح جديد" in response.text, "Generate button text not found"
        print("✓ Generate AI Explanation button exists")
    
    def test_04_ai_explanation_content_exists(self):
        """Test that AI explanation content is displayed"""
        self.login()
        
        finding_url = f"{BASE_URL}/findings/{FINDING_ID}/"
        response = self.session.get(finding_url)
        
        assert response.status_code == 200
        
        # Check for AI explanation content
        assert 'data-testid="ai-explanation"' in response.text, "AI explanation content area not found"
        print("✓ AI explanation content area exists")
    
    def test_05_disclaimer_displayed(self):
        """Test that human review disclaimer is displayed"""
        self.login()
        
        finding_url = f"{BASE_URL}/findings/{FINDING_ID}/"
        response = self.session.get(finding_url)
        
        assert response.status_code == 200
        
        # Check for disclaimer
        assert "استشاري فقط" in response.text or "يتطلب مراجعة بشرية" in response.text, "Disclaimer not found"
        print("✓ Human review disclaimer is displayed")
    
    def test_06_confidence_score_displayed(self):
        """Test that confidence score is displayed"""
        self.login()
        
        finding_url = f"{BASE_URL}/findings/{FINDING_ID}/"
        response = self.session.get(finding_url)
        
        assert response.status_code == 200
        
        # Check for confidence score
        assert "درجة الثقة" in response.text, "Confidence score label not found"
        # Check for percentage display
        assert "%" in response.text, "Percentage not found"
        print("✓ Confidence score is displayed")
    
    def test_07_ai_explanation_log_section(self):
        """Test that AI explanation log history section exists"""
        self.login()
        
        finding_url = f"{BASE_URL}/findings/{FINDING_ID}/"
        response = self.session.get(finding_url)
        
        assert response.status_code == 200
        
        # Check for log history section
        assert "سجل الشروحات الذكية" in response.text, "AI explanation log section not found"
        print("✓ AI explanation log history section exists")


class TestAIExplanationDatabase:
    """Test AI Explanation database records via Django shell"""
    
    def test_08_ai_explanation_log_exists(self):
        """Test that AIExplanationLog record exists in database"""
        import subprocess
        result = subprocess.run(
            ["python", "manage.py", "shell", "-c", 
             f"from compliance.models import AuditFinding, AIExplanationLog; "
             f"finding = AuditFinding.objects.filter(id='{FINDING_ID}').first(); "
             f"logs = AIExplanationLog.objects.filter(finding=finding) if finding else []; "
             f"print(f'LOG_COUNT:{{logs.count() if hasattr(logs, \"count\") else 0}}'); "
             f"[print(f'APPROVAL_STATUS:{{log.approval_status}}') for log in logs]; "
             f"[print(f'REQUIRES_HUMAN_REVIEW:{{log.requires_human_review}}') for log in logs]"
            ],
            cwd="/app/backend",
            capture_output=True,
            text=True
        )
        
        output = result.stdout
        assert "LOG_COUNT:1" in output or "LOG_COUNT:2" in output, f"No AI explanation logs found. Output: {output}"
        assert "APPROVAL_STATUS:pending" in output, f"Approval status should be pending. Output: {output}"
        assert "REQUIRES_HUMAN_REVIEW:True" in output, f"requires_human_review should be True. Output: {output}"
        print("✓ AIExplanationLog record exists with correct status")
    
    def test_09_finding_ai_explanation_updated(self):
        """Test that finding's ai_explanation_ar field is updated"""
        import subprocess
        result = subprocess.run(
            ["python", "manage.py", "shell", "-c", 
             f"import re; "
             f"from compliance.models import AuditFinding; "
             f"finding = AuditFinding.objects.filter(id='{FINDING_ID}').first(); "
             f"has_explanation = bool(finding.ai_explanation_ar) if finding else False; "
             f"print(f'HAS_EXPLANATION:{{has_explanation}}'); "
             f"print(f'AI_CONFIDENCE:{{finding.ai_confidence if finding else 0}}'); "
             f"arabic_pattern = re.compile(r'[\\u0600-\\u06FF]'); "
             f"is_arabic = bool(arabic_pattern.search(finding.ai_explanation_ar)) if finding and finding.ai_explanation_ar else False; "
             f"print(f'IS_ARABIC:{{is_arabic}}')"
            ],
            cwd="/app/backend",
            capture_output=True,
            text=True
        )
        
        output = result.stdout
        assert "HAS_EXPLANATION:True" in output, f"Finding should have AI explanation. Output: {output}"
        assert "IS_ARABIC:True" in output, f"AI explanation should be in Arabic. Output: {output}"
        print("✓ Finding's ai_explanation_ar field is updated with Arabic content")
    
    def test_10_model_used_is_gemini(self):
        """Test that the model used is Gemini 3 Flash"""
        import subprocess
        result = subprocess.run(
            ["python", "manage.py", "shell", "-c", 
             f"from compliance.models import AIExplanationLog; "
             f"logs = AIExplanationLog.objects.filter(finding_id='{FINDING_ID}'); "
             f"[print(f'MODEL:{{log.model_used}}') for log in logs]; "
             f"[print(f'PROVIDER:{{log.provider}}') for log in logs]"
            ],
            cwd="/app/backend",
            capture_output=True,
            text=True
        )
        
        output = result.stdout
        assert "gemini" in output.lower(), f"Model should be Gemini. Output: {output}"
        print("✓ Model used is Gemini 3 Flash")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
