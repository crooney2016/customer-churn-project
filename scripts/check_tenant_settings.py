#!/usr/bin/env python3
"""
Check Power BI tenant settings programmatically.

This script uses the Power BI Admin API to verify tenant settings are correctly
configured for service principal executeQueries access.

Usage:
    python scripts/check_tenant_settings.py
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


def get_tenant_settings(token: str) -> dict:
    """
    Get Power BI tenant settings using Admin API.

    Args:
        token: Access token

    Returns:
        Dictionary with tenant settings
    """
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # Try both endpoint formats
    urls = [
        "https://api.powerbi.com/v1.0/myorg/admin/tenantsettings",
        "https://api.powerbi.com/v1/admin/tenantsettings"
    ]

    response = None
    for url in urls:
        response = requests.get(url, headers=headers, timeout=60)
        if response.status_code == 200:
            return response.json()
        elif response.status_code not in (404, 405):  # 404/405 means wrong endpoint
            # Return error for other status codes
            break

    # Handle errors
    if response:
        if response.status_code == 403:
            print("✗ Error: 403 Forbidden")
            print(
                "  Reason: Service principal needs 'Service principals can access "
                "read-only admin APIs' enabled"
            )
            print("  OR you need Tenant.Read.All application permission")
            return {}
        elif response.status_code == 401:
            print("✗ Error: 401 Unauthorized")
            print("  Reason: Token invalid or insufficient permissions")
            return {}
        else:
            print(f"✗ Error: {response.status_code}")
            print(f"  Response: {response.text[:200]}")
            return {}

    print("✗ Error: Could not find valid endpoint")
    return {}


def find_setting(settings: list, setting_name: str, partial_match: bool = True) -> dict:
    """
    Find a specific tenant setting by name.

    Args:
        settings: List of tenant settings
        setting_name: Name of setting to find (exact or partial)
        partial_match: If True, also search for partial matches

    Returns:
        Setting dictionary or empty dict if not found
    """
    for setting in settings:
        name = setting.get("name", "")
        # Exact match
        if name == setting_name:
            return setting
        # Partial match (case-insensitive)
        if partial_match and setting_name.lower() in name.lower():
            return setting
    return {}


def main() -> None:
    """Main function to check tenant settings."""
    print("=" * 60)
    print("Power BI Tenant Settings Check")
    print("=" * 60)
    print()

    try:
        # Validate configuration first
        if not config.PBI_TENANT_ID:
            print("✗ Error: PBI_TENANT_ID not set in .env file")
            sys.exit(1)
        if not config.PBI_CLIENT_ID:
            print("✗ Error: PBI_CLIENT_ID not set in .env file")
            sys.exit(1)
        if not config.PBI_CLIENT_SECRET:
            print("✗ Error: PBI_CLIENT_SECRET not set in .env file")
            sys.exit(1)

        # Get access token
        print("Getting access token...")
        token = get_access_token()
        print("✓ Token acquired")
        print()

        # Get tenant settings
        print("Fetching tenant settings...")
        settings_data = get_tenant_settings(token)
        
        if not settings_data:
            print("\n✗ Could not retrieve tenant settings")
            print("\nThis might mean:")
            print("  1. 'Service principals can access read-only admin APIs' is not enabled")
            print("  2. Service principal is not in the allowed security group")
            print("  3. Missing Tenant.Read.All application permission")
            sys.exit(1)

        settings = settings_data.get("tenantSettings", [])
        print(f"✓ Retrieved {len(settings)} tenant settings")
        print()

        # Check critical settings
        print("Checking critical settings for executeQueries:")
        print("-" * 60)

        # 1. Allow service principals to use Power BI APIs
        sp_api_setting = find_setting(
            settings,
            "AllowServicePrincipalsToUsePowerBI",
            partial_match=True
        )
        if not sp_api_setting:
            # Try alternative names
            sp_api_setting = find_setting(settings, "ServicePrincipal", partial_match=True)
        if sp_api_setting:
            enabled = sp_api_setting.get("value", False)
            scope = sp_api_setting.get("scope", "Unknown")
            print("\n1. Allow service principals to use Power BI APIs")
            print(f"   Status: {'✓ Enabled' if enabled else '✗ Disabled'}")
            print(f"   Scope: {scope}")
            if not enabled:
                print("   ⚠️  REQUIRED: This must be enabled!")
        else:
            print("\n1. Allow service principals to use Power BI APIs")
            print("   ✗ Setting not found")

        # 2. Semantic Model Execute Queries REST API
        execute_queries_setting = find_setting(
            settings,
            "ExecuteQueriesRestApi",
            partial_match=True
        )
        if not execute_queries_setting:
            # Try alternative names
            execute_queries_setting = find_setting(settings, "ExecuteQueries", partial_match=True)
            if not execute_queries_setting:
                execute_queries_setting = find_setting(settings, "SemanticModel", partial_match=True)
        if execute_queries_setting:
            enabled = execute_queries_setting.get("value", False)
            scope = execute_queries_setting.get("scope", "Unknown")
            print("\n2. Semantic Model Execute Queries REST API")
            print(f"   Status: {'✓ Enabled' if enabled else '✗ Disabled'}")
            print(f"   Scope: {scope}")
            if not enabled:
                print("   ⚠️  REQUIRED: This must be enabled!")
        else:
            print("\n2. Semantic Model Execute Queries REST API")
            print("   ✗ Setting not found")

        # 3. Service principals can access read-only admin APIs
        admin_api_setting = find_setting(
            settings,
            "AllowServicePrincipalsToUseReadOnlyAdminAPIs"
        )
        if admin_api_setting:
            enabled = admin_api_setting.get("value", False)
            scope = admin_api_setting.get("scope", "Unknown")
            print("\n3. Service principals can access read-only admin APIs")
            print(f"   Status: {'✓ Enabled' if enabled else '✗ Disabled'}")
            print(f"   Scope: {scope}")
        else:
            print("\n3. Service principals can access read-only admin APIs")
            print("   ⚠️  Setting not found (may not be available)")

        print("\n" + "=" * 60)
        print("Summary")
        print("=" * 60)

        # Check if both critical settings are enabled
        sp_enabled = sp_api_setting.get("value", False) if sp_api_setting else False
        eq_enabled = execute_queries_setting.get("value", False) if execute_queries_setting else False

        if sp_enabled and eq_enabled:
            print("✓ Both critical settings are enabled")
            print("\nIf executeQueries still fails with 401, check:")
            print("  - Service principal is in the allowed security groups")
            print("  - Dataset is not DirectLake or has RLS enabled")
            print("  - Service principal has Build permission on dataset")
        else:
            print("✗ One or more critical settings are disabled")
            if not sp_enabled:
                print("  - Enable 'Allow service principals to use Power BI APIs'")
            if not eq_enabled:
                print("  - Enable 'Semantic Model Execute Queries REST API'")

        print()

    except Exception as e:  # pylint: disable=broad-exception-caught
        print(f"\n✗ Error: {type(e).__name__}")
        print(f"  Reason: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
