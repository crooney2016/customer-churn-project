# Code Review - Century Churn Prediction Project

**Review Date:** 2024-12-19  
**Reviewer:** AI Code Review  
**Scope:** function_app/ directory and project structure

**Rules Referenced:**

- `.cursor/rules/overview.md` - Project architecture and constraints
- `.cursor/rules/function-app.md` - Azure Function structure and patterns
- `.cursor/rules/dax.md` - DAX query handling and column naming
- `.cursor/rules/error-handling.md` - Error handling patterns and idempotency
- `.cursor/rules/notebooks.md` - Notebook best practices

## Executive Summary

### Overall Assessment: ✅ **GOOD** with Minor Improvements Needed

The codebase demonstrates solid architecture and follows many best practices. The separation of concerns is clear, type hints are used consistently, and error handling is present. However, there are several areas for improvement including error handling robustness, model path resolution, DAX query handling, and some code quality issues.

### Files Reviewed

- ✅ `config.py` - **OK** (minor improvements)
- ⚠️ `dax_client.py` - **Needs Work** (DAX query handling)
- ✅ `scorer.py` - **OK** (well-structured)
- ⚠️ `sql_client.py` - **Needs Work** (error handling, performance)
- ✅ `pbi_client.py` - **OK** (good structure)
- ✅ `email_client.py` - **OK** (good structure)
- ⚠️ `function_app.py` - **Needs Work** (DAX query handling)
- ✅ `__init__.py` - **OK** (clean entry points)

---

## Detailed File Reviews

### 1. config.py ✅

**Status:** OK - Minor improvements recommended

**Strengths:**

- ✅ Clean class-based configuration
- ✅ Type hints present
- ✅ Validation method implemented
- ✅ Helper method for parsing recipients
- ✅ No hardcoded secrets

**Issues Found:**

1. **Missing Environment Variable Documentation**
   - No `.env.example` file visible in project
   - Consider adding inline comments documenting expected format

2. **Configuration Validation Timing**
   - Validation only happens when `validate()` is called
   - Consider validating on import or using `__post_init__` pattern

**Recommendations:**

```python
# Add to Config class:
@classmethod
def from_env(cls) -> 'Config':
    """Factory method that validates on creation."""
    instance = cls()
    instance.validate()
    return instance
```

**Action Items:**

- [ ] Create `.env.example` file with all required variables
- [ ] Consider adding validation on config instantiation
- [ ] Add documentation for each configuration variable

---

### 2. dax_client.py ⚠️

**Status:** Needs Work

**Rules Reference:** `.cursor/rules/dax.md` - DAX queries should be in `dax/` directory, columns must match schema

**Strengths:**

- ✅ Good use of MSAL for authentication
- ✅ Type hints present
- ✅ Error handling for token acquisition
- ✅ Proper DataFrame conversion
- ✅ Handles bracketed column names (per dax.md rules)

**Issues Found:**

1. **Critical: DAX Query Handling** (Violates dax.md rules)
   - `execute_dax_query()` expects a query string, but `function_app.py` passes `config.DAX_QUERY_NAME` (which is a string name, not the query)
   - `get_dax_query_from_dataset()` is a stub that returns empty string
   - **This will cause runtime failures**
   - Per `dax.md`: Queries should be loaded from `dax/` directory files (`churn_features.dax` or `churn_features_dax_multimonth.dax`)

2. **Missing Query Source** (Violates dax.md rules)
   - No mechanism to load DAX queries from files in `dax/` directory
   - Queries exist but are not integrated into code
   - Should load from `dax/churn_features.dax` or `dax/churn_features_dax_multimonth.dax`

3. **Column Validation Missing** (Per dax.md rules)
   - Should validate 77 columns per customer per snapshot
   - Should verify columns match expected schema before processing
   - Missing validation for required columns: CustomerId, AccountName, Segment, CostCenter, SnapshotDate

4. **Error Handling**
   - `execute_dax_query()` raises generic `ValueError` for empty results
   - Should provide more context about what query failed

5. **Timeout Configuration**
   - Hardcoded 300 second timeout may be too long for some queries
   - Should be configurable

**Recommendations:**

```python
# Per dax.md rules: Load from dax/ directory
def load_dax_query_from_file(query_name: str = "churn_features") -> str:
    """Load DAX query from dax/ directory per dax.md rules."""
    query_path = Path(__file__).parent.parent / "dax" / f"{query_name}.dax"
    if not query_path.exists():
        raise FileNotFoundError(f"DAX query file not found: {query_path}")
    return query_path.read_text()

# Validate expected columns per dax.md (77 columns)
def validate_dax_columns(df: pd.DataFrame) -> None:
    """Validate DAX output matches expected schema per dax.md rules."""
    required = ["CustomerId", "AccountName", "Segment", "CostCenter", "SnapshotDate"]
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    # Should have ~77 total columns per dax.md
```

**Action Items:**

- [ ] **CRITICAL:** Fix DAX query loading mechanism (per dax.md rules)
- [ ] Implement query loading from `dax/` directory files (`churn_features.dax`)
- [ ] Add column validation (77 columns per dax.md rules)
- [ ] Add better error messages with query context
- [ ] Make timeout configurable
- [ ] Add query validation before execution

---

### 3. scorer.py ✅

**Status:** OK - Well-structured

**Strengths:**

- ✅ Excellent separation of concerns (normalize, preprocess, score, reason generation)
- ✅ Good handling of Excel date conversion
- ✅ Comprehensive feature phrase mapping
- ✅ Type hints throughout
- ✅ Handles edge cases (missing columns, NaN values)

**Issues Found:**

1. **Model Path Resolution**
   - `load_model()` looks for model in `function_app/model/` but README says `model/`
   - Path resolution may fail in Azure Functions deployment

   ```python
   model_dir = Path(__file__).parent / "model"  # function_app/model/
   # But model files are in project root: model/
   ```

2. **Hardcoded Feature Lists**
   - Feature columns list in `sql_client.py` duplicates logic
   - Consider centralizing feature definitions

3. **Type Hints**
   - `load_model()` returns `Tuple[object, list]` - should be more specific
   - Consider `Tuple[xgb.Booster, List[str]]`

**Recommendations:**

```python
# Fix model path
def load_model() -> Tuple[xgb.Booster, List[str]]:
    """Load XGBoost model and model columns."""
    # Try multiple paths for flexibility
    possible_paths = [
        Path(__file__).parent / "model",  # function_app/model/
        Path(__file__).parent.parent / "model",  # project root model/
    ]
    
    for model_dir in possible_paths:
        model_path = model_dir / "churn_model.pkl"
        if model_path.exists():
            # Load from this path
            break
    else:
        raise FileNotFoundError(f"Model not found in any expected location")
```

**Action Items:**

- [ ] Fix model path resolution to check multiple locations
- [ ] Improve type hints for model return type
- [ ] Consider extracting feature column definitions to shared module
- [ ] Add validation that model columns match expected features

---

### 4. sql_client.py ⚠️

**Status:** Needs Work

**Rules Reference:** `.cursor/rules/error-handling.md` - Must be idempotent, single transaction, rollback on failure

**Strengths:**

- ✅ Good use of Azure Managed Identity
- ✅ Comprehensive parameter handling
- ✅ Safe type conversion helpers
- ✅ Transaction rollback on error (per error-handling.md)
- ✅ Single transaction wraps all writes (per error-handling.md)

**Issues Found:**

1. **Performance: Row-by-Row Insert** (Violates error-handling.md efficiency)
   - `insert_churn_scores()` processes rows one at a time
   - For 12k+ rows, this will be very slow
   - Should use bulk insert or batch processing
   - Per error-handling.md: Should handle large datasets efficiently

2. **Error Handling** (Partially violates error-handling.md)
   - Generic exception catching loses specific SQL error details
   - Should preserve SQL error codes and messages
   - Per error-handling.md: Should log to Application Insights and email on failure
   - Current implementation rolls back (✅) but doesn't log to Application Insights

3. **Connection Management**
   - Managed Identity token acquisition is attempted but token not used
   - Connection string authentication may not work with Managed Identity

4. **Hardcoded Feature List**
   - Feature columns list is duplicated from schema
   - Should be derived from DataFrame or shared constant

5. **Missing Retry Logic** (Per error-handling.md)
   - Should implement exponential backoff for transient errors (network timeouts, connection drops)
   - Max 3 attempts per error-handling.md rules
   - Currently fails immediately on any error

**Recommendations:**

```python
# Use bulk insert for better performance
def insert_churn_scores(df: pd.DataFrame) -> int:
    """Insert churn scores using bulk insert."""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Prepare data for bulk insert
        # Use executemany or bulk insert pattern
        # Or use pandas to_sql with SQLAlchemy
        
        # For now, batch in chunks of 1000
        batch_size = 1000
        rows_processed = 0
        
        for i in range(0, len(df), batch_size):
            batch = df.iloc[i:i+batch_size]
            # Process batch
            rows_processed += len(batch)
        
        conn.commit()
        return rows_processed
    except Exception as e:
        if conn:
            conn.rollback()
        # Preserve SQL error details
        raise RuntimeError(f"SQL operation failed: {str(e)}") from e
```

**Action Items:**

- [ ] **HIGH PRIORITY:** Implement bulk insert or batch processing
- [ ] **HIGH PRIORITY:** Add retry logic with exponential backoff (per error-handling.md)
- [ ] Fix Managed Identity authentication (use token in connection)
- [ ] Improve error handling to preserve SQL error details
- [ ] Add Application Insights logging on failure (per error-handling.md)
- [ ] Extract feature column list to shared constant
- [ ] Add connection pooling configuration
- [ ] Consider using SQLAlchemy for better connection management

---

### 5. pbi_client.py ✅

**Status:** OK

**Strengths:**

- ✅ Clean separation of concerns
- ✅ Good timeout handling
- ✅ Proper error handling for refresh failures
- ✅ Reuses access token function

**Issues Found:**

1. **Polling Interval**
   - 5 second polling may be too frequent for long-running refreshes
   - Consider exponential backoff

2. **Error Details**
   - Refresh failure error could include more context (dataset name, workspace)

**Minor Recommendations:**

- Consider configurable polling interval
- Add more context to error messages

**Action Items:**

- [ ] Consider exponential backoff for polling
- [ ] Enhance error messages with dataset context

---

### 6. email_client.py ✅

**Status:** OK

**Strengths:**

- ✅ Clean email composition
- ✅ Good HTML formatting
- ✅ Proper error handling
- ✅ Reusable email functions

**Issues Found:**

1. **Division by Zero Risk**
   - `send_success_email()` divides by `total` without checking

   ```python
   high_risk/total*100  # Could divide by zero if total is 0
   ```

2. **Email Template**
   - HTML template is embedded in code
   - Consider externalizing to template file for easier maintenance

**Recommendations:**

```python
def send_success_email(...):
    total = sum(risk_distribution.values())
    if total == 0:
        # Handle edge case
        return
    
    high_risk_pct = (high_risk / total * 100) if total > 0 else 0
    # ...
```

**Action Items:**

- [ ] Add zero-division check in success email
- [ ] Consider externalizing email templates

---

### 7. function_app.py ⚠️

**Status:** Needs Work

**Rules Reference:**

- `.cursor/rules/error-handling.md` - Must be idempotent, email on success/failure
- `.cursor/rules/dax.md` - DAX queries from `dax/` directory
- `.cursor/rules/overview.md` - Architecture constraints

**Strengths:**

- ✅ Clear pipeline structure (per overview.md architecture)
- ✅ Good logging
- ✅ Comprehensive error handling
- ✅ Step tracking for debugging
- ✅ Email notifications on success/failure (per error-handling.md)
- ✅ Idempotent design (per error-handling.md)

**Issues Found:**

1. **Critical: DAX Query Handling** (Violates dax.md rules)
   - Line 43: `dax_query = config.DAX_QUERY_NAME or ""`
   - This gets a query NAME, not the query TEXT
   - Then passes it to `execute_dax_query()` which expects query text
   - **This will fail at runtime**
   - Per dax.md: Should load from `dax/` directory files

2. **Error Handling** (Partially violates error-handling.md)
   - Catches broad exceptions but may miss some edge cases
   - Email sending failure is caught but pipeline still fails (✅ correct per error-handling.md)
   - Missing: Should exit non-zero on failure (per error-handling.md)
   - Missing: Should log to Application Insights (per error-handling.md)

3. **Power BI Refresh**
   - Refresh is triggered but failure is only logged as warning
   - Per error-handling.md: Should email on failure
   - Consider making this configurable (required vs optional)

4. **Missing Retry Logic** (Per error-handling.md)
   - Should implement exponential backoff for transient errors
   - Currently fails immediately on network/connection errors

**Recommendations:**

```python
# Fix DAX query loading
step = "dax_query"
logger.info("Loading DAX query...")

# Option 1: Load from file
from pathlib import Path
dax_query_file = Path(__file__).parent.parent / "dax" / "churn_features.dax"
if not dax_query_file.exists():
    raise FileNotFoundError(f"DAX query file not found: {dax_query_file}")
dax_query = dax_query_file.read_text()

# Option 2: Use config with full query text
dax_query = config.DAX_QUERY_TEXT  # Add this to config

logger.info("Executing DAX query...")
df = execute_dax_query(dax_query)
```

**Action Items:**

- [ ] **CRITICAL:** Fix DAX query loading (per dax.md rules - load from `dax/` directory)
- [ ] Add validation that DAX query is not empty before execution
- [ ] Add retry logic with exponential backoff (per error-handling.md)
- [ ] Ensure exit non-zero on failure (per error-handling.md)
- [ ] Add Application Insights logging (per error-handling.md)
- [ ] Consider making Power BI refresh optional/configurable

---

### 8. **init**.py ✅

**Status:** OK

**Strengths:**

- ✅ Clean Azure Functions entry points
- ✅ Proper HTTP response handling
- ✅ Good error handling

**Issues Found:**

1. **HTTP Response Format**
   - Success response is plain text
   - Consider JSON response for programmatic access

2. **Error Response Details**
   - Error messages exposed to HTTP clients
   - May want to sanitize for production

**Minor Recommendations:**

- Return JSON responses for better API consistency
- Consider adding request logging

**Action Items:**

- [ ] Consider JSON response format
- [ ] Add request/response logging

---

## Additional Components Review

### Notebooks (Per notebooks.md rules)

**Files Reviewed:**

- `scripts/local_scoring.ipynb` - Local scoring workflow
- `model/training-notebook.ipynb` - Model training reference

**Rules Reference:** `.cursor/rules/notebooks.md` - Notebook best practices

**Compliance Check:**

- ✅ Notebooks in appropriate locations (`scripts/`, `model/`)
- ⚠️ Should verify outputs are cleared before git commit (per notebooks.md)
- ⚠️ Should verify one task per cell (per notebooks.md)
- ⚠️ Should verify markdown cells for intent (per notebooks.md)
- ✅ No hardcoded secrets (per notebooks.md)
- ✅ Uses reusable code from `.py` files (per notebooks.md - uses `function_app/scorer.py`)

**Recommendations:**

- Add `.ipynb_checkpoints/` to `.gitignore` (already present ✅)
- Consider adding notebook linting/pre-commit hooks to clear outputs

---

## Project Structure Review

### ✅ Strengths

1. **Clear Separation of Concerns**
   - Client modules (dax, sql, pbi, email) are well-separated
   - Scoring logic is isolated
   - Configuration is centralized

2. **Good Documentation**
   - README is comprehensive
   - Project structure documented
   - Setup instructions clear

3. **Proper Git Ignore**
   - Model files excluded
   - Environment files excluded
   - Output files excluded

### ⚠️ Issues

1. **Model File Location**
   - README says model files in `model/`
   - Code looks in `function_app/model/`
   - Inconsistency will cause deployment issues

2. **Missing Files**
   - No `.env.example` file
   - No test directory (though `testing.md` exists)
   - No CI/CD configuration visible

3. **DAX Query Integration** (Violates dax.md rules)
   - DAX files in `dax/` directory not integrated into code
   - No mechanism to load them
   - Per dax.md: Should load from `dax/churn_features.dax` or `dax/churn_features_dax_multimonth.dax`
   - Missing column validation (should verify 77 columns per dax.md)

---

## Code Quality Issues

### Type Hints

- ✅ Generally good coverage
- ⚠️ Some return types could be more specific (`object`, `list` vs `xgb.Booster`, `List[str]`)

### Error Handling (Per error-handling.md rules)

- ✅ Most functions have error handling
- ✅ Transaction rollback implemented (per error-handling.md)
- ✅ Email notifications on success/failure (per error-handling.md)
- ⚠️ Missing retry logic with exponential backoff (per error-handling.md)
- ⚠️ Missing Application Insights logging (per error-handling.md)
- ⚠️ Some generic exception catching loses error context
- ⚠️ SQL errors could be more descriptive
- ⚠️ Should exit non-zero on failure (per error-handling.md)

### Documentation

- ✅ Docstrings present on most functions
- ⚠️ Some functions missing docstrings
- ⚠️ No module-level documentation

### Security

- ✅ No hardcoded secrets
- ✅ Uses environment variables
- ⚠️ SQL parameterization could be improved
- ✅ Managed Identity used (though implementation needs work)

---

## Linter Status

**Pylint:** Not available in environment (expected in Azure Functions runtime)

**Pyright:** Configuration present, no errors reported

**Manual Review Findings:**

- No obvious syntax errors
- Import statements look correct
- Type hints generally consistent

---

## Critical Issues Summary

### 🔴 **MUST FIX BEFORE DEPLOYMENT**

1. **DAX Query Loading (dax_client.py, function_app.py)**
   - Current implementation will fail at runtime
   - Need to implement query loading from files or config

2. **Model Path Resolution (scorer.py)**
   - Path mismatch between code and README
   - Will fail in Azure Functions deployment

3. **SQL Performance (sql_client.py)**
   - Row-by-row insert will be too slow for production
   - Need bulk insert implementation

### 🟡 **SHOULD FIX SOON**

1. **Error Handling Improvements** (Per error-handling.md)
   - Add retry logic with exponential backoff for transient errors
   - Add Application Insights logging on failures
   - Ensure exit non-zero on failure
   - Preserve SQL error details

2. **Managed Identity Authentication (sql_client.py)**
   - Token acquired but not used in connection
   - May cause authentication failures

3. **Configuration Documentation**
   - Missing `.env.example` file
   - Need documentation for all environment variables

4. **DAX Column Validation** (Per dax.md)
   - Add validation for 77 expected columns
   - Verify required columns before processing

### 🟢 **NICE TO HAVE**

1. **Email Template Externalization**
2. **JSON API Responses**
3. **Test Suite Implementation**
4. **CI/CD Pipeline**

---

## Recommendations by Priority

### High Priority

1. **Fix DAX Query Loading**

   ```python
   # Add to dax_client.py
   def load_dax_query(query_name: str) -> str:
       query_path = Path(__file__).parent.parent / "dax" / f"{query_name}.dax"
       return query_path.read_text()
   ```

2. **Fix Model Path**

   ```python
   # Update scorer.py load_model() to check multiple paths
   ```

3. **Implement Bulk SQL Insert**

   ```python
   # Use batch processing or pandas to_sql
   ```

### Medium Priority

1. **Fix Managed Identity Authentication**
2. **Add .env.example File**
3. **Improve Error Messages**
4. **Add Request/Response Logging**

### Low Priority

1. **Externalize Email Templates**
2. **Add JSON API Responses**
3. **Implement Test Suite**
4. **Add CI/CD Pipeline**

---

## Next Steps

1. **Immediate Actions:**
   - [ ] Fix DAX query loading mechanism
   - [ ] Fix model path resolution
   - [ ] Implement bulk SQL insert

2. **Short Term:**
   - [ ] Create `.env.example` file
   - [ ] Fix Managed Identity authentication
   - [ ] Improve error handling

3. **Long Term:**
   - [ ] Implement test suite
   - [ ] Add CI/CD pipeline
   - [ ] Performance optimization
   - [ ] Monitoring and alerting enhancements

---

## Files Status Summary

| File              | Status        | Priority Issues                    |
| ----------------- | ------------- | ---------------------------------- |
| `config.py`       | ✅ OK         | Documentation                      |
| `dax_client.py`   | ⚠️ Needs Work | **CRITICAL:** Query loading        |
| `scorer.py`       | ✅ OK         | Model path resolution              |
| `sql_client.py`   | ⚠️ Needs Work | **CRITICAL:** Performance, Auth    |
| `pbi_client.py`   | ✅ OK         | Minor improvements                 |
| `email_client.py` | ✅ OK         | Zero-division check                |
| `function_app.py` | ⚠️ Needs Work | **CRITICAL:** DAX query            |
| `__init__.py`     | ✅ OK         | Response format                    |

---

## Conclusion

The codebase is well-structured and follows good practices. The main concerns are around **DAX query loading**, **model path resolution**, and **SQL performance**. Once these critical issues are addressed, the code should be production-ready.

**Overall Grade: B+** (Good, with critical fixes needed before production deployment)

---

*Review completed using project rules:*

- `.cursor/rules/overview.md` - Architecture and constraints
- `.cursor/rules/function-app.md` - Azure Function patterns
- `.cursor/rules/dax.md` - DAX query handling
- `.cursor/rules/error-handling.md` - Error handling and idempotency
- `.cursor/rules/notebooks.md` - Notebook best practices
- *Plus Python and Azure Functions best practices*
