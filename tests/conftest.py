import os
import sys
from unittest.mock import MagicMock, AsyncMock

# Set environment variables BEFORE importing the app
os.environ["MONGO_URL"] = "mongodb://mongomock://localhost"
os.environ["JWT_SECRET"] = "test-secret-for-tests-only"
os.environ["ADMIN_EMAIL"] = "admin@llmrelay.local"
os.environ["ADMIN_PASSWORD"] = "WikiAdmin2026!"
os.environ["ADMIN_SECRET"] = "test-admin-secret"  # Enable admin login
os.environ["EMERGENT_LLM_KEY"] = "test-key-for-testing"
os.environ["DB_NAME"] = "llm_wiki_dashboard"
os.environ["V3_ADMIN_PASSWORD"] = "test-v3-password"
os.environ["V3_ADMIN_EMAIL"] = "admin@v3.test.local"
os.environ["V3_JWT_SECRET"] = "test-v3-jwt-secret"

# Mock motor modules to avoid connection errors
mock_motor = MagicMock()
mock_motor_asyncio = MagicMock()
mock_motor_tornado = MagicMock()

mock_client = MagicMock()
mock_database = MagicMock()
mock_providers_collection = MagicMock()
mock_users_collection = MagicMock()

mock_client.__getitem__.return_value = mock_database
mock_client.get_database.return_value = mock_database
mock_database.providers = mock_providers_collection
mock_database.users = mock_users_collection

mock_motor_asyncio.AsyncIOMotorClient.return_value = mock_client
mock_motor_tornado.AsyncIOMotorClient.return_value = mock_client

mock_motor.motor_asyncio = mock_motor_asyncio
mock_motor.motor_tornado = mock_motor_tornado

sys.modules['motor'] = mock_motor
sys.modules['motor.motor_asyncio'] = mock_motor_asyncio
sys.modules['motor.motor_tornado'] = mock_motor_tornado

# Now we can import the app and the hash_password function
from backend.server import app, hash_password

# Provide a TestClient for the app
from fastapi.testclient import TestClient
import pytest

# We need to mock the collection methods and ensure_bootstrap to return the expected values
# We'll do this in a fixture that runs before each test
@pytest.fixture(autouse=True)
def setup_database_moks(monkeypatch):
    # Mock ensure_bootstrap to do nothing
    async def mock_ensure_bootstrap():
        return None
    monkeypatch.setattr('backend.server.ensure_bootstrap', mock_ensure_bootstrap)
    
    # Reset the mock collections for each test
    mock_providers_collection.reset_mock()
    mock_users_collection.reset_mock()
    mock_client.reset_mock()
    mock_motor_asyncio.reset_mock()
    mock_motor_tornado.reset_mock()
    
    # We need to mock the find method to return an async iterable when chained with sort
    # Let's create a mock for the cursor that is an async iterable
    class MockCursor:
        def __init__(self, data):
            self.data = data
            self.index = 0
        
        def sort(self, *args, **kwargs):
            # For simplicity, we ignore the sort args and just return self
            return self
        
        def __aiter__(self):
            return self
        
        async def __anext__(self):
            if self.index < len(self.data):
                result = self.data[self.index]
                self.index += 1
                return result
            else:
                raise StopAsyncIteration
    
    # Now, we make the find method return an instance of MockCursor for providers
    mock_providers_collection.find.return_value = MockCursor([{
        "provider_id": "anthropic-universal",
        "name": "Anthropic (Universal Key)",
        "type": "emergent-anthropic",
        "base_url": "emergent://anthropic",
        "api_key": "test-key-for-testing",
        "default_model": "claude-3-5-sonnet-20240620",
        "is_default": False,
        "priority": 55,
        "status": "configured",
        "created_at": "2026-05-01T00:00:00Z"
    }])
    
    # Also, we need to mock find_one to return None so that the provider is inserted (since it doesn't exist)
    mock_providers_collection.find_one.return_value = None
    
    # Make insert_one and update_one async mocks for providers
    mock_providers_collection.insert_one = AsyncMock(return_value=None)
    mock_providers_collection.update_one = AsyncMock(return_value=None)
    # Mock create_index for the bootstrap
    mock_providers_collection.create_index = AsyncMock(return_value=None)
    
    # For the users collection, we want to return a user that matches the test credentials
    # We'll use a fixed valid ObjectId string for the _id
    fake_object_id = "000000000000000000000000"
    hashed_pw = hash_password("WikiAdmin2026!")
    async def mock_find_one(query):
        # print(f"[DEBUG] mock_find_one called with query: {query}")  # Uncomment for debugging
        if "email" in query:
            # print("[DEBUG] Returning user for email query")  # Uncomment for debugging
            return {
                "_id": fake_object_id,
                "email": "admin@llmrelay.local",
                "password_hash": hashed_pw,
                "name": "Admin",
                "role": "admin",
            }
        elif "_id" in query:
            # Convert the query's _id to string for comparison
            if str(query["_id"]) == fake_object_id:
                # print("[DEBUG] Returning user for _id query")  # Uncomment for debugging
                return {
                    "_id": fake_object_id,
                    "email": "admin@llmrelay.local",
                    "password_hash": hashed_pw,
                    "name": "Admin",
                    "role": "admin",
                }
            else:
                # print(f"[DEBUG] Returning None for _id query: {query['_id']}")  # Uncomment for debugging
                return None
        else:
            # print(f"[DEBUG] Returning None for unknown query: {query}")  # Uncomment for debugging
            return None
    
    mock_users_collection.find_one = mock_find_one
    
    yield
    
    # After the test, we can check if the mocks were called as expected if needed

@pytest.fixture
def wiki_client():
    return TestClient(app)
