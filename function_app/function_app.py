"""
Azure Function App entry points.
Timer trigger for monthly runs and HTTP endpoints for manual triggers.
"""

import logging
import time
from typing import Dict, Any

from .config import config
from .dax_client import execute_dax_query, get_dax_query_from_dataset
from .scorer import score_customers
from .sql_client import insert_churn_scores
from .pbi_client import trigger_dataset_refresh, wait_for_refresh_completion
from .email_client import send_success_email, send_failure_email

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_monthly_pipeline() -> Dict[str, Any]:
    """
    Main pipeline: DAX query → score → SQL write → PBI refresh → email.

    Returns:
        Dictionary with execution results
    """
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
