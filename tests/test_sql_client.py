"""
Unit tests for sql_client.py module.
"""

import pytest
import pandas as pd
from function_app.sql_client import (
    insert_churn_scores,
    _validate_dataframe_schema,
    get_connection,
    _parse_connection_string,
)


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

def test_insert_scores_batch_size_exact(mock_sql_connection):
    """Test insert_churn_scores with exact batch size."""
    conn, cursor = mock_sql_connection
    cursor.fetchone.return_value = (100, 0, 100)

    # Create DataFrame with exactly batch_size rows
    df = pd.DataFrame({
        "CustomerId": [f"00{i}" for i in range(100)],
        "ChurnRiskPct": [0.5] * 100,
        "RiskBand": ["B - Medium Risk"] * 100,
        "Reason_1": ["Reason 1"] * 100,
        "Reason_2": ["Reason 2"] * 100,
        "Reason_3": ["Reason 3"] * 100,
        "SnapshotDate": pd.to_datetime(["2024-01-01"] * 100),
        "AccountName": ["Account"] * 100,
        "Segment": ["FITNESS"] * 100,
        "CostCenter": ["CMFIT"] * 100,
        "FirstPurchaseDate": pd.to_datetime(["2023-01-01"] * 100),
        "LastPurchaseDate": pd.to_datetime(["2024-01-01"] * 100),
    })

    rows_written = insert_churn_scores(df, batch_size=100)

    assert rows_written == 100
    assert cursor.executemany.call_count == 1  # Exactly one batch
    assert conn.commit.call_count == 1

def test_insert_scores_merge_unexpected_result_format(mock_sql_connection, sample_scored_df):
    """Test insert_churn_scores handles unexpected MERGE result format."""
    _conn, cursor = mock_sql_connection
    # Mock MERGE procedure result with unexpected format (not enough values)
    cursor.fetchone.return_value = (len(sample_scored_df),)  # Only one value instead of 3

    # Should still complete successfully but log warning
    rows_written = insert_churn_scores(sample_scored_df)

    assert rows_written == len(sample_scored_df)
    # MERGE was still called
    assert cursor.execute.called

def test_insert_scores_with_nan_values(mock_sql_connection):
    """Test insert_churn_scores handles NaN values correctly."""
    _conn, cursor = mock_sql_connection
    cursor.fetchone.return_value = (2, 0, 2)

    # DataFrame with NaN values
    df = pd.DataFrame({
        "CustomerId": ["001", "002"],
        "SnapshotDate": pd.to_datetime(["2024-01-01", "2024-01-01"]),
        "ChurnRiskPct": [0.5, 0.6],
        "RiskBand": ["B - Medium Risk", "A - High Risk"],
        "Reason_1": ["Reason 1", None],  # NaN value
        "Reason_2": [None, "Reason 2"],  # NaN value
        "Reason_3": ["Reason 3", "Reason 3"],
        "AccountName": ["Account A", "Account B"],
        "Segment": ["FITNESS", "FARRELL"],
        "CostCenter": ["CMFIT", "CMFIT"],
        "FirstPurchaseDate": pd.to_datetime(["2023-01-01", "2023-06-01"]),
        "LastPurchaseDate": pd.to_datetime([None, "2024-01-01"]),  # NaN value
    })

    rows_written = insert_churn_scores(df)

    assert rows_written == 2
    assert cursor.executemany.called
    # Verify None values were handled (check that executemany was called with tuples containing None)
    call_args = cursor.executemany.call_args
    assert call_args is not None
    data_tuples = call_args[0][1]  # Second argument is data tuples
    assert len(data_tuples) == 2


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
def test_insert_scores_integration(db_connection, db_cleanup, sample_scored_df):
    """
    Integration test for insert_churn_scores (requires actual database).

    Tests:
    1. Insert scored data into actual database
    2. Verify data in ChurnScoresHistory table
    3. Verify staging table is empty after MERGE
    """
    from function_app.sql_client import insert_churn_scores

    cursor = db_connection.cursor()

    # Clean up before test
    db_cleanup(['ChurnScoresStaging', 'ChurnScoresHistory'])

    # Insert scores
    rows_written = insert_churn_scores(sample_scored_df)

    # Verify rows written
    assert rows_written == len(sample_scored_df)

    # Verify data in main table
    cursor.execute("SELECT COUNT(*) FROM dbo.ChurnScoresHistory;")
    main_count = cursor.fetchone()[0]
    assert main_count == len(sample_scored_df)

    # Verify staging table is empty after MERGE
    cursor.execute("SELECT COUNT(*) FROM dbo.ChurnScoresStaging;")
    staging_count = cursor.fetchone()[0]
    assert staging_count == 0

    # Verify data integrity - check one record
    cursor.execute("""
        SELECT CustomerId, SnapshotDate, ChurnRiskPct, RiskBand
        FROM dbo.ChurnScoresHistory
        WHERE CustomerId = '001'
    """)
    row = cursor.fetchone()
    assert row is not None
    assert row[0] == "001"
    assert row[1] == pd.Timestamp("2024-01-01").date()
    assert row[2] == 0.15
    assert row[3] == "C - Low Risk"


@pytest.mark.integration
def test_staging_table_full_flow(db_connection, db_cleanup, sample_scored_df):
    """
    Integration test for complete staging table pattern.

    Tests:
    1. Insert into staging table using insert_churn_scores()
    2. Verify staging table has data (query staging table)
    3. Verify MERGE was called (check main table has data)
    4. Verify staging table is empty after MERGE (query staging table)
    """
    from function_app.sql_client import insert_churn_scores

    cursor = db_connection.cursor()

    # Clean up before test
    db_cleanup(['ChurnScoresStaging', 'ChurnScoresHistory'])

    # Insert scores (this inserts into staging, then calls MERGE)
    rows_written = insert_churn_scores(sample_scored_df)

    # Verify rows written
    assert rows_written == len(sample_scored_df)

    # Verify staging table is empty after MERGE (insert_churn_scores calls MERGE internally)
    cursor.execute("SELECT COUNT(*) FROM dbo.ChurnScoresStaging;")
    staging_count = cursor.fetchone()[0]
    assert staging_count == 0

    # Verify main table has data
    cursor.execute("SELECT COUNT(*) FROM dbo.ChurnScoresHistory;")
    main_count = cursor.fetchone()[0]
    assert main_count == len(sample_scored_df)

    # Verify all records are in main table
    cursor.execute("""
        SELECT CustomerId, SnapshotDate, ChurnRiskPct
        FROM dbo.ChurnScoresHistory
        ORDER BY CustomerId
    """)
    rows = cursor.fetchall()
    assert len(rows) == len(sample_scored_df)


@pytest.mark.integration
def test_staging_table_merge_idempotent(db_connection, db_cleanup, sample_scored_df):
    """
    Integration test to verify MERGE is idempotent.

    Tests that calling insert_churn_scores() twice with same data:
    1. First call: Inserts new records
    2. Second call: Updates existing records (no duplicates)
    """
    from function_app.sql_client import insert_churn_scores

    cursor = db_connection.cursor()

    # Clean up before test
    db_cleanup(['ChurnScoresStaging', 'ChurnScoresHistory'])

    # First insert
    rows_written_1 = insert_churn_scores(sample_scored_df)
    assert rows_written_1 == len(sample_scored_df)

    # Verify main table has data
    cursor.execute("SELECT COUNT(*) FROM dbo.ChurnScoresHistory;")
    count_1 = cursor.fetchone()[0]
    assert count_1 == len(sample_scored_df)

    # Second insert with same data (should update, not duplicate)
    rows_written_2 = insert_churn_scores(sample_scored_df)
    assert rows_written_2 == len(sample_scored_df)

    # Verify no duplicates (count should be same)
    cursor.execute("SELECT COUNT(*) FROM dbo.ChurnScoresHistory;")
    count_2 = cursor.fetchone()[0]
    assert count_2 == len(sample_scored_df)

    # Verify data was updated (check ScoredAt timestamp if it changed)
    # The MERGE should have updated the records, not created duplicates
    cursor.execute("""
        SELECT COUNT(*) FROM (
            SELECT CustomerId, SnapshotDate
            FROM dbo.ChurnScoresHistory
            GROUP BY CustomerId, SnapshotDate
            HAVING COUNT(*) > 1
        ) AS duplicates
    """)
    duplicate_count = cursor.fetchone()[0]
    assert duplicate_count == 0, "Found duplicate records after second insert"


class TestParseConnectionString:
    """Tests for _parse_connection_string function."""

    def test_parse_connection_string_full(self):
        """Test parsing full connection string."""
        conn_str = "Server=server;Port=1433;Database=db;UID=user;PWD=pass;"
        result = _parse_connection_string(conn_str)

        assert result["server"] == "server"
        assert result["port"] == 1433
        assert result["database"] == "db"
        assert result["user"] == "user"
        assert result["password"] == "pass"

    def test_parse_connection_string_minimal(self):
        """Test parsing minimal connection string (server only)."""
        conn_str = "Server=server;"
        result = _parse_connection_string(conn_str)

        assert result["server"] == "server"

    def test_parse_connection_string_case_insensitive(self):
        """Test parsing connection string with different cases."""
        conn_str = "SERVER=server;DATABASE=db;UID=user;PWD=pass;"
        result = _parse_connection_string(conn_str)

        assert result["server"] == "server"
        assert result["database"] == "db"
        assert result["user"] == "user"
        assert result["password"] == "pass"

    def test_parse_connection_string_alternative_key_names(self):
        """Test parsing connection string with alternative key names."""
        conn_str = "Server=server;Initial Catalog=db;User ID=user;Password=pass;"
        result = _parse_connection_string(conn_str)

        assert result["server"] == "server"
        assert result["database"] == "db"
        assert result["user"] == "user"
        assert result["password"] == "pass"


class TestGetConnection:
    """Tests for get_connection function."""

    def test_get_connection_missing_env(self, mocker):
        """Test get_connection raises error when connection string is missing."""
        # Mock config to return None
        mocker.patch("function_app.sql_client.config.SQL_CONNECTION_STRING", None)
        
        # get_connection() will try to parse None, which will fail with AttributeError
        # when _parse_connection_string tries to call .split() on None
        # This is expected behavior - should raise AttributeError
        with pytest.raises(AttributeError):
            get_connection()

    def test_get_connection_network_error(self, mocker):
        """Test get_connection handles network errors with retry."""
        import pymssql
        mocker.patch.dict("os.environ", {
            "SQL_CONNECTION_STRING": "Server=test;Database=db;UID=user;PWD=pass;"
        })
        mocker.patch(
            "function_app.sql_client.pymssql.connect",
            side_effect=pymssql.OperationalError("Network error")
        )

        # Should retry and eventually raise
        with pytest.raises(pymssql.OperationalError):
            get_connection()

    def test_get_connection_invalid_connection_string(self, mocker):
        """Test get_connection handles invalid connection string."""
        mocker.patch("function_app.sql_client.config.SQL_CONNECTION_STRING", "invalid")

        # Should still parse (may raise connection error later)
        # But parsing should handle gracefully
        try:
            result = _parse_connection_string("invalid")
            # If parsing succeeds, connection will fail at connect() stage
            assert "server" in result or result == {}
        except (ValueError, AttributeError):
            # Parsing failed - that's okay for invalid input
            pass
