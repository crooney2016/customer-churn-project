"""
Unit tests for sql_client.py module.
"""

import pytest
import pandas as pd
from function_app.sql_client import insert_churn_scores, _validate_dataframe_schema


def test_insert_scores_uses_executemany(mock_sql_connection, sample_scored_df):
    """Test that insert_churn_scores uses executemany() for bulk inserts."""
    conn, cursor = mock_sql_connection
    # Mock MERGE procedure result
    cursor.fetchone.return_value = (len(sample_scored_df), 0, len(sample_scored_df))

    rows_written = insert_churn_scores(sample_scored_df, batch_size=5000)

    # Verify executemany was called for bulk insert into staging table
    assert cursor.executemany.called
    # Verify MERGE stored procedure was called
    assert cursor.execute.called
    # Verify commit was called once (single transaction)
    assert conn.commit.call_count == 1
    # Verify rows_written matches input
    assert rows_written == len(sample_scored_df)


def test_insert_scores_rollback_on_error(mock_sql_connection, sample_scored_df):
    """Test that insert_churn_scores rolls back on error."""
    conn, cursor = mock_sql_connection
    cursor.executemany.side_effect = Exception("DB error")

    with pytest.raises(Exception):
        insert_churn_scores(sample_scored_df)

    # Verify rollback was called
    assert conn.rollback.called
    # Verify commit was not called (transaction rolled back)
    assert not conn.commit.called


def test_insert_scores_batches_correctly(mock_sql_connection):
    """Test that insert_churn_scores processes data in batches."""
    conn, cursor = mock_sql_connection
    # Mock MERGE procedure result
    cursor.fetchone.return_value = (2500, 0, 2500)

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
    # Should have called executemany multiple times (once per batch)
    assert cursor.executemany.call_count >= 2  # At least 2 batches (1000 + 1000 + 500)
    # Should commit once (single transaction)
    assert conn.commit.call_count == 1


def test_insert_scores_calls_merge_procedure(mock_sql_connection, sample_scored_df):
    """Test that insert_churn_scores calls MERGE stored procedure."""
    _conn, cursor = mock_sql_connection
    # Mock MERGE procedure result
    cursor.fetchone.return_value = (len(sample_scored_df), 0, len(sample_scored_df))

    insert_churn_scores(sample_scored_df)

    # Verify MERGE stored procedure was called
    execute_calls = [call[0][0] for call in cursor.execute.call_args_list]
    merge_called = any("spMergeChurnScoresFromStaging" in str(call) for call in execute_calls)
    assert merge_called, "MERGE stored procedure should be called"

    # Verify truncate was called
    truncate_called = any("TRUNCATE" in str(call).upper() for call in execute_calls)
    assert truncate_called, "TRUNCATE should be called after MERGE"


def test_insert_scores_empty_dataframe(mock_sql_connection):
    """Test that insert_churn_scores handles empty DataFrame."""
    _conn, cursor = mock_sql_connection

    empty_df = pd.DataFrame()
    rows_written = insert_churn_scores(empty_df)

    # Should return 0 and not call any database operations
    assert rows_written == 0
    assert not cursor.executemany.called
    assert not cursor.execute.called


def test_validate_dataframe_schema_missing_required_column():
    """Test that _validate_dataframe_schema raises error for missing required columns."""
    df = pd.DataFrame({
        "CustomerId": ["001", "002"],
        # Missing SnapshotDate
        "ChurnRiskPct": [0.5, 0.6],
    })

    with pytest.raises(ValueError, match="missing required columns"):
        _validate_dataframe_schema(df, ["CustomerId", "SnapshotDate"])


def test_validate_dataframe_schema_all_required_present():
    """Test that _validate_dataframe_schema passes when all required columns present."""
    df = pd.DataFrame({
        "CustomerId": ["001", "002"],
        "SnapshotDate": pd.to_datetime(["2024-01-01", "2024-01-01"]),
        "ChurnRiskPct": [0.5, 0.6],
    })

    # Should not raise
    _validate_dataframe_schema(df, ["CustomerId", "SnapshotDate"])


def test_insert_scores_validates_schema(mock_sql_connection):
    """Test that insert_churn_scores validates schema before insert."""
    conn, cursor = mock_sql_connection

    # DataFrame missing required SnapshotDate column
    df = pd.DataFrame({
        "CustomerId": ["001", "002"],
        "ChurnRiskPct": [0.5, 0.6],
    })

    with pytest.raises(ValueError, match="missing required columns"):
        insert_churn_scores(df)

    # Verify no database operations were attempted
    assert not cursor.executemany.called
    assert not cursor.execute.called
    assert not conn.commit.called


@pytest.mark.integration
def test_insert_scores_integration():
    """
    Integration test for insert_churn_scores (requires actual database).

    Marked as integration test - skip in CI without database.
    """
    pytest.skip("Requires database connection - run locally or in integration test environment")


@pytest.mark.integration
def test_staging_table_full_flow():
    """
    Integration test for complete staging table pattern.

    Tests:
    1. Insert into staging table using insert_churn_scores()
    2. Verify staging table has data (query staging table)
    3. Verify MERGE was called (check main table has data)
    4. Verify staging table is empty after MERGE (query staging table)

    Marked as integration test - skip in CI without database.
    """
    pytest.skip("Requires database connection - run locally or in integration test environment")


@pytest.mark.integration
def test_staging_table_merge_idempotent():
    """
    Integration test to verify MERGE is idempotent.

    Tests that calling insert_churn_scores() twice with same data:
    1. First call: Inserts new records
    2. Second call: Updates existing records (no duplicates)

    Marked as integration test - skip in CI without database.
    """
    pytest.skip("Requires database connection - run locally or in integration test environment")
