# Test Coverage Report

**Generated:** 2025-01-16
**Target Coverage:** ≥80%
**Current Coverage:** 53.16%
**Status:** ❌ Below Threshold

## Executive Summary

The test suite currently covers **53.16%** of `function_app/` code, which is below the configured 80% threshold. There are **117 tests** total, with **16 failed**, **85 passed**, **4 skipped**, and **15 errors**.

### Coverage by Module

| Module | Statements | Missing | Coverage | Status |
| -------- | ------------ | --------- | ---------- | -------- |
| `csv_validator.py` | 154 | 29 | **81%** | ✅ Above threshold |
| `sql_client.py` | 115 | 26 | **77%** | ⚠️ Below threshold |
| `config.py` | 57 | 14 | **75%** | ⚠️ Below threshold |
| `scorer.py` | 131 | 47 | **64%** | ⚠️ Below threshold |
| `email_client.py` | 8 | 3 | **62%** | ⚠️ Below threshold |
| `blob_client.py` | 183 | 134 | **27%** | ❌ Critical gap |
| `function_app.py` | 82 | 68 | **17%** | ❌ Critical gap |
| `__init__.py` | 60 | 49 | **18%** | ❌ Critical gap |
| **TOTAL** | **790** | **370** | **53%** | ❌ Below threshold |

## Module-by-Module Breakdown

### ✅ `csv_validator.py` - 81% Coverage

**Status:** Above threshold, good coverage.

#### csv_validator Missing Coverage

- Lines 100, 102, 104: Edge case error handling
- Lines 196-199: Optional validation paths
- Lines 310-330: Complex validation logic
- Lines 360-361, 378-379, 385, 392: Error handling paths
- Lines 506, 509-511: Edge case handling

#### csv_validator Recommendations

- Add tests for edge cases in validation logic
- Test error handling paths for malformed CSV data
- Priority: 🟢 Low (already above threshold)

---

### ⚠️ `sql_client.py` - 77% Coverage

**Status:** Close to threshold, needs improvement.

#### sql_client Missing Coverage

- Lines 47-66: Connection error handling
- Lines 88-98: Transaction rollback scenarios
- Line 210: Edge case error handling
- Line 246: Final error handling path

#### sql_client Recommendations

- Add tests for connection failures
- Test transaction rollback scenarios thoroughly
- Test edge cases in batch processing
- Priority: 🟡 Medium (critical for data integrity)

---

### ⚠️ `config.py` - 75% Coverage

**Status:** Below threshold, needs improvement.

#### config Missing Coverage

- Lines 17-19: Dotenv import error handling
- Line 117: Email recipients validation edge case
- Lines 129-150: Manual validation method (backward compatibility)
- Line 154: Email recipients parsing
- Lines 173-175: Final exception handling

#### config Recommendations

- Add tests for dotenv import failures
- Test edge cases in email recipients validation
- Test manual validation method
- Priority: 🟡 Medium (configuration is critical)

---

### ⚠️ `scorer.py` - 64% Coverage

**Status:** Below threshold, needs significant improvement.

#### scorer Missing Coverage

- Line 178: Feature processing edge case
- Line 184: Data normalization edge case
- Lines 217-233: Complex risk band calculation logic
- Lines 247-323: Reason generation and feature phrase logic

#### scorer Recommendations

- Add tests for edge cases in risk band calculation
- Test reason generation with various feature combinations
- Test feature phrase generation for all feature types
- Priority: 🟡 Medium (core business logic)

---

### ⚠️ `email_client.py` - 62% Coverage

**Status:** New stub module, needs implementation and tests.

#### email_client Missing Coverage

- Lines 29-35: Success email sending logic
- Line 51: Failure email sending logic

#### email_client Recommendations

- This is a stub module - needs full implementation
- Once implemented, add comprehensive tests
- Priority: 🟡 Medium (currently just logging)

---

### ❌ `blob_client.py` - 27% Coverage

**Status:** Critical gap, needs major improvement.

#### blob_client Missing Coverage

- Lines 65-71: Connection initialization error handling
- Lines 84-85: Configuration validation
- Lines 99-100: Blob service client creation
- Lines 122-133: Blob read operations
- Lines 153-154: Blob write operations
- Lines 178-192: Blob deletion operations
- Lines 215-216: Blob existence checks
- Lines 231-240: Blob copy operations
- Lines 255-256: Blob move operations
- Lines 274-275: Blob listing operations
- Lines 300-321: Complex blob path manipulation
- Lines 341-355: Snapshot date extraction
- Lines 373, 397-415: Processed/error folder operations
- Lines 433-446, 460-473: Blob metadata operations
- Lines 492-502: Error handling and retry logic
- Lines 517, 532, 547-586: Complex blob operations
- Lines 606-626, 644-664: Integration operations
- Lines 682-699, 725-729: Final error handling

#### blob_client Recommendations

- Add comprehensive tests for all blob operations
- Test error handling and retry logic
- Test edge cases in blob path manipulation
- Test snapshot date extraction from various blob names
- Priority: 🔴 High (critical for pipeline functionality)

---

### ❌ `function_app.py` - 17% Coverage

**Status:** Critical gap, needs major improvement.

#### function_app Missing Coverage

- Lines 50-160: Main pipeline logic (`run_pipeline_from_blob`)
- Lines 178-196: URL-based pipeline (`run_pipeline_from_url`)
- Line 220: Legacy pipeline functions

#### function_app Test Issues

- Tests are failing due to missing module imports (`get_dax_query_from_dataset`)
- Need to mock dependencies properly
- Integration tests need fixing

#### function_app Recommendations

- Fix test mocks for missing dependencies
- Add comprehensive tests for `run_pipeline_from_blob`
- Add tests for `run_pipeline_from_url`
- Test error handling and file movement operations
- Test email notifications in success/failure scenarios
- Priority: 🔴 High (core pipeline logic)

---

### ❌ `__init__.py` - 18% Coverage

**Status:** Critical gap, but lower priority.

#### init Missing Coverage

- Lines 16-17: Lazy import functions
- Lines 22-23: Lazy import functions
- Lines 28-29: Lazy import functions
- Lines 46-85: Blob trigger handler
- Lines 104-106: Timer trigger handler
- Lines 127-160: HTTP trigger handlers
- Lines 168-174: Health check handler

#### init Recommendations

- Add tests for Azure Function entry points
- Test blob trigger handler logic
- Test HTTP trigger handlers (success and error cases)
- Test health check endpoint
- Priority: 🟡 Medium (Azure Function integration points)

## Test Failures Analysis

### Critical Test Failures

1. **`test_function_app.py`** - 3 failures

- Issue: Missing module `get_dax_query_from_dataset`
- Impact: Cannot test main pipeline logic
- Action: Fix test mocks or implement missing module

1. **`test_blob_client.py`** - 15 errors

- Issue: Import or setup errors
- Impact: Blob operations cannot be tested
- Action: Fix test setup and mocks

1. **`test_csv_validator.py`** - 3 failures

- Issue: Column count validation too strict for test data
- Impact: Some validation tests fail
- Action: Adjust test data or validation logic

### Other Test Failures

1. **`test_config.py`** - 2 failures

- Issue: Environment variable handling in tests
- Impact: Some config tests fail
- Action: Fix test environment setup

1. **`test_scorer.py`** - 2 failures

- Issue: Test assertions don't match actual behavior
- Impact: Some scoring tests fail
- Action: Update test expectations or fix implementation

1. **`test_review_rules.py`** - 2 failures

- Issue: Missing rule files or output reference
- Impact: Rule validation tests fail
- Action: Add missing files or update references

## Uncovered Code Analysis

### Critical Paths (High Priority)

1. **Pipeline Error Handling** (`function_app.py`)

- File movement to error folder
- Failure email notifications
- Transaction rollbacks

1. **Blob Operations** (`blob_client.py`)

- All blob read/write operations
- Error handling and retries
- Snapshot date extraction

1. **Data Integrity** (`sql_client.py`)

- Transaction rollback scenarios
- Connection failure handling

### Important Paths (Medium Priority)

1. **Risk Band Calculation** (`scorer.py`)

- Edge cases in risk band logic
- Reason generation for various scenarios

1. **Configuration Validation** (`config.py`)

- Edge cases in environment variable validation
- Email recipients parsing

1. **Azure Function Entry Points** (`__init__.py`)

- Trigger handlers
- HTTP endpoints

### Nice-to-Have Paths (Low Priority)

1. **Edge Case Error Handling**

- Dotenv import failures
- Optional validation paths

1. **Email Client** (`email_client.py`)

- Currently just a stub, low priority until implemented

## Action Recommendations

### Immediate Actions (To Reach 80% Coverage)

1. **Fix Test Failures**

- 🔴 High: Fix `test_function_app.py` and `test_blob_client.py` errors
- 🟡 Medium: Fix remaining test failures
- Target: All tests passing before improving coverage

1. **Add Tests for Critical Modules**

- 🔴 High: Add tests for `blob_client.py` (currently 27%)
- 🔴 High: Add tests for `function_app.py` (currently 17%)
- 🟡 Medium: Improve `sql_client.py` coverage to 80%+

1. **Improve Coverage for Core Logic**

- 🟡 Medium: Add tests for edge cases in `scorer.py`
- 🟡 Medium: Add tests for configuration edge cases

### Long-Term Improvements

1. **Test Organization**

- Review test fixtures and helpers
- Ensure test isolation
- Improve test maintainability

1. **Integration Tests**

- Add proper integration tests with proper markers
- Test end-to-end pipeline scenarios

1. **Coverage Tools**

- Set up coverage reporting in CI/CD
- Add coverage badges to README
- Track coverage trends over time

## Action Items

### Priority 1: Fix Test Failures

- [ ] Fix `test_blob_client.py` errors (15 errors)
- [ ] Fix `test_function_app.py` failures (3 failures)
- [ ] Fix remaining test failures (11 failures)

### Priority 2: Improve Critical Module Coverage

- [ ] Add tests for `blob_client.py` (target: 70%+)
- [ ] Add tests for `function_app.py` (target: 70%+)
- [ ] Add tests for `__init__.py` (target: 50%+)

### Priority 3: Reach 80% Overall Coverage

- [ ] Improve `sql_client.py` to 80%+
- [ ] Improve `scorer.py` to 70%+
- [ ] Improve `config.py` to 80%+
- [ ] Improve `email_client.py` to 80%+ (after implementation)

## Test Quality Assessment

### Strengths

- ✅ Good coverage of `csv_validator.py` (81%)
- ✅ Comprehensive test fixtures in `conftest.py`
- ✅ Good use of pytest-mock for mocking
- ✅ Proper test organization by module

### Areas for Improvement

- ⚠️ Many tests failing due to setup/mock issues
- ⚠️ Integration tests need better isolation
- ⚠️ Some tests have hardcoded values instead of fixtures
- ⚠️ Missing tests for error handling paths
- ⚠️ Missing tests for edge cases

## Conclusion

The test suite has a solid foundation with **85 passing tests**, but **significant gaps** remain, particularly in:

- Blob operations (27% coverage)
- Main pipeline logic (17% coverage)
- Azure Function entry points (18% coverage)

### To Reach the 80% Threshold

1. Fix all test failures (priority 1)
1. Add comprehensive tests for `blob_client.py` and `function_app.py` (priority 2)
1. Improve coverage in remaining modules (priority 3)

**Estimated effort:** 2-3 days to fix test failures and reach 80% coverage.

---

### Next Steps

1. Review this report with the team
1. Prioritize action items
1. Create tasks for test improvements
1. Re-run coverage report after improvements
