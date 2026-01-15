# Code Review - dax_client.py

**Review Date:** 2025-01-27  
**Reviewer:** AI Code Review  
**File:** `function_app/dax_client.py`  
**Class Name:** N/A (No classes - functions only, per function-app.md preference)

**Rules Referenced:**

- `.cursor/rules/python.md` - Python coding standards, type hints, docstrings
- `.cursor/rules/dax.md` - DAX query handling and column naming
- `.cursor/rules/error-handling.md` - Error handling patterns and idempotency
- `.cursor/rules/logging.md` - Logging strategy and Application Insights integration
- `.cursor/rules/function-app.md` - Azure Function structure and patterns

---

## Executive Summary

### Overall Assessment: ⚠️ **NEEDS WORK** - Several Issues to Address

The `dax_client.py` module demonstrates good structure and follows many Python best practices. However, there are **important issues** that should be addressed for production readiness, particularly around logging, error handling with retry logic, and DAX column validation. The code is functional but lacks some production-grade features required by project rules.

### Status: ⚠️ **Needs Work**

---

## File Overview

**Module:** `dax_client.py`  
**Purpose:** Power BI DAX query execution client using MSAL authentication  
**Functions:** 4 public functions (no classes)  
**Lines of Code:** 155

**Functions:**

1. `get_access_token()` - Acquires Power BI access token via MSAL
2. `execute_dax_query()` - Executes DAX query against Power BI dataset
3. `load_dax_query_from_file()` - Loads DAX query from `dax/` directory files
4. `get_dax_query_from_dataset()` - Convenience wrapper for loading queries

---

## Detailed Review

### Strengths

1. ✅ **Type Hints** (Per python.md)
   - All functions have complete type hints
   - Return types are specific (`str`, `pd.DataFrame`)
   - Optional parameters properly typed with `Optional[str]`

2. ✅ **Docstrings** (Per python.md)
   - All functions have Google-style docstrings
   - Module-level docstring present
   - Args, Returns, and Raises sections included where appropriate

3. ✅ **DAX Query Loading** (Per dax.md)
   - `load_dax_query_from_file()` correctly loads from `dax/` directory
   - Supports both query file options per dax.md rules
   - Proper error handling with FileNotFoundError

4. ✅ **Functions Over Classes** (Per function-app.md)
   - No classes - all functions (per function-app.md preference)
   - Clean, stateless design

5. ✅ **Error Handling Structure** (Per error-handling.md)
   - Explicit error handling in `get_access_token()`
   - Proper validation of external library responses
   - Type checking before accessing dictionary keys

6. ✅ **External Library Returns** (Per python.md)
   - Excellent handling of `Optional[Dict[str, Any]]` from MSAL
   - Explicit None checks and type validation
   - Follows python.md best practices for external library returns

7. ✅ **Code Organization** (Per python.md)
   - Imports properly organized (standard, third-party, local)
   - Module docstring at top
   - Logical function ordering

---

## Issues Found

### 🔴 **CRITICAL: Missing Logging** (Violates logging.md)

**Rule Violation:** `.cursor/rules/logging.md` requires logging for all operations

**Issue:**

- No logging module imported or used
- No logging for token acquisition attempts
- No logging for DAX query execution
- No logging for query loading operations
- Per logging.md: Should log at INFO level for operations, ERROR for failures

**Impact:** Operations are not logged to Application Insights, making debugging and monitoring difficult.

**Recommendation:**

```python
import logging

logger = logging.getLogger(__name__)

def get_access_token() -> str:
    """Get access token for Power BI using service principal."""
    logger.info("Acquiring Power BI access token...")
    app = ConfidentialClientApplication(...)
    
    result: Optional[Dict[str, Any]] = app.acquire_token_for_client(scopes=[scope])
    
    if result is None:
        logger.error("Failed to acquire token: No response from authentication service")
        raise RuntimeError("Failed to acquire token: No response from authentication service")
    
    logger.info("Access token acquired successfully")
    return str(access_token)

def execute_dax_query(query: str, dataset_id: Optional[str] = None) -> pd.DataFrame:
    """Execute DAX query against Power BI dataset."""
    if dataset_id is None:
        dataset_id = config.PBI_DATASET_ID
    
    logger.info("Executing DAX query against dataset %s", dataset_id)
    logger.debug("DAX query length: %d characters", len(query))
    
    access_token = get_access_token()
    
    # ... existing code ...
    
    logger.info("DAX query returned %d rows with %d columns", len(df), len(df.columns))
    return df
```

**Action Item:**

- [ ] **🔴 CRITICAL:** Add logging module import and logger initialization
- [ ] Add INFO-level logging for all operations
- [ ] Add ERROR-level logging for failures with `exc_info=True`
- [ ] Log query execution details (dataset ID, row count, column count)

---

### 🔴 **CRITICAL: Missing Retry Logic** (Violates error-handling.md)

**Rule Violation:** `.cursor/rules/error-handling.md` requires retry logic for transient errors

**Issue:**

- No retry logic for network timeouts, connection drops, or API throttling
- Per error-handling.md: Should retry transient errors with exponential backoff, max 3 attempts
- Currently fails immediately on any network error

**Impact:** Transient network issues will cause unnecessary pipeline failures.

**Recommendation:**

```python
import time
from typing import Callable, TypeVar

T = TypeVar('T')

def retry_with_backoff(
    func: Callable[[], T],
    max_attempts: int = 3,
    base_delay: float = 1.0
) -> T:
    """Retry function with exponential backoff per error-handling.md."""
    logger = logging.getLogger(__name__)
    
    for attempt in range(max_attempts):
        try:
            return func()
        except (requests.exceptions.Timeout, 
                requests.exceptions.ConnectionError,
                requests.exceptions.RequestException) as e:
            if attempt == max_attempts - 1:
                logger.error("Max retries exceeded for transient error: %s", str(e), exc_info=True)
                raise
            delay = base_delay * (2 ** attempt)
            logger.warning(
                "Attempt %d/%d failed: %s. Retrying in %.1f seconds...",
                attempt + 1, max_attempts, str(e), delay
            )
            time.sleep(delay)
    
    raise RuntimeError("Max retries exceeded")

def execute_dax_query(query: str, dataset_id: Optional[str] = None) -> pd.DataFrame:
    """Execute DAX query with retry logic."""
    if dataset_id is None:
        dataset_id = config.PBI_DATASET_ID
    
    def _execute():
        access_token = get_access_token()
        url = f"https://api.powerbi.com/v1.0/myorg/datasets/{dataset_id}/executeQueries"
        # ... rest of execution code ...
        return df
    
    # Per error-handling.md: Retry transient errors
    return retry_with_backoff(_execute, max_attempts=3)
```

**Action Item:**

- [ ] **🔴 CRITICAL:** Implement retry logic with exponential backoff for `execute_dax_query()`
- [ ] Retry on network timeouts, connection errors, API throttling
- [ ] Max 3 attempts per error-handling.md rules
- [ ] Log retry attempts

---

### 🟡 **SHOULD FIX: Missing DAX Column Validation** (Violates dax.md)

**Rule Violation:** `.cursor/rules/dax.md` requires validation of 77 expected columns

**Issue:**

- No validation that DAX output has expected 77 columns per customer per snapshot
- No verification of required identifier columns: CustomerId, AccountName, Segment, CostCenter, SnapshotDate
- Per dax.md: Should validate expected output schema before processing

**Impact:** Invalid DAX queries or schema changes may not be caught early, causing downstream failures.

**Recommendation:**

```python
def validate_dax_columns(df: pd.DataFrame) -> None:
    """
    Validate DAX output matches expected schema per dax.md rules.
    
    Args:
        df: DataFrame from DAX query
        
    Raises:
        ValueError: If required columns are missing or column count is unexpected
    """
    logger = logging.getLogger(__name__)
    
    # Required identifier columns per dax.md
    required = ["CustomerId", "AccountName", "Segment", "CostCenter", "SnapshotDate"]
    missing = [col for col in required if col not in df.columns]
    
    if missing:
        error_msg = f"Missing required columns: {missing}"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    # Per dax.md: Should have ~77 total columns (5 identifiers + 3 dates + ~69 features)
    column_count = len(df.columns)
    logger.info("DAX query returned %d columns, %d rows", column_count, len(df))
    
    if column_count < 70:  # Allow some variance but warn
        logger.warning("Expected ~77 columns per dax.md, got %d", column_count)
    elif column_count > 85:  # Also warn if too many
        logger.warning("Expected ~77 columns per dax.md, got %d (may indicate schema change)", column_count)

def execute_dax_query(query: str, dataset_id: Optional[str] = None) -> pd.DataFrame:
    """Execute DAX query with validation."""
    # ... existing code to get df ...
    
    # Validate columns per dax.md
    validate_dax_columns(df)
    
    return df
```

**Action Item:**

- [ ] **🟡 SHOULD FIX:** Add `validate_dax_columns()` function
- [ ] Validate required identifier columns exist
- [ ] Warn if column count doesn't match expected ~77 columns per dax.md
- [ ] Log validation results

---

### 🟡 **SHOULD FIX: Hardcoded Timeout** (Per python.md best practices)

**Issue:**

- Timeout hardcoded to 300 seconds in `execute_dax_query()`
- Per python.md: Should use constants for configuration values
- May be too long for some queries, too short for others

**Recommendation:**

```python
# Constants per python.md
DEFAULT_DAX_TIMEOUT = 300  # 5 minutes
MAX_DAX_TIMEOUT = 600  # 10 minutes

def execute_dax_query(
    query: str, 
    dataset_id: Optional[str] = None,
    timeout: int = DEFAULT_DAX_TIMEOUT
) -> pd.DataFrame:
    """Execute DAX query with configurable timeout."""
    # ... existing code ...
    response = requests.post(url, headers=headers, json=payload, timeout=timeout)
```

**Action Item:**

- [ ] Extract timeout to constant per python.md
- [ ] Make timeout configurable via parameter
- [ ] Consider making it configurable via config.py

---

### 🟡 **SHOULD FIX: Error Messages Could Be More Descriptive**

**Issue:**

- Some error messages lack context (e.g., which dataset, query length)
- Could include more diagnostic information

**Recommendation:**

```python
if "results" not in result or len(result["results"]) == 0:
    error_msg = (
        f"No results returned from DAX query. "
        f"Dataset: {dataset_id}, Query length: {len(query)} characters"
    )
    logger.error(error_msg)
    raise ValueError(error_msg)
```

**Action Item:**

- [ ] Enhance error messages with more context
- [ ] Include dataset ID, query information where relevant

---

### 🟢 **NICE TO HAVE: Column Name Normalization**

**Issue:**

- DAX returns column names with brackets: `[ColumnName]`
- Per dax.md: Python code should strip brackets during preprocessing
- Current code doesn't explicitly handle bracket removal

**Note:** This may be handled in `scorer.py` preprocessing, but could be done here for consistency.

**Recommendation:**

```python
def normalize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """
    Remove brackets from column names per dax.md rules.
    
    DAX returns: {"[CustomerId]": "001"}
    Python expects: {"CustomerId": "001"}
    """
    df.columns = [col.strip('[]') if isinstance(col, str) else col for col in df.columns]
    return df

def execute_dax_query(query: str, dataset_id: Optional[str] = None) -> pd.DataFrame:
    """Execute DAX query with column normalization."""
    # ... existing code to get df ...
    
    # Normalize column names per dax.md
    df = normalize_column_names(df)
    
    return df
```

**Action Item:**

- [ ] Consider adding column name normalization if not handled elsewhere
- [ ] Verify bracket removal is handled in preprocessing pipeline

---

## Compliance Summary

### Rule Compliance

| Rule File            | Compliance | Key Issues                                  |
| -------------------- | ---------- | ------------------------------------------- |
| `python.md`          | ✅ Good    | Type hints, docstrings, code org            |
| `dax.md`             | ⚠️ Partial | Missing column validation                   |
| `error-handling.md`  | ❌ Poor    | **Missing retry logic**                     |
| `logging.md`         | ❌ Poor    | **Missing logging**                         |
| `function-app.md`    | ✅ Good    | Functions over classes                      |

---

## Code Quality Assessment

### Type Hints (Per python.md)

- ✅ All functions have complete type hints
- ✅ Return types are specific
- ✅ Optional parameters properly typed
- ✅ External library returns handled correctly

### Docstrings (Per python.md)

- ✅ All functions have Google-style docstrings
- ✅ Module-level docstring present
- ✅ Args and Returns sections included
- ✅ Raises sections included where appropriate

### Error Handling (Per error-handling.md)

- ✅ Explicit error handling in `get_access_token()`
- ✅ Proper validation of external library responses
- ✅ Type checking before accessing dictionary keys
- ❌ Missing retry logic for transient errors
- ⚠️ Error messages could be more descriptive

### Logging (Per logging.md)

- ❌ No logging module imported
- ❌ No logging for operations
- ❌ No logging for errors
- ❌ Operations not logged to Application Insights

### DAX Query Handling (Per dax.md)

- ✅ Query loading from `dax/` directory implemented
- ✅ Supports both query file options
- ✅ Proper file path resolution
- ❌ Missing column validation (77 columns)
- ❌ Missing required column verification

### Code Organization (Per python.md)

- ✅ Imports properly organized
- ✅ Module docstring at top
- ✅ Logical function ordering
- ✅ Functions over classes (per function-app.md)

---

## Recommendations by Priority

### High Priority (🔴 Critical)

1. **Add Logging** (Per logging.md)

   - Import logging module
   - Add logger initialization
   - Log all operations at INFO level
   - Log errors at ERROR level with `exc_info=True`

2. **Implement Retry Logic** (Per error-handling.md)

   - Add retry function with exponential backoff
   - Retry transient errors (network timeouts, connection errors)
   - Max 3 attempts per error-handling.md rules
   - Log retry attempts

### Medium Priority (🟡 Should Fix)

1. **Add DAX Column Validation** (Per dax.md)

   - Validate required identifier columns
   - Check column count matches expected ~77 columns
   - Log validation results

2. **Extract Hardcoded Values** (Per python.md)

   - Move timeout to constant
   - Make timeout configurable

3. **Enhance Error Messages**

   - Include more context in error messages
   - Add diagnostic information

### Low Priority (🟢 Nice to Have)

1. **Column Name Normalization**

   - Consider adding bracket removal if not handled elsewhere
   - Verify preprocessing handles this

---

## Action Items

### Immediate Actions

- [ ] **🔴 CRITICAL:** Add logging module and logger initialization
- [ ] **🔴 CRITICAL:** Add INFO-level logging for all operations
- [ ] **🔴 CRITICAL:** Add ERROR-level logging for failures
- [ ] **🔴 CRITICAL:** Implement retry logic with exponential backoff

### Short Term

- [ ] **🟡 SHOULD FIX:** Add DAX column validation function
- [ ] **🟡 SHOULD FIX:** Extract timeout to constant
- [ ] **🟡 SHOULD FIX:** Enhance error messages with context

### Long Term

- [ ] **🟢 NICE TO HAVE:** Consider column name normalization
- [ ] **🟢 NICE TO HAVE:** Add performance metrics logging
- [ ] **🟢 NICE TO HAVE:** Add query execution time tracking

---

## Conclusion

The `dax_client.py` module is well-structured and follows many Python best practices. The code is functional and handles external library returns correctly. However, it **lacks critical production features** required by project rules:

1. **No logging** - Operations are not logged to Application Insights
2. **No retry logic** - Transient errors will cause unnecessary failures
3. **No column validation** - DAX schema changes may not be caught early

Once these issues are addressed, the module will be production-ready. The architecture is sound, and the code quality is good overall.

**Overall Grade: B-** (Good structure, missing production features)

**Recommendation:** Address all 🔴 Critical and 🟡 Should Fix issues before production deployment.

---

*Review completed using project rules:*

- `.cursor/rules/python.md` - Python coding standards
- `.cursor/rules/dax.md` - DAX query handling
- `.cursor/rules/error-handling.md` - Error handling patterns
- `.cursor/rules/logging.md` - Logging strategy
- `.cursor/rules/function-app.md` - Azure Function patterns
