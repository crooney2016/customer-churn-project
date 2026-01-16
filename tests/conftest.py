"""
Pytest configuration and shared fixtures.
"""

import os
import sys
from pathlib import Path
import pandas as pd
import pytest

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Set all required environment variables with dummy test values at module level
# This ensures they're set before any imports that trigger config instantiation
# These can be overridden by individual tests using monkeypatch
_required_test_vars = {
    "SQL_CONNECTION_STRING": "Server=test;Database=test;UID=test;PWD=test;",
    "BLOB_STORAGE_CONNECTION_STRING": (
        "DefaultEndpointsProtocol=https;AccountName=test;"
        "AccountKey=testkey;EndpointSuffix=core.windows.net"
    ),
    "BLOB_STORAGE_CONTAINER_NAME": "churn-feature-data",
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
def mock_blob_client(mocker):
    """
    Mock blob client for testing blob storage operations.

    Returns:
        Tuple of (mock_service_client, mock_container_client, mock_blob_client)
    """
    mock_service = mocker.MagicMock()
    mock_container = mocker.MagicMock()
    mock_blob = mocker.MagicMock()

    mock_service.get_container_client.return_value = mock_container
    mock_service.get_blob_client.return_value = mock_blob

    mocker.patch(
        "function_app.blob_client.BlobServiceClient.from_connection_string",
        return_value=mock_service
    )

    yield mock_service, mock_container, mock_blob


@pytest.fixture
def mock_email_client(mocker):
    """
    Mock email client for testing HTML generation.

    Returns:
        Mock object for email client functions
    """
    mocker.patch("function_app.email_client.send_success_email")
    mocker.patch("function_app.email_client.send_failure_email")
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


# Check if SQL connection is available for integration tests
SQL_CONNECTION_AVAILABLE = (
    os.getenv('SQL_CONNECTION_STRING') is not None and
    os.getenv('SQL_CONNECTION_STRING') != "Server=test;Database=test;UID=test;PWD=test;"
)


@pytest.fixture(scope="session")
def db_schema_setup():
    """
    Set up database schema for integration tests.

    Runs deploy_sql_schema.py to create tables, procedures, and functions.
    Only runs if SQL_CONNECTION_STRING is available.

    Yields:
        bool: True if schema was set up, False if skipped
    """
    if not SQL_CONNECTION_AVAILABLE:
        pytest.skip("SQL_CONNECTION_STRING not available - skipping schema setup")

    try:
        from scripts.deploy_sql_schema import main as deploy_schema
        deploy_schema()
        yield True
    except (ImportError, RuntimeError, ConnectionError) as e:
        pytest.skip(f"Failed to set up database schema: {str(e)}")


@pytest.fixture
def db_connection(db_schema_setup):  # pylint: disable=unused-argument
    """
    Get real database connection for integration tests.

    Skips test if SQL_CONNECTION_STRING is not available.

    Yields:
        pymssql.Connection: Database connection
    """
    if not SQL_CONNECTION_AVAILABLE:
        pytest.skip("SQL_CONNECTION_STRING not available - skipping integration test")

    from scripts.deploy_sql_schema import get_connection

    conn = get_connection()

    try:
        yield conn
    finally:
        conn.close()


@pytest.fixture
def db_cleanup(db_connection):
    """
    Clean up database tables after integration tests.

    Truncates staging table and optionally clears main table.
    """
    cursor = db_connection.cursor()

    # Cleanup function
    def cleanup(tables=None):
        """Truncate specified tables."""
        if tables is None:
            tables = ['ChurnScoresStaging']

        for table in tables:
            try:
                cursor.execute(f"TRUNCATE TABLE dbo.{table};")
                db_connection.commit()
            except Exception:  # pylint: disable=broad-exception-caught
                # Table might not exist or already empty - ignore
                # Intentionally catching all exceptions for cleanup resilience
                db_connection.rollback()

    yield cleanup

    # Final cleanup
    cleanup()
