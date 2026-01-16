# Century Churn Scoring System

Customer churn risk scoring system for Century Martial Arts (CMFIT wholesale division). Monthly batch scoring of wholesale customers to predict 90-day churn risk with actionable reasons.

## Architecture

```text
DAX Query → Python (score + reasons) → SQL History Table → SQL Views → Power BI
```

- **Azure Function**: Thin orchestration layer
- **SQL**: Business logic (views, functions, stored procedures)
- **Power BI**: Pivot, trends, aggregations via DAX
- **No blob storage**: All in-memory processing

## Setup

### Prerequisites

- Python 3.11+
- Azure SQL Database
- Power BI workspace with dataset and DAX query
- Service Principal for Power BI and Graph API access
- Managed Identity or Service Principal for SQL access

### Local Development

1. **Create virtual environment:**

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

2. **Install dependencies:**

   ```bash
   # Production dependencies
   pip install -r requirements.txt
   
   # Development dependencies (for testing and linting)
   pip install -r requirements-dev.txt
   ```

3. **Configure environment variables:**

   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Verify model files exist:**
   - `model/churn_model.pkl`
   - `model/model_columns.pkl`

## Local Development Workflow

### Scoring Customers (Recommended: Notebook)

**Use the interactive notebook for easier debugging and exploration:**

Open `scripts/local_scoring.ipynb` in Jupyter/VS Code:

- Interactive step-by-step execution
- Visualize intermediate results
- Easy to debug and modify
- Uses the same scoring logic as production (`function_app/scorer.py`)

The notebook handles:

- **Optional:** Split large CSV files into chunks
- **Load** CSV files (single file or directory)
- **Score** customers with churn predictions (uses production `function_app/scorer.py`)
- **Shape** data to match SQL view structure (`dbo.vwCustomerCurrent`)
- **Analyze** and generate comprehensive business report
- **Export** outputs for Power BI exploration

**Outputs:**

- `outputs/churn_scores_combined.csv` - All scored records (all snapshots)
- `outputs/churn_scores_sql_view.csv` - **Shaped to match SQL view `dbo.vwCustomerCurrent`** (latest snapshot per customer, includes Status calculation)
- `outputs/model_report.md` - **Formal business report** with model analysis, KPIs, distributions, and insights
- `outputs/README.md` - Project documentation
- `outputs/model_conda.yml` - Model environment configuration

### Command-Line Scripts (Alternative)

If you prefer command-line execution:

```bash
# Use the interactive notebook for local scoring (recommended)
# Open scripts/local_scoring.ipynb and run the cells
```

**Performance:**

- 400k rows: ~2-3 minutes scoring + reasons
- 12k rows (monthly): ~10 seconds
- XGBoost is CPU-optimized, handles it easily

**Note on SQL View Output:**

The `churn_scores_sql_view.csv` file matches the structure of the SQL view `dbo.vwCustomerCurrent`:

- Latest snapshot per customer (using `ROW_NUMBER` window function logic)
- Status calculation (New/Active/Churned/Reactivated) matching `fnCalculateStatus`
- Column ordering matches SQL view structure
- Ready for Power BI exploration with the same structure as production SQL

## Database Setup

1. **Create schema:**

   ```bash
   # Execute SQL scripts in order:
   sqlcmd -S your-server -d your-database -i sql/schema.sql
   sqlcmd -S your-server -d your-database -i sql/functions.sql
   sqlcmd -S your-server -d your-database -i sql/views.sql
   sqlcmd -S your-server -d your-database -i sql/procedures.sql
   ```

2. **Verify:**
   - Table: `dbo.ChurnScoresHistory`
   - View: `dbo.vwCustomerCurrent`
   - Function: `dbo.fnCalculateStatus`
   - Procedure: `dbo.spInsertChurnScores`

## Azure Function App Deployment

### Prerequisite

- Azure Function App (Python 3.11, Consumption plan)
- Application Insights enabled
- Managed Identity or Service Principal configured

### Deployment Steps

1. **Set environment variables in Function App:**
   - All variables from `.env.example`
   - Set via Azure Portal → Configuration → Application settings

2. **Deploy Function App:**

   ```bash
   cd function_app
   func azure functionapp publish <your-function-app-name>
   ```

3. **Verify deployment:**

   ```bash
   # Test health endpoint
   curl https://<your-function-app>.azurewebsites.net/api/health
   
   # Trigger manual run
   curl -X POST https://<your-function-app>.azurewebsites.net/api/score
   ```

4. **Monitor:**
   - Application Insights for logs and traces
   - Function App → Monitor for execution history
   - Email notifications for success/failure

### Function Endpoints

- **Timer Trigger**: Runs automatically on 1st of each month at 6 AM
- **POST /api/score**: Manual trigger for full pipeline
- **GET /api/health**: Health check endpoint

## Project Structure

```text
.
├── scripts/                    # Utility scripts and notebooks
│   ├── local_scoring.ipynb     # ⭐ Interactive notebook for local scoring (all-in-one workflow)
│   └── clean-git-history.sh   # Git maintenance script
├── tests/                      # Test suite
│   ├── __init__.py
│   ├── conftest.py            # Shared pytest fixtures
│   ├── test_scorer.py         # Scoring logic tests
│   ├── test_config.py         # Configuration tests
│   ├── test_dax_client.py     # DAX client tests
│   └── test_sql_client.py     # SQL client tests
├── requirements.txt            # Production Python dependencies
├── requirements-dev.txt        # Development dependencies (testing, linting)
├── pyproject.toml              # Ruff configuration
├── pytest.ini                  # Pytest configuration
├── .env.example                # Environment variable template
├── model/                      # XGBoost model files
│   ├── churn_model.pkl
│   └── model_columns.pkl
├── sql/                        # Database schema
│   ├── schema.sql
│   ├── views.sql
│   ├── functions.sql
│   └── procedures.sql
├── function_app/              # Azure Function App
│   ├── __init__.py            # Function entry points
│   ├── function_app.py        # Pipeline logic
│   ├── config.py              # Configuration (Pydantic Settings)
│   ├── scorer.py              # Model scoring
│   ├── dax_client.py          # Power BI DAX queries (Tenacity retries)
│   ├── sql_client.py          # Database writes
│   ├── pbi_client.py          # Dataset refresh (Tenacity retries)
│   ├── email_client.py        # Notifications (Tenacity retries)
│   ├── host.json
│   ├── function.json
│   └── requirements.txt
└── outputs/                    # Local scoring outputs
```

## Key Constraints

1. Function outputs scores + reasons only; SQL derives Status
2. Single History table is system of record
3. No intermediate files or blob storage
4. Idempotent: succeeds completely or rolls back completely
5. Model packaged in Function, not pulled at runtime

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=function_app --cov-report=html

# Run only unit tests (exclude integration tests)
pytest -m "not integration"

# Run only integration tests (requires database/Power BI access)
pytest -m integration
```

### Code Quality

```bash
# Lint and format with Ruff
ruff check .
ruff format .

# Type checking with Pyright
pyright function_app/

# Run all quality checks
ruff check . && ruff format --check . && pyright function_app/
```

## Troubleshooting

### Local Scoring Issues

- **Model not found**: Verify `model/churn_model.pkl` exists
- **Column mismatch**: Ensure input CSV has all 77 DAX feature columns
- **Date conversion errors**: Check for Excel serial dates (values > 40000)

### Function App Issues

- **Import errors**: Verify `azure-functions` is in `requirements.txt`
- **Authentication failures**: Check Service Principal credentials in environment variables
- **SQL connection errors**: Verify connection string and Managed Identity permissions
- **Pydantic validation errors**: Check that all required environment variables are set (see config.py)

### Database Issues

- **Primary key violations**: Check for duplicate (CustomerId, SnapshotDate) pairs
- **Status calculation errors**: Verify `fnCalculateStatus` function exists

### Testing Issues

- **Import errors in tests**: Ensure `requirements-dev.txt` is installed: `pip install -r requirements-dev.txt`
- **Coverage below 80%**: Add more unit tests for uncovered code paths

## Support

For issues or questions, check:

- Application Insights logs (Function App)
- SQL error logs
- Email notifications for pipeline failures
