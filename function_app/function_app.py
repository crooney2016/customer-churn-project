"""
Azure Function App entry points.
Blob trigger for processing CSV files and HTTP endpoints for manual triggers.
"""

import logging
import time
from typing import Dict, Any, Optional

from .config import config
from .blob_client import (
    read_blob_bytes,
    extract_snapshot_date_from_csv,
    move_to_processed,
    move_to_error,
    DEFAULT_CONTAINER,
)
from .csv_validator import (
    parse_csv_from_bytes,
    validate_csv_schema,
    normalize_column_names,
)
from .scorer import score_customers
from .sql_client import insert_churn_scores
from .email_client import send_success_email, send_failure_email

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_pipeline_from_blob(
    blob_data: bytes,
    blob_name: str,
    container_name: str = DEFAULT_CONTAINER
) -> Dict[str, Any]:
    """
    Main pipeline triggered by blob storage: CSV → validate → score → SQL → move → email.

    Args:
        blob_data: CSV file content as bytes
        blob_name: Name of the blob file
        container_name: Name of the container (default: churn-feature-data)

    Returns:
        Dictionary with execution results
    """
    start_time = time.time()
    step = "initialization"
    snapshot_date: Optional[str] = None

    try:
        logger.info("Starting pipeline for blob '%s'", blob_name)

        # Step 1: Extract snapshot date from CSV (for file naming later)
        step = "extract_snapshot_date"
        logger.info("Extracting snapshot date from CSV...")
        snapshot_date = extract_snapshot_date_from_csv(blob_data)
        if snapshot_date:
            logger.info("Snapshot date: %s", snapshot_date)
        else:
            logger.warning("Could not extract snapshot date from CSV")
            snapshot_date = "unknown"

        # Step 2: Parse CSV from bytes
        step = "parse_csv"
        logger.info("Parsing CSV from blob...")
        df = parse_csv_from_bytes(blob_data)
        logger.info("Parsed CSV with %d rows and %d columns", len(df), len(df.columns))

        if len(df) == 0:
            raise ValueError("CSV file contains no data rows")

        # Step 3: Validate CSV schema
        step = "validate_schema"
        logger.info("Validating CSV schema...")
        validate_csv_schema(df, normalize=True)
        logger.info("CSV schema validation passed")

        # Step 4: Normalize column names for scoring
        step = "normalize_columns"
        df = normalize_column_names(df)

        # Step 5: Score customers
        step = "scoring"
        logger.info("Scoring customers...")
        scored_df = score_customers(df)
        logger.info("Scored %d customers", len(scored_df))

        # Step 6: Write to SQL
        step = "sql_write"
        logger.info("Writing to SQL database...")
        rows_written = insert_churn_scores(scored_df)
        logger.info("Wrote %d rows to database", rows_written)

        # Step 7: Move file to processed folder
        step = "move_to_processed"
        logger.info("Moving file to processed folder...")
        new_blob_name = move_to_processed(container_name, blob_name, snapshot_date)
        logger.info("File moved to: %s", new_blob_name)

        # Step 8: Send success email
        step = "email"
        duration = time.time() - start_time

        # Calculate risk distribution
        risk_dist = scored_df["RiskBand"].value_counts().to_dict()

        send_success_email(
            row_count=len(scored_df),
            snapshot_date=snapshot_date,
            duration_seconds=duration,
            risk_distribution=risk_dist
        )
        logger.info("Success email sent")

        return {
            "status": "success",
            "blob_name": blob_name,
            "processed_blob_name": new_blob_name,
            "snapshot_date": snapshot_date,
            "rows_scored": len(scored_df),
            "rows_written": rows_written,
            "duration_seconds": duration,
            "risk_distribution": risk_dist
        }

    except (ValueError, ConnectionError, TimeoutError, OSError, RuntimeError) as e:
        duration = time.time() - start_time
        error_type = type(e).__name__
        error_message = str(e)

        logger.error(
            "Pipeline failed at step '%s' for blob '%s': %s",
            step,
            blob_name,
            error_message,
            exc_info=True
        )

        # Try to move file to error folder
        try:
            error_blob_name = move_to_error(container_name, blob_name)
            logger.info("File moved to error folder: %s", error_blob_name)
        except (OSError, IOError, RuntimeError) as move_error:
            logger.error("Failed to move file to error folder: %s", str(move_error))

        # Send failure email
        try:
            send_failure_email(
                error_type=error_type,
                error_message=error_message,
                step=step
            )
        except (ConnectionError, TimeoutError, OSError) as email_error:
            logger.error("Failed to send error email: %s", str(email_error))

        raise


def run_pipeline_from_url(
    blob_url: str,
    container_name: str = DEFAULT_CONTAINER
) -> Dict[str, Any]:
    """
    Run pipeline from a blob URL (for manual testing via HTTP trigger).

    Args:
        blob_url: Full URL to the blob (or just blob name if in default container)
        container_name: Name of the container

    Returns:
        Dictionary with execution results
    """
    # Extract blob name from URL if full URL provided
    if "blob.core.windows.net" in blob_url:
        # Parse blob name from URL
        parts = blob_url.split("/")
        # URL format: https://account.blob.core.windows.net/container/path/to/blob.csv
        container_idx = parts.index(container_name) if container_name in parts else -1
        if container_idx >= 0:
            blob_name = "/".join(parts[container_idx + 1:])
        else:
            blob_name = parts[-1]
    else:
        blob_name = blob_url

    logger.info("Reading blob '%s' from container '%s'", blob_name, container_name)

    # Read blob bytes
    blob_data = read_blob_bytes(container_name, blob_name)

    # Run pipeline
    return run_pipeline_from_blob(blob_data, blob_name, container_name)


# =============================================================================
# Legacy DAX-based pipeline (kept for backward compatibility)
# =============================================================================

def run_monthly_pipeline() -> Dict[str, Any]:
    """
    Legacy pipeline: DAX query → score → SQL write → PBI refresh → email.

    DEPRECATED: This function is kept for backward compatibility.
    Use run_pipeline_from_blob() with blob trigger instead.

    Returns:
        Dictionary with execution results
    """
    # Import DAX and PBI clients only when needed (lazy import)
    from .dax_client import execute_dax_query, get_dax_query_from_dataset
    from .pbi_client import trigger_dataset_refresh, wait_for_refresh_completion

    start_time = time.time()
    step = "initialization"

    try:
        # Validate configuration
        config.validate()
        logger.info("Configuration validated")

        # Step 1: Execute DAX query
        step = "dax_query"
        logger.info("Executing DAX query...")

        # Get DAX query from file (uses config.DAX_QUERY_NAME or defaults to "churn_features")
        dax_query = get_dax_query_from_dataset()

        df = execute_dax_query(dax_query)
        logger.info("DAX query returned %d rows", len(df))

        if len(df) == 0:
            raise ValueError("DAX query returned no rows")

        # Step 2: Score customers
        step = "scoring"
        logger.info("Scoring customers...")
        scored_df = score_customers(df)
        logger.info("Scored %d customers", len(scored_df))

        # Step 3: Write to SQL
        step = "sql_write"
        logger.info("Writing to SQL database...")
        rows_written = insert_churn_scores(scored_df)
        logger.info("Wrote %d rows to database", rows_written)

        # Step 4: Trigger Power BI refresh
        step = "pbi_refresh"
        logger.info("Triggering Power BI dataset refresh...")
        refresh_id = trigger_dataset_refresh()
        logger.info("Power BI refresh triggered: %s", refresh_id)

        # Wait for refresh (optional, can be async)
        try:
            wait_for_refresh_completion(timeout=300)
            logger.info("Power BI refresh completed")
        except (TimeoutError, ConnectionError, ValueError) as e:
            logger.warning("Power BI refresh monitoring failed: %s", str(e))

        # Step 5: Send success email
        step = "email"
        duration = time.time() - start_time

        # Calculate risk distribution
        risk_dist = scored_df["RiskBand"].value_counts().to_dict()
        snapshot_date = str(scored_df["SnapshotDate"].iloc[0]) if len(scored_df) > 0 else "Unknown"

        send_success_email(
            row_count=len(scored_df),
            snapshot_date=snapshot_date,
            duration_seconds=duration,
            risk_distribution=risk_dist
        )
        logger.info("Success email sent")

        return {
            "status": "success",
            "rows_scored": len(scored_df),
            "rows_written": rows_written,
            "duration_seconds": duration,
            "risk_distribution": risk_dist
        }

    except (ValueError, ConnectionError, TimeoutError, OSError) as e:
        duration = time.time() - start_time
        error_type = type(e).__name__
        error_message = str(e)

        logger.error("Pipeline failed at step '%s': %s", step, error_message, exc_info=True)

        # Send failure email
        try:
            send_failure_email(
                error_type=error_type,
                error_message=error_message,
                step=step
            )
        except (ConnectionError, TimeoutError, OSError) as email_error:
            logger.error("Failed to send error email: %s", str(email_error))

        raise
