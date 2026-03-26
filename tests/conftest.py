import pytest
from api import _api_keys, _settings, invalidate_score_caches

TEST_API_KEY = "sk-sn-test-key-for-tests"


@pytest.fixture(autouse=True)
def inject_test_api_key():
    """Ensure all tests have a valid admin API key available."""
    # Set as admin key so POST/DELETE endpoints accept it
    old_keys = _settings.API_KEYS
    _settings.API_KEYS = TEST_API_KEY
    invalidate_score_caches()
    yield
    _settings.API_KEYS = old_keys
