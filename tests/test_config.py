"""
Unit tests for config.py module.
"""

import importlib
import sys
from types import ModuleType

import pytest

# Import to ensure module is in sys.modules for reload()
import function_app.config  # pylint: disable=unused-import


def test_config_loads_from_env(monkeypatch):
    """Test that Config loads values from environment variables."""
    monkeypatch.setenv("SQL_CONNECTION_STRING", "test_conn_string")
    monkeypatch.setenv(
        "BLOB_STORAGE_CONNECTION_STRING",
        "DefaultEndpointsProtocol=https;AccountName=test"
    )
    monkeypatch.setenv("BLOB_STORAGE_CONTAINER_NAME", "test-container")

    # Reload config module to pick up new env vars
    config_module: ModuleType = importlib.reload(
        sys.modules['function_app.config']
    )

    config = config_module.Config()
    assert config.SQL_CONNECTION_STRING == "test_conn_string"
    assert config.BLOB_STORAGE_CONTAINER_NAME == "test-container"


def test_config_raises_on_missing_required(monkeypatch):
    """Test that Config raises ValidationError when required fields are missing."""
    # Remove all required env vars
    required_vars = [
        "SQL_CONNECTION_STRING",
        "BLOB_STORAGE_CONNECTION_STRING",
    ]

    for var in required_vars:
        monkeypatch.delenv(var, raising=False)

    # Reloading config module should raise ValueError during module-level instantiation
    with pytest.raises(ValueError, match="Configuration validation failed"):
        importlib.reload(sys.modules['function_app.config'])


def test_config_container_name_has_default(monkeypatch):
    """Test that BLOB_STORAGE_CONTAINER_NAME has a default value."""
    monkeypatch.setenv("SQL_CONNECTION_STRING", "test")
    monkeypatch.setenv("BLOB_STORAGE_CONNECTION_STRING", "test")
    monkeypatch.delenv("BLOB_STORAGE_CONTAINER_NAME", raising=False)

    config_module: ModuleType = importlib.reload(
        sys.modules['function_app.config']
    )

    config = config_module.Config()
    assert config.BLOB_STORAGE_CONTAINER_NAME == "churn-feature-data"


def test_config_logic_app_endpoint_optional(monkeypatch):
    """Test that LOGIC_APP_ENDPOINT is optional."""
    monkeypatch.setenv("SQL_CONNECTION_STRING", "test")
    monkeypatch.setenv("BLOB_STORAGE_CONNECTION_STRING", "test")
    monkeypatch.delenv("LOGIC_APP_ENDPOINT", raising=False)

    config_module: ModuleType = importlib.reload(
        sys.modules['function_app.config']
    )

    config = config_module.Config()
    assert config.LOGIC_APP_ENDPOINT is None


def test_config_validate_method(monkeypatch):
    """Test the validate() method checks required fields."""
    monkeypatch.setenv("SQL_CONNECTION_STRING", "test")
    monkeypatch.setenv("BLOB_STORAGE_CONNECTION_STRING", "test")

    config_module: ModuleType = importlib.reload(
        sys.modules['function_app.config']
    )

    config = config_module.Config()
    # Should not raise
    config.validate()


def test_config_validate_raises_on_empty(monkeypatch):
    """Test that validate() raises on empty required fields."""
    # This test simulates a scenario where fields exist but are empty
    # Pydantic's min_length=1 should catch this during module-level instantiation
    monkeypatch.setenv("SQL_CONNECTION_STRING", "")
    monkeypatch.setenv("BLOB_STORAGE_CONNECTION_STRING", "test")

    # Reloading config module should raise ValueError during module-level instantiation
    with pytest.raises(ValueError, match="Configuration validation failed"):
        importlib.reload(sys.modules['function_app.config'])
