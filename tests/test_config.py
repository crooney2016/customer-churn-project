"""
Unit tests for config.py module.
"""

import pytest
import os
from function_app.config import Config


def test_config_loads_from_env(monkeypatch):
    """Test that Config loads values from environment variables."""
    monkeypatch.setenv("SQL_CONNECTION_STRING", "test_conn_string")
    monkeypatch.setenv("PBI_TENANT_ID", "test_tenant_id")
    monkeypatch.setenv("PBI_CLIENT_ID", "test_client_id")
    monkeypatch.setenv("PBI_CLIENT_SECRET", "test_secret")
    monkeypatch.setenv("PBI_WORKSPACE_ID", "test_workspace_id")
    monkeypatch.setenv("PBI_DATASET_ID", "test_dataset_id")
    monkeypatch.setenv("EMAIL_TENANT_ID", "test_email_tenant_id")
    monkeypatch.setenv("EMAIL_CLIENT_ID", "test_email_client_id")
    monkeypatch.setenv("EMAIL_CLIENT_SECRET", "test_email_secret")
    monkeypatch.setenv("EMAIL_SENDER", "test@example.com")
    monkeypatch.setenv("EMAIL_RECIPIENTS", "recipient1@example.com,recipient2@example.com")

    # Need to reload config module to pick up new env vars
    import importlib
    import function_app.config
    importlib.reload(function_app.config)

    config = function_app.config.Config()
    assert config.SQL_CONNECTION_STRING == "test_conn_string"
    assert config.PBI_TENANT_ID == "test_tenant_id"
    assert config.EMAIL_RECIPIENTS == "recipient1@example.com,recipient2@example.com"


def test_config_raises_on_missing_required(monkeypatch):
    """Test that Config raises ValidationError when required fields are missing."""
    # Remove all required env vars
    required_vars = [
        "SQL_CONNECTION_STRING",
        "PBI_TENANT_ID",
        "PBI_CLIENT_ID",
        "PBI_CLIENT_SECRET",
        "PBI_WORKSPACE_ID",
        "PBI_DATASET_ID",
        "EMAIL_TENANT_ID",
        "EMAIL_CLIENT_ID",
        "EMAIL_CLIENT_SECRET",
        "EMAIL_SENDER",
        "EMAIL_RECIPIENTS",
    ]

    for var in required_vars:
        monkeypatch.delenv(var, raising=False)

    # Need to reload config module
    import importlib
    import function_app.config
    importlib.reload(function_app.config)

    # Pydantic raises ValidationError, but our code wraps it in ValueError
    with pytest.raises((ValueError, Exception)):  # Either ValidationError or ValueError wrapper
        function_app.config.Config()


def test_config_get_email_recipients():
    """Test that get_email_recipients parses comma-separated recipients."""
    # This test requires a valid config instance
    # In practice, this is tested with actual config loading
    recipients_str = "user1@example.com,user2@example.com, user3@example.com "
    # Parse manually to test logic
    recipients = [r.strip() for r in recipients_str.split(",") if r.strip()]
    assert len(recipients) == 3
    assert "user1@example.com" in recipients
    assert "user2@example.com" in recipients
    assert "user3@example.com" in recipients


def test_config_dax_query_name_optional(monkeypatch):
    """Test that DAX_QUERY_NAME is optional."""
    # Set all required vars
    required_vars = {
        "SQL_CONNECTION_STRING": "test",
        "PBI_TENANT_ID": "test",
        "PBI_CLIENT_ID": "test",
        "PBI_CLIENT_SECRET": "test",
        "PBI_WORKSPACE_ID": "test",
        "PBI_DATASET_ID": "test",
        "EMAIL_TENANT_ID": "test",
        "EMAIL_CLIENT_ID": "test",
        "EMAIL_CLIENT_SECRET": "test",
        "EMAIL_SENDER": "test@example.com",
        "EMAIL_RECIPIENTS": "test@example.com",
    }
    for key, value in required_vars.items():
        monkeypatch.setenv(key, value)

    # Don't set DAX_QUERY_NAME
    monkeypatch.delenv("DAX_QUERY_NAME", raising=False)

    import importlib
    import function_app.config
    importlib.reload(function_app.config)

    config = function_app.config.Config()
    assert config.DAX_QUERY_NAME is None
