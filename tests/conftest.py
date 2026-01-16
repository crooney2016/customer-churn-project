"""
Pytest configuration and shared fixtures.
"""

import pytest
from unittest.mock import MagicMock, patch
import pandas as pd
import numpy as np


@pytest.fixture
def mock_sql_connection():
    """
    Mock SQL connection and cursor for testing SQL operations.

    Returns:
        Tuple of (mock_connection, mock_cursor)
    """
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_conn.commit.return_value = None
    mock_conn.rollback.return_value = None

    with patch("function_app.sql_client.get_connection", return_value=mock_conn):
        yield mock_conn, mock_cursor


@pytest.fixture
def mock_pbi_client():
    """
    Mock Power BI client for testing DAX queries and dataset refresh.

    Returns:
        Mock object for Power BI client functions
    """
    with patch("function_app.dax_client.get_access_token", return_value="mock_token"):
        with patch("function_app.pbi_client.get_access_token", return_value="mock_token"):
            yield MagicMock()


@pytest.fixture
def mock_email_client():
    """
    Mock email client for testing email notifications.

    Returns:
        Mock object for email client functions
    """
    with patch("function_app.email_client.get_graph_access_token", return_value="mock_token"):
        with patch("function_app.email_client.send_email"):
            yield MagicMock()


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
