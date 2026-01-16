# Service Principal Setup for Power BI executeQueries

Complete step-by-step guide to set up a service principal for Power BI executeQueries.

## Prerequisites

- Power BI Admin access
- Azure AD Global Admin or Power BI Admin role
- Premium Per User (PPU) or Premium capacity

## Step 1: Create App Registration

1. Go to **Azure Portal** → **Microsoft Entra ID** → **App registrations**
2. Click **"+ New registration"**
3. In the dialog, select: **"Register an application to integrate with Microsoft Entra ID (App you're developing)"**
4. Fill in:
   - **Name**: `Power BI Service Principal` (or your preferred name)
   - **Supported account types**: "Accounts in this organizational directory only"
   - Click **Register**

5. **Save these values** (you'll need them for `.env`):
   - **Application (client) ID** - This is your `PBI_CLIENT_ID`
   - **Directory (tenant) ID** - This is your `PBI_TENANT_ID`

## Step 2: Create Client Secret

1. In your app registration, go to **Certificates & secrets**
2. Click **"+ New client secret"**
3. Fill in:
   - **Description**: `Power BI executeQueries secret`
   - **Expires**: Choose appropriate expiration (e.g., 24 months)
4. Click **Add**
5. **IMMEDIATELY copy the secret value** - This is your `PBI_CLIENT_SECRET`
   - ⚠️ You won't be able to see it again!

## Step 3: Create Security Group

1. Go to **Azure Portal** → **Microsoft Entra ID** → **Groups**
2. Click **"+ New group"**
3. Fill in:
   - **Group type**: **Security**
   - **Group name**: `Power BI Service Principle` (or your preferred name)
   - Click **Create**

4. Add the service principal to the group:
   - Open the group you just created
   - Click **Members** → **+ Add members**
   - Search for your app registration name (`Power BI Service Principal`)
   - Select it and click **Select**
   - ⚠️ Important: You're adding the **Enterprise Application** (service principal), not the app registration

## Step 4: Configure Power BI Tenant Settings

### 4a. Enable "Allow service principals to use Power BI APIs"

1. Go to **Power BI Service** → **Settings** (gear icon) → **Admin portal**
2. Go to **Tenant settings** → **Developer settings** (or **Admin API settings**)
3. Find: **"Allow service principals to use Power BI APIs"**
4. Toggle to **Enabled**
5. Select **"Specific security groups"**
6. Add your security group: `Power BI Service Principle`
7. Click **Apply**

### 4b. Enable "Semantic Model Execute Queries REST API"

1. Still in **Tenant settings**, go to **Integration settings**
2. Find: **"Semantic Model Execute Queries REST API"**
3. Toggle to **Enabled**
4. Select **"Specific security groups"**
5. Add the same security group: `Power BI Service Principle`
6. Click **Apply**

## Step 5: Grant Dataset Permissions

1. Go to **Power BI Service** → Your workspace
2. Find your dataset (e.g., "MTS V2")
3. Click **"..."** menu next to the dataset → **Manage permissions**
4. Click **"Grant people access"**
5. Add your service principal:
   - Enter the service principal's **Object ID** (NOT Client ID)
   - Find Object ID: Azure Portal → App registrations → Your app → Overview → Object ID
6. Grant permissions: **Read** + **Build** (or **ReadExplore**)
7. Click **Grant access**

## Step 6: Grant Workspace Access (Optional but Recommended)

1. Go to **Power BI Service** → Your workspace
2. Click **"..."** menu → **Workspace access**
3. Add your service principal (use Object ID)
4. Grant role: **Admin** or **Member**
5. Click **Add**

## Step 7: Configure Your Application

**IMPORTANT: Do NOT add any API permissions in Azure AD!**

According to Microsoft docs, apps using service principal for executeQueries **must NOT** have any admin-consent required (Application) permissions for Power BI.

1. Go to **Azure Portal** → **App registrations** → Your app → **API permissions**
2. **Verify there are NO Application permissions** for Power BI Service
3. If you see any Application permissions (like `Tenant.Read.All`), **remove them**
4. You can keep Delegated permissions if needed, but they're not required for executeQueries

## Step 8: Update .env File

Add these values to your `.env` file:

```bash
PBI_TENANT_ID=<your-tenant-id-from-step-1>
PBI_CLIENT_ID=<your-client-id-from-step-1>
PBI_CLIENT_SECRET=<your-secret-from-step-2>
PBI_WORKSPACE_ID=<your-workspace-id>
PBI_DATASET_ID=<your-dataset-id>
```

## Step 9: Wait for Propagation

Wait **5-10 minutes** for all changes to propagate:

- Security group membership
- Tenant settings
- Dataset permissions

## Step 10: Test

Run the test script:

```bash
python scripts/test_dax_query.py churn_features
```

## Troubleshooting

### 401 Unauthorized

1. Verify tenant settings are enabled and scoped correctly
2. Verify service principal is in the security group
3. Verify NO Application permissions exist for Power BI Service
4. Verify dataset has Build permission for service principal
5. Wait 10-15 minutes for propagation

### Token has roles but still 401

- This means Application permissions are present
- Remove ALL Application permissions for Power BI Service
- Token should NOT have `roles` claim when correct

## Key Points

- **No API permissions needed** - Tenant settings provide authorization
- **Application permissions block executeQueries** - Must be removed
- **Security group membership required** - SP must be in allowed groups
- **Build permission required** - On dataset, not just workspace
- **Object ID vs Client ID** - Use Object ID for Power BI permissions, Client ID for authentication
