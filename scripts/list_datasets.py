#!/usr/bin/env python3
"""
List datasets in a Power BI workspace.

Usage:
    python scripts/list_datasets.py

This will show all datasets in the workspace specified by PBI_WORKSPACE_ID in .env
"""

import logging
import sys
from pathlib import Path

import requests

# Add function_app to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import config and dax_client
# Note: This will import __init__.py, but it now lazy-loads function_app
# so sql_client/pyodbc won't be loaded unless needed
# pylint: disable=wrong-import-position,wrong-import-order
from function_app.config import config
from function_app.dax_client import get_access_token

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def list_datasets(workspace_id: str) -> list[dict]:
    """
    List all datasets in a Power BI workspace.

    Args:
        workspace_id: Power BI workspace (group) ID

    Returns:
        List of dataset dictionaries with id, name, etc.
    """
    access_token = get_access_token()

    url = f"https://api.powerbi.com/v1.0/myorg/groups/{workspace_id}/datasets"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    response = requests.get(url, headers=headers, timeout=60)
    response.raise_for_status()

    return response.json().get("value", [])


def main() -> None:
    """Main function to list datasets."""
    try:
        # Validate configuration
        if not config.PBI_WORKSPACE_ID:
            logger.error("PBI_WORKSPACE_ID not set in .env file")
            sys.exit(1)

        if not config.PBI_TENANT_ID or not config.PBI_CLIENT_ID or not config.PBI_CLIENT_SECRET:
            logger.error("Power BI credentials not set in .env file")
            logger.error("Required: PBI_TENANT_ID, PBI_CLIENT_ID, PBI_CLIENT_SECRET")
            sys.exit(1)

        logger.info("Listing datasets in workspace: %s", config.PBI_WORKSPACE_ID)
        logger.info("=" * 60)

        datasets = list_datasets(config.PBI_WORKSPACE_ID)

        if not datasets:
            logger.info("No datasets found in workspace")
            return

        logger.info("Found %d dataset(s):\n", len(datasets))

        for i, dataset in enumerate(datasets, 1):
            logger.info("%d. Name: %s", i, dataset.get("name", "Unknown"))
            logger.info("   ID: %s", dataset.get("id", "Unknown"))
            logger.info("   Is Refreshable: %s", dataset.get("isRefreshable", False))
            logger.info("   Configured By: %s", dataset.get("configuredBy", "Unknown"))
            logger.info("")

        logger.info("=" * 60)
        logger.info("To use a dataset, add this to your .env file:")
        logger.info("PBI_DATASET_ID=<dataset-id-from-above>")
        logger.info("=" * 60)

    except (ValueError, RuntimeError, requests.exceptions.RequestException) as e:
        # Catch specific exceptions from dax_client and requests
        logger.error("Error listing datasets: %s", str(e), exc_info=True)
        sys.exit(1)
    except Exception as e:  # pylint: disable=broad-exception-caught
        # Catch any other unexpected errors to provide user-friendly message
        logger.error("Unexpected error listing datasets: %s", str(e), exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
