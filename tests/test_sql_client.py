"""
Unit tests for sql_client.py module.
"""

import pytest
import pandas as pd
from unittest.mock import patch, MagicMock
from function_app.sql_client import insert_churn_scores


def test_insert_scores_calls_execute(mock_sql_connection, sample_scored_df):
    """Test that insert_churn_scores calls execute for each row."""
    conn, cursor = mock_sql_connection

    rows_written = insert_churn_scores(sample_scored_df, batch_size=1000)

    # Verify execute was called (at least once per row)
    assert cursor.execute.call_count >= len(sample_scored_df)
    # Verify commit was called (at least once per batch)
    assert conn.commit.called
    # Verify rows_written matches input
    assert rows_written == len(sample_scored_df)


def test_insert_scores_rollback_on_error(mock_sql_connection, sample_scored_df):
    """Test that insert_churn_scores rolls back on error."""
    conn, cursor = mock_sql_connection
    cursor.execute.side_effect = Exception("DB error")

    with pytest.raises(Exception):
        insert_churn_scores(sample_scored_df)

    # Verify rollback was called
    assert conn.rollback.called
    # Verify commit was not called (transaction rolled back)
    assert not conn.commit.called


def test_insert_scores_batches_correctly(mock_sql_connection):
    """Test that insert_churn_scores processes data in batches."""
    conn, cursor = mock_sql_connection

    # Create a larger DataFrame
    large_df = pd.DataFrame({
        "CustomerId": [f"00{i}" for i in range(2500)],
        "ChurnRiskPct": [0.5] * 2500,
        "RiskBand": ["B - Medium Risk"] * 2500,
        "Reason_1": ["Reason 1"] * 2500,
        "Reason_2": ["Reason 2"] * 2500,
        "Reason_3": ["Reason 3"] * 2500,
        "SnapshotDate": pd.to_datetime(["2024-01-01"] * 2500),
        "AccountName": ["Account"] * 2500,
        "Segment": ["FITNESS"] * 2500,
        "CostCenter": ["CMFIT"] * 2500,
        "FirstPurchaseDate": pd.to_datetime(["2023-01-01"] * 2500),
        "LastPurchaseDate": pd.to_datetime(["2024-01-01"] * 2500),
    })

    rows_written = insert_churn_scores(large_df, batch_size=1000)

    # Should process 2500 rows
    assert rows_written == 2500
    # Should have committed multiple times (once per batch)
    assert conn.commit.call_count >= 2  # At least 2 batches (1000 + 1000 + 500)


@pytest.mark.integration
def test_insert_scores_integration(sample_scored_df):
    """
    Integration test for insert_churn_scores (requires actual database).

    Marked as integration test - skip in CI without database.
    """
    pytest.skip("Requires database connection - run locally or in integration test environment")
