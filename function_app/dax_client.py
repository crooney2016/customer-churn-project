"""
Power BI DAX query execution client.
Uses MSAL for authentication and Power BI REST API.
"""

from pathlib import Path
from typing import Any, Dict, Optional

import pandas as pd
import requests
from msal import ConfidentialClientApplication

from .config import config


def get_access_token() -> str:
    """Get access token for Power BI using service principal."""
    app = ConfidentialClientApplication(
        client_id=config.PBI_CLIENT_ID,
        client_credential=config.PBI_CLIENT_SECRET,
        authority=f"https://login.microsoftonline.com/{config.PBI_TENANT_ID}"
    )

    scope = "https://analysis.windows.net/powerbi/api/.default"
    result: Optional[Dict[str, Any]] = app.acquire_token_for_client(scopes=[scope])

    if result is None:
        raise RuntimeError("Failed to acquire token: No response from authentication service")

    if not isinstance(result, dict):
        raise RuntimeError("Failed to acquire token: Invalid response type")

    if "access_token" not in result:
        error_desc: str = str(result.get('error_description', 'Unknown error'))
        raise RuntimeError(f"Failed to acquire token: {error_desc}")

    access_token: Any = result.get("access_token")
    if not access_token or not isinstance(access_token, str):
        raise RuntimeError("Failed to acquire token: access_token is missing or invalid")

    return str(access_token)


def execute_dax_query(query: str, dataset_id: Optional[str] = None) -> pd.DataFrame:
    """
    Execute DAX query against Power BI dataset.

    Args:
        query: DAX query string
        dataset_id: Power BI dataset ID (defaults to config.PBI_DATASET_ID)

    Returns:
        pandas DataFrame with query results
    """
    if dataset_id is None:
        dataset_id = config.PBI_DATASET_ID

    access_token = get_access_token()

    url = f"https://api.powerbi.com/v1.0/myorg/datasets/{dataset_id}/executeQueries"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    payload = {
        "queries": [
            {
                "query": query
            }
        ],
        "serializerSettings": {
            "includeNulls": True
        }
    }

    response = requests.post(url, headers=headers, json=payload, timeout=300)
    response.raise_for_status()

    result = response.json()

    if "results" not in result or len(result["results"]) == 0:
        raise ValueError("No results returned from DAX query")

    # Parse results into DataFrame
    tables = result["results"][0].get("tables", [])
    if not tables:
        raise ValueError("No tables in DAX query results")

    # Convert to DataFrame
    table = tables[0]
    rows = table.get("rows", [])

    if not rows:
        return pd.DataFrame()

    # Extract column names
    columns = [col["name"] for col in table.get("columns", [])]

    # Construct DataFrame from dict for better type safety
    if rows and isinstance(rows[0], dict):
        # Rows are dicts - use directly
        df = pd.DataFrame(rows)
    else:
        # Rows are lists - convert to dict first
        df = pd.DataFrame({col: [row[i] for row in rows] for i, col in enumerate(columns)})

    return df


def load_dax_query_from_file(query_name: str = "churn_features") -> str:
    """
    Load DAX query from dax/ directory files.
    
    Args:
        query_name: Name of the DAX query file (without .dax extension).
                   Options: "churn_features" or "churn_features_dax_multimonth"
                   Defaults to "churn_features"
    
    Returns:
        DAX query string from the file
    
    Raises:
        FileNotFoundError: If the DAX query file doesn't exist
    """
    # Get project root (parent of function_app directory)
    project_root = Path(__file__).parent.parent
    query_path = project_root / "dax" / f"{query_name}.dax"

    if not query_path.exists():
        raise FileNotFoundError(
            f"DAX query file not found: {query_path}. "
            f"Available options: churn_features, churn_features_dax_multimonth"
        )

    return query_path.read_text(encoding="utf-8")


def get_dax_query_from_dataset(query_name: Optional[str] = None) -> str:
    """
    Get DAX query by loading from dax/ directory file.
    This is a convenience wrapper around load_dax_query_from_file.

    Args:
        query_name: Name of the DAX query file (without .dax extension).
                   If None, uses config.DAX_QUERY_NAME or defaults to "churn_features"
    
    Returns:
        DAX query string from the file
    """
    if query_name is None:
        query_name = config.DAX_QUERY_NAME or "churn_features"

    return load_dax_query_from_file(query_name)
