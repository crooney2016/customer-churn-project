# CI/CD Pipeline Setup Guide

**Project:** Century Churn Prediction System
**Last Updated:** 2024-12-19
**Version:** 1.0

## Overview

This document provides instructions for setting up CI/CD pipelines for the Century Churn Prediction System. The project supports **dual remotes**:

- **GitHub Actions** (`.github/workflows/`) - Triggered by pushes to `github` remote
- **Azure DevOps Pipelines** (`azure-pipelines.yml`) - Triggered by pushes to `azure` remote

Both pipelines include automated testing, linting, and deployment to Azure Function App. Choose based on your deployment preference:

- **GitHub Actions:** Easy setup, good for AI tool integration
- **Azure DevOps:** Native Microsoft integration, enterprise features

See [Git Remotes Setup Guide](./GIT_REMOTES_SETUP.md) for configuring dual remotes.

## Prerequisites

### For GitHub Actions

- GitHub repository with Actions enabled
- Azure subscription with appropriate permissions
- Azure Function App created
- Azure Service Principal or Publish Profile for deployment

### For Azure DevOps

- Azure DevOps organization and project
- Azure subscription with appropriate permissions
- Azure Function App created
- Azure Service Connection configured in Azure DevOps

## Pipeline Configuration

### Option 1: GitHub Actions (`.github/workflows/`)

#### Triggers

- Push to `main` or `develop` branches (on `github` remote)
- Pull requests to `main` or `develop` branches

#### Jobs

1. **Test Job:**
   - Runs pytest with coverage
   - Uploads coverage to Codecov (optional)
   - Python 3.11

1. **Lint Job:**
   - Runs pylint, pyright, ruff check, ruff format
   - Python 3.11

1. **Type Check Job:**
   - Runs pyright for type checking
   - Python 3.11

#### Triggers (Option 1: GitHub Actions (`.github/workflows/`))

- Push to `main` branch (changes in `function_app/`)
- Manual workflow dispatch (with environment selection)

#### Jobs (Option 1: GitHub Actions (`.github/workflows/`))

1. **Build and Deploy:**
   - Runs tests (continues on failure for safety)
   - Deploys to Azure Function App
   - Supports staging and production environments

### Option 2: Azure DevOps Pipelines (`azure-pipelines.yml`)

#### CI/CD Pipeline

#### Triggers (Option 2: Azure DevOps Pipelines (`azure-pipelines.yml`))

- Push to `main` or `develop` branches (on `azure` remote)
- Pull requests to `main` or `develop` branches

#### Stages

1. **Test Stage:**
   - **Test Job:** Runs pytest with coverage, publishes coverage results
   - **Lint Job:** Runs pylint, pyright, ruff check, ruff format
   - **Type Check Job:** Runs pyright

1. **Deploy Stage:**
   - **Deploy Job:** Deploys to Azure Function App (main branch only)
   - Uses Azure Service Connection
   - Supports environment-specific deployments

#### Key Features

- Integrated with Azure DevOps environments
- Native Azure Service Connection support
- Coverage results published to Azure DevOps

## Setup Instructions

### Choose Your Pipeline Platform

**GitHub Actions:** See "GitHub Actions Setup" below
**Azure DevOps:** See "Azure DevOps Setup" below

## GitHub Actions Setup

### Step 1: Configure GitHub Secrets

Add the following secrets to your GitHub repository:

Navigate to: **Settings → Secrets and variables → Actions → New repository secret**

#### Required Secrets

1. **`AZURE_FUNCTIONAPP_NAME`**
   - Value: Your Azure Function App name
   - Example: `century-churn-function-app`

1. **`AZURE_CREDENTIALS`** (Service Principal JSON)
   - Value: JSON credentials for Azure login
   - See "Create Service Principal" section below

1. **`AZURE_FUNCTIONAPP_PUBLISH_PROFILE`** (Alternative to Service Principal)
   - Value: Publish Profile XML from Azure Portal
   - See "Get Publish Profile" section below

### Step 2: Create Azure Service Principal (Option 1)

#### Using Azure CLI

```bash
# Login to Azure
az login

# Create service principal
az ad sp create-for-rbac --name "github-actions-century-churn" \
  --role contributor \
  --scopes /subscriptions/<subscription-id>/resourceGroups/<resource-group> \
  --sdk-auth

# Copy the JSON output and save as GitHub secret AZURE_CREDENTIALS
```

## Example output

```json
{
  "clientId": "...",
  "clientSecret": "...",
  "subscriptionId": "...",
  "tenantId": "...",
  "activeDirectoryEndpointUrl": "[https://login.microsoftonline.com](https://login.microsoftonline.com)",
  "resourceManagerEndpointUrl": "[https://management.azure.com/](https://management.azure.com/)",
  "activeDirectoryGraphResourceId": "[https://graph.windows.net/](https://graph.windows.net/)",
  "sqlManagementEndpointUrl": "[https://management.core.windows.net:8443/](https://management.core.windows.net:8443/)",
  "galleryEndpointUrl": "[https://gallery.azure.com/](https://gallery.azure.com/)",
  "managementEndpointUrl": "[https://management.core.windows.net/](https://management.core.windows.net/)"
}
```

### Step 3: Get Publish Profile (Option 2)

#### Alternative to Service Principal

1. Azure Portal → Function App → Get publish profile
1. Download the `.PublishSettings` file
1. Open file and copy XML content
1. Save as GitHub secret `AZURE_FUNCTIONAPP_PUBLISH_PROFILE`

**Note:** Publish Profile method is simpler but less secure. Use Service Principal for production.

### Step 4: Verify Repository Settings

1. **Enable GitHub Actions:**
   - Repository → Settings → Actions → General
   - Ensure "Allow all actions and reusable workflows" is selected

1. **Branch Protection (Recommended):**
   - Repository → Settings → Branches → Add rule
   - Branch name pattern: `main`
   - Require status checks: Enable CI pipeline checks
   - Require branches to be up to date: Enable

### Step 5: Configure Environments (Optional)

#### For staging/production separation

1. Repository → Settings → Environments
1. Create `staging` environment
1. Create `production` environment
1. Add environment-specific secrets if needed

## Pipeline Behavior

### On Pull Request

1. Runs tests with coverage
1. Runs linting checks
1. Runs type checking
1. Results shown in PR checks

#### On Push to Main/Develop

1. Same as PR checks
1. Uploads coverage (if Codecov configured)

#### On Push to Main

1. Runs tests (continues on failure)
1. Builds Function App package
1. Deploys to Azure Function App
1. Post-deployment verification

#### Manual Deployment

1. Actions → Deploy to Azure Function App → Run workflow
1. Select environment (staging/production)
1. Pipeline runs deployment

## Customization

### Adjust Test Thresholds

Edit `.github/workflows/ci.yml`:

```yaml

- name: Run pylint

  run: |
    pylint function_app/ --fail-under=8.0  # Adjust threshold
```

### Add Deployment Environments

Edit `.github/workflows/deploy.yml`:

```yaml
on:
  workflow_dispatch:
    inputs:
      environment:
        options:

          - development
          - staging
          - production
```

### Skip Deployment on Certain Changes

Edit `.github/workflows/deploy.yml`:

```yaml
on:
  push:
    branches: [main]
    paths-ignore:

      - 'docs/**'
      - 'README.md'
```

## Troubleshooting

### CI Pipeline Fails

**Issue:** Tests failing
**Fix:** Fix test failures locally, ensure tests pass before pushing

**Issue:** Linting failures
**Fix:** Run linting locally (`ruff check .`, `pylint function_app/`)

**Issue:** Type checking failures
**Fix:** Fix type errors, run `pyright function_app/` locally

### Deployment Pipeline Fails

**Issue:** Azure authentication failed

#### Fix (Deployment Pipeline Fails)

- Verify `AZURE_CREDENTIALS` secret is correct
- Verify Service Principal has correct permissions
- Check Azure subscription is active

**Issue:** Function App deployment failed

- Verify `AZURE_FUNCTIONAPP_NAME` is correct
- Check Function App exists and is accessible
- Verify publish profile is valid (if using)

**Issue:** Tests failing in deployment pipeline

- Deployment pipeline continues on test failure for safety
- Fix test failures and re-run
- Or disable test step temporarily if needed

### Debug Pipeline

1. **View Logs:**
   - Actions → Select workflow run → View logs

1. **Run Locally:**

   ```bash
   # Test locally what CI does
   pytest --cov=function_app --cov-report=term-missing -v
   pylint function_app/
   pyright function_app/
   ```

1. **Validate Secrets:**
   - Repository → Settings → Secrets
   - Verify all required secrets are set

## Security Best Practices

1. **Use Service Principal:**
   - More secure than Publish Profile
   - Can be scoped to specific resources
   - Can be rotated easily

1. **Limit Permissions:**
   - Service Principal should only have `contributor` role on Function App
   - Avoid using subscription-level permissions

1. **Rotate Secrets:**
   - Rotate Service Principal credentials periodically
   - Update GitHub secrets when rotated

1. **Branch Protection:**
   - Require PR reviews
   - Require CI checks to pass
   - Prevent force pushes to main

## Monitoring

### View Pipeline Status

1. **GitHub Actions Tab:**
   - Repository → Actions
   - View workflow runs and status

1. **Badge (Optional):**

   ```markdown
   ![CI](https://github.com/<owner>/<repo>/workflows/CI/badge.svg)
   ```

### Notification Settings

1. Repository → Settings → Notifications
1. Configure email notifications for workflow failures
1. Or integrate with Slack/Teams via webhooks

## Advanced Configuration

### Matrix Testing (Multiple Python Versions)

Edit `.github/workflows/ci.yml`:

```yaml
strategy:
  matrix:
    python-version: ["3.11", "3.12"]
```

### Caching Dependencies

Add to CI pipeline:

```yaml

- name: Cache pip packages

  uses: actions/cache@v3
  with:
    path: ~/.cache/pip
    key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements*.txt') }}
    restore-keys: |
      ${{ runner.os }}-pip-
```

### Conditional Deployment

Edit `.github/workflows/deploy.yml`:

```yaml

- name: Deploy to Staging

  if: github.ref == 'refs/heads/develop'
  # ... deployment steps

- name: Deploy to Production

  if: github.ref == 'refs/heads/main'
  # ... deployment steps
```

## Azure DevOps Setup

### Step 1: Create Pipeline

1. **Azure DevOps → Pipelines → New Pipeline**

1. **Select Repository:**
   - Choose Azure Repos Git
   - Select your repository

1. **Configure Pipeline:**
   - Choose "Existing Azure Pipelines YAML file"
   - Path: `azure-pipelines.yml`
   - Click "Continue"

1. **Review and Run:**
   - Review pipeline configuration
   - Click "Run" to test

### Step 2: Configure Service Connection

1. **Azure DevOps → Project Settings → Service connections → New service connection**

1. **Select Azure Resource Manager:**
   - Service connection type: Azure Resource Manager
   - Authentication method: Service principal (automatic)

1. **Configure:**
   - Scope level: Subscription
   - Subscription: Select your subscription
   - Resource group: Select your resource group (optional)
   - Service connection name: `Azure Function App Connection` (or similar)
   - Grant access permission to all pipelines: ✅

1. **Verify:**
   - Test connection
   - Save

### Step 3: Configure Pipeline Variables

1. **Azure DevOps → Pipelines → Your Pipeline → Edit → Variables**

1. **Add Variables:**
   - `AZURE_SERVICE_CONNECTION`: Name of your service connection (e.g., `Azure Function App Connection`)
   - `AZURE_FUNCTIONAPP_NAME`: Your Function App name (e.g., `century-churn-function-app`)
   - `pythonVersion`: `3.11` (optional, defaults in YAML)

1. **Save Variables**

### Step 4: Configure Environments (Optional)

1. **Azure DevOps → Pipelines → Environments → Create environment**

1. **Create Production Environment:**
   - Name: `production`
   - Add approval gates if needed

1. **Update Pipeline:**
   - Environment name in `azure-pipelines.yml` should match

### Step 5: Verify Pipeline

1. **Run Pipeline Manually:**
   - Pipelines → Run pipeline
   - Select branch: `main`
   - Run

1. **Monitor Execution:**
   - View logs in real-time
   - Verify all stages complete successfully

## Dual Remote Configuration

If you want to use both GitHub Actions and Azure DevOps:

1. **Set up dual remotes:** See [Git Remotes Setup Guide](./GIT_REMOTES_SETUP.md)

1. **GitHub Actions triggers:** Only on pushes to `github` remote

1. **Azure DevOps triggers:** Only on pushes to `azure` remote

1. **Sync both remotes:** Use `scripts/sync-remotes.sh` to keep them in sync

## References

### GitHub Actions

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Azure Functions Deployment](https://learn.microsoft.com/azure/azure-functions/functions-how-to-github-actions)
- [Azure Service Principal](https://learn.microsoft.com/azure/active-directory/develop/app-objects-and-service-principals)
- [Workflow Syntax](https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions)

### Azure DevOps

- [Azure Pipelines Documentation](https://learn.microsoft.com/azure/devops/pipelines/)
- [Azure Functions Deployment](https://learn.microsoft.com/azure/azure-functions/functions-how-to-azure-devops)
- [Service Connections](https://learn.microsoft.com/azure/devops/pipelines/library/service-endpoints)
- [YAML Pipeline Reference](https://learn.microsoft.com/azure/devops/pipelines/yaml-schema)

### Dual Remotes

- [Git Remotes Setup Guide](./GIT_REMOTES_SETUP.md)
