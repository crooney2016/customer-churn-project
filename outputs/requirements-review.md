# Requirements Files Code Review

**Review Date:** 2025-01-27  
**Scope:** Requirements file structure and dependencies  
**Reviewer:** AI Code Review

---

## Executive Summary

### Overall Assessment: ⚠️ **NEEDS CONSOLIDATION** - Multiple Requirements Files Cause Confusion

The project has **3 requirements files** with overlapping and incomplete dependencies. This causes confusion about which file to use and has led to missing dependencies when setting up the environment.

### Status: ⚠️ **Needs Work**

---

## Current Requirements Files

### 1. `requirements.txt` (Root) ⚠️ **INCOMPLETE**

**Location:** `/requirements.txt`

**Contents:**
```
xgboost>=2.0.0
pandas>=2.0.0
numpy>=1.24.0
pyodbc>=5.0.0
```

**Issues:**

- ❌ **Missing critical dependencies:**
  - `msal` - Required for Power BI authentication (used by `dax_client.py`)
  - `requests` - Required for Power BI REST API calls (used by `dax_client.py`, `pbi_client.py`)
  - `python-dotenv` - Required for loading `.env` file (used by `config.py`)
  - `azure-functions` - Required for Azure Function deployment
  - `azure-identity` - Required for Azure authentication

- ❌ **Documentation mismatch:**
  - README.md instructs users to run `pip install -r requirements.txt`
  - This will fail for scripts that import from `function_app` (missing `requests`, `msal`, etc.)

- ⚠️ **Outdated:** Appears to be an old/incomplete version

**Impact:** Users following README instructions will get `ModuleNotFoundError` when running scripts.

---

### 2. `function_app/requirements.txt` ✅ **COMPLETE**

**Location:** `/function_app/requirements.txt`

**Contents:**
```
azure-functions>=1.18.0
azure-identity>=1.15.0
pyodbc>=5.0.0
xgboost>=2.0.0
pandas>=2.0.0
numpy>=1.24.0
msal>=1.24.0
requests>=2.31.0
python-dotenv>=1.0.0
```

**Status:** ✅ Complete - Contains all dependencies needed for:
- Azure Function deployment
- Local development (scripts)
- Power BI integration
- SQL database access
- Model scoring

**Used by:**
- Azure Functions deployment (automatically)
- Should be used by local development (but README says to use root requirements.txt)

---

### 3. `scripts/requirements.txt` ⚠️ **REDUNDANT**

**Location:** `/scripts/requirements.txt`

**Contents:**
```
requests>=2.31.0
msal>=1.24.0
python-dotenv>=1.0.0
pandas>=2.0.0
```

**Issues:**

- ⚠️ **Redundant:** Scripts import from `function_app`, so they need ALL function_app dependencies
- ⚠️ **Incomplete:** Missing `numpy`, `xgboost` (if scripts use scorer), `pyodbc` (if scripts use sql_client)
- ⚠️ **Confusing:** Creates ambiguity about which requirements file to use

**Impact:** Users might install this thinking it's sufficient, but will still get import errors.

---

## Dependency Analysis

### What Scripts Actually Need

**Scripts that import from `function_app`:**
- `scripts/list_datasets.py` - Imports `function_app.config`, `function_app.dax_client`
- `scripts/test_dax_query.py` - Imports `function_app.config`, `function_app.dax_client`

**Dependencies Required:**
- `msal` - For `dax_client.get_access_token()`
- `requests` - For Power BI REST API calls
- `python-dotenv` - For `config.py` to load `.env` file
- `pandas` - For DataFrame operations (if scripts process results)

**Conclusion:** Scripts need the same dependencies as `function_app` because they import from it.

---

## Recommendations

### Option 1: Consolidate to Single Requirements File (Recommended) ✅

**Action:**
1. Update root `requirements.txt` to match `function_app/requirements.txt`
2. Delete `scripts/requirements.txt` (redundant)
3. Update README.md to reference root `requirements.txt`
4. Keep `function_app/requirements.txt` for Azure Functions deployment (Azure uses it automatically)

**Benefits:**
- Single source of truth for local development
- README instructions work correctly
- No confusion about which file to use
- Azure Functions still uses its own requirements.txt (as designed)

**Implementation:**
```bash
# Root requirements.txt becomes:
azure-functions>=1.18.0
azure-identity>=1.15.0
pyodbc>=5.0.0
xgboost>=2.0.0
pandas>=2.0.0
numpy>=1.24.0
msal>=1.24.0
requests>=2.31.0
python-dotenv>=1.0.0
```

---

### Option 2: Update Documentation Only ⚠️

**Action:**
1. Keep root `requirements.txt` as-is (incomplete)
2. Update README.md to instruct: `pip install -r function_app/requirements.txt`
3. Delete `scripts/requirements.txt`

**Benefits:**
- Minimal changes
- Uses existing complete requirements file

**Drawbacks:**
- Root requirements.txt remains misleading/incomplete
- Two requirements files still exist (confusing)

---

### Option 3: Separate Development vs Production ⚠️

**Action:**
1. Root `requirements.txt` - Complete for local development
2. `function_app/requirements.txt` - For Azure deployment (keep as-is)
3. Delete `scripts/requirements.txt`

**Benefits:**
- Clear separation of concerns
- Local dev uses root, deployment uses function_app

**Drawbacks:**
- Two files to maintain (but they'd be identical)

---

## Recommended Solution: Option 1

**Rationale:**
- Simplest for users (one file to install from)
- README already references root requirements.txt
- Azure Functions automatically uses function_app/requirements.txt (no change needed)
- Eliminates confusion

---

## Action Items

### Immediate Actions

- [ ] **🔴 CRITICAL:** Update root `requirements.txt` to include all dependencies from `function_app/requirements.txt`
- [ ] **🔴 CRITICAL:** Delete `scripts/requirements.txt` (redundant and incomplete)
- [ ] **🟡 SHOULD FIX:** Update README.md if needed (verify it references correct file)

### Verification

- [ ] Test: Create fresh venv, install from root requirements.txt
- [ ] Test: Run `scripts/list_datasets.py` (should work without errors)
- [ ] Test: Run `scripts/test_dax_query.py` (should work without errors)
- [ ] Verify: Azure Functions deployment still works (uses function_app/requirements.txt automatically)

---

## Compliance Summary

| Aspect                    | Status | Notes                                    |
| ------------------------- | ------ | ---------------------------------------- |
| Dependency completeness   | ❌     | Root requirements.txt incomplete         |
| Documentation accuracy    | ❌     | README references incomplete file        |
| File redundancy           | ⚠️     | 3 requirements files (should be 2)       |
| Azure deployment          | ✅     | function_app/requirements.txt is correct |

---

## Conclusion

The project has **3 requirements files** with overlapping dependencies. The root `requirements.txt` is **incomplete** and causes `ModuleNotFoundError` when users follow README instructions. The `scripts/requirements.txt` is **redundant** since scripts import from `function_app`.

**Recommended fix:** Consolidate root `requirements.txt` to match `function_app/requirements.txt`, delete `scripts/requirements.txt`, and verify README instructions work correctly.

**Overall Grade: D** (Multiple files, incomplete dependencies, documentation mismatch)

---

*Review completed using project rules:*

- `.cursor/rules/prompts/code-review.md` - Code review process
- `.cursor/rules/python.md` - Python best practices
