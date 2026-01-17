"""
SQL client for writing churn scores to database.
Uses pymssql (FreeTDS-based, no ODBC driver required) for connections.
"""

import logging
import time
from datetime import datetime

import pandas as pd
import pymssql
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from .config import config

# Configure logging per logging.md
logger = logging.getLogger(__name__)

# Connection settings for Azure SQL Serverless (handles cold starts)
CONNECTION_TIMEOUT = 60  # seconds - serverless may take up to 60s to wake
MAX_CONNECTION_RETRIES = 3
BASE_RETRY_DELAY = 5.0  # seconds

# SQL table and procedure names
STAGING_TABLE = "dbo.ChurnScoresStaging"
MAIN_TABLE = "dbo.ChurnScoresHistory"
MERGE_PROCEDURE = "dbo.spMergeChurnScoresFromStaging"

# Required columns for SQL schema (NOT NULL columns)
REQUIRED_COLUMNS = ["CustomerId", "SnapshotDate"]


def _parse_connection_string(connection_string: str) -> dict:
    """
    Parse connection string to pymssql.connect() parameters.

    Expected format: Server=hostname;Port=1433;Database=dbname;UID=username;PWD=password;

    All parameters except Server are optional (Port defaults to 1433).
    """
    params = {}
    for part in connection_string.split(';'):
        part = part.strip()
        if '=' in part:
            key, value = part.split('=', 1)
            key = key.strip().lower()
            value = value.strip()

            if key == 'server':
                params['server'] = value
            elif key == 'port':
                params['port'] = int(value)
            elif key in ['database', 'initial catalog']:
                params['database'] = value
            elif key in ['uid', 'user id', 'user']:
                params['user'] = value
            elif key in ['pwd', 'password']:
                params['password'] = value

    return params


@retry(
    stop=stop_after_attempt(MAX_CONNECTION_RETRIES),
    wait=wait_exponential(multiplier=BASE_RETRY_DELAY, min=BASE_RETRY_DELAY, max=30),
    retry=retry_if_exception_type((pymssql.OperationalError, pymssql.DatabaseError, pymssql.Error)),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
def get_connection() -> pymssql.Connection:
    """
    Get SQL connection using connection string from .env (SQL Server authentication).

    Includes retry logic for Azure SQL Serverless cold starts which can take
    up to 60 seconds to resume from paused state.

    Connection string format: Server=hostname;Port=1433;Database=dbname;UID=username;PWD=password;

    Returns:
        pymssql.Connection: Database connection object
    """
    logger.debug("Establishing SQL database connection")
    connection_string = config.SQL_CONNECTION_STRING

    # Parse connection string to pymssql parameters
    conn_params = _parse_connection_string(connection_string)

    # pymssql.connect() uses keyword arguments
    conn = pymssql.connect(**conn_params, timeout=CONNECTION_TIMEOUT)
    logger.debug("SQL connection established successfully")

    return conn


def _validate_dataframe_schema(df: pd.DataFrame, required_columns: list[str]) -> None:
    """
    Validate DataFrame has required columns for SQL insert.

    Args:
        df: DataFrame to validate
        required_columns: List of required column names

    Raises:
        ValueError: If required columns are missing
    """
    missing = set(required_columns) - set(df.columns)
    if missing:
        raise ValueError(
            f"DataFrame missing required columns: {sorted(missing)}. "
            f"Available columns: {sorted(df.columns)}"
        )


def insert_churn_scores(df: pd.DataFrame, batch_size: int = 5000) -> int:
    """
    Insert churn scores into database using staging table pattern with bulk inserts.

    Uses staging table + MERGE pattern for efficient bulk operations:
    1. Bulk insert into ChurnScoresStaging using executemany()
    2. Call spMergeChurnScoresFromStaging to MERGE into main table
    3. Truncate staging table
    4. All wrapped in a single transaction

    Args:
        df: DataFrame with scored data (columns must match SQL schema)
        batch_size: Number of rows to process per batch (default: 5000)

    Returns:
        Number of rows inserted/updated

    Raises:
        ValueError: If DataFrame is missing required columns
    """
    conn = None
    step = "sql_write"
    total_rows = len(df)
    rows_processed = 0

    if total_rows == 0:
        logger.warning("Step '%s': DataFrame is empty, nothing to insert", step)
        return 0

    # Validate required columns before attempting insert
    try:
        _validate_dataframe_schema(df, REQUIRED_COLUMNS)
        logger.debug(
            "Step '%s': Schema validation passed - required columns present",
            step
        )
    except ValueError as e:
        logger.error(
            "Step '%s': Schema validation failed: %s",
            step,
            str(e)
        )
        raise

    try:
        logger.info(
            "Step '%s': Starting bulk insert for %d rows (batch size: %d)",
            step,
            total_rows,
            batch_size
        )
        conn = get_connection()
        logger.debug("Step '%s': Database connection established", step)
        cursor = conn.cursor()

        start_time = time.time()

        # Build INSERT statement dynamically from DataFrame columns
        # SQL client is schema-agnostic - works with any DataFrame structure
        columns = ', '.join(df.columns)
        placeholders = ', '.join(['?' for _ in df.columns])
        insert_sql = f"INSERT INTO {STAGING_TABLE} ({columns}) VALUES ({placeholders})"

        logger.debug(
            "Step '%s': Built INSERT statement for %d columns",
            step,
            len(df.columns)
        )

        # Process in batches
        for batch_start in range(0, total_rows, batch_size):
            batch_end = min(batch_start + batch_size, total_rows)
            batch_df = df.iloc[batch_start:batch_end]

            logger.debug(
                "Step '%s': Processing batch %d-%d of %d",
                step,
                batch_start + 1,
                batch_end,
                total_rows
            )

            # Prepare data as list of tuples for executemany()
            # Convert each row to tuple, handling NaN/None values
            data_tuples = []
            for row in batch_df.itertuples(index=False):
                row_tuple = []
                for val in row:
                    # Convert NaN/None to None (SQL NULL)
                    if pd.isna(val):
                        row_tuple.append(None)
                    # Convert datetime to date if needed
                    elif isinstance(val, (datetime, pd.Timestamp)):
                        row_tuple.append(val.date())
                    else:
                        row_tuple.append(val)
                data_tuples.append(tuple(row_tuple))

            # Bulk insert using executemany() - much faster than row-by-row
            cursor.executemany(insert_sql, data_tuples)
            rows_processed += len(data_tuples)

            logger.debug(
                "Step '%s': Bulk inserted %d rows into staging table",
                step,
                len(data_tuples)
            )

        # Call MERGE stored procedure to merge staging into main table
        # The procedure handles MERGE, truncate, and transaction internally
        logger.debug("Step '%s': Calling MERGE stored procedure", step)
        cursor.execute(f"EXEC {MERGE_PROCEDURE}")

        # Fetch MERGE results (inserted/updated counts)
        merge_result = cursor.fetchone()
        if merge_result and len(merge_result) >= 3:
            inserted_count = merge_result[0]
            updated_count = merge_result[1]
            total_count = merge_result[2]
            logger.info(
                "Step '%s': MERGE completed - %d inserted, %d updated, %d total",
                step,
                inserted_count,
                updated_count,
                total_count
            )
        else:
            logger.warning(
                "Step '%s': MERGE procedure returned unexpected result format: %s",
                step,
                merge_result
            )

        # Commit entire transaction (stored procedure already committed its transaction,
        # but we commit here to finalize the bulk inserts)
        conn.commit()
        logger.debug("Step '%s': Transaction committed", step)

        duration = time.time() - start_time
        throughput = rows_processed / duration if duration > 0 else 0
        logger.info(
            "Step '%s': Successfully processed %d rows in %.2f seconds (%.2f rows/sec)",
            step,
            rows_processed,
            duration,
            throughput
        )
        return rows_processed

    except Exception as e:
        if conn:
            conn.rollback()
            logger.error(
                "Step '%s': Database transaction rolled back due to error",
                step
            )

        logger.error(
            "Step '%s': Failed to insert churn scores. Rows processed: %d/%d. Error: %s",
            step,
            rows_processed,
            total_rows,
            str(e),
            exc_info=True
        )
        error_msg = (
            f"Failed to insert churn scores after processing "
            f"{rows_processed}/{total_rows} rows: {str(e)}"
        )
        raise RuntimeError(error_msg) from e
    finally:
        if conn:
            conn.close()
            logger.debug("Step '%s': Database connection closed", step)
