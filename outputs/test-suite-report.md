# Test Suite Report

**Generated:** $(date)
**Python Version:** 3.9.6
**Pytest Version:** 8.4.2
**Coverage Tool:** pytest-cov 7.0.0

---

## Executive Summary

| Metric | Count | Percentage |
| ------ | ----- | ---------- |
| **Total Tests** | 146 | 100% |
| **Passed** | 141 | 96.6% |
| **Failed** | 1 | 0.7% |
| **Skipped** | 4 | 2.7% |
| **Total Coverage** | **77%** | **Below 80% threshold** |

### ⚠️ Status: Coverage Below Target

The test suite has **77% code coverage**, which is below the required **80% threshold**. One test is failing.

---

## Test Results by Module

### test_blob_client.py (14 tests)

**Status:** 13 passed, 1 failed

#### TestReadBlobBytes

- ✅ `test_read_blob_bytes_success` - PASSED
- ✅ `test_read_blob_bytes_not_found` - PASSED

#### TestReadBlobText

- ✅ `test_read_blob_text_success` - PASSED

#### TestWriteBlobBytes

- ✅ `test_write_blob_bytes_success` - PASSED

#### TestDeleteBlob

- ✅ `test_delete_blob_success` - PASSED
- ✅ `test_delete_blob_not_found` - PASSED

#### TestBlobExists

- ✅ `test_blob_exists_true` - PASSED
- ✅ `test_blob_exists_false` - PASSED

#### TestCopyBlob

- ❌ `test_copy_blob_success` - **FAILED**
  - **Error:** `ValueError: Connection string is either blank or malformed.`
  - **Location:** `tests/test_blob_client.py:209`
  - **Issue:** The test is not properly mocking the blob service client for the `copy_blob` function

#### TestMoveBlob

- ✅ `test_move_blob_success` - PASSED

#### TestListBlobs

- ✅ `test_list_blobs_success` - PASSED
- ✅ `test_list_blobs_with_prefix` - PASSED

#### TestMoveToProcessed

- ✅ `test_move_to_processed_success` - PASSED

#### TestMoveToError

- ✅ `test_move_to_error_success` - PASSED

#### TestGetProcessingFolderBlobs

- ✅ `test_get_processing_folder_blobs` - PASSED

---

### test_config.py (6 tests)

**Status:** 6 passed ✅

- ✅ `test_config_loads_from_env` - PASSED
- ✅ `test_config_raises_on_missing_required` - PASSED
- ✅ `test_config_container_name_has_default` - PASSED
- ✅ `test_config_logic_app_endpoint_optional` - PASSED
- ✅ `test_config_validate_method` - PASSED
- ✅ `test_config_validate_raises_on_empty` - PASSED

---

### test_csv_validator.py (30 tests)

**Status:** 30 passed ✅

#### TestParseCsvFromBytes

- ✅ `test_parse_csv_success` - PASSED
- ✅ `test_parse_csv_empty_bytes` - PASSED
- ✅ `test_parse_csv_empty_file` - PASSED
- ✅ `test_parse_csv_malformed` - PASSED
- ✅ `test_parse_csv_utf8_encoding` - PASSED

#### TestNormalizeColumnNames

- ✅ `test_normalize_customer_columns` - PASSED
- ✅ `test_normalize_feature_columns` - PASSED
- ✅ `test_normalize_preserves_data` - PASSED
- ✅ `test_normalize_already_normalized` - PASSED

#### TestValidateCsvSchema

- ✅ `test_validate_valid_schema` - PASSED
- ✅ `test_validate_missing_required_columns` - PASSED

#### TestValidateColumnCount

- ✅ `test_validate_column_count_valid` - PASSED
- ✅ `test_validate_column_count_too_few` - PASSED
- ✅ `test_validate_column_count_many_warns` - PASSED

#### TestValidateRequiredColumns

- ✅ `test_validate_required_columns_present` - PASSED
- ✅ `test_validate_required_columns_missing` - PASSED
- ✅ `test_validate_required_columns_partial` - PASSED

#### TestValidateNoDuplicateColumns

- ✅ `test_validate_no_duplicates` - PASSED
- ✅ `test_validate_with_duplicates` - PASSED

#### TestValidateColumnTypes

- ✅ `test_validate_types_valid` - PASSED
- ✅ `test_validate_types_with_warnings` - PASSED

#### TestGetExpectedColumns

- ✅ `test_get_expected_columns` - PASSED

#### TestGetColumnSummary

- ✅ `test_get_column_summary` - PASSED

#### TestValidateSnapshotDatePresent

- ✅ `test_validate_snapshot_date_present` - PASSED
- ✅ `test_validate_snapshot_date_with_brackets` - PASSED
- ✅ `test_validate_snapshot_date_missing` - PASSED
- ✅ `test_validate_snapshot_date_all_null` - PASSED

#### TestIntegration

- ✅ `test_full_validation_pipeline` - PASSED
- ✅ `test_validation_with_real_column_count` - PASSED

---

### test_deploy_sql_schema.py (16 tests)

**Status:** 16 passed ✅

- ✅ `test_parse_connection_string` - PASSED
- ✅ `test_parse_connection_string_minimal` - PASSED
- ✅ `test_extract_username` - PASSED
- ✅ `test_extract_username_missing` - PASSED
- ✅ `test_get_connection` - PASSED
- ✅ `test_get_connection_missing_env` - PASSED
- ✅ `test_grant_permissions` - PASSED
- ✅ `test_grant_permissions_already_member` - PASSED
- ✅ `test_verify_permissions` - PASSED
- ✅ `test_verify_permissions_fails_select` - PASSED
- ✅ `test_execute_sql_file` - PASSED
- ✅ `test_execute_sql_file_handles_go_statements` - PASSED
- ✅ `test_execute_sql_file_handles_already_exists` - PASSED
- ✅ `test_main_success` - PASSED
- ✅ `test_main_missing_connection_string` - PASSED
- ✅ `test_main_permission_grant_fails` - PASSED

**Note:** 3 warnings about pytest-mock context managers (can be ignored or fixed)

---

### test_email_client.py (10 tests)

**Status:** 10 passed ✅

- ✅ `test_render_success_template` - PASSED
- ✅ `test_render_failure_template` - PASSED
- ✅ `test_render_template_not_found` - PASSED
- ✅ `test_post_html_success` - PASSED
- ✅ `test_post_html_no_endpoint` - PASSED
- ✅ `test_post_html_error_logged_not_raised` - PASSED
- ✅ `test_send_success_email` - PASSED
- ✅ `test_send_failure_email` - PASSED
- ✅ `test_send_success_email_template_error_handled` - PASSED
- ✅ `test_send_failure_email_template_error_handled` - PASSED

---

### test_function_app.py (14 tests)

**Status:** 14 passed ✅

#### TestRunPipeline

- ✅ `test_run_pipeline_success` - PASSED
- ✅ `test_run_pipeline_empty_csv_raises_error` - PASSED
- ✅ `test_run_pipeline_moves_to_error_on_failure` - PASSED
- ✅ `test_run_pipeline_sends_failure_email_on_error` - PASSED

#### TestProcessChurnCsv

- ✅ `test_skips_processed_folder` - PASSED
- ✅ `test_skips_error_folder` - PASSED
- ✅ `test_skips_non_csv_files` - PASSED
- ✅ `test_processes_csv_file` - PASSED
- ✅ `test_handles_empty_blob` - PASSED

#### TestExtractBlobName

- ✅ `test_extract_from_full_url` - PASSED
- ✅ `test_extract_from_blob_name` - PASSED
- ✅ `test_extract_from_url_without_container` - PASSED

#### TestHealthCheck

- ✅ `test_health_check_returns_ok` - PASSED

#### TestScoreHttp

- ✅ `test_score_http_requires_blob_url` - PASSED
- ✅ `test_score_http_handles_invalid_json` - PASSED
- ✅ `test_score_http_success` - PASSED
- ✅ `test_score_http_pipeline_failure` - PASSED

---

### test_review_rules.py (9 tests)

**Status:** 9 passed ✅

- ✅ `test_all_core_rules_exist` - PASSED
- ✅ `test_all_domain_rules_exist` - PASSED
- ✅ `test_all_prompts_exist` - PASSED
- ✅ `test_review_rules_structure` - PASSED
- ✅ `test_no_broken_markdown_references` - PASSED
- ✅ `test_linting_script_references` - PASSED
- ✅ `test_output_reference` - PASSED
- ✅ `test_checklist_structure` - PASSED
- ✅ `test_all_rule_files_exist` - PASSED

---

### test_review_rules_lint.py (5 tests)

**Status:** 5 passed ✅

- ✅ `test_file_exists` - PASSED
- ✅ `test_fix_script_exists` - PASSED
- ✅ `test_python_syntax_valid` - PASSED
- ✅ `test_no_linting_errors` - PASSED
- ✅ `test_follows_project_standards` - PASSED

---

### test_scorer.py (26 tests)

**Status:** 25 passed, 1 skipped

- ✅ `test_normalize_cols_strips_brackets` - PASSED
- ✅ `test_normalize_cols_strips_whitespace` - PASSED
- ✅ `test_convert_excel_dates_handles_excel_serial` - PASSED
- ✅ `test_preprocess_strips_brackets` - PASSED
- ✅ `test_preprocess_fills_null_segment` - PASSED
- ✅ `test_preprocess_creates_dummy_columns` - PASSED
- ✅ `test_risk_band_high` - PASSED
- ✅ `test_risk_band_medium` - PASSED
- ✅ `test_risk_band_low` - PASSED
- ✅ `test_score_customers_structure` - PASSED
- ⏭️ `test_score_customers_integration` - **SKIPPED** (Requires model files)
- ✅ `test_convert_excel_dates_handles_string_dates` - PASSED
- ✅ `test_convert_excel_dates_handles_normal_dates` - PASSED
- ✅ `test_preprocess_handles_missing_costcenter` - PASSED
- ✅ `test_preprocess_drops_identifier_columns` - PASSED
- ✅ `test_feature_phrase_segment` - PASSED
- ✅ `test_feature_phrase_costcenter` - PASSED
- ✅ `test_feature_phrase_mapped_feature` - PASSED
- ✅ `test_feature_phrase_unknown_feature` - PASSED
- ✅ `test_reason_text_segment_returns_base` - PASSED
- ✅ `test_reason_text_risk_mode_high_is_good` - PASSED
- ✅ `test_reason_text_risk_mode_high_is_bad` - PASSED
- ✅ `test_reason_text_safe_mode_high_is_good` - PASSED
- ✅ `test_reason_text_safe_mode_high_is_bad` - PASSED
- ✅ `test_top_reasons_high_risk` - PASSED
- ✅ `test_top_reasons_low_risk` - PASSED
- ✅ `test_top_reasons_medium_risk` - PASSED
- ✅ `test_top_reasons_excludes_bias` - PASSED

---

### test_sql_client.py (11 tests)

**Status:** 8 passed, 3 skipped

- ✅ `test_insert_scores_uses_executemany` - PASSED
- ✅ `test_insert_scores_rollback_on_error` - PASSED
- ✅ `test_insert_scores_batches_correctly` - PASSED
- ✅ `test_insert_scores_calls_merge_procedure` - PASSED
- ✅ `test_insert_scores_empty_dataframe` - PASSED
- ✅ `test_validate_dataframe_schema_missing_required_column` - PASSED
- ✅ `test_validate_dataframe_schema_all_required_present` - PASSED
- ✅ `test_insert_scores_validates_schema` - PASSED
- ⏭️ `test_insert_scores_integration` - **SKIPPED** (Requires database connection)
- ⏭️ `test_staging_table_full_flow` - **SKIPPED** (Requires database connection)
- ⏭️ `test_staging_table_merge_idempotent` - **SKIPPED** (Requires database connection)

---

## Code Coverage Report

### Overall Coverage: 77% (Below 80% Threshold)

| Module | Statements | Missed | Coverage | Missing Lines |
| ------ | ---------- | ------ | -------- | ------------- |
| `function_app/__init__.py` | 0 | 0 | **100%** | - |
| `function_app/email_client.py` | 47 | 4 | **91%** | 27-29, 35 |
| `function_app/function_app.py` | 126 | 10 | **92%** | 91-93, 230-231, 243, 247, 291-292, 301-302 |
| `function_app/config.py` | 38 | 6 | **84%** | 17-19, 80, 83, 102-104 |
| `function_app/sql_client.py` | 115 | 26 | **77%** | 47-66, 88-98, 210, 246 |
| `function_app/csv_validator.py` | 154 | 32 | **79%** | 100, 102, 104, 188-199, 310-330, 360-361, 378-379, 385, 392, 512-514 |
| `function_app/blob_client.py` | 183 | 60 | **67%** | 67, 84-85, 100, 215-216, 275, 314, 316-321, 373, 402, 404, 433-446, 460-473, 517, 532, 547-586, 687-688, 696-697, 729 |
| `function_app/scorer.py` | 131 | 47 | **64%** | 178, 184, 217-233, 247-323 |
| **TOTAL** | **794** | **185** | **77%** | - |

### Coverage Gaps Analysis

#### 🔴 Critical (Below 70%)

1. **`function_app/scorer.py` (64%)** - Missing coverage for:
- Model scoring functions (lines 217-233, 247-323)
- Some preprocessing edge cases (178, 184)
- **Action Needed:** Add unit tests for scoring logic and edge cases

1. **`function_app/blob_client.py` (67%)** - Missing coverage for:
- Error handling paths (67, 84-85, 100, 215-216)
- Copy blob functionality (314, 316-321) - **Note:** Test is currently failing
- Retry/error recovery logic (433-446, 460-473)
- Advanced blob operations (547-586, 687-688, 696-697, 729)
- **Action Needed:** Fix failing test and add error path tests

#### 🟡 Moderate (70-79%)

1. **`function_app/csv_validator.py` (79%)** - Missing coverage for:
- Error handling paths (100, 102, 104)
- Advanced validation logic (188-199, 310-330)
- Edge cases (360-361, 378-379, 385, 392)
- Exit/error paths (512-514)
- **Action Needed:** Add tests for edge cases and error conditions

1. **`function_app/sql_client.py` (77%)** - Missing coverage for:
- Connection error handling (47-66, 88-98)
- Edge cases (210, 246)
- **Action Needed:** Add tests for connection failures and edge cases

#### 🟢 Good (80%+)

- `function_app/config.py` (84%)
- `function_app/function_app.py` (92%)
- `function_app/email_client.py` (91%)
- `function_app/__init__.py` (100%)

---

## Failed Tests Detail

### 1. test_copy_blob_success (test_blob_client.py)

**Status:** ❌ FAILED
**Location:** `tests/test_blob_client.py:209`
**Error Type:** `ValueError`

#### Error Message

```text
ValueError: Connection string is either blank or malformed.
```

#### Stack Trace

```text
function_app/blob_client.py:313: in copy_blob
    source_props = get_blob_properties(source_container, source_blob)
function_app/blob_client.py:274: in get_blob_properties
    blob_client = _get_blob_client(container_name, blob_name)
function_app/blob_client.py:99: in _get_blob_client
    service_client = _get_blob_service_client()
function_app/blob_client.py:71: in _get_blob_service_client
    return BlobServiceClient.from_connection_string(connection_string)
```

#### Root Cause
The test is calling `copy_blob()` directly without properly mocking the blob service client. The `copy_blob` function internally calls `get_blob_properties()`, which tries to create a real blob service client instead of using the mocked one.

#### Fix Required

1. Mock `_get_blob_service_client()` or `_get_blob_client()` at the module level
1. Ensure the test uses the `mock_blob_client` fixture properly
1. Mock `get_blob_properties()` directly for this test

---

## Skipped Tests (4 total)

### Integration Tests (Require External Services)

1. **`test_score_customers_integration`** (test_scorer.py)
- **Reason:** Requires model files
- **Marked as:** `@pytest.mark.integration`
- **Action:** Run locally with model files or in integration test environment

1. **`test_insert_scores_integration`** (test_sql_client.py)
- **Reason:** Requires database connection
- **Marked as:** `@pytest.mark.integration`
- **Action:** Run locally with database access or in integration test environment

1. **`test_staging_table_full_flow`** (test_sql_client.py)
- **Reason:** Requires database connection
- **Marked as:** `@pytest.mark.integration`
- **Action:** Run locally with database access or in integration test environment

1. **`test_staging_table_merge_idempotent`** (test_sql_client.py)
- **Reason:** Requires database connection
- **Marked as:** `@pytest.mark.integration`
- **Action:** Run locally with database access or in integration test environment

**Note:** Skipped tests are expected and do not affect the test suite quality. They should be run in integration test environments.

---

## Test Warnings

### PytestMockWarning (3 instances)

**Location:** `tests/test_deploy_sql_schema.py`

The following tests have warnings about using pytest-mock mocks as context managers:

1. `test_main_success` (lines 227, 230)
1. `test_main_permission_grant_fails` (line 264)

#### Message

```text
PytestMockWarning: Mocks returned by pytest-mock do not need to be used as context managers. The mocker fixture automatically undoes mocking at the end of a test.
```

**Fix:** Remove `with` statements around `mocker.patch()` calls. Pytest-mock automatically cleans up mocks.

### urllib3 OpenSSL Warning

**Warning:** urllib3 v2 only supports OpenSSL 1.1.1+, currently the 'ssl' module is compiled with 'LibreSSL 2.8.3'

This is a system-level warning and does not affect test functionality. It can be ignored or fixed by updating OpenSSL.

---

## Recommendations

### Immediate Actions

1. **Fix Failing Test:**
- Fix `test_copy_blob_success` by properly mocking blob service client
- This will also improve coverage for `blob_client.py`

1. **Improve Coverage to 80%:**
- Focus on `scorer.py` (needs +16% coverage)
- Focus on `blob_client.py` (needs +13% coverage)
- Add tests for error paths and edge cases

1. **Clean Up Warnings:**
- Remove `with` statements from `mocker.patch()` calls in `test_deploy_sql_schema.py`

### Medium-Term Improvements

1. **Add Integration Test Infrastructure:**
- Set up test database for SQL client integration tests
- Provide test model files for scorer integration tests
- Document how to run integration tests locally

1. **Increase Coverage Target:**
- Once 80% is achieved, consider increasing to 85% or 90%
- Focus on critical paths and error handling

1. **Test Organization:**
- Consider grouping related tests better
- Add more descriptive test names where needed
- Document test fixtures and their purposes

---

## Test Execution Commands

### Run All Tests

```bash
python3 -m pytest
```

### Run with Coverage

```bash
python3 -m pytest --cov=function_app --cov-report=term-missing --cov-report=html
```

### Run Unit Tests Only (Exclude Integration)

```bash
python3 -m pytest -m "not integration"
```

### Run Integration Tests Only

```bash
python3 -m pytest -m integration
```

### Run Specific Test File

```bash
python3 -m pytest tests/test_blob_client.py
```

### Run Specific Test

```bash
python3 -m pytest tests/test_blob_client.py::TestCopyBlob::test_copy_blob_success
```

### View HTML Coverage Report

```bash
open htmlcov/index.html
```

---

## Summary Statistics

- **Total Test Files:** 10
- **Total Test Classes:** 14
- **Total Test Functions:** 146
- **Execution Time:** ~40 seconds
- **Success Rate:** 96.6% (excluding skipped tests)
- **Coverage Status:** ❌ Below threshold (77% vs 80% required)

---

#### Report generated automatically from pytest and coverage tools
