"""
SQL client for writing churn scores to database.
Uses azure-identity for authentication and pyodbc for connections.
"""

import logging
import time
from datetime import datetime, date
from typing import Any, Optional, Union
import pandas as pd
import pyodbc

from .config import config

# Configure logging per logging.md
logger = logging.getLogger(__name__)


def get_connection() -> pyodbc.Connection:
    """Get SQL connection using connection string from .env (SQL Server authentication)."""
    logger.debug("Establishing SQL database connection")
    connection_string = config.SQL_CONNECTION_STRING

    # Use direct SQL Server authentication from connection string in .env
    # Connection string format:
    # Driver={ODBC Driver 18 for SQL Server};Server=...;Database=...;UID=...;PWD=...;
    conn = pyodbc.connect(connection_string, timeout=30)
    logger.debug("SQL connection established successfully")

    return conn


def insert_churn_scores(df: pd.DataFrame, batch_size: int = 1000) -> int:
    """
    Insert churn scores into database using stored procedure in batches.

    Args:
        df: DataFrame with scored data (must include all required columns)
        batch_size: Number of rows to process per batch (default: 1000)

    Returns:
        Number of rows inserted/updated
    """
    conn = None
    step = "sql_write"
    rows_processed = 0
    total_rows = len(df)

    # Helper function to safely convert date
    def safe_date_convert(val: Union[str, date, datetime, int, float, None]) -> Optional[date]:
        if val is None:
            return None
        try:
            if pd.isna(val):  # type: ignore[arg-type]
                return None
            dt = pd.to_datetime(val)  # type: ignore[arg-type]
            return dt.date()  # type: ignore[return-value]
        except (ValueError, TypeError):
            return None

    # Helper function to safely convert to float
    def safe_float(val: Union[str, int, float, None]) -> Optional[float]:
        if val is None:
            return None
        try:
            if pd.isna(val):  # type: ignore[arg-type]
                return None
            return float(val)  # type: ignore[arg-type]
        except (ValueError, TypeError):
            return None

    # Helper function to safely convert to string
    def safe_str(val: Union[str, int, float, None]) -> Optional[str]:
        if val is None:
            return None
        try:
            if pd.isna(val):  # type: ignore[arg-type]
                return None
            return str(val)  # type: ignore[arg-type]
        except (ValueError, TypeError):
            return None

    try:
        logger.info(
            "Step '%s': Starting database write for %d rows (batch size: %d)",
            step,
            total_rows,
            batch_size
        )
        conn = get_connection()
        logger.debug("Step '%s': Database connection established", step)
        cursor = conn.cursor()

        start_time = time.time()

        # Helper function to safely get attribute from named tuple (defined outside loop for performance)
        def get_attr(row_obj: Any, attr: str, default: Any = None) -> Any:
            """Safely get attribute from named tuple, returning default if missing."""
            return getattr(row_obj, attr, default)

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

            # Use itertuples() instead of iterrows() for 10-100× better performance
            # itertuples returns named tuples with column names as attributes
            for row in batch_df.itertuples(index=False):

                # Prepare parameters for stored procedure
                # Extract values and handle None properly
                snapshot_date_val = get_attr(row, 'SnapshotDate')
                first_purchase_val = get_attr(row, 'FirstPurchaseDate')
                last_purchase_val = get_attr(row, 'LastPurchaseDate')
                churn_risk_val = get_attr(row, 'ChurnRiskPct')
                risk_band_val = get_attr(row, 'RiskBand')
                reason_1_val = get_attr(row, 'Reason_1')
                reason_2_val = get_attr(row, 'Reason_2')
                reason_3_val = get_attr(row, 'Reason_3')
                account_name_val = get_attr(row, 'AccountName')
                segment_val = get_attr(row, 'Segment')
                cost_center_val = get_attr(row, 'CostCenter')
                customer_id_val = get_attr(row, 'CustomerId', '')

                params = {
                    '@CustomerId': str(customer_id_val),
                    '@SnapshotDate': safe_date_convert(snapshot_date_val),
                    '@ChurnRiskPct': safe_float(churn_risk_val),
                    '@RiskBand': safe_str(risk_band_val),
                    '@Reason_1': safe_str(reason_1_val),
                    '@Reason_2': safe_str(reason_2_val),
                    '@Reason_3': safe_str(reason_3_val),
                    '@ScoredAt': datetime.now(),
                    '@AccountName': safe_str(account_name_val),
                    '@Segment': safe_str(segment_val),
                    '@CostCenter': safe_str(cost_center_val),
                    '@FirstPurchaseDate': safe_date_convert(first_purchase_val),
                    '@LastPurchaseDate': safe_date_convert(last_purchase_val),
                }

                # Add all feature columns
                feature_cols = [
                    'Orders_CY', 'Orders_PY', 'Orders_Lifetime',
                    'Spend_CY', 'Spend_PY', 'Spend_Lifetime',
                    'Units_CY', 'Units_PY', 'Units_Lifetime',
                    'AOV_CY', 'DaysSinceLast', 'TenureDays',
                    'Spend_Trend', 'Orders_Trend', 'Units_Trend',
                    'Uniforms_Units_CY', 'Uniforms_Units_PY', 'Uniforms_Units_Lifetime',
                    'Uniforms_Spend_CY', 'Uniforms_Spend_PY', 'Uniforms_Spend_Lifetime',
                    'Uniforms_Orders_CY', 'Uniforms_Orders_Lifetime',
                    'Uniforms_DaysSinceLast', 'Uniforms_Pct_of_Total_CY',
                    'Sparring_Units_CY', 'Sparring_Units_PY', 'Sparring_Units_Lifetime',
                    'Sparring_Spend_CY', 'Sparring_Spend_PY', 'Sparring_Spend_Lifetime',
                    'Sparring_Orders_CY', 'Sparring_Orders_Lifetime',
                    'Sparring_DaysSinceLast', 'Sparring_Pct_of_Total_CY',
                    'Belts_Units_CY', 'Belts_Units_PY', 'Belts_Units_Lifetime',
                    'Belts_Spend_CY', 'Belts_Spend_PY', 'Belts_Spend_Lifetime',
                    'Belts_Orders_CY', 'Belts_Orders_Lifetime',
                    'Belts_DaysSinceLast', 'Belts_Pct_of_Total_CY',
                    'Bags_Units_CY', 'Bags_Units_PY', 'Bags_Units_Lifetime',
                    'Bags_Spend_CY', 'Bags_Spend_PY', 'Bags_Spend_Lifetime',
                    'Bags_Orders_CY', 'Bags_Orders_Lifetime',
                    'Bags_DaysSinceLast', 'Bags_Pct_of_Total_CY',
                    'Customs_Units_CY', 'Customs_Units_PY', 'Customs_Units_Lifetime',
                    'Customs_Spend_CY', 'Customs_Spend_PY', 'Customs_Spend_Lifetime',
                    'Customs_Orders_CY', 'Customs_Orders_Lifetime',
                    'Customs_DaysSinceLast', 'Customs_Pct_of_Total_CY',
                    'CUBS_Categories_Active_CY', 'CUBS_Categories_Active_PY',
                    'CUBS_Categories_Ever', 'CUBS_Categories_Trend',
                ]

                for col in feature_cols:
                    param_name = f'@{col}'
                    value = get_attr(row, col)

                    # Check if value is None or NaN
                    if value is None or (isinstance(value, (float, int)) and pd.isna(value)):
                        params[param_name] = None
                        continue

                    # Convert to appropriate type
                    try:
                        if 'Pct' in col or 'Trend' in col:
                            params[param_name] = float(value)  # type: ignore[arg-type]
                        elif ('Date' in col or 'Days' in col or
                              col.endswith(('_CY', '_PY', '_Lifetime', '_Ever'))):
                            if 'Date' in col:
                                params[param_name] = safe_date_convert(value)
                            else:
                                params[param_name] = int(value)  # type: ignore[arg-type]
                        else:
                            params[param_name] = float(value)  # type: ignore[arg-type]
                    except (ValueError, TypeError):
                        params[param_name] = None

                # Build stored procedure call
                sp_name = 'dbo.spInsertChurnScores'
                param_placeholders = ', '.join([f'{k}=?' for k in params])

                sql = f"EXEC {sp_name} {param_placeholders}"

                cursor.execute(sql, list(params.values()))
                rows_processed += 1

            # Commit after each batch for better error recovery
            conn.commit()
            logger.debug(
                "Step '%s': Committed batch %d-%d",
                step,
                batch_start + 1,
                batch_end
            )

        duration = time.time() - start_time
        throughput = rows_processed / duration if duration > 0 else 0
        logger.info(
            "Step '%s': Successfully wrote %d rows in %.2f seconds (%.2f rows/sec)",
            step,
            rows_processed,
            duration,
            throughput
        )
        return rows_processed

    except (OSError, ConnectionError, TimeoutError, ValueError) as e:
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
