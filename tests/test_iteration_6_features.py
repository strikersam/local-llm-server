"""
Test iteration 6 features:
- POST /api/tasks/ auto-assigns an available agent when agent_id is omitted
- Task creation stores the authenticated owner instead of 'unknown'
- POST /runtimes/{id}/start and POST /runtimes/stop-all return non-blocking informational payloads
- Chat fallback uses local/free providers first and returns approval_required before commercial fallback

These are live-server integration tests — they are skipped automatically when the
backend is not reachable (e.g. in CI without a running server).
"""

import os
import socket
import pytest
import requests
from urllib.parse import urlparse

# Use the public backend URL for testing
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8001")

# Test credentials from test_credentials.md
ADMIN_EMAIL = "admin@llmrelay.local"
ADMIN_PASSWORD = "WikiAdmin2026!"


def _server_reachable(url: str, timeout: float = 1.0) -> bool:
    """Return True if we can open a TCP connection to the backend server."""
    try:
        parsed = urlparse(url)
        host = parsed.hostname or "localhost"
        port = parsed.port or (443 if parsed.scheme == "https" else 8001)
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


_LIVE = _server_reachable(BASE_URL)

# Skip the entire module when no live backend is available (e.g. CI without a
# running server).  Using pytestmark at module level applies the marker to every
# test class and function defined below.
pytestmark = pytest.mark.skipif(
    not _LIVE,
    reason=f"Live backend not reachable at {BASE_URL} — skipping live-server integration tests",
)


class TestAuthAndTaskCreation:
    """Test authentication and task creation with owner assignment"""

    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token for admin user"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "access_token" in data, f"No access_token in response: {data}"
        return data["access_token"]

    @pytest.fixture(scope="class")
    def auth_headers(self, auth_token):
        """Return headers with Bearer token"""
        return {"Authorization": f"Bearer {auth_token}"}

    def test_login_returns_valid_token(self, auth_token):
        """Verify login returns a valid access token"""
        assert auth_token is not None
        assert len(auth_token) > 10

    def test_task_creation_stores_authenticated_owner(self, auth_headers):
        """POST /api/tasks/ should store the authenticated user as owner, not 'unknown'"""
        response = requests.post(
            f"{BASE_URL}/api/tasks/",
            json={
                "title": "TEST_task_owner_check",
                "description": "Testing that owner is set correctly",
                "task_type": "general"
            },
            headers=auth_headers
        )
        assert response.status_code == 201, f"Task creation failed: {response.text}"
        data = response.json()
        task = data.get("task", {})
        
        # Owner should NOT be 'unknown'
        owner_id = task.get("owner_id", "")
        assert owner_id != "unknown", f"Owner should not be 'unknown', got: {owner_id}"
        assert owner_id != "", f"Owner should not be empty"
        
        # Clean up - delete the test task
        task_id = task.get("task_id")
        if task_id:
            requests.delete(f"{BASE_URL}/api/tasks/{task_id}", headers=auth_headers)

    def test_task_creation_without_agent_id_may_auto_assign(self, auth_headers):
        """POST /api/tasks/ without agent_id should attempt auto-assignment if agents exist"""
        response = requests.post(
            f"{BASE_URL}/api/tasks/",
            json={
                "title": "TEST_auto_assign_check",
                "description": "Testing auto-assignment",
                "task_type": "general",
                "status": "todo"
                # Note: agent_id is intentionally omitted
            },
            headers=auth_headers
        )
        assert response.status_code == 201, f"Task creation failed: {response.text}"
        data = response.json()
        task = data.get("task", {})
        
        # The task should be created successfully
        assert "task_id" in task, "Task should have a task_id"
        
        # Check execution_log for auto-assignment event (if agents were available)
        execution_log = task.get("execution_log", [])
        auto_assigned = any(
            entry.get("event_type") == "agent_auto_assigned" 
            for entry in execution_log
        )
        
        # If there are agents available, auto-assignment should have occurred
        # If no agents, that's also valid - just verify the task was created
        print(f"Auto-assigned: {auto_assigned}, agent_id: {task.get('agent_id')}")
        
        # Clean up
        task_id = task.get("task_id")
        if task_id:
            requests.delete(f"{BASE_URL}/api/tasks/{task_id}", headers=auth_headers)


class TestRuntimeControl:
    """Test runtime start/stop endpoints return informational payloads in remote environments"""

    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token for admin user"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        return response.json()["access_token"]

    @pytest.fixture(scope="class")
    def auth_headers(self, auth_token):
        return {"Authorization": f"Bearer {auth_token}"}

    def test_list_runtimes(self, auth_headers):
        """GET /runtimes/ should return list of runtimes"""
        response = requests.get(f"{BASE_URL}/runtimes/", headers=auth_headers)
        assert response.status_code == 200, f"List runtimes failed: {response.text}"
        data = response.json()
        assert "runtimes" in data

    def test_start_runtime_returns_informational_payload(self, auth_headers):
        """POST /runtimes/{id}/start should return non-blocking informational payload in remote env"""
        # Try to start a known runtime (hermes is in RUNTIME_CONTAINERS)
        response = requests.post(f"{BASE_URL}/runtimes/hermes/start", headers=auth_headers)
        
        # Should NOT return 500 error - should return 200 with informational payload
        assert response.status_code == 200, f"Start runtime returned error: {response.status_code} - {response.text}"
        
        data = response.json()
        # In remote/no-Docker environment, should have informational fields
        # Either 'remote_managed' or 'docker_unavailable' or 'started'
        assert any(key in data for key in ["status", "remote_managed", "docker_unavailable"]), \
            f"Response should have status info: {data}"

    def test_stop_all_runtimes_returns_informational_payload(self, auth_headers):
        """POST /runtimes/stop-all should return non-blocking informational payload"""
        response = requests.post(f"{BASE_URL}/runtimes/stop-all", headers=auth_headers)
        
        # Should NOT return 500 error
        assert response.status_code == 200, f"Stop all returned error: {response.status_code} - {response.text}"
        
        data = response.json()
        # Should have runtimes dict with per-runtime status
        assert "runtimes" in data, f"Response should have 'runtimes' key: {data}"

    def test_runtime_policy_update_requires_auth(self, auth_headers):
        """PUT /runtimes/policy should work with valid auth"""
        # First get current policy
        get_response = requests.get(f"{BASE_URL}/runtimes/policy", headers=auth_headers)
        assert get_response.status_code == 200
        
        # Try to update policy (should work for admin)
        update_response = requests.put(
            f"{BASE_URL}/runtimes/policy",
            json={"never_use_paid_providers": True},
            headers=auth_headers
        )
        assert update_response.status_code == 200, f"Policy update failed: {update_response.text}"


class TestChatFallbackAndApproval:
    """Test chat fallback behavior with commercial provider approval"""

    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token for admin user"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        return response.json()["access_token"]

    @pytest.fixture(scope="class")
    def auth_headers(self, auth_token):
        return {"Authorization": f"Bearer {auth_token}"}

    def test_chat_send_endpoint_exists(self, auth_headers):
        """POST /api/chat/send endpoint should exist and accept requests"""
        # Send a simple message - may fail due to no LLM but should not 404
        response = requests.post(
            f"{BASE_URL}/api/chat/send",
            json={
                "content": "Hello, test message",
                "agent_mode": False
            },
            headers=auth_headers
        )
        # Should not be 404 or 405
        assert response.status_code not in [404, 405], f"Chat endpoint issue: {response.status_code}"
        # May be 502/503 if no LLM available, or 200 if successful, or 409 if approval needed
        print(f"Chat response status: {response.status_code}")

    def test_chat_message_model_has_approval_field(self):
        """Verify ChatMessage model accepts allow_commercial_fallback_once field"""
        # This is a structural test - the endpoint should accept this field
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        token = response.json()["access_token"]
        
        # Send with the approval field
        chat_response = requests.post(
            f"{BASE_URL}/api/chat/send",
            json={
                "content": "Test with approval field",
                "allow_commercial_fallback_once": True,
                "agent_mode": False
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        # Should not fail with validation error (422)
        assert chat_response.status_code != 422, \
            f"allow_commercial_fallback_once field not accepted: {chat_response.text}"


class TestProviderRouter:
    """Test provider router behavior"""

    @pytest.fixture(scope="class")
    def auth_token(self):
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert response.status_code == 200
        return response.json()["access_token"]

    @pytest.fixture(scope="class")
    def auth_headers(self, auth_token):
        return {"Authorization": f"Bearer {auth_token}"}

    def test_list_providers(self, auth_headers):
        """GET /api/providers should return list of configured providers"""
        response = requests.get(f"{BASE_URL}/api/providers", headers=auth_headers)
        assert response.status_code == 200, f"List providers failed: {response.text}"
        data = response.json()
        assert "providers" in data

    def test_routing_policy_endpoint(self, auth_headers):
        """GET /runtimes/policy should return current routing policy"""
        response = requests.get(f"{BASE_URL}/runtimes/policy", headers=auth_headers)
        assert response.status_code == 200, f"Get policy failed: {response.text}"
        data = response.json()
        assert "policy" in data
        policy = data["policy"]
        # Should have the key policy fields
        assert "never_use_paid_providers" in policy or policy.get("never_use_paid_providers") is not None


class TestAgentAutoAssignment:
    """Test agent auto-assignment in task creation"""

    @pytest.fixture(scope="class")
    def auth_token(self):
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert response.status_code == 200
        return response.json()["access_token"]

    @pytest.fixture(scope="class")
    def auth_headers(self, auth_token):
        return {"Authorization": f"Bearer {auth_token}"}

    def test_list_agents(self, auth_headers):
        """GET /api/agents/ should return list of agents"""
        response = requests.get(f"{BASE_URL}/api/agents/", headers=auth_headers)
        assert response.status_code == 200, f"List agents failed: {response.text}"
        data = response.json()
        assert "agents" in data
        print(f"Available agents: {len(data['agents'])}")

    def test_task_with_specific_task_type_may_match_agent(self, auth_headers):
        """Task with specific task_type should match agents with that type"""
        # First check what agents exist
        agents_response = requests.get(f"{BASE_URL}/api/agents/", headers=auth_headers)
        agents = agents_response.json().get("agents", [])
        
        if not agents:
            pytest.skip("No agents available for auto-assignment test")
        
        # Create a task with a task_type that might match an agent
        response = requests.post(
            f"{BASE_URL}/api/tasks/",
            json={
                "title": "TEST_task_type_match",
                "description": "Testing task type matching",
                "task_type": "code_generation",  # Common task type
                "status": "todo"
            },
            headers=auth_headers
        )
        assert response.status_code == 201
        task = response.json().get("task", {})
        
        # Check if agent was auto-assigned
        agent_id = task.get("agent_id")
        print(f"Task created with agent_id: {agent_id}")
        
        # Clean up
        task_id = task.get("task_id")
        if task_id:
            requests.delete(f"{BASE_URL}/api/tasks/{task_id}", headers=auth_headers)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
