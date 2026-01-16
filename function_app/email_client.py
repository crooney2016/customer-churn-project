"""
Email client module for sending notifications via Microsoft Graph API.

TODO: This is a stub module. Full implementation pending.
New architecture: template generation → HTTP endpoint → Logic App → Outlook connector
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


def send_success_email(
    row_count: int,
    snapshot_date: str,
    duration_seconds: float,
    risk_distribution: Dict[str, int]
) -> None:
    """
    Send success notification email.

    Args:
        row_count: Number of rows scored
        snapshot_date: Snapshot date string
        duration_seconds: Execution duration in seconds
        risk_distribution: Dictionary mapping risk bands to counts
    """
    logger.info(
        "Success email (stub): %d rows scored for snapshot %s in %.2f seconds",
        row_count,
        snapshot_date,
        duration_seconds
    )
    logger.debug("Risk distribution: %s", risk_distribution)


def send_failure_email(
    error_type: str,
    error_message: str,
    step: str
) -> None:
    """
    Send failure notification email.

    Args:
        error_type: Type of error that occurred
        error_message: Error message
        step: Pipeline step where error occurred
    """
    logger.error(
        "Failure email (stub): Error in step '%s': %s - %s",
        step,
        error_type,
        error_message
    )
