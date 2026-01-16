"""
Power BI dataset refresh client.
Triggers dataset refresh via REST API.
"""

import time
from typing import Optional
import requests
from tenacity import (
    retry,
    stop_after_attempt,
    retry_if_exception_type,
    wait_exponential,
    before_sleep_log,
    after_log,
)
import logging
from .config import config
from .dax_client import get_access_token

logger = logging.getLogger(__name__)

# Retry configuration per error-handling.md
MAX_RETRIES = 3
BASE_RETRY_DELAY = 1.0

# Retry decorator for transient errors
retry_transient = retry(
    stop=stop_after_attempt(MAX_RETRIES),
    wait=wait_exponential(multiplier=BASE_RETRY_DELAY, min=BASE_RETRY_DELAY, max=60),
    retry=retry_if_exception_type((
        requests.exceptions.Timeout,
        requests.exceptions.ConnectionError,
        requests.exceptions.RequestException,
    )),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    after=after_log(logger, logging.ERROR),
    reraise=True,
)


@retry_transient
def trigger_dataset_refresh(dataset_id: Optional[str] = None) -> str:
    """
    Trigger Power BI dataset refresh.

    Args:
        dataset_id: Power BI dataset ID (defaults to config.PBI_DATASET_ID)

    Returns:
        Refresh ID for tracking
    """
    if dataset_id is None:
        dataset_id = config.PBI_DATASET_ID

    access_token = get_access_token()

    base_url = "https://api.powerbi.com/v1.0/myorg/groups"
    url = f"{base_url}/{config.PBI_WORKSPACE_ID}/datasets/{dataset_id}/refreshes"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    # Trigger refresh (no parameters = full refresh)
    response = requests.post(url, headers=headers, json={}, timeout=60)
    response.raise_for_status()

    # Return refresh ID if available
    return response.headers.get("Location", "")


def wait_for_refresh_completion(dataset_id: Optional[str] = None, timeout: int = 600) -> bool:
    """
    Wait for dataset refresh to complete.

    Args:
        dataset_id: Power BI dataset ID
        timeout: Maximum time to wait in seconds

    Returns:
        True if refresh completed successfully, False if timeout
    """
    if dataset_id is None:
        dataset_id = config.PBI_DATASET_ID

    access_token = get_access_token()

    base_url = "https://api.powerbi.com/v1.0/myorg/groups"
    url = f"{base_url}/{config.PBI_WORKSPACE_ID}/datasets/{dataset_id}/refreshes"

    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    start_time = time.time()

    while time.time() - start_time < timeout:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        refreshes = response.json().get("value", [])
        if refreshes:
            latest = refreshes[0]
            status = latest.get("status", "")

            if status == "Completed":
                return True
            elif status in ["Failed", "Cancelled"]:
                error_json = latest.get('serviceExceptionJson', {})
                raise RuntimeError(f"Dataset refresh {status.lower()}: {error_json}")

        time.sleep(5)  # Poll every 5 seconds

    return False  # Timeout
