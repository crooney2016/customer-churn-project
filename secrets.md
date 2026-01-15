# Secrets Management Rules

## Principles

1. Never commit secrets to git
2. Use environment variables locally
3. Use Key Vault in production
4. Use Managed Identity where possible

## Local Development

### .env File

Create `.env` in project root (gitignored):

```
SQL_CONNECTION_STRING=Driver={ODBC Driver 18 for SQL Server};Server=localhost;Database=ChurnDev;Trusted_Connection=yes;
PBI_TENANT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
PBI_CLIENT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
PBI_CLIENT_SECRET=your-secret-here
PBI_WORKSPACE_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
PBI_DATASET_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
EMAIL_TENANT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
EMAIL_CLIENT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
EMAIL_CLIENT_SECRET=your-secret-here
EMAIL_SENDER=churn-alerts@company.com
EMAIL_RECIPIENTS=you@company.com
```

### Load in Python

```python
from dotenv import load_dotenv
load_dotenv()

# Then use os.getenv()
```

### .gitignore

Ensure these are ignored:
```
.env
*.env
local.settings.json
```

## Azure Key Vault

### Create Key Vault

```bash
az keyvault create \
  --name kv-churn-prod \
  --resource-group rg-churn-prod \
  --location eastus
```

### Add Secrets

```bash
az keyvault secret set \
  --vault-name kv-churn-prod \
  --name pbi-client-secret \
  --value "your-secret-here"

az keyvault secret set \
  --vault-name kv-churn-prod \
  --name email-client-secret \
  --value "your-secret-here"
```

### Grant Function App Access

```bash
# Get Function App identity
IDENTITY=$(az functionapp identity show \
  --name func-churn-scoring-prod \
  --resource-group rg-churn-prod \
  --query principalId -o tsv)

# Grant Key Vault access
az keyvault set-policy \
  --name kv-churn-prod \
  --object-id $IDENTITY \
  --secret-permissions get list
```

### Reference in App Settings

```bash
az functionapp config appsettings set \
  --name func-churn-scoring-prod \
  --resource-group rg-churn-prod \
  --settings \
    PBI_CLIENT_SECRET="@Microsoft.KeyVault(VaultName=kv-churn-prod;SecretName=pbi-client-secret)" \
    EMAIL_CLIENT_SECRET="@Microsoft.KeyVault(VaultName=kv-churn-prod;SecretName=email-client-secret)"
```

## Managed Identity for SQL

No secrets needed. Use Active Directory authentication:

```python
# Connection string with Managed Identity
conn_str = (
    "Driver={ODBC Driver 18 for SQL Server};"
    "Server=sql-churn-prod.database.windows.net;"
    "Database=ChurnDB;"
    "Authentication=ActiveDirectoryMsi;"
)
```

Grant access in SQL:
```sql
CREATE USER [func-churn-scoring-prod] FROM EXTERNAL PROVIDER;
ALTER ROLE db_datareader ADD MEMBER [func-churn-scoring-prod];
ALTER ROLE db_datawriter ADD MEMBER [func-churn-scoring-prod];
```

## Secret Rotation

### Client Secrets

1. Create new secret in App Registration
2. Update Key Vault
3. Verify Function works
4. Delete old secret

### Rotation Schedule

- Client secrets: Every 12 months (set calendar reminder)
- Key Vault notifies 30 days before expiry if configured

### Enable Expiry Notification

```bash
az keyvault secret set-attributes \
  --vault-name kv-churn-prod \
  --name pbi-client-secret \
  --expires "2026-01-15T00:00:00Z"
```

## Never Do This

```python
# WRONG - hardcoded secret
client_secret = "abc123-my-secret"

# WRONG - secret in code comment
# Password: MyP@ssw0rd

# WRONG - logging secrets
logging.info(f"Connecting with secret: {client_secret}")

# WRONG - secret in error message
raise Exception(f"Auth failed for {client_id} with {client_secret}")
```

## Always Do This

```python
# RIGHT - from environment
client_secret = os.getenv("PBI_CLIENT_SECRET")
if not client_secret:
    raise ValueError("PBI_CLIENT_SECRET not set")

# RIGHT - mask in logs
logging.info(f"Connecting with client_id: {client_id}")
# Don't log the secret at all

# RIGHT - generic error
raise Exception("Authentication failed - check credentials")
```
