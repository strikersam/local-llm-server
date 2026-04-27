#!/usr/bin/env python3
"""
Backend API Testing for LLM Wiki Dashboard - Iteration 3
Tests all API endpoints including new providers, models, keys, observability features
"""

import requests
import sys
import json
import time
from datetime import datetime

class LLMWikiAPITesterV3:
    def __init__(self, base_url="https://feature-spotlight-8.preview.emergentagent.com"):
        self.base_url = base_url
        self.session = requests.Session()
        self.tests_run = 0
        self.tests_passed = 0
        self.failed_tests = []

    def log(self, message):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")

    def run_test(self, name, method, endpoint, expected_status, data=None):
        """Run a single API test"""
        url = f"{self.base_url}{endpoint}"
        self.tests_run += 1
        
        self.log(f"🔍 Testing {name}...")
        
        try:
            if method == 'GET':
                response = self.session.get(url)
            elif method == 'POST':
                response = self.session.post(url, json=data)
            elif method == 'PUT':
                response = self.session.put(url, json=data)
            elif method == 'DELETE':
                response = self.session.delete(url)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                self.log(f"✅ {name} - Status: {response.status_code}")
                try:
                    return True, response.json()
                except:
                    return True, response.text
            else:
                self.log(f"❌ {name} - Expected {expected_status}, got {response.status_code}")
                self.log(f"   Response: {response.text[:200]}")
                self.failed_tests.append({
                    "test": name,
                    "endpoint": endpoint,
                    "expected": expected_status,
                    "actual": response.status_code,
                    "response": response.text[:200]
                })
                return False, {}

        except Exception as e:
            self.log(f"❌ {name} - Error: {str(e)}")
            self.failed_tests.append({
                "test": name,
                "endpoint": endpoint,
                "error": str(e)
            })
            return False, {}

    def test_authentication(self):
        """Test authentication flow"""
        self.log("🔐 Testing Authentication...")
        
        # Test health check (no auth required)
        self.run_test("Health Check", "GET", "/api/health", 200)
        
        # Test login
        success, response = self.run_test(
            "Admin Login",
            "POST",
            "/api/auth/login",
            200,
            data={"email": "admin@llmwiki.local", "password": "WikiAdmin2026!"}
        )
        
        if not success:
            self.log("❌ Login failed - cannot continue with authenticated tests")
            return False
            
        # Test /me endpoint
        self.run_test("Get Current User", "GET", "/api/auth/me", 200)
        
        return True

    def test_dashboard_stats(self):
        """Test dashboard and stats endpoints"""
        self.log("📊 Testing Dashboard & Stats...")
        
        self.run_test("Get Stats", "GET", "/api/stats", 200)
        self.run_test("Get Platform Info", "GET", "/api/platform", 200)
        self.run_test("Get Activity Log", "GET", "/api/activity", 200)

    def test_providers_crud(self):
        """Test providers CRUD operations (new in iteration 3)"""
        self.log("🔧 Testing Providers CRUD...")
        
        # List providers
        success, providers_data = self.run_test("List Providers", "GET", "/api/providers", 200)
        
        if success:
            self.log(f"   Found {len(providers_data.get('providers', []))} providers")
        
        # Create a test provider
        test_provider = {
            "provider_id": "test-provider-automation",
            "name": "Test Provider for Automation",
            "type": "openai-compatible",
            "base_url": "https://api.openai.com/v1",
            "api_key": "sk-test123456789",
            "default_model": "gpt-4o-mini",
            "is_default": False
        }
        
        success, create_response = self.run_test(
            "Create Test Provider",
            "POST",
            "/api/providers",
            200,
            data=test_provider
        )
        
        if success:
            # Test provider connection (will likely fail but should return proper response)
            self.run_test(
                "Test Provider Connection",
                "POST",
                f"/api/providers/{test_provider['provider_id']}/test",
                200
            )
            
            # Update provider
            self.run_test(
                "Update Provider",
                "PUT",
                f"/api/providers/{test_provider['provider_id']}",
                200,
                data={"name": "Updated Test Provider Name"}
            )
            
            # Delete test provider
            self.run_test(
                "Delete Test Provider",
                "DELETE",
                f"/api/providers/{test_provider['provider_id']}",
                200
            )

    def test_models_hub(self):
        """Test models hub endpoints (new in iteration 3)"""
        self.log("📦 Testing Models Hub...")
        
        # List models
        success, models_data = self.run_test("List Models", "GET", "/api/models", 200)
        
        if success:
            self.log(f"   Found {len(models_data.get('models', []))} models")

    def test_api_keys_crud(self):
        """Test API keys CRUD operations (new in iteration 3)"""
        self.log("🔑 Testing API Keys CRUD...")
        
        # List API keys
        success, keys_data = self.run_test("List API Keys", "GET", "/api/keys", 200)
        
        if success:
            self.log(f"   Found {len(keys_data.get('keys', []))} API keys")
        
        # Create a test API key
        test_key_data = {
            "email": "test-automation@example.com",
            "department": "testing",
            "label": "Automation Test Key"
        }
        
        success, key_response = self.run_test(
            "Create Test API Key",
            "POST",
            "/api/keys",
            200,
            data=test_key_data
        )
        
        if success and 'key_id' in key_response:
            key_id = key_response['key_id']
            self.log(f"   Created key with ID: {key_id}")
            
            # Delete the test key
            self.run_test(
                "Delete Test API Key",
                "DELETE",
                f"/api/keys/{key_id}",
                200
            )

    def test_observability(self):
        """Test observability endpoints (new in iteration 3)"""
        self.log("📈 Testing Observability...")
        
        success, status_data = self.run_test("Observability Status", "GET", "/api/observability/status", 200)
        
        if success:
            configured = status_data.get('configured', False)
            connected = status_data.get('connected', False)
            self.log(f"   Langfuse configured: {configured}, connected: {connected}")
        
        self.run_test("Observability Dashboard URL", "GET", "/api/observability/dashboard-url", 200)

    def test_chat_functionality(self):
        """Test chat endpoints"""
        self.log("💬 Testing Chat Functionality...")
        
        # List sessions
        self.run_test("List Chat Sessions", "GET", "/api/chat/sessions", 200)
        
        # Send a chat message
        success, chat_response = self.run_test(
            "Send Chat Message",
            "POST",
            "/api/chat/send",
            200,
            data={"content": "Hello, this is a test message for iteration 3"}
        )
        
        if success and 'session_id' in chat_response:
            session_id = chat_response['session_id']
            self.log(f"   Created session: {session_id}")
            
            # Get the session
            self.run_test(
                "Get Chat Session",
                "GET",
                f"/api/chat/sessions/{session_id}",
                200
            )

    def test_wiki_crud(self):
        """Test wiki CRUD operations"""
        self.log("📚 Testing Wiki CRUD...")
        
        # List wiki pages
        self.run_test("List Wiki Pages", "GET", "/api/wiki/pages", 200)
        
        # Create a test wiki page
        test_page = {
            "title": "Iteration 3 Test Page",
            "content": "This is a test wiki page for iteration 3 testing",
            "tags": ["test", "iteration3", "automation"]
        }
        
        success, page_response = self.run_test(
            "Create Wiki Page",
            "POST",
            "/api/wiki/pages",
            200,
            data=test_page
        )
        
        if success and 'slug' in page_response:
            slug = page_response['slug']
            self.log(f"   Created page with slug: {slug}")
            
            # Get the page
            self.run_test(
                "Get Wiki Page",
                "GET",
                f"/api/wiki/pages/{slug}",
                200
            )
            
            # Update the page
            self.run_test(
                "Update Wiki Page",
                "PUT",
                f"/api/wiki/pages/{slug}",
                200,
                data={"content": "Updated content for iteration 3"}
            )
            
            # Delete the page
            self.run_test(
                "Delete Wiki Page",
                "DELETE",
                f"/api/wiki/pages/{slug}",
                200
            )

    def test_sources_functionality(self):
        """Test sources endpoints"""
        self.log("📄 Testing Sources Functionality...")
        
        # List sources
        self.run_test("List Sources", "GET", "/api/sources", 200)

    def run_all_tests(self):
        """Run all test suites"""
        self.log("🚀 Starting LLM Wiki Dashboard API Tests - Iteration 3")
        self.log(f"📍 Base URL: {self.base_url}")
        
        # Test authentication first
        if not self.test_authentication():
            self.log("❌ Authentication failed - stopping tests")
            return False
        
        # Run all test suites
        self.test_dashboard_stats()
        self.test_providers_crud()
        self.test_models_hub()
        self.test_api_keys_crud()
        self.test_observability()
        self.test_chat_functionality()
        self.test_wiki_crud()
        self.test_sources_functionality()
        
        # Test logout
        self.run_test("Logout", "POST", "/api/auth/logout", 200)
        
        # Print summary
        self.log(f"\n📊 Test Summary:")
        self.log(f"Tests run: {self.tests_run}")
        self.log(f"Tests passed: {self.tests_passed}")
        self.log(f"Tests failed: {self.tests_run - self.tests_passed}")
        self.log(f"Success rate: {(self.tests_passed/self.tests_run)*100:.1f}%")
        
        if self.failed_tests:
            self.log(f"\n❌ Failed Tests:")
            for test in self.failed_tests:
                error_msg = test.get('error', f"Expected {test.get('expected')}, got {test.get('actual')}")
                self.log(f"  - {test['test']}: {error_msg}")
        
        return self.tests_passed == self.tests_run

def main():
    tester = LLMWikiAPITesterV3()
    success = tester.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())