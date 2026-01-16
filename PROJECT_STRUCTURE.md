# Project Structure

Complete organization guide for the Century Churn Prediction project.

## Directory Tree

```text
century-churn-prediction-project/
│
├── .cursor/                    # Cursor IDE rules and configuration
│   └── rules/                  # Coding standards and AI prompts
│       ├── *.md                # Rule files (python, testing, etc.)
│       └── prompts/            # AI assistant task prompts
│
├── .github/                    # GitHub Actions workflows
│   └── workflows/
│       ├── ci.yml              # CI pipeline (tests, linting)
│       └── deploy.yml          # Deployment pipeline
│
├── .vscode/                    # VS Code configuration
│   ├── extensions.json         # Recommended extensions
│   ├── launch.json             # Debug configurations
│   ├── settings.json           # Workspace settings
│   └── tasks.json              # Task definitions
│
├── docs/                       # Operational documentation
│   ├── DEPLOYMENT.md           # Complete deployment runbook
│   ├── CI_CD_SETUP.md          # CI/CD pipeline setup
│   ├── APPLICATION_INSIGHTS_ALERTS.md  # Monitoring configuration
│   ├── SERVICE_PRINCIPAL_SETUP.md      # Authentication setup
│   ├── COST_MONITORING.md      # Cost optimization guide
│   ├── GIT_REMOTES_SETUP.md    # Dual remote configuration
│   └── STREAMLIT_DASHBOARD_ASSESSMENT.md  # Dashboard feasibility
│
├── dax/                        # DAX query files
│   ├── churn_features.dax      # Main feature query
│   └── churn_features_dax_multimonth.dax  # Multi-month query
│
├── function_app/               # Azure Function App
│   ├── __init__.py             # Function entry points
│   ├── function_app.py         # Main pipeline logic
│   ├── config.py               # Configuration (Pydantic Settings)
│   ├── scorer.py               # Model scoring
│   ├── dax_client.py           # Power BI DAX queries
│   ├── sql_client.py           # Database writes
│   ├── pbi_client.py           # Dataset refresh
│   ├── email_client.py         # Notifications (Graph API)
│   ├── function.json           # Function bindings (v2 model)
│   ├── host.json               # Host configuration
│   ├── requirements.txt        # Python dependencies
│   └── .funcignore             # Function deployment exclusions
│
├── model/                      # Machine learning model
│   ├── conda.yml               # Model training environment
│   └── training-notebook.ipynb # Training notebook
│
├── outputs/                    # Generated outputs
│   ├── README.md               # Output documentation
│   ├── code-review.md          # Code review findings
│   └── *.csv                   # Scoring output files
│
├── .internal/                  # Internal documentation (not for release)
│   ├── README.md               # Internal docs explanation
│   └── *.md                    # Analysis and review documents
│
├── scripts/                    # Utility scripts
│   ├── *.py                    # Python utility scripts
│   ├── *.sh                    # Shell scripts
│   ├── local_scoring.ipynb     # Local scoring notebook
│   ├── README_LINTING.md       # Linting documentation
│   ├── README_MARKDOWN_SCRIPTS.md  # Markdown scripts docs
│   └── README_PYTHON_SCRIPTS.md    # Python scripts docs
│
├── sql/                        # Database schema
│   ├── schema.sql              # Tables
│   ├── views.sql               # Views
│   ├── functions.sql           # SQL functions
│   └── procedures.sql          # Stored procedures
│
├── tests/                      # Test suite
│   ├── __init__.py
│   ├── conftest.py             # Shared pytest fixtures
│   ├── test_scorer.py          # Scoring logic tests
│   ├── test_config.py          # Configuration tests
│   ├── test_dax_client.py      # DAX client tests
│   ├── test_sql_client.py      # SQL client tests
│   └── test_*.py               # Other test files
│
├── .gitignore                  # Git ignore patterns
├── .pylintrc                   # Pylint configuration
├── .pre-commit-config.yaml     # Pre-commit hooks
├── azure-pipelines.yml         # Azure DevOps pipeline
├── Makefile                    # Make targets
├── pyproject.toml              # Ruff configuration
├── pyrightconfig.json          # Pyright type checking config
├── pytest.ini                  # Pytest configuration
├── README.md                   # Project README
├── requirements.txt            # Production dependencies
└── requirements-dev.txt        # Development dependencies
```

## Directory Descriptions

### Core Application Code

- **`function_app/`** - Azure Function App code for scoring and services
  - Entry points, pipeline logic, clients for DAX/SQL/Power BI/Email
  - Configuration management and model scoring

- **`dax/`** - DAX query files for churn feature definitions
  - Power BI queries that extract customer features
  - Loaded and executed via `dax_client.py`

- **`sql/`** - Database schema, views, functions, and stored procedures
  - Schema definitions, business logic views, helper functions
  - Stored procedures for data insertion

- **`model/`** - Machine learning model files
  - Training notebook and environment configuration
  - Model files (`.pkl`) stored with Function App

### Testing and Quality

- **`tests/`** - Test suite
  - Unit tests for all Function App components
  - Integration tests (marked with `@pytest.mark.integration`)

- **Configuration files** - `.pylintrc`, `pyproject.toml`, `pytest.ini`, etc.
  - Linting, type checking, and testing configuration

### Scripts and Utilities

- **`scripts/`** - Utility scripts and tools
  - Linting scripts (`fix-markdown-lint.py`, `fix-python-lint.py`)
  - Power BI utilities (`list_datasets.py`, `check_app_permissions.py`)
  - Git utilities (`sync-remotes.sh`, `clean-git-history.sh`)
  - Local scoring notebook (`local_scoring.ipynb`)
  - Documentation (`README_*.md` files)

### Documentation

- **`docs/`** - Operational documentation
  - Deployment runbooks, setup guides, troubleshooting
  - Monitoring, authentication, and cost management guides

- **`.cursor/rules/`** - Coding standards and patterns
  - Development rules, coding standards, AI prompts
  - Quick references and best practices

- **`outputs/`** - Generated outputs and code reviews
  - Code review findings and assessments
  - Scoring output files (CSV)

- **`.internal/`** - Internal documentation (not for release)
  - Analysis and review documents
  - Working documents and historical reviews

### CI/CD and Deployment

- **`.github/workflows/`** - GitHub Actions pipelines
  - CI pipeline: tests, linting, type checking
  - Deploy pipeline: Azure Function App deployment

- **`azure-pipelines.yml`** - Azure DevOps pipeline
  - Alternative CI/CD pipeline for Azure DevOps

- **`Makefile`** - Make targets for common tasks
  - `make lint-fix` - Fix all linting errors
  - `make lint-check` - Check for linting errors

## Documentation Structure

### `.cursor/rules/` - Coding Standards & Patterns

**Purpose:** Guide development, define coding standards, quick references
**Audience:** Developers, AI assistants
**Content:** Patterns, rules, standards, examples, quick reference

#### Key Files - Rules

- **Core Rules:**
  - `python.md` - Python coding standards, type hints, docstrings
  - `testing.md` - Testing patterns and pytest usage
  - `error-handling.md` - Error handling patterns and idempotency
  - `logging.md` - Logging strategy and Application Insights
  - `secrets.md` - Secret management and environment variables

- **Domain-Specific Rules:**
  - `function-app.md` - Azure Function structure and patterns
  - `scoring.md` - Model scoring logic and preprocessing
  - `sql.md` - SQL schema, views, and procedures
  - `dax.md` - DAX query patterns and Power BI integration
  - `power-bi.md` - Power BI API and authentication

- **Code Quality Rules:**
  - `linting.md` - Linting philosophy and error documentation
  - `linting-python-scripts.md` - Python linting for utility scripts
  - `markdown.md` - Markdown formatting standards
  - `linting-markdown.md` - Markdown linting rules
  - `markdown-quick-reference.md` - Quick lookup cheat sheet

- **Operational Rules:**
  - `deployment.md` - Deployment quick reference
  - `documentation.md` - Documentation reference guide
  - `notebooks.md` - Jupyter notebook best practices
  - `overview.md` - Project architecture and constraints

- **Prompts:**
  - `prompts/` - AI assistant task prompts for common workflows

### `docs/` - Operational Documentation

**Purpose:** Step-by-step guides, runbooks, setup procedures
**Audience:** Operators, deployers, administrators
**Content:** Procedures, checklists, troubleshooting, configuration

#### Key Files - Documentation

- `DEPLOYMENT.md` - Complete deployment runbook with step-by-step instructions
- `CI_CD_SETUP.md` - CI/CD pipeline setup (GitHub Actions and Azure DevOps)
- `APPLICATION_INSIGHTS_ALERTS.md` - Application Insights alerts configuration
- `SERVICE_PRINCIPAL_SETUP.md` - Service Principal configuration guide
- `COST_MONITORING.md` - Cost monitoring and optimization guide
- `GIT_REMOTES_SETUP.md` - Dual remote setup (GitHub + Azure DevOps)
- `STREAMLIT_DASHBOARD_ASSESSMENT.md` - Streamlit dashboard feasibility assessment

**Relationship:** Rules reference docs for detailed procedures. Docs reference rules for coding standards.

## Quick Navigation

### For Developers

- **Start here:** `README.md` - Project overview and setup
- **Coding standards:** `.cursor/rules/python.md` - Python coding standards
- **Testing:** `.cursor/rules/testing.md` - Testing patterns
- **Architecture:** `.cursor/rules/overview.md` - Project architecture

### For Operators

- **Deploy:** `docs/DEPLOYMENT.md` - Deployment runbook
- **Setup CI/CD:** `docs/CI_CD_SETUP.md` - Pipeline configuration
- **Monitor:** `docs/APPLICATION_INSIGHTS_ALERTS.md` - Monitoring setup
- **Troubleshoot:** Check relevant `docs/*.md` files

### For AI Assistants

- **Review rules:** `.cursor/rules/` - All rule files with cross-references
- **Use prompts:** `.cursor/rules/prompts/` - Task-specific prompts
- **Check scripts:** `scripts/README_*.md` - Script documentation

## File Naming Conventions

### Python Files

- Application code: `snake_case.py` (e.g., `dax_client.py`)
- Test files: `test_*.py` (e.g., `test_scorer.py`)
- Scripts: `kebab-case.py` or `snake_case.py` (e.g., `fix-markdown-lint.py`)

### Documentation Files

- Markdown files: `UPPERCASE.md` for docs (e.g., `DEPLOYMENT.md`)
- Rules files: `kebab-case.md` (e.g., `function-app.md`)
- README files: `README.md` or `README_*.md`

### Configuration Files

- Standard configs: `.filename` or `filename.ext` (e.g., `.pylintrc`, `pyproject.toml`)

## References

- `.cursor/rules/overview.md` - Project architecture and constraints
- `.cursor/rules/documentation.md` - Complete documentation index
- `README.md` - Project README with setup instructions
