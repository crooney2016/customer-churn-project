"""
Azure Functions entry point.
Defines Azure Functions that delegate to function_app module.
"""

import logging
import azure.functions as func  # type: ignore[reportMissingImports]
from .config import config

logger = logging.getLogger(__name__)


# Lazy imports to avoid loading heavy dependencies unless needed
def _get_run_pipeline_from_blob():
    """Lazy import for blob-based pipeline."""
    from .function_app import run_pipeline_from_blob
    return run_pipeline_from_blob


def _get_run_pipeline_from_url():
    """Lazy import for URL-based pipeline (manual testing)."""
    from .function_app import run_pipeline_from_url
    return run_pipeline_from_url


def _get_run_monthly_pipeline():
    """Lazy import for legacy DAX-based pipeline."""
    from .function_app import run_monthly_pipeline
    return run_monthly_pipeline


# =============================================================================
# Blob Trigger (Primary - New Pipeline)
# =============================================================================

def blob_trigger_handler(blob: func.InputStream) -> None:
    """
    Blob trigger handler for processing CSV files.

    Triggered when a new CSV file is uploaded to the churn-feature-data container.
    Only fires for files in the root folder (not processed/ or error/ subfolders).

    Args:
        blob: Input stream from blob trigger
    """
    blob_name = blob.name
    logger.info("Blob trigger fired for: %s", blob_name)

    # Skip files in processed/ or error/ folders
    if blob_name and ("processed/" in blob_name or "error/" in blob_name):
        logger.info("Skipping file in processed/error folder: %s", blob_name)
        return

    try:
        # Read blob content
        blob_data = blob.read()

        if not blob_data:
            logger.error("Blob '%s' is empty", blob_name)
            return

        logger.info(
            "Processing blob '%s' (%d bytes)",
            blob_name,
            len(blob_data)
        )

        # Run pipeline
        run_pipeline_from_blob = _get_run_pipeline_from_blob()
        result = run_pipeline_from_blob(
            blob_data=blob_data,
            blob_name=blob_name,
            container_name="churn-feature-data"
        )

        logger.info(
            "Pipeline completed successfully for '%s'. Rows scored: %d",
            blob_name,
            result.get("rows_scored", 0)
        )

    except Exception as e:  # pylint: disable=broad-except
        # Catch all exceptions to prevent blob trigger retries
        # The file will be moved to error folder by the pipeline
        logger.error(
            "Pipeline failed for blob '%s': %s",
            blob_name,
            str(e),
            exc_info=True
        )


# =============================================================================
# Timer Trigger (Legacy - DAX Pipeline)
# =============================================================================

def monthly_timer_trigger(_timer: func.TimerRequest) -> None:
    """
    Timer trigger for monthly churn scoring (legacy DAX pipeline).

    DEPRECATED: This trigger uses the legacy DAX-based pipeline.
    The new pipeline is triggered by blob storage uploads.
    """
    logger.info("Timer trigger fired - running legacy DAX pipeline")
    run_monthly_pipeline = _get_run_monthly_pipeline()
    run_monthly_pipeline()


# =============================================================================
# HTTP Triggers (Manual Testing)
# =============================================================================

def score_http_trigger(req: func.HttpRequest) -> func.HttpResponse:
    """
    HTTP endpoint for manual scoring trigger.

    Supports two modes:
    1. POST with 'blob_url' in body - runs blob-based pipeline
    2. POST without body - runs legacy DAX pipeline

    Request body (optional):
    {
        "blob_url": "features-test.csv",  // Blob name or full URL
        "container_name": "churn-feature-data"  // Optional, defaults to churn-feature-data
    }
    """
    try:
        # Try to get blob_url from request body
        try:
            req_body = req.get_json()
            blob_url = req_body.get("blob_url")
            container_name = req_body.get("container_name", "churn-feature-data")
        except ValueError:
            blob_url = None
            container_name = "churn-feature-data"

        if blob_url:
            # Use new blob-based pipeline
            logger.info("Running blob pipeline for: %s", blob_url)
            run_pipeline_from_url = _get_run_pipeline_from_url()
            result = run_pipeline_from_url(blob_url, container_name)
            return func.HttpResponse(
                f"Pipeline completed successfully. "
                f"Rows scored: {result.get('rows_scored', 0)}, "
                f"Snapshot date: {result.get('snapshot_date', 'Unknown')}",
                status_code=200
            )
        else:
            # Fall back to legacy DAX pipeline
            logger.info("Running legacy DAX pipeline")
            run_monthly_pipeline = _get_run_monthly_pipeline()
            result = run_monthly_pipeline()
            return func.HttpResponse(
                f"Pipeline completed successfully. Rows scored: {result['rows_scored']}",
                status_code=200
            )

    except (ValueError, ConnectionError, TimeoutError, OSError, RuntimeError) as e:
        logger.error("Pipeline failed: %s", str(e), exc_info=True)
        return func.HttpResponse(
            f"Pipeline failed: {str(e)}",
            status_code=500
        )


def health_check(_req: func.HttpRequest) -> func.HttpResponse:
    """Health check endpoint."""
    try:
        # Basic config validation
        # Note: We don't require blob storage config for health check
        # as it may be configured separately
        return func.HttpResponse("OK", status_code=200)
    except ValueError as e:
        return func.HttpResponse(f"Configuration error: {str(e)}", status_code=500)
