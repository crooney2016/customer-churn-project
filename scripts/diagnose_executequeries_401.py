#!/usr/bin/env python3
"""
Comprehensive diagnostic script for Power BI executeQueries 401 errors.

Checks:
- Dataset metadata (type, RLS, SSO status)
- Service principal identity
- Token scope and claims
- Dataset permissions
- Actual API error details

Usage:
    python scripts/diagnose_executequeries_401.py
"""

import base64
import json
import logging
import sys
from pathlib import Path

import requests

# Add function_app to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# pylint: disable=wrong-import-position,wrong-import-order
from function_app.config import config
from function_app.dax_client import get_access_token

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def decode_jwt_token(token: str) -> dict:
    """
    Decode JWT token to inspect claims (without verification).

    Args:
        token: JWT token string

    Returns:
        Dictionary with token claims
    """
    try:
        # JWT has 3 parts: header.payload.signature
        parts = token.split('.')
        if len(parts) != 3:
            return {"error": "Invalid JWT format"}

        # Decode payload (second part)
        payload = parts[1]
        # Add padding if needed
        padding = 4 - len(payload) % 4
        if padding != 4:
            payload += '=' * padding

        decoded = base64.urlsafe_b64decode(payload)
        return json.loads(decoded)
    except (ValueError, json.JSONDecodeError, TypeError) as e:
        return {"error": f"Failed to decode token: {str(e)}"}


def get_dataset_metadata(workspace_id: str, dataset_id: str, token: str) -> dict:
    """
    Get detailed dataset metadata from Power BI API.

    Args:
        workspace_id: Power BI workspace ID
        dataset_id: Power BI dataset ID
        token: Access token

    Returns:
        Dataset metadata dictionary
    """
    url = f"https://api.powerbi.com/v1.0/myorg/groups/{workspace_id}/datasets/{dataset_id}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    response = requests.get(url, headers=headers, timeout=60)
    if response.status_code == 200:
        return response.json()
    else:
        logger.warning(
            "Failed to get dataset metadata: %s - %s",
            response.status_code,
            response.text[:200]
        )
        return {}


def get_dataset_users(workspace_id: str, dataset_id: str, token: str) -> list:
    """
    Get list of users with access to the dataset.

    Args:
        workspace_id: Power BI workspace ID
        dataset_id: Power BI dataset ID
        token: Access token

    Returns:
        List of dataset users
    """
    url = f"https://api.powerbi.com/v1.0/myorg/groups/{workspace_id}/datasets/{dataset_id}/users"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    response = requests.get(url, headers=headers, timeout=60)
    if response.status_code == 200:
        return response.json().get("value", [])
    else:
        logger.warning(
            "Failed to get dataset users: %s - %s",
            response.status_code,
            response.text[:200]
        )
        return []


def test_executequeries(workspace_id: str, dataset_id: str, token: str) -> dict:
    """
    Test executeQueries API and capture detailed error information.

    Args:
        workspace_id: Power BI workspace ID
        dataset_id: Power BI dataset ID
        token: Access token

    Returns:
        Dictionary with test results and error details
    """
    url = (
        f"https://api.powerbi.com/v1.0/myorg/groups/{workspace_id}"
        f"/datasets/{dataset_id}/executeQueries"
    )
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # Simple test query
    payload = {
        "queries": [
            {
                "query": "EVALUATE ROW(\"Test\", \"Value\")"
            }
        ],
        "serializerSettings": {
            "includeNulls": True
        }
    }

    response = requests.post(url, headers=headers, json=payload, timeout=60)

    result = {
        "status_code": response.status_code,
        "success": response.status_code == 200,
        "headers": dict(response.headers),
        "response_text": response.text[:1000] if response.text else None
    }

    # Try to parse error details
    if response.status_code != 200:
        try:
            error_json = response.json()
            result["error_details"] = error_json
        except (ValueError, json.JSONDecodeError):
            pass

    return result


def main() -> None:
    """Main diagnostic function."""
    print("=" * 80)
    print("Power BI executeQueries 401 Diagnostic")
    print("=" * 80)
    print()

    try:
        # Validate configuration
        if not all([config.PBI_WORKSPACE_ID, config.PBI_DATASET_ID,
                   config.PBI_TENANT_ID, config.PBI_CLIENT_ID]):
            logger.error("Missing required configuration in .env file")
            sys.exit(1)

        print("1. Configuration Check")
        print("-" * 80)
        print(f"   Workspace ID: {config.PBI_WORKSPACE_ID}")
        print(f"   Dataset ID: {config.PBI_DATASET_ID}")
        print(f"   Tenant ID: {config.PBI_TENANT_ID}")
        print(f"   Client ID: {config.PBI_CLIENT_ID}")
        print()

        # Get access token
        print("2. Token Acquisition")
        print("-" * 80)
        try:
            token = get_access_token()
            print("   ✅ Token acquired successfully")
            print(f"   Token length: {len(token)} characters")
            print()

            # Decode token to inspect claims
            print("3. Token Claims Analysis")
            print("-" * 80)
            claims = decode_jwt_token(token)
            if "error" not in claims:
                appid = claims.get("appid", "N/A")
                aud = claims.get("aud", "N/A")
                roles = claims.get("roles", [])
                scp = claims.get("scp", "N/A")
                print(f"   Application ID (appid): {appid}")
                print(f"   Audience (aud): {aud}")
                print(f"   Roles: {roles if roles else 'None'}")
                print(f"   Scope (scp): {scp}")
                print(f"   Expected Client ID: {config.PBI_CLIENT_ID}")
                if appid != config.PBI_CLIENT_ID:
                    print("   ⚠️  WARNING: Token appid doesn't match configured Client ID!")
                print()
            else:
                error_msg = claims.get('error', 'Unknown error')
                print(f"   ⚠️  Could not decode token: {error_msg}")
                print()
        except (ValueError, RuntimeError, requests.exceptions.RequestException) as e:
            logger.error("Failed to get token: %s", str(e), exc_info=True)
            sys.exit(1)

        # Get dataset metadata
        print("4. Dataset Metadata")
        print("-" * 80)
        metadata = get_dataset_metadata(config.PBI_WORKSPACE_ID, config.PBI_DATASET_ID, token)
        if metadata:
            name = metadata.get("name", "Unknown")
            dataset_type = metadata.get("contentProviderType", "Unknown")
            is_refreshable = metadata.get("isRefreshable", False)
            configured_by = metadata.get("configuredBy", "Unknown")
            is_on_prem_gateway = metadata.get("isOnPremGatewayRequired", False)
            is_effective_identity_required = metadata.get("isEffectiveIdentityRequired", False)

            print(f"   Name: {name}")
            print(f"   Type: {dataset_type}")
            print(f"   Is Refreshable: {is_refreshable}")
            print(f"   Configured By: {configured_by}")
            print(f"   On-Prem Gateway Required: {is_on_prem_gateway}")
            print(f"   Effective Identity Required: {is_effective_identity_required}")

            # Check for RLS indicators
            if is_effective_identity_required:
                print("   ⚠️  WARNING: Dataset requires effective identity (may indicate RLS/SSO)")
            print()

            # Check model type (DirectLake, Import, etc.)
            # This might be in a different endpoint or property
            print("   Note: Check in Power BI Service if dataset is DirectLake or SSO-enabled")
            print("   (Service principals may not support executeQueries on these model types)")
            print()
        else:
            print("   ⚠️  Could not retrieve dataset metadata")
            print()

        # Check dataset users
        print("5. Dataset Permissions")
        print("-" * 80)
        users = get_dataset_users(config.PBI_WORKSPACE_ID, config.PBI_DATASET_ID, token)
        print(f"   Total users with dataset access: {len(users)}")

        # Look for service principal
        sp_found = False
        for user in users:
            identifier = user.get("identifier", "")
            principal_type = user.get("principalType", "")
            access_right = user.get("datasetUserAccessRight", "")

            # Check if this is our service principal
            if (config.PBI_CLIENT_ID in identifier or
                principal_type == "App" or
                "service" in identifier.lower() or
                "principal" in identifier.lower()):
                print("   ✅ Found potential service principal:")
                print(f"      Identifier: {identifier}")
                print(f"      Principal Type: {principal_type}")
                print(f"      Access Right: {access_right}")
                if "Explore" in access_right or "Build" in access_right:
                    print("      ✅ Has Build/Explore permission")
                else:
                    print("      ⚠️  Missing Build/Explore permission")
                sp_found = True

        if not sp_found:
            print("   ⚠️  Service principal not found in dataset users list")
            print("   (This may be OK if permissions are inherited from workspace)")
        print()

        # Test executeQueries
        print("6. executeQueries API Test")
        print("-" * 80)
        test_result = test_executequeries(config.PBI_WORKSPACE_ID, config.PBI_DATASET_ID, token)

        if test_result["success"]:
            print("   ✅ executeQueries succeeded!")
        else:
            print(f"   ❌ executeQueries failed with status {test_result['status_code']}")
            print(f"   Response: {test_result.get('response_text', 'No response text')}")

            if "error_details" in test_result:
                error = test_result["error_details"]
                print(f"   Error details: {json.dumps(error, indent=2)}")

            # Check for specific error patterns
            response_text = test_result.get("response_text", "").lower()
            if "unauthorized" in response_text or test_result["status_code"] == 401:
                print()
                print("   🔍 401 Unauthorized - Critical checks:")
                print(
                    "      1. ⚠️  'Allow service principals to use Power BI APIs' "
                    "(Developer settings) MUST be enabled - this is REQUIRED"
                )
                print(
                    "      2. 'Semantic Model Execute Queries REST API' "
                    "(Integration settings) must be enabled"
                )
                print(
                    "      3. Dataset may be DirectLake - some DirectLake "
                    "datasets don't support SP executeQueries even without RLS"
                )
                print("      4. Service principal must be in allowed security groups")
                print("      5. Missing Build permission on dataset")
        print()

        # Summary
        print("=" * 80)
        print("Diagnostic Summary")
        print("=" * 80)
        print()
        print("Next steps:")
        print(
            "1. ⚠️  CRITICAL: Verify 'Allow service principals to use Power BI APIs' "
            "is enabled in Developer settings (REQUIRED for executeQueries)"
        )
        print("2. Verify 'Semantic Model Execute Queries REST API' is enabled")
        print("3. Check if dataset is DirectLake (may not support SP executeQueries)")
        print("4. Verify service principal is in allowed security groups for both settings")
        print("5. Wait 5-10 minutes after any permission changes for propagation")
        print()

    except (ValueError, RuntimeError, requests.exceptions.RequestException) as e:
        logger.error("Error during diagnosis: %s", str(e), exc_info=True)
        sys.exit(1)
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.error("Unexpected error: %s", str(e), exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
