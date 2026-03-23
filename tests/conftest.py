import pytest
from api import _api_keys

TEST_API_KEY = "sk-sn-test-key-for-tests"


@pytest.fixture(autouse=True)
def inject_test_api_key():
    """Ensure all tests have a valid API key available."""
    _api_keys[TEST_API_KEY] = {"email": "test@test.com", "created_at": "2026-01-01T00:00:00Z"}
    yield
    _api_keys.pop(TEST_API_KEY, None)
