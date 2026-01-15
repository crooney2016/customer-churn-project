# Testing Rules

## Structure

```
tests/
  __init__.py
  test_scorer.py
  test_sql_client.py
  test_config.py
  conftest.py          # Shared fixtures
  fixtures/
    sample_input.csv
    expected_output.csv
```

## Dependencies

Add to requirements.txt:
```
pytest
pytest-cov
pytest-mock
```

## Run Tests

```bash
# All tests
pytest tests/

# With coverage
pytest tests/ --cov=function_app --cov-report=term-missing

# Single file
pytest tests/test_scorer.py

# Single test
pytest tests/test_scorer.py::test_risk_band_high
```

## Unit Tests

### test_scorer.py

```python
import pytest
import pandas as pd
from function_app.scorer import (
    preprocess,
    calculate_risk_band,
    generate_reasons,
)

def test_risk_band_high():
    assert calculate_risk_band(0.75) == "A - High Risk"
    assert calculate_risk_band(0.70) == "A - High Risk"

def test_risk_band_medium():
    assert calculate_risk_band(0.50) == "B - Medium Risk"
    assert calculate_risk_band(0.30) == "B - Medium Risk"

def test_risk_band_low():
    assert calculate_risk_band(0.29) == "C - Low Risk"
    assert calculate_risk_band(0.0) == "C - Low Risk"

def test_preprocess_strips_brackets():
    df = pd.DataFrame({"[CustomerId]": ["123"], "[Segment]": ["FITNESS"]})
    result = preprocess(df)
    assert "CustomerId" in result.columns
    assert "[CustomerId]" not in result.columns

def test_preprocess_fills_null_segment():
    df = pd.DataFrame({"CustomerId": ["123"], "Segment": [None]})
    result = preprocess(df)
    assert result["Segment"].iloc[0] == "UNKNOWN"
```

### test_config.py

```python
import pytest
import os
from function_app.config import Config

def test_config_loads_from_env(monkeypatch):
    monkeypatch.setenv("SQL_CONNECTION_STRING", "test_conn")
    monkeypatch.setenv("PBI_TENANT_ID", "test_tenant")
    
    config = Config()
    assert config.sql_connection_string == "test_conn"
    assert config.pbi_tenant_id == "test_tenant"

def test_config_raises_on_missing_required(monkeypatch):
    monkeypatch.delenv("SQL_CONNECTION_STRING", raising=False)
    
    with pytest.raises(ValueError):
        Config()
```

## Mocking External Services

### conftest.py

```python
import pytest
from unittest.mock import MagicMock

@pytest.fixture
def mock_sql_connection(mocker):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mocker.patch("pyodbc.connect", return_value=mock_conn)
    return mock_conn, mock_cursor

@pytest.fixture
def mock_pbi_client(mocker):
    mock = MagicMock()
    mocker.patch("function_app.pbi_client.refresh_dataset", return_value=True)
    return mock

@pytest.fixture
def sample_input_df():
    return pd.DataFrame({
        "CustomerId": ["001", "002"],
        "Segment": ["FITNESS", "FARRELL"],
        "CostCenter": ["CMFIT", "CMFIT"],
        "Orders_CY": [10, 2],
        "Spend_Lifetime": [5000.0, 500.0],
    })
```

### test_sql_client.py

```python
def test_insert_scores_calls_execute(mock_sql_connection, sample_input_df):
    conn, cursor = mock_sql_connection
    
    from function_app.sql_client import insert_scores
    insert_scores(sample_input_df)
    
    assert cursor.execute.called
    assert conn.commit.called

def test_insert_scores_rollback_on_error(mock_sql_connection, sample_input_df):
    conn, cursor = mock_sql_connection
    cursor.execute.side_effect = Exception("DB error")
    
    from function_app.sql_client import insert_scores
    
    with pytest.raises(Exception):
        insert_scores(sample_input_df)
    
    assert conn.rollback.called
```

## Integration Tests

Mark with `@pytest.mark.integration`:

```python
@pytest.mark.integration
def test_full_scoring_pipeline():
    """Requires local SQL and model files."""
    # Skip in CI without database
    pass
```

Run separately:
```bash
pytest tests/ -m integration
pytest tests/ -m "not integration"
```

## CI Configuration

### pytest.ini

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_functions = test_*
markers =
    integration: marks tests requiring external services
```

## Coverage Threshold

Enforce minimum coverage:
```bash
pytest tests/ --cov=function_app --cov-fail-under=80
```
