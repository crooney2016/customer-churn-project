# Deployment Rules

## Azure Resources

Required:
- Azure Function App (Python 3.11, Consumption plan)
- Azure SQL Database
- App Registration (Power BI + Graph API)

Optional:
- Key Vault (for secrets)
- Application Insights (auto-created with Function)

## Function App Setup

### Create via CLI

```bash
# Resource group
az group create --name rg-churn-prod --location eastus

# Storage account (required for Functions)
az storage account create \
  --name stchurnprod \
  --resource-group rg-churn-prod \
  --sku Standard_LRS

# Function App
az functionapp create \
  --name func-churn-scoring-prod \
  --resource-group rg-churn-prod \
  --storage-account stchurnprod \
  --consumption-plan-location eastus \
  --runtime python \
  --runtime-version 3.11 \
  --functions-version 4 \
  --os-type Linux
```

### Enable Managed Identity

```bash
az functionapp identity assign \
  --name func-churn-scoring-prod \
  --resource-group rg-churn-prod
```

Grant SQL access:
```sql
CREATE USER [func-churn-scoring-prod] FROM EXTERNAL PROVIDER;
ALTER ROLE db_datareader ADD MEMBER [func-churn-scoring-prod];
ALTER ROLE db_datawriter ADD MEMBER [func-churn-scoring-prod];
GRANT EXECUTE ON SCHEMA::dbo TO [func-churn-scoring-prod];
```

## Environment Variables

Set in Azure Portal or CLI:

```bash
az functionapp config appsettings set \
  --name func-churn-scoring-prod \
  --resource-group rg-churn-prod \
  --settings \
    SQL_CONNECTION_STRING="Driver={ODBC Driver 18 for SQL Server};Server=sql-churn-prod.database.windows.net;Database=ChurnDB;Authentication=ActiveDirectoryMsi;" \
    PBI_TENANT_ID="..." \
    PBI_CLIENT_ID="..." \
    PBI_CLIENT_SECRET="@Microsoft.KeyVault(VaultName=kv-churn-prod;SecretName=pbi-client-secret)" \
    PBI_WORKSPACE_ID="..." \
    PBI_DATASET_ID="..." \
    EMAIL_TENANT_ID="..." \
    EMAIL_CLIENT_ID="..." \
    EMAIL_CLIENT_SECRET="@Microsoft.KeyVault(VaultName=kv-churn-prod;SecretName=email-client-secret)" \
    EMAIL_SENDER="churn-alerts@company.com" \
    EMAIL_RECIPIENTS="team@company.com"
```

## Deploy Code

### Via CLI

```bash
cd function_app
func azure functionapp publish func-churn-scoring-prod
```

### Via GitHub Actions

`.github/workflows/deploy.yml`:

```yaml
name: Deploy Function App

on:
  push:
    branches: [main]
    paths:
      - 'function_app/**'

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          cd function_app
          pip install -r requirements.txt

      - name: Run tests
        run: pytest tests/ -m "not integration"

      - name: Deploy to Azure
        uses: Azure/functions-action@v1
        with:
          app-name: func-churn-scoring-prod
          package: function_app
          publish-profile: ${{ secrets.AZURE_FUNCTIONAPP_PUBLISH_PROFILE }}
```

## Deployment Checklist

Before deploying:
- [ ] Tests pass locally
- [ ] Linters pass
- [ ] Environment variables set in Azure
- [ ] SQL schema deployed
- [ ] Managed identity has SQL permissions
- [ ] Service principal has Power BI permissions
- [ ] App registration has Graph API permissions

After deploying:
- [ ] Health endpoint returns 200
- [ ] Check Application Insights for errors
- [ ] Test /score endpoint manually
- [ ] Verify timer trigger schedule

## Rollback

If deployment fails:

```bash
# List deployment slots (if using)
az functionapp deployment slot list \
  --name func-churn-scoring-prod \
  --resource-group rg-churn-prod

# Redeploy previous version
func azure functionapp publish func-churn-scoring-prod --slot staging
az functionapp deployment slot swap \
  --name func-churn-scoring-prod \
  --resource-group rg-churn-prod \
  --slot staging
```

Or redeploy from previous git commit:
```bash
git checkout <previous-commit>
func azure functionapp publish func-churn-scoring-prod
```

## Monitoring

Application Insights queries:

```kusto
// Failed requests
requests
| where success == false
| order by timestamp desc

// Function duration
requests
| summarize avg(duration), max(duration) by name
| order by avg_duration desc

// Exceptions
exceptions
| order by timestamp desc
| take 50
```
