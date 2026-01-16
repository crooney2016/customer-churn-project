# Deployment Runbook

**Project:** Century Churn Prediction System  
**Last Updated:** 2024-12-19  
**Version:** 1.0

## Overview

This document provides step-by-step instructions for deploying the Century Churn Prediction System to Azure Function App. It covers deployment, configuration, verification, and troubleshooting procedures.

## Prerequisites

### Required Access

- Azure subscription with Contributor role or higher
- Power BI workspace with admin access
- Azure SQL Database with write access
- Microsoft 365 tenant with App Registration permissions (for email notifications)

### Required Tools

- Azure Functions Core Tools v4+
- Python 3.11+ installed locally
- Azure CLI (optional, for Azure Portal operations)
- Access to Application Insights workspace

### Required Information

Before deployment, gather:

- Azure Function App name (or create new)
- Azure SQL Database connection string
- Power BI Service Principal credentials (Tenant ID, Client ID, Client Secret)
- Power BI Workspace ID and Dataset ID
- Microsoft Graph API Service Principal credentials (for email)
- Email sender address and recipients

## Pre-Deployment Checklist

- [ ] All environment variables defined (see Configuration section)
- [ ] Service Principal created and granted permissions
- [ ] Model files exist (`model/churn_model.pkl`, `model/model_columns.pkl`)
- [ ] SQL database schema deployed (tables, views, stored procedures)
- [ ] Power BI dataset created and accessible
- [ ] Application Insights workspace created

## Step 1: Azure Function App Setup

### Create Function App (if new)

```bash
# Login to Azure
az login

# Create resource group (if needed)
az group create --name rg-century-churn --location eastus

# Create Function App
az functionapp create \
  --resource-group rg-century-churn \
  --consumption-plan-location eastus \
  --runtime python \
  --runtime-version 3.11 \
  --functions-version 4 \
  --name <your-function-app-name> \
  --storage-account <storage-account-name>
```

### Configure Function App Settings

1. Open Azure Portal → Function App → Configuration → Application settings
2. Add all required environment variables (see Configuration section below)
3. Click "Save" to apply changes

## Step 2: Local Deployment Preparation

### Install Dependencies

```bash
# Navigate to project root
cd /path/to/century-churn-prediction-project

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install Azure Functions Core Tools dependencies
pip install -r requirements.txt
pip install -r function_app/requirements.txt
```

### Verify Configuration

```bash
# Verify model files exist
ls -la function_app/model/churn_model.pkl
ls -la function_app/model/model_columns.pkl

# Test local function (optional)
cd function_app
func start
```

## Step 3: Deploy to Azure

### Method 1: Azure Functions Core Tools (Recommended)

```bash
# Navigate to function_app directory
cd function_app

# Deploy to Azure Function App
func azure functionapp publish <your-function-app-name>

# Verify deployment
func azure functionapp list-functions <your-function-app-name>
```

### Method 2: VS Code Azure Functions Extension

1. Install Azure Functions extension in VS Code
2. Right-click on `function_app/` folder
3. Select "Deploy to Function App"
4. Choose existing Function App or create new
5. Monitor deployment progress

### Method 3: Azure DevOps / GitHub Actions (CI/CD)

See CI/CD Pipeline section for automated deployment setup.

## Step 4: Configuration

### Required Environment Variables

Set these in Azure Portal → Function App → Configuration → Application settings:

#### SQL Database

```bash
SQL_CONNECTION_STRING=Driver={ODBC Driver 18 for SQL Server};Server=<server>;Database=<database>;UID=<user>;PWD=<password>;
```

#### Power BI (DAX queries and dataset refresh)

```bash
PBI_TENANT_ID=<tenant-id>
PBI_CLIENT_ID=<service-principal-client-id>
PBI_CLIENT_SECRET=<service-principal-secret>
PBI_WORKSPACE_ID=<workspace-id>
PBI_DATASET_ID=<dataset-id>
DAX_QUERY_NAME=churn_features  # Optional, defaults to "churn_features"
```

#### Email Notifications (Microsoft Graph API)

```bash
EMAIL_TENANT_ID=<tenant-id>
EMAIL_CLIENT_ID=<service-principal-client-id>
EMAIL_CLIENT_SECRET=<service-principal-secret>
EMAIL_SENDER=<sender@domain.com>
EMAIL_RECIPIENTS=recipient1@domain.com,recipient2@domain.com
```

### Verify Configuration

After setting environment variables:

1. Restart Function App (Configuration → Save triggers restart)
2. Test configuration validation:

```bash
# Test health endpoint
curl https://<your-function-app>.azurewebsites.net/api/health
```

## Step 5: Database Schema Deployment

### Deploy SQL Objects

Execute SQL scripts in order:

```bash
# 1. Schema (tables)
sqlcmd -S <server> -d <database> -U <user> -i sql/schema.sql

# 2. Views
sqlcmd -S <server> -d <database> -U <user> -i sql/views.sql

# 3. Functions
sqlcmd -S <server> -d <database> -U <user> -i sql/functions.sql

# 4. Stored Procedures
sqlcmd -S <server> -d <database> -U <user> -i sql/procedures.sql
```

Or use Azure Data Studio / SSMS to execute scripts in order.

## Step 6: Power BI Configuration

### Service Principal Setup

1. **Create App Registration:**
   - Azure Portal → Azure Active Directory → App registrations → New registration
   - Name: `pbi-churn-scoring-sp`
   - Save Client ID and Tenant ID

2. **Create Client Secret:**
   - Certificates & secrets → New client secret
   - Save secret value (only shown once)

3. **Grant Permissions:**
   - API permissions → Add permission → Power BI Service → Delegated permissions
   - Grant: `Dataset.Read.All`, `Dataset.ReadWrite.All`
   - Admin consent required

4. **Add Service Principal to Workspace:**
   - Power BI Portal → Workspace → Access → Add service principal
   - Role: Member or Admin

### Dataset Access

Verify Service Principal has access to:
- Dataset read permissions (for DAX queries)
- Dataset refresh permissions (for triggering refresh)

## Step 7: Verification

### Health Check

```bash
# Test health endpoint
curl https://<your-function-app>.azurewebsites.net/api/health

# Expected: 200 OK
```

### Manual Trigger Test

```bash
# Trigger scoring pipeline manually
curl -X POST https://<your-function-app>.azurewebsites.net/api/score

# Monitor execution in Application Insights or Function App logs
```

### Verify Pipeline Execution

1. **Check Application Insights:**
   - Azure Portal → Application Insights → Logs
   - Query: `traces | where message contains "Pipeline completed" | order by timestamp desc | take 10`

2. **Check Function App Logs:**
   - Azure Portal → Function App → Functions → Monitor
   - View recent executions

3. **Check Email Notifications:**
   - Verify success/failure emails received

4. **Check SQL Database:**
   ```sql
   -- Verify rows inserted
   SELECT COUNT(*) FROM dbo.ChurnHistory
   WHERE SnapshotDate = CAST(GETDATE() AS DATE)

   -- Check recent scores
   SELECT TOP 10 * FROM dbo.vwCustomerCurrent
   ORDER BY ScoredAt DESC
   ```

5. **Check Power BI:**
   - Power BI Portal → Dataset → Refresh history
   - Verify refresh was triggered

## Step 8: Timer Configuration

The Function App uses a timer trigger that runs on the 1st of each month at 6 AM UTC.

### Verify Timer Schedule

1. Azure Portal → Function App → Functions → `monthly_timer_trigger`
2. Verify schedule: `0 0 6 1 * *` (cron expression)
3. Enable function if disabled

### Test Timer (optional)

```bash
# Manually trigger timer function for testing
curl -X POST https://<your-function-app>.azurewebsites.net/admin/functions/monthly_timer_trigger
```

## Troubleshooting

### Common Issues

#### 1. Function App Won't Start

**Symptoms:** Function App shows "Error" status or fails to start

**Diagnosis:**
- Check Application Insights logs for startup errors
- Verify Python runtime version (must be 3.11)
- Check for import errors in `function_app/__init__.py`

**Fix:**
```bash
# Check logs
az functionapp logs tail --name <function-app-name> --resource-group <resource-group>

# Verify requirements.txt matches deployed version
```

#### 2. Configuration Validation Errors

**Symptoms:** `ValueError: Configuration validation failed`

**Diagnosis:**
- Missing required environment variables
- Invalid environment variable format

**Fix:**
1. Azure Portal → Function App → Configuration
2. Verify all required variables are set
3. Check for typos in variable names
4. Restart Function App after changes

#### 3. DAX Query Failures

**Symptoms:** `RuntimeError: Failed to acquire token` or `401 Unauthorized`

**Diagnosis:**
- Service Principal credentials incorrect
- Service Principal not added to Power BI workspace
- Insufficient permissions

**Fix:**
1. Verify `PBI_TENANT_ID`, `PBI_CLIENT_ID`, `PBI_CLIENT_SECRET`
2. Power BI Portal → Workspace → Access → Verify service principal
3. Re-grant permissions if needed

#### 4. SQL Connection Errors

**Symptoms:** `pyodbc.Error: (connection string invalid)`

**Diagnosis:**
- Connection string format incorrect
- Database credentials incorrect
- Firewall rules blocking access

**Fix:**
1. Verify connection string format:
   ```
   Driver={ODBC Driver 18 for SQL Server};Server=<server>;Database=<db>;UID=<user>;PWD=<pwd>;
   ```
2. Azure Portal → SQL Database → Connection strings → Copy ADO.NET connection string
3. Verify firewall rules allow Azure services

#### 5. Model File Not Found

**Symptoms:** `FileNotFoundError: Model file not found`

**Diagnosis:**
- Model files not deployed to Function App
- Incorrect path in code

**Fix:**
1. Verify model files exist in `function_app/model/`
2. Include in deployment:
   ```bash
   # Verify model files are included
   func azure functionapp publish <name> --build remote
   ```
3. Check `.funcignore` doesn't exclude model files

#### 6. Email Not Sent

**Symptoms:** Pipeline succeeds but no email received

**Diagnosis:**
- Email service principal credentials incorrect
- Email sender address not authorized
- Email service throttling

**Fix:**
1. Verify `EMAIL_CLIENT_ID`, `EMAIL_CLIENT_SECRET`, `EMAIL_SENDER`
2. Azure Portal → Azure AD → App registrations → Verify API permissions
3. Grant `Mail.Send` permission with admin consent
4. Verify sender address exists in tenant

### Debugging Steps

1. **Enable Debug Logging:**
   - Azure Portal → Function App → Configuration
   - Set `AZURE_FUNCTIONS_ENVIRONMENT=Development` (temporary)
   - Restart Function App

2. **View Real-Time Logs:**
   ```bash
   az functionapp logs tail --name <function-app-name> --resource-group <resource-group>
   ```

3. **Application Insights Queries:**
   ```kusto
   // Recent errors
   traces
   | where severityLevel >= 3
   | where timestamp > ago(1h)
   | order by timestamp desc

   // Pipeline execution times
   traces
   | where message contains "Pipeline completed"
   | project timestamp, message, customDimensions

   // Errors by step
   traces
   | where severityLevel >= 3
   | where message contains "Step"
   | summarize count() by tostring(customDimensions.step)
   ```

4. **Test Locally:**
   ```bash
   cd function_app
   func start
   # Test endpoints locally before deployment
   ```

### Rollback Procedure

If deployment causes issues:

1. **Revert to Previous Deployment:**
   - Azure Portal → Function App → Deployment Center → Deployment history
   - Select previous successful deployment
   - Click "Redeploy"

2. **Disable Function Temporarily:**
   - Azure Portal → Function App → Functions
   - Disable problematic function

3. **Restore Configuration:**
   - Export current configuration (backup)
   - Restore previous environment variables

## Monitoring

### Key Metrics to Monitor

1. **Function Execution:**
   - Execution count
   - Success/failure rate
   - Average duration
   - Error rate by step

2. **Cost Monitoring:**
   - Azure Consumption plan usage (GB-seconds)
   - Function execution count
   - Cost per execution

3. **Data Quality:**
   - Rows scored per run
   - Expected vs actual row counts
   - Risk distribution changes

### Application Insights Alerts

Set up alerts for:

1. **Error Rate:**
   - Alert when error rate > 5% in 1 hour

2. **Function Failures:**
   - Alert on any function failure

3. **Performance:**
   - Alert when duration > 10 minutes

4. **Data Quality:**
   - Alert when row count < expected threshold

## Maintenance

### Regular Tasks

1. **Monthly:**
   - Review Application Insights logs
   - Verify timer trigger execution
   - Check cost metrics

2. **Quarterly:**
   - Review and rotate secrets
   - Update dependencies (`requirements.txt`)
   - Review and update model files

3. **As Needed:**
   - Update model files when retraining
   - Adjust timer schedule if needed
   - Update email recipients

### Secret Rotation

1. **Generate New Secrets:**
   - Azure AD → App registrations → Certificates & secrets
   - Create new client secret

2. **Update Configuration:**
   - Azure Portal → Function App → Configuration
   - Update `PBI_CLIENT_SECRET` or `EMAIL_CLIENT_SECRET`
   - Save and restart

3. **Verify:**
   - Trigger manual test run
   - Verify emails and logs

## Support

For deployment issues:

1. Check Application Insights logs
2. Review this runbook's troubleshooting section
3. Check Azure Function App status page
4. Contact Azure support if needed

## References

- [Azure Functions Documentation](https://learn.microsoft.com/azure/azure-functions/)
- [Power BI Service Principal Setup](./SERVICE_PRINCIPAL_SETUP.md)
- [Project README](../README.md)
- [Code Review Summary](../outputs/code-review.md)
