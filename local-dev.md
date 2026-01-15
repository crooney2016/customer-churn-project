# Local Development Rules

## Prerequisites

```bash
# Azure Functions Core Tools
brew install azure-functions-core-tools@4

# Python 3.11
brew install python@3.11

# ODBC Driver for SQL Server
brew install microsoft/mssql-release/msodbcsql18
```

## Setup

```bash
# Create venv
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -r function_app/requirements.txt
```

## local.settings.json

Create `function_app/local.settings.json`:

```json
{
  "IsEncrypted": false,
  "Values": {
    "FUNCTIONS_WORKER_RUNTIME": "python",
    "AzureWebJobsStorage": "UseDevelopmentStorage=false",
    "SQL_CONNECTION_STRING": "Driver={ODBC Driver 18 for SQL Server};Server=localhost;Database=ChurnDev;Trusted_Connection=yes;",
    "PBI_TENANT_ID": "",
    "PBI_CLIENT_ID": "",
    "PBI_CLIENT_SECRET": "",
    "PBI_WORKSPACE_ID": "",
    "PBI_DATASET_ID": "",
    "EMAIL_TENANT_ID": "",
    "EMAIL_CLIENT_ID": "",
    "EMAIL_CLIENT_SECRET": "",
    "EMAIL_SENDER": "",
    "EMAIL_RECIPIENTS": ""
  }
}
```

Never commit this file. Add to .gitignore.

## Run Locally

```bash
cd function_app
func start
```

Endpoints available at:
- http://localhost:7071/api/health
- http://localhost:7071/api/score
- http://localhost:7071/api/dax/execute
- http://localhost:7071/api/sql/write
- http://localhost:7071/api/pbi/refresh

## VS Code Debugging

### launch.json

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Attach to Python Functions",
      "type": "python",
      "request": "attach",
      "port": 9091,
      "preLaunchTask": "func: host start"
    }
  ]
}
```

### tasks.json

```json
{
  "version": "2.0.0",
  "tasks": [
    {
      "type": "func",
      "label": "func: host start",
      "command": "host start",
      "problemMatcher": "$func-python-watch",
      "isBackground": true,
      "options": {
        "cwd": "${workspaceFolder}/function_app"
      }
    }
  ]
}
```

## Testing Endpoints

```bash
# Health check
curl http://localhost:7071/api/health

# Trigger scoring (POST)
curl -X POST http://localhost:7071/api/score

# With payload
curl -X POST http://localhost:7071/api/score \
  -H "Content-Type: application/json" \
  -d '{"snapshot_date": "2025-01-01"}'
```

## Local SQL

Options:
- Azure SQL dev database (connection string in local.settings.json)
- Docker SQL Server: `docker run -e 'ACCEPT_EULA=Y' -e 'SA_PASSWORD=...' -p 1433:1433 mcr.microsoft.com/mssql/server:2022-latest`
- SQL Server LocalDB (Windows only)

## Skipping External Services

For local testing without Power BI or email:

```python
# In config.py
SKIP_PBI_REFRESH = os.getenv("SKIP_PBI_REFRESH", "false").lower() == "true"
SKIP_EMAIL = os.getenv("SKIP_EMAIL", "false").lower() == "true"
```

Add to local.settings.json:
```json
"SKIP_PBI_REFRESH": "true",
"SKIP_EMAIL": "true"
```
