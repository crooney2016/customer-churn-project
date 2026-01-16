# CI/CD Pipeline Setup Guide

**Project:** Century Churn Prediction System  
**Last Updated:** 2024-12-19  
**Version:** 1.0

## Overview

This document provides instructions for setting up CI/CD pipelines for the Century Churn Prediction System using GitHub Actions. The pipeline includes automated testing, linting, and deployment to Azure Function App.

## Prerequisites

- GitHub repository with Actions enabled
- Azure subscription with appropriate permissions
- Azure Function App created
- Azure Service Principal or Publish Profile for deployment

## Pipeline Configuration

### CI Pipeline (`.github/workflows/ci.yml`)

**Triggers:**
- Push to `main` or `develop` branches
- Pull requests to `main` or `develop` branches

**Jobs:**

1. **Test Job:**
   - Runs pytest with coverage
   - Uploads coverage to Codecov (optional)
   - Python 3.11

2. **Lint Job:**
   - Runs pylint, pyright, ruff check, ruff format
   - Python 3.11

3. **Type Check Job:**
   - Runs pyright for type checking
   - Python 3.11

### Deployment Pipeline (`.github/workflows/deploy.yml`)

**Triggers:**
- Push to `main` branch (changes in `function_app/`)
- Manual workflow dispatch (with environment selection)

**Jobs:**

1. **Build and Deploy:**
   - Runs tests (continues on failure for safety)
   - Deploys to Azure Function App
   - Supports staging and production environments

## Setup Instructions

### Step 1: Configure GitHub Secrets

Add the following secrets to your GitHub repository:

**Settings → Secrets and variables → Actions → New repository secret**

#### Required Secrets

1. **`AZURE_FUNCTIONAPP_NAME`**
   - Value: Your Azure Function App name
   - Example: `century-churn-function-app`

2. **`AZURE_CREDENTIALS`** (Service Principal JSON)
   - Value: JSON credentials for Azure login
   - See "Create Service Principal" section below

3. **`AZURE_FUNCTIONAPP_PUBLISH_PROFILE`** (Alternative to Service Principal)
   - Value: Publish Profile XML from Azure Portal
   - See "Get Publish Profile" section below

### Step 2: Create Azure Service Principal (Option 1)

**Using Azure CLI:**

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

**Example output:**
```json
{
  "clientId": "...",
  "clientSecret": "...",
  "subscriptionId": "...",
  "tenantId": "...",
  "activeDirectoryEndpointUrl": "https://login.microsoftonline.com",
  "resourceManagerEndpointUrl": "https://management.azure.com/",
  "activeDirectoryGraphResourceId": "https://graph.windows.net/",
  "sqlManagementEndpointUrl": "https://management.core.windows.net:8443/",
  "galleryEndpointUrl": "https://gallery.azure.com/",
  "managementEndpointUrl": "https://management.core.windows.net/"
}
```

### Step 3: Get Publish Profile (Option 2)

**Alternative to Service Principal:**

1. Azure Portal → Function App → Get publish profile
2. Download the `.PublishSettings` file
3. Open file and copy XML content
4. Save as GitHub secret `AZURE_FUNCTIONAPP_PUBLISH_PROFILE`

**Note:** Publish Profile method is simpler but less secure. Use Service Principal for production.

### Step 4: Verify Repository Settings

1. **Enable GitHub Actions:**
   - Repository → Settings → Actions → General
   - Ensure "Allow all actions and reusable workflows" is selected

2. **Branch Protection (Recommended):**
   - Repository → Settings → Branches → Add rule
   - Branch name pattern: `main`
   - Require status checks: Enable CI pipeline checks
   - Require branches to be up to date: Enable

### Step 5: Configure Environments (Optional)

**For staging/production separation:**

1. Repository → Settings → Environments
2. Create `staging` environment
3. Create `production` environment
4. Add environment-specific secrets if needed

## Pipeline Behavior

### CI Pipeline

**On Pull Request:**

1. Runs tests with coverage
2. Runs linting checks
3. Runs type checking
4. Results shown in PR checks

**On Push to Main/Develop:**

1. Same as PR checks
2. Uploads coverage (if Codecov configured)

### Deployment Pipeline

**On Push to Main:**

1. Runs tests (continues on failure)
2. Builds Function App package
3. Deploys to Azure Function App
4. Post-deployment verification

**Manual Deployment:**

1. Actions → Deploy to Azure Function App → Run workflow
2. Select environment (staging/production)
3. Pipeline runs deployment

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
**Fix:** 
- Verify `AZURE_CREDENTIALS` secret is correct
- Verify Service Principal has correct permissions
- Check Azure subscription is active

**Issue:** Function App deployment failed  
**Fix:**
- Verify `AZURE_FUNCTIONAPP_NAME` is correct
- Check Function App exists and is accessible
- Verify publish profile is valid (if using)

**Issue:** Tests failing in deployment pipeline  
**Fix:**
- Deployment pipeline continues on test failure for safety
- Fix test failures and re-run
- Or disable test step temporarily if needed

### Debug Pipeline

1. **View Logs:**
   - Actions → Select workflow run → View logs

2. **Run Locally:**
   ```bash
   # Test locally what CI does
   pytest --cov=function_app --cov-report=term-missing -v
   pylint function_app/
   pyright function_app/
   ```

3. **Validate Secrets:**
   - Repository → Settings → Secrets
   - Verify all required secrets are set

## Security Best Practices

1. **Use Service Principal:**
   - More secure than Publish Profile
   - Can be scoped to specific resources
   - Can be rotated easily

2. **Limit Permissions:**
   - Service Principal should only have `contributor` role on Function App
   - Avoid using subscription-level permissions

3. **Rotate Secrets:**
   - Rotate Service Principal credentials periodically
   - Update GitHub secrets when rotated

4. **Branch Protection:**
   - Require PR reviews
   - Require CI checks to pass
   - Prevent force pushes to main

## Monitoring

### View Pipeline Status

1. **GitHub Actions Tab:**
   - Repository → Actions
   - View workflow runs and status

2. **Badge (Optional):**
   ```markdown
   ![CI](https://github.com/<owner>/<repo>/workflows/CI/badge.svg)
   ```

### Notification Settings

1. Repository → Settings → Notifications
2. Configure email notifications for workflow failures
3. Or integrate with Slack/Teams via webhooks

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

## References

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Azure Functions Deployment](https://learn.microsoft.com/azure/azure-functions/functions-how-to-github-actions)
- [Azure Service Principal](https://learn.microsoft.com/azure/active-directory/develop/app-objects-and-service-principals)
- [Workflow Syntax](https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions)
