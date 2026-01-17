# Test Suite Report

**Generated:** 2026-01-16 17:18:56

---

## Summary

### Test Execution: ❌ FAILED

All tests completed with exit code: 1

### Code Coverage

- **Statements**: 792
- **Covered**: 735
- **Coverage**: 92.8%

## Code Quality Analysis

Code quality scores (0-100) generated using CodeHealthAnalyzer:

### Main Application Code (`function_app/`)

🔴 **Quality Score:** 50/100 (Needs Improvement)

- Violations: 4
- Errors: 3

### Test Code (`tests/`)

🟢 **Quality Score:** 100/100 (Excellent)

- Violations: 4
- Errors: 3

### Scripts (`scripts/`)

🟢 **Quality Score:** 100/100 (Excellent)

- Violations: 4
- Errors: 3

---

## Test Execution Output

```text
============================= test session starts ==============================
platform darwin -- Python 3.9.6, pytest-8.4.2, pluggy-1.6.0 -- /Library/Developer/CommandLineTools/usr/bin/python3
cachedir: .pytest_cache
rootdir: /Users/chrisrooney/Desktop/century-churn-prediction-project
configfile: pytest.ini
testpaths: tests
plugins: anyio-4.12.1, mock-3.15.1, cov-7.0.0
collecting ... collected 190 items

tests/test_blob_client.py::TestGetBlobServiceClient::test_get_blob_service_client_missing_connection_string PASSED [  0%]
tests/test_blob_client.py::TestReadBlobBytes::test_read_blob_bytes_success PASSED [  1%]
tests/test_blob_client.py::TestReadBlobBytes::test_read_blob_bytes_not_found PASSED [  1%]
tests/test_blob_client.py::TestReadBlobText::test_read_blob_text_success PASSED [  2%]
tests/test_blob_client.py::TestWriteBlobBytes::test_write_blob_bytes_success PASSED [  2%]
tests/test_blob_client.py::TestDeleteBlob::test_delete_blob_success PASSED [  3%]
tests/test_blob_client.py::TestDeleteBlob::test_delete_blob_not_found PASSED [  3%]
tests/test_blob_client.py::TestBlobExists::test_blob_exists_true PASSED  [  4%]
tests/test_blob_client.py::TestBlobExists::test_blob_exists_false PASSED [  4%]
tests/test_blob_client.py::TestCopyBlob::test_copy_blob_success PASSED   [  5%]
tests/test_blob_client.py::TestCopyBlob::test_copy_blob_missing_content_type PASSED [  5%]
tests/test_blob_client.py::TestCopyBlob::test_copy_blob_resource_not_found PASSED [  6%]
tests/test_blob_client.py::TestMoveBlob::test_move_blob_success PASSED   [  6%]
tests/test_blob_client.py::TestRenameBlob::test_rename_blob_success PASSED [  7%]
tests/test_blob_client.py::TestListBlobs::test_list_blobs_success PASSED [  7%]
tests/test_blob_client.py::TestListBlobs::test_list_blobs_with_prefix PASSED [  8%]
tests/test_blob_client.py::TestListBlobs::test_list_blobs_with_name_starts_with PASSED [  8%]
tests/test_blob_client.py::TestListBlobs::test_list_blobs_with_both_prefix_and_name_starts_with PASSED [  9%]
tests/test_blob_client.py::TestListBlobsWithProperties::test_list_blobs_with_properties_success PASSED [ 10%]
tests/test_blob_client.py::TestListBlobsWithProperties::test_list_blobs_with_properties_no_content_type PASSED [ 10%]
tests/test_blob_client.py::TestDeleteBlobPrefix::test_delete_blob_prefix_success PASSED [ 11%]
tests/test_blob_client.py::TestDeleteBlobPrefix::test_delete_blob_prefix_partial_failure PASSED [ 11%]
tests/test_blob_client.py::TestMoveToProcessed::test_move_to_processed_success PASSED [ 12%]
tests/test_blob_client.py::TestMoveToError::test_move_to_error_success PASSED [ 12%]
tests/test_blob_client.py::TestGetProcessingFolderBlobs::test_get_processing_folder_blobs PASSED [ 13%]
tests/test_blob_client.py::test_extract_snapshot_date_from_csv_success PASSED [ 13%]
tests/test_blob_client.py::test_extract_snapshot_date_from_csv_with_brackets PASSED [ 14%]
tests/test_blob_client.py::test_extract_snapshot_date_from_csv_datetime_format PASSED [ 14%]
tests/test_blob_client.py::test_extract_snapshot_date_from_csv_missing_column PASSED [ 15%]
tests/test_blob_client.py::test_extract_snapshot_date_from_csv_null_value PASSED [ 15%]
tests/test_blob_client.py::test_extract_snapshot_date_from_csv_invalid_date PASSED [ 16%]
tests/test_blob_client.py::test_extract_snapshot_date_from_csv_parse_error PASSED [ 16%]
tests/test_blob_client.py::test_get_container_client PASSED              [ 17%]
tests/test_blob_client.py::test_get_blob_client PASSED                   [ 17%]
tests/test_config.py::test_config_loads_from_env PASSED                  [ 18%]
tests/test_config.py::test_config_raises_on_missing_required PASSED      [ 18%]
tests/test_config.py::test_config_container_name_has_default PASSED      [ 19%]
tests/test_config.py::test_config_logic_app_endpoint_optional PASSED     [ 20%]
tests/test_config.py::test_config_validate_method PASSED                 [ 20%]
tests/test_config.py::test_config_validate_raises_on_empty PASSED        [ 21%]
tests/test_csv_validator.py::TestParseCsvFromBytes::test_parse_csv_success PASSED [ 21%]
tests/test_csv_validator.py::TestParseCsvFromBytes::test_parse_csv_empty_bytes PASSED [ 22%]
tests/test_csv_validator.py::TestParseCsvFromBytes::test_parse_csv_empty_file PASSED [ 22%]
tests/test_csv_validator.py::TestParseCsvFromBytes::test_parse_csv_malformed PASSED [ 23%]
tests/test_csv_validator.py::TestParseCsvFromBytes::test_parse_csv_utf8_encoding PASSED [ 23%]
tests/test_csv_validator.py::TestNormalizeColumnNames::test_normalize_customer_columns PASSED [ 24%]
tests/test_csv_validator.py::TestNormalizeColumnNames::test_normalize_feature_columns PASSED [ 24%]
tests/test_csv_validator.py::TestNormalizeColumnNames::test_normalize_preserves_data PASSED [ 25%]
tests/test_csv_validator.py::TestNormalizeColumnNames::test_normalize_already_normalized PASSED [ 25%]
tests/test_csv_validator.py::TestValidateCsvSchema::test_validate_valid_schema PASSED [ 26%]
tests/test_csv_validator.py::TestValidateCsvSchema::test_vali
```
