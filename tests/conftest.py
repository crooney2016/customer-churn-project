"""
Pytest configuration and shared fixtures.
"""

import os
import pandas as pd
import pytest

# Set all required environment variables with dummy test values at module level
# This ensures they're set before any imports that trigger config instantiation
# These can be overridden by individual tests using monkeypatch
_required_test_vars = {
    "SQL_CONNECTION_STRING": "test_connection_string",
    "PBI_TENANT_ID": "test_pbi_tenant_id",
    "PBI_CLIENT_ID": "test_pbi_client_id",
    "PBI_CLIENT_SECRET": "test_pbi_client_secret",
    "PBI_WORKSPACE_ID": "test_pbi_workspace_id",
    "PBI_DATASET_ID": "test_pbi_dataset_id",
    "EMAIL_TENANT_ID": "test_email_tenant_id",
    "EMAIL_CLIENT_ID": "test_email_client_id",
    "EMAIL_CLIENT_SECRET": "test_email_client_secret",
    "EMAIL_SENDER": "test@example.com",
    "EMAIL_RECIPIENTS": "test@example.com",
}

for key, value in _required_test_vars.items():
    # Only set if not already set (allows tests to override)
    if key not in os.environ:
        os.environ[key] = value


@pytest.fixture
def mock_sql_connection(mocker):
    """
    Mock SQL connection and cursor for testing SQL operations.

    Returns:
        Tuple of (mock_connection, mock_cursor)
    """
    mock_conn = mocker.MagicMock()
    mock_cursor = mocker.MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_conn.commit.return_value = None
    mock_conn.rollback.return_value = None

    mocker.patch("function_app.sql_client.get_connection", return_value=mock_conn)
    yield mock_conn, mock_cursor


@pytest.fixture
def mock_pbi_client(mocker):
    """
    Mock Power BI client for testing DAX queries and dataset refresh.

    Returns:
        Mock object for Power BI client functions
    """
    mocker.patch("function_app.dax_client.get_access_token", return_value="mock_token")
    mocker.patch("function_app.pbi_client.get_access_token", return_value="mock_token")
    yield mocker.MagicMock()


@pytest.fixture
def mock_email_client(mocker):
    """
    Mock email client for testing email notifications.

    Returns:
        Mock object for email client functions
    """
    mocker.patch("function_app.email_client.get_graph_access_token", return_value="mock_token")
    mocker.patch("function_app.email_client.send_email")
    yield mocker.MagicMock()


@pytest.fixture
def sample_input_df():
    """
    Sample input DataFrame with required columns for scoring.

    Returns:
        DataFrame with sample customer data
    """
    return pd.DataFrame({
        "CustomerId": ["001", "002", "003"],
        "AccountName": ["Account A", "Account B", "Account C"],
        "Segment": ["FITNESS", "FARRELL", "FITNESS"],
        "CostCenter": ["CMFIT", "CMFIT", "CMFIT"],
        "SnapshotDate": pd.to_datetime(["2024-01-01", "2024-01-01", "2024-01-01"]),
        "FirstPurchaseDate": pd.to_datetime(["2023-01-01", "2023-06-01", "2022-01-01"]),
        "LastPurchaseDate": pd.to_datetime(["2024-01-01", "2023-12-01", "2024-01-01"]),
        # Sample feature columns
        "Orders_CY": [10, 5, 20],
        "Orders_PY": [8, 4, 18],
        "Orders_Lifetime": [50, 25, 100],
        "Spend_CY": [5000.0, 2500.0, 10000.0],
        "Spend_PY": [4000.0, 2000.0, 9000.0],
        "Spend_Lifetime": [25000.0, 12500.0, 50000.0],
        "Units_CY": [100, 50, 200],
        "AOV_CY": [500.0, 500.0, 500.0],
        "DaysSinceLast": [10, 30, 5],
        "TenureDays": [365, 180, 730],
        "Spend_Trend": [0.25, 0.25, 0.11],
        "Orders_Trend": [0.25, 0.25, 0.11],
        "Units_Trend": [0.25, 0.25, 0.11],
    })


@pytest.fixture
def sample_scored_df():
    """
    Sample scored DataFrame with churn predictions.

    Returns:
        DataFrame with sample scored customer data including ChurnRiskPct and RiskBand
    """
    df = pd.DataFrame({
        "CustomerId": ["001", "002", "003"],
        "AccountName": ["Account A", "Account B", "Account C"],
        "Segment": ["FITNESS", "FARRELL", "FITNESS"],
        "CostCenter": ["CMFIT", "CMFIT", "CMFIT"],
        "SnapshotDate": pd.to_datetime(["2024-01-01", "2024-01-01", "2024-01-01"]),
        "FirstPurchaseDate": pd.to_datetime(["2023-01-01", "2023-06-01", "2022-01-01"]),
        "LastPurchaseDate": pd.to_datetime(["2024-01-01", "2023-12-01", "2024-01-01"]),
        "ChurnRiskPct": [0.15, 0.45, 0.85],
        "RiskBand": ["C - Low Risk", "B - Medium Risk", "A - High Risk"],
        "Reason_1": ["High lifetime spend", "Medium order count", "Low recent orders"],
        "Reason_2": ["Low days since last", "High days since last", "Declining trend"],
        "Reason_3": ["High tenure", "Medium tenure", "Low engagement"],
    })
    return df
