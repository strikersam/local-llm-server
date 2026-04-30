#!/usr/bin/env python3
"""
Backend API Testing for LLM Wiki Dashboard
Tests all API endpoints with proper authentication flow
"""

import requests
import sys
import json
import time
from datetime import datetime

class LLMWikiAPITester:
    def __init__(self, base_url="https://feature-spotlight-8.preview.emergentagent.com"):
        self.base_url = base_url
        self.session = requests.Session()
        self.tests_run = 0
        self.tests_passed = 0
        self.failed_tests = []

    def log(self, message):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")

    def run_test(self, name, method, endpoint, expected_status, data=None, files=None):
        """Run a single API test"""
        url = f"{self.base_url}{endpoint}"
        self.tests_run += 1
        
        self.log(f"🔍 Testing {name}...")
        
        try:
            if method == 'GET':
                response = self.session.get(url)
            elif method == 'POST':
                if files:
                    response = self.session.post(url, data=data, files=files)
                elif endpoint == "/api/sources/ingest":
                    # Use form data for source ingestion
                    response = self.session.post(url, data=data)
                else:
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
                    "response": response.text[:500]
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

    def test_health(self):
        """Test health endpoint"""
        return self.run_test("Health Check", "GET", "/api/health", 200)

    def test_login(self):
        """Test login with admin credentials"""
        success, response = self.run_test(
            "Admin Login",
            "POST",
            "/api/auth/login",
            200,
            data={"email": "admin@llmwiki.local", "password": "WikiAdmin2026!"}
        )
        return success

    def test_auth_me(self):
        """Test getting current user info"""
        return self.run_test("Get Current User", "GET", "/api/auth/me", 200)

    def test_stats(self):
        """Test dashboard stats"""
        return self.run_test("Dashboard Stats", "GET", "/api/stats", 200)

    def test_wiki_operations(self):
        """Test wiki CRUD operations"""
        # List wiki pages
        success, _ = self.run_test("List Wiki Pages", "GET", "/api/wiki/pages", 200)
        if not success:
            return False

        # Create wiki page
        wiki_data = {
            "title": "Test Wiki Page",
            "content": "# Test Page\n\nThis is a test wiki page created by automated testing.",
            "tags": ["test", "automation"]
        }
        success, create_response = self.run_test("Create Wiki Page", "POST", "/api/wiki/pages", 200, data=wiki_data)
        if not success:
            return False

        # Get the created page
        if 'slug' in create_response:
            slug = create_response['slug']
            success, _ = self.run_test(f"Get Wiki Page", "GET", f"/api/wiki/pages/{slug}", 200)
            if not success:
                return False

            # Update the page
            update_data = {
                "title": "Updated Test Wiki Page",
                "content": "# Updated Test Page\n\nThis page has been updated.",
                "tags": ["test", "automation", "updated"]
            }
            success, _ = self.run_test("Update Wiki Page", "PUT", f"/api/wiki/pages/{slug}", 200, data=update_data)
            if not success:
                return False

            # Delete the page
            success, _ = self.run_test("Delete Wiki Page", "DELETE", f"/api/wiki/pages/{slug}", 200)
            return success

        return False

    def test_chat_operations(self):
        """Test chat functionality"""
        # List sessions
        success, _ = self.run_test("List Chat Sessions", "GET", "/api/chat/sessions", 200)
        if not success:
            return False

        # Send a chat message (this will create a new session)
        chat_data = {
            "content": "Hello, this is a test message for the wiki agent.",
            "model": "gpt-4o-mini"
        }
        success, chat_response = self.run_test("Send Chat Message", "POST", "/api/chat/send", 200, data=chat_data)
        if not success:
            return False

        # Get the session if created
        if 'session_id' in chat_response:
            session_id = chat_response['session_id']
            success, _ = self.run_test("Get Chat Session", "GET", f"/api/chat/sessions/{session_id}", 200)
            if not success:
                return False

            # Delete the session
            success, _ = self.run_test("Delete Chat Session", "DELETE", f"/api/chat/sessions/{session_id}", 200)
            return success

        return True  # Chat might work without session creation

    def test_source_operations(self):
        """Test source ingestion"""
        # List sources
        success, _ = self.run_test("List Sources", "GET", "/api/sources", 200)
        if not success:
            return False

        # Test text ingestion using multipart form data
        success, source_response = self.run_test("Ingest Text Source", "POST", "/api/sources/ingest", 200, 
                                                data={"content_text": "This is test content for source ingestion testing.", "title": "Test Source"})
        if not success:
            return False

        # Get the source if created
        if '_id' in source_response:
            source_id = source_response['_id']
            success, _ = self.run_test("Get Source", "GET", f"/api/sources/{source_id}", 200)
            if not success:
                return False

            # Delete the source
            success, _ = self.run_test("Delete Source", "DELETE", f"/api/sources/{source_id}", 200)
            return success

        return True

    def test_activity_log(self):
        """Test activity log"""
        return self.run_test("Get Activity Log", "GET", "/api/activity", 200)

    def test_providers(self):
        """Test providers endpoints"""
        return self.run_test("Get Providers", "GET", "/api/providers", 200)

    def test_wiki_lint(self):
        """Test wiki lint functionality"""
        return self.run_test("Wiki Lint", "POST", "/api/wiki/lint", 200)

    def test_logout(self):
        """Test logout"""
        return self.run_test("Logout", "POST", "/api/auth/logout", 200)

    def run_all_tests(self):
        """Run comprehensive API test suite"""
        self.log("🚀 Starting LLM Wiki Dashboard API Tests")
        self.log(f"📍 Base URL: {self.base_url}")
        
        # Test health first
        if not self.test_health()[0]:
            self.log("❌ Health check failed - stopping tests")
            return False

        # Test authentication
        if not self.test_login():
            self.log("❌ Login failed - stopping tests")
            return False

        if not self.test_auth_me()[0]:
            self.log("❌ Auth verification failed")
            return False

        # Test core functionality
        test_functions = [
            self.test_stats,
            self.test_wiki_operations,
            self.test_chat_operations,
            self.test_source_operations,
            self.test_activity_log,
            self.test_providers,
            self.test_wiki_lint,
            self.test_logout
        ]

        for test_func in test_functions:
            try:
                test_func()
                time.sleep(0.5)  # Small delay between tests
            except Exception as e:
                self.log(f"❌ Test {test_func.__name__} failed with exception: {e}")

        # Print results
        self.log(f"\n📊 Test Results: {self.tests_passed}/{self.tests_run} passed")
        
        if self.failed_tests:
            self.log("\n❌ Failed Tests:")
            for failure in self.failed_tests:
                error_msg = failure.get('error', f"Status {failure.get('actual')} != {failure.get('expected')}")
                self.log(f"   - {failure['test']}: {error_msg}")

        return self.tests_passed == self.tests_run

def main():
    tester = LLMWikiAPITester()
    success = tester.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())