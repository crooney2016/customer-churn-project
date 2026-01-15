# Power BI Rules

## Service Principal Setup

### 1. Create App Registration

Azure Portal → App registrations → New registration:
- Name: `sp-churn-powerbi`
- Supported account types: Single tenant

### 2. Create Client Secret

Certificates & secrets → New client secret:
- Description: `churn-scoring`
- Expiry: 24 months

Save the secret value immediately.

### 3. API Permissions

API permissions → Add:
- Power BI Service → Delegated:
  - Dataset.ReadWrite.All
  - Workspace.Read.All

Grant admin consent.

### 4. Power BI Admin Portal

Power BI Admin Portal → Tenant settings → Developer settings:
- Enable "Service principals can use Fabric APIs"
- Apply to specific security group containing the service principal

### 5. Workspace Access

In Power BI workspace:
- Settings → Access
- Add service principal as Member or Contributor

## DAX Query Execution

### Endpoint

```
POST https://api.powerbi.com/v1.0/myorg/groups/{workspaceId}/datasets/{datasetId}/executeQueries
```

### Request Body

```json
{
  "queries": [
    {
      "query": "EVALUATE churn_features"
    }
  ],
  "serializerSettings": {
    "includeNulls": true
  }
}
```

### Authentication

```python
import msal

def get_pbi_token(tenant_id: str, client_id: str, client_secret: str) -> str:
    authority = f"https://login.microsoftonline.com/{tenant_id}"
    app = msal.ConfidentialClientApplication(
        client_id,
        authority=authority,
        client_credential=client_secret,
    )
    result = app.acquire_token_for_client(
        scopes=["https://analysis.windows.net/powerbi/api/.default"]
    )
    if "access_token" not in result:
        raise Exception(f"Token acquisition failed: {result.get('error_description')}")
    return result["access_token"]
```

### Execute Query

```python
import requests
import pandas as pd

def execute_dax(
    token: str,
    workspace_id: str,
    dataset_id: str,
    query: str
) -> pd.DataFrame:
    url = f"https://api.powerbi.com/v1.0/myorg/groups/{workspace_id}/datasets/{dataset_id}/executeQueries"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    
    body = {
        "queries": [{"query": query}],
        "serializerSettings": {"includeNulls": True},
    }
    
    response = requests.post(url, headers=headers, json=body, timeout=300)
    response.raise_for_status()
    
    data = response.json()
    rows = data["results"][0]["tables"][0]["rows"]
    return pd.DataFrame(rows)
```

## Dataset Refresh

### Endpoint

```
POST https://api.powerbi.com/v1.0/myorg/groups/{workspaceId}/datasets/{datasetId}/refreshes
```

### Execute Refresh

```python
def refresh_dataset(
    token: str,
    workspace_id: str,
    dataset_id: str
) -> None:
    url = f"https://api.powerbi.com/v1.0/myorg/groups/{workspace_id}/datasets/{dataset_id}/refreshes"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    
    body = {"notifyOption": "NoNotification"}
    
    response = requests.post(url, headers=headers, json=body, timeout=60)
    
    # 202 Accepted = refresh started
    if response.status_code != 202:
        response.raise_for_status()
```

## Rate Limits

- DAX query: 120 requests per minute per user
- Dataset refresh: 8 refreshes per day (Pro), 48 (Premium)

Handle 429 responses:
```python
if response.status_code == 429:
    retry_after = int(response.headers.get("Retry-After", 60))
    time.sleep(retry_after)
    # Retry
```

## Timeout Handling

DAX queries can be slow for large datasets:
- Set timeout to 300 seconds minimum
- Consider pagination for very large results
- Use Premium capacity for better performance

## Troubleshooting

### Common Errors

**401 Unauthorized**
- Token expired → refresh token
- Wrong scope → check API permissions

**403 Forbidden**
- Service principal not in workspace
- Tenant setting not enabled

**400 Bad Request**
- Invalid DAX syntax
- Column name doesn't exist

### Debug Logging

```python
import logging

logging.basicConfig(level=logging.DEBUG)
logging.getLogger("msal").setLevel(logging.DEBUG)
```
