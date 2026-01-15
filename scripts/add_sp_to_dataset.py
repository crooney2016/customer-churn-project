#!/usr/bin/env python3
"""
Add service principal to Power BI dataset with Read + Build permissions.

This script uses the Admin API to grant dataset permissions to a service principal.
Required for executeQueries to work.

Usage:
    python scripts/add_sp_to_dataset.py
"""

import logging
import sys
from pathlib import Path

import requests

# Add function_app to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# pylint: disable=wrong-import-position
from function_app.config import config
from function_app.dax_client import get_access_token

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_service_principal_object_id() -> str:
    """
    Get the service principal's Object ID from Azure AD.

    Returns:
        Object ID of the service principal
    """
    # For now, we'll use the client ID and try to find the object ID
    # Or you can provide it manually
    # The Object ID is different from Client ID (Application ID)
    # You can find it in Azure Portal → App registrations → Your app → Overview → Object ID
    
    # We'll need to get this from Azure AD Graph API or have user provide it
    # For now, return the client ID as a placeholder
    return config.PBI_CLIENT_ID


def add_sp_to_dataset(
    dataset_id: str,
    workspace_id: str,
    sp_object_id: str,
    access_right: str = "ReadExplore"
) -> bool:
    """
    Add service principal to dataset using Admin API.

    Args:
        dataset_id: Power BI dataset ID
        workspace_id: Power BI workspace ID
        sp_object_id: Service principal Object ID (not Client ID)
        access_right: Dataset access right (ReadExplore = Read + Build)

    Returns:
        True if successful, False otherwise
    """
    token = get_access_token()

    # Use Admin API to add SP to dataset
    url = f"https://api.powerbi.com/v1.0/myorg/admin/datasets/{dataset_id}/users"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    payload = {
        "identifier": sp_object_id,
        "principalType": "App",
        "datasetUserAccessRight": access_right
    }

    logger.info(
        "Adding service principal %s to dataset %s with %s permissions",
        sp_object_id,
        dataset_id,
        access_right
    )

    response = requests.post(url, headers=headers, json=payload, timeout=60)

    if response.status_code in (200, 201):
        logger.info("✅ Successfully added service principal to dataset!")
        return True
    else:
        logger.error("❌ Failed to add service principal: %s", response.status_code)
        try:
            error_data = response.json()
            logger.error("Error details: %s", error_data)
        except:
            logger.error("Error text: %s", response.text[:500])
        return False


def main() -> None:
    """Main function to add service principal to dataset."""
    print("=" * 60)
    print("Add Service Principal to Dataset")
    print("=" * 60)

    print("\n⚠️  IMPORTANT: You need the Service Principal's OBJECT ID")
    print("   (Not the Client ID/Application ID)")
    print("\n   Find it in:")
    print("   Azure Portal → App registrations → Your app → Overview")
    print("   Look for 'Object ID' (different from Application ID)")

    # Use the Object ID provided by user
    sp_object_id = "4ebf91b8-e10f-43ca-bf28-a9fc3b09176c"
    print(f"Using Service Principal Object ID: {sp_object_id}")

    print(f"\nDataset ID: {config.PBI_DATASET_ID}")
    print(f"Workspace ID: {config.PBI_WORKSPACE_ID}")
    print(f"Service Principal: {sp_object_id}")

    # Auto-proceed since we have the Object ID
    print("\nProceeding to add SP to dataset...")

    success = add_sp_to_dataset(
        dataset_id=config.PBI_DATASET_ID,
        workspace_id=config.PBI_WORKSPACE_ID,
        sp_object_id=sp_object_id,
        access_right="ReadExplore"  # Read + Build (Explore)
    )

    if success:
        print("\n" + "=" * 60)
        print("✅ Service principal added successfully!")
        print("=" * 60)
        print("\nWait 1-2 minutes for permissions to propagate, then try:")
        print("  python scripts/test_dax_query.py churn_features")
    else:
        print("\n" + "=" * 60)
        print("❌ Failed to add service principal")
        print("=" * 60)
        print("\nCommon issues:")
        print("1. Wrong Object ID (need Object ID, not Client ID)")
        print("2. Need Power BI Admin role to use Admin API")
        print("3. Tenant settings not fully enabled")
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nCancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error("Error: %s", str(e), exc_info=True)
        sys.exit(1)
