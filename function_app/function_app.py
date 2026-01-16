"""
Azure Functions entry point using v2 programming model.

This is the main entry point for the Azure Function App.
Uses Python decorators to define triggers and bindings.

Architecture:
    Logic App (Timer + DAX Query) → Blob Storage → This Function
    → CSV Parse → Score → SQL Upsert → Email
"""

import logging
import azure.functions as func  # type: ignore[import-untyped]

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

# Create the Function App instance
app = func.FunctionApp()

# Configure logging
logger = logging.getLogger(__name__)


# =============================================================================
# Blob Trigger (Primary Pipeline)
# =============================================================================

@app.blob_trigger(
    arg_name="blob",
    path="churn-feature-data/{name}",
    connection="AzureWebJobsStorage"
)
def process_churn_csv(blob: func.InputStream) -> None:
    """
    Process CSV files uploaded to blob storage.

    Triggered when a new CSV file is uploaded to the churn-feature-data container.
    Skips files in processed/ or error/ subfolders.

    Pipeline: CSV Parse → Validate → Score → SQL Upsert → Move to processed/
    """
    blob_name = blob.name or "unknown"
    logger.info("Blob trigger fired for: %s", blob_name)

    # Skip files in processed/ or error/ folders
    if "processed/" in blob_name or "error/" in blob_name:
        logger.info("Skipping file in processed/error folder: %s", blob_name)
        return

    # Skip non-CSV files
    if not blob_name.endswith(".csv"):
        logger.info("Skipping non-CSV file: %s", blob_name)
        return

    try:
        blob_data = blob.read()
        if not blob_data:
            logger.error("Blob '%s' is empty", blob_name)
            return

        logger.info("Processing blob '%s' (%d bytes)", blob_name, len(blob_data))

        # Run the pipeline
        result = _run_pipeline(blob_data, blob_name, DEFAULT_CONTAINER)

        logger.info(
            "Pipeline completed for '%s'. Rows scored: %d",
            blob_name,
            result.get("rows_scored", 0)
        )

    except Exception as e:  # pylint: disable=broad-except
        # Catch all exceptions to prevent blob trigger retries
        logger.error(
            "Pipeline failed for blob '%s': %s",
            blob_name,
            str(e),
            exc_info=True
        )


# =============================================================================
# HTTP Triggers (Manual Testing & Health Check)
# =============================================================================

@app.route(route="score", methods=["POST"], auth_level=func.AuthLevel.FUNCTION)
def score_http(req: func.HttpRequest) -> func.HttpResponse:
    """
    HTTP endpoint for manual scoring trigger.

    Request body:
    {
        "blob_url": "features-test.csv",  // Blob name or full URL (required)
        "container_name": "churn-feature-data"  // Optional
    }
    """
    try:
        req_body = req.get_json()
        blob_url = req_body.get("blob_url")
        container_name = req_body.get("container_name", DEFAULT_CONTAINER)
    except ValueError:
        return func.HttpResponse(
            "Request body must be valid JSON with 'blob_url' field",
            status_code=400
        )

    if not blob_url:
        return func.HttpResponse(
            'Missing required field "blob_url". '
            'Example: {"blob_url": "features-test.csv"}',
            status_code=400
        )

    try:
        # Extract blob name from URL if full URL provided
        blob_name = _extract_blob_name(blob_url, container_name)

        logger.info("Running pipeline for blob: %s", blob_name)

        # Read blob and run pipeline
        blob_data = read_blob_bytes(container_name, blob_name)
        result = _run_pipeline(blob_data, blob_name, container_name)

        return func.HttpResponse(
            f"Pipeline completed. "
            f"Rows scored: {result.get('rows_scored', 0)}, "
            f"Snapshot: {result.get('snapshot_date', 'Unknown')}",
            status_code=200
        )

    except (ValueError, ConnectionError, TimeoutError, OSError, RuntimeError) as e:
        logger.error("Pipeline failed: %s", str(e), exc_info=True)
        return func.HttpResponse(f"Pipeline failed: {str(e)}", status_code=500)


@app.route(route="health", methods=["GET"], auth_level=func.AuthLevel.ANONYMOUS)
def health_check(req: func.HttpRequest) -> func.HttpResponse:
    """Health check endpoint for monitoring."""
    return func.HttpResponse("OK", status_code=200)


# =============================================================================
# Pipeline Logic
# =============================================================================

def _run_pipeline(blob_data: bytes, blob_name: str, container_name: str) -> dict:
    """
    Main pipeline: CSV → validate → score → SQL → move → email.

    Args:
        blob_data: CSV file content as bytes
        blob_name: Name of the blob file
        container_name: Name of the container

    Returns:
        Dictionary with execution results
    """
    import time
    start_time = time.time()
    step = "initialization"
    snapshot_date = "unknown"

    try:
        # Step 1: Extract snapshot date
        step = "extract_snapshot_date"
        snapshot_date = extract_snapshot_date_from_csv(blob_data) or "unknown"
        logger.info("Snapshot date: %s", snapshot_date)

        # Step 2: Parse CSV
        step = "parse_csv"
        df = parse_csv_from_bytes(blob_data)
        logger.info("Parsed %d rows, %d columns", len(df), len(df.columns))

        if len(df) == 0:
            raise ValueError("CSV file contains no data rows")

        # Step 3: Validate schema
        step = "validate_schema"
        validate_csv_schema(df, normalize=True)
        logger.info("Schema validation passed")

        # Step 4: Normalize columns
        step = "normalize_columns"
        df = normalize_column_names(df)

        # Step 5: Score customers
        step = "scoring"
        scored_df = score_customers(df)
        logger.info("Scored %d customers", len(scored_df))

        # Step 6: Write to SQL
        step = "sql_write"
        rows_written = insert_churn_scores(scored_df)
        logger.info("Wrote %d rows to database", rows_written)

        # Step 7: Move to processed folder
        step = "move_to_processed"
        new_blob_name = move_to_processed(container_name, blob_name, snapshot_date)
        logger.info("Moved to: %s", new_blob_name)

        # Step 8: Send success email
        step = "email"
        duration = time.time() - start_time
        risk_dist = scored_df["RiskBand"].value_counts().to_dict()

        send_success_email(
            row_count=len(scored_df),
            snapshot_date=snapshot_date,
            duration_seconds=duration,
            risk_distribution=risk_dist
        )

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
        error_message = str(e)

        logger.error("Pipeline failed at step '%s': %s", step, error_message, exc_info=True)

        # Move file to error folder
        try:
            move_to_error(container_name, blob_name)
        except (OSError, IOError, RuntimeError) as move_err:
            logger.error("Failed to move file to error folder: %s", str(move_err))

        # Send failure email
        try:
            send_failure_email(
                error_type=type(e).__name__,
                error_message=error_message,
                step=step
            )
        except (ConnectionError, TimeoutError, OSError) as email_err:
            logger.error("Failed to send error email: %s", str(email_err))

        raise


def _extract_blob_name(blob_url: str, container_name: str) -> str:
    """Extract blob name from URL or return as-is if already a blob name."""
    if "blob.core.windows.net" in blob_url:
        parts = blob_url.split("/")
        if container_name in parts:
            idx = parts.index(container_name)
            return "/".join(parts[idx + 1:])
        return parts[-1]
    return blob_url
