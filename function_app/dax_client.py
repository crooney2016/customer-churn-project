"""
Power BI DAX query execution client.
Uses MSAL for authentication and Power BI REST API.
"""

from typing import Optional
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
    result = app.acquire_token_for_client(scopes=[scope])

    if "access_token" not in result:
        error_desc = result.get('error_description', 'Unknown error')
        raise RuntimeError(f"Failed to acquire token: {error_desc}")

    return result["access_token"]


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


def get_dax_query_from_dataset(query_name: Optional[str] = None) -> str:
    """
    Get DAX query from dataset (if stored as a query).
    For now, returns empty string - queries should be passed directly.
    """
    # This could be extended to fetch queries from Power BI if needed
    if query_name:
        # In a real implementation, you might fetch the query from Power BI
        # For now, queries should be provided directly
        pass
    return ""
