#!/usr/bin/env python3
"""
Check Azure AD app permissions to verify no admin-consent required permissions.

According to Microsoft docs, apps using service principal authentication for
read-only admin APIs MUST NOT have any admin-consent required permissions
for Power BI set on it.

Usage:
    python scripts/check_app_permissions.py
"""

import sys
import warnings
from pathlib import Path

import requests

# Suppress urllib3 warnings
warnings.filterwarnings("ignore", category=UserWarning, module="urllib3")

# Add function_app to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# pylint: disable=wrong-import-position,wrong-import-order
from function_app.config import config
from function_app.dax_client import get_access_token

# Configure logging
import logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


def get_app_permissions(token: str, app_id: str) -> dict:
    """
    Get app permissions from Microsoft Graph API.

    Args:
        token: Access token
        app_id: Application (client) ID

    Returns:
        Dictionary with app permissions
    """
    # Get app registration details
    url = "https://graph.microsoft.com/v1.0/applications"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # Filter by appId
    params = {"$filter": f"appId eq '{app_id}'"}

    response = requests.get(url, headers=headers, params=params, timeout=60)

    if response.status_code == 200:
        apps = response.json().get("value", [])
        if apps:
            return apps[0]

    return {}


def check_permissions(app_data: dict) -> None:
    """
    Check if app has admin-consent required permissions for Power BI.

    Args:
        app_data: Application data from Graph API
    """
    print("=" * 60)
    print("Azure AD App Permissions Check")
    print("=" * 60)
    print()
    print(f"App ID: {config.PBI_CLIENT_ID}")
    print()

    # Get required resource access (API permissions)
    required_resource_access = app_data.get("requiredResourceAccess", [])

    if not required_resource_access:
        print("✓ No API permissions configured")
        print("\nThis is correct - apps using service principal for admin APIs")
        print("should NOT have admin-consent required permissions for Power BI.")
        return

    print("Found API permissions:")
    print("-" * 60)

    power_bi_permissions = []
    for resource in required_resource_access:
        resource_id = resource.get("resourceAppId", "")

        # Check if this is Power BI Service
        if resource_id == "00000009-0000-0000-c000-000000000000":  # Power BI Service
            app_permissions = resource.get("resourceAccess", [])
            for perm in app_permissions:
                perm_id = perm.get("id", "")
                perm_type = perm.get("type", "")

                if perm_type == "Role":  # Application permission (admin consent required)
                    power_bi_permissions.append({
                        "id": perm_id,
                        "type": perm_type,
                        "name": "Unknown"  # Would need to look up by ID
                    })
    
    if power_bi_permissions:
        print("\n⚠️  WARNING: Found admin-consent required permissions for Power BI!")
        print(f"   Count: {len(power_bi_permissions)}")
        print("\n   According to Microsoft docs:")
        print("   'An app using service principal authentication that calls")
        print("   read-only admin APIs MUST NOT have any admin-consent required")
        print("   permissions for Power BI set on it.'")
        print("\n   Action required:")
        print("   1. Go to Azure Portal → App registrations → Your app")
        print("   2. Go to 'API permissions'")
        print("   3. Remove any Application permissions for Power BI Service")
        print("   4. Keep only Delegated permissions if needed")
    else:
        print("\n✓ No admin-consent required permissions found for Power BI")
        print("  This is correct!")


def main() -> None:
    """Main function."""
    try:
        print("Getting access token...")
        token = get_access_token()
        print("✓ Token acquired")
        print()

        print("Fetching app registration details...")
        app_data = get_app_permissions(token, config.PBI_CLIENT_ID)

        if not app_data:
            print("✗ Could not retrieve app registration")
            print("\nManual check required:")
            print("1. Go to Azure Portal → App registrations")
            print(f"2. Find app with Client ID: {config.PBI_CLIENT_ID}")
            print("3. Go to 'API permissions'")
            print("4. Check if there are any Application permissions for Power BI Service")
            print("5. If yes, REMOVE them (keep only Delegated if needed)")
            sys.exit(1)

        check_permissions(app_data)
        print()

    except Exception as e:  # pylint: disable=broad-exception-caught
        print(f"\n✗ Error: {type(e).__name__}")
        print(f"  Reason: {str(e)}")
        print("\nManual check required:")
        print("1. Go to Azure Portal → App registrations")
        print(f"2. Find app with Client ID: {config.PBI_CLIENT_ID}")
        print("3. Go to 'API permissions'")
        print("4. Check if there are any Application permissions for Power BI Service")
        print("5. If yes, REMOVE them (keep only Delegated if needed)")
        sys.exit(1)


if __name__ == "__main__":
    main()
