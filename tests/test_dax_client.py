"""
Unit tests for dax_client.py module.
"""

import pytest
from unittest.mock import patch, MagicMock
import pandas as pd
from function_app.dax_client import (
    normalize_column_names,
    validate_dax_columns,
    get_access_token,
)


def test_normalize_column_names_removes_brackets():
    """Test that normalize_column_names removes square brackets."""
    df = pd.DataFrame({"[CustomerId]": ["123"], "[Segment]": ["FITNESS"]})
    result = normalize_column_names(df)
    assert "CustomerId" in result.columns
    assert "[CustomerId]" not in result.columns


def test_validate_dax_columns_passes_with_required():
    """Test that validate_dax_columns passes with all required columns."""
    df = pd.DataFrame({
        "CustomerId": ["123"],
        "AccountName": ["Account"],
        "Segment": ["FITNESS"],
        "CostCenter": ["CMFIT"],
        "SnapshotDate": ["2024-01-01"],
        # Add enough columns to meet minimum
    })
    # Add dummy columns to reach minimum count
    for i in range(70):
        df[f"Feature_{i}"] = [i]

    # Should not raise
    validate_dax_columns(df)


def test_validate_dax_columns_raises_missing_required():
    """Test that validate_dax_columns raises when required columns are missing."""
    df = pd.DataFrame({
        "CustomerId": ["123"],
        # Missing AccountName, Segment, CostCenter, SnapshotDate
    })

    with pytest.raises(ValueError, match="Missing required columns"):
        validate_dax_columns(df)


def test_get_access_token_success(monkeypatch):
    """Test that get_access_token returns token on success."""
    mock_app = MagicMock()
    mock_app.acquire_token_for_client.return_value = {
        "access_token": "mock_access_token"
    }

    with patch("function_app.dax_client.ConfidentialClientApplication", return_value=mock_app):
        # Mock config
        with patch("function_app.dax_client.config") as mock_config:
            mock_config.PBI_CLIENT_ID = "test_client_id"
            mock_config.PBI_CLIENT_SECRET = "test_secret"
            mock_config.PBI_TENANT_ID = "test_tenant_id"

            token = get_access_token()
            assert token == "mock_access_token"


def test_get_access_token_raises_on_no_token(monkeypatch):
    """Test that get_access_token raises when token is missing."""
    mock_app = MagicMock()
    mock_app.acquire_token_for_client.return_value = {
        "error": "invalid_client",
        "error_description": "Client authentication failed"
    }

    with patch("function_app.dax_client.ConfidentialClientApplication", return_value=mock_app):
        with patch("function_app.dax_client.config") as mock_config:
            mock_config.PBI_CLIENT_ID = "test_client_id"
            mock_config.PBI_CLIENT_SECRET = "test_secret"
            mock_config.PBI_TENANT_ID = "test_tenant_id"

            with pytest.raises(RuntimeError, match="Failed to acquire token"):
                get_access_token()


@pytest.mark.integration
def test_execute_dax_query_integration():
    """
    Integration test for execute_dax_query (requires Power BI connection).

    Marked as integration test - skip in CI without Power BI access.
    """
    pytest.skip("Requires Power BI connection - run locally or in integration test environment")
