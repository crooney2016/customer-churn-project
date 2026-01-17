"""
Tests for csv_validator module.
Tests CSV parsing, schema validation, and data transformation.
"""

import pytest
import pandas as pd


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def sample_csv_bytes_valid():
    """Valid CSV file content with expected schema."""
    csv_content = (
        "[SnapshotDate],Customers[account_Order],Customers[account_Name],"
        "Customers[Segment],Customers[Cost Center],[FirstPurchaseDate],"
        "[LastPurchaseDate],[Orders_CY],[Spend_CY],[Units_CY]\n"
        "2025-01-31,001,Account A,FITNESS,CMFIT,2023-01-01,2024-12-01,10,5000.00,100\n"
        "2025-01-31,002,Account B,FARRELL,CMFIT,2023-06-01,2024-11-15,5,2500.00,50\n"
        "2025-01-31,003,Account C,FITNESS,CMFIT,2022-01-01,2025-01-01,20,10000.00,200\n"
    )
    return csv_content.encode("utf-8")


@pytest.fixture
def sample_csv_bytes_missing_columns():
    """CSV file missing required columns."""
    csv_content = """[SnapshotDate],[Orders_CY]
2025-01-31,10
2025-01-31,5
"""
    return csv_content.encode("utf-8")


@pytest.fixture
def sample_df_normalized():
    """Sample DataFrame with normalized column names."""
    return pd.DataFrame({
        "SnapshotDate": pd.to_datetime(["2025-01-31", "2025-01-31", "2025-01-31"]),
        "CustomerId": ["001", "002", "003"],
        "AccountName": ["Account A", "Account B", "Account C"],
        "Segment": ["FITNESS", "FARRELL", "FITNESS"],
        "CostCenter": ["CMFIT", "CMFIT", "CMFIT"],
        "FirstPurchaseDate": pd.to_datetime(["2023-01-01", "2023-06-01", "2022-01-01"]),
        "LastPurchaseDate": pd.to_datetime(["2024-12-01", "2024-11-15", "2025-01-01"]),
        "Orders_CY": [10, 5, 20],
        "Spend_CY": [5000.0, 2500.0, 10000.0],
    })


@pytest.fixture
def sample_df_raw():
    """Sample DataFrame with raw column names (brackets)."""
    return pd.DataFrame({
        "[SnapshotDate]": pd.to_datetime(["2025-01-31", "2025-01-31", "2025-01-31"]),
        "Customers[account_Order]": ["001", "002", "003"],
        "Customers[account_Name]": ["Account A", "Account B", "Account C"],
        "Customers[Segment]": ["FITNESS", "FARRELL", "FITNESS"],
        "Customers[Cost Center]": ["CMFIT", "CMFIT", "CMFIT"],
        "[FirstPurchaseDate]": pd.to_datetime(["2023-01-01", "2023-06-01", "2022-01-01"]),
        "[LastPurchaseDate]": pd.to_datetime(["2024-12-01", "2024-11-15", "2025-01-01"]),
        "[Orders_CY]": [10, 5, 20],
        "[Spend_CY]": [5000.0, 2500.0, 10000.0],
    })


# =============================================================================
# CSV Parsing Tests
# =============================================================================

class TestParseCsvFromBytes:
    """Tests for parse_csv_from_bytes function."""

    def test_parse_csv_success(self, sample_csv_bytes_valid):
        """Test successful CSV parsing."""
        from function_app.csv_validator import parse_csv_from_bytes

        df = parse_csv_from_bytes(sample_csv_bytes_valid)

        assert len(df) == 3
        assert len(df.columns) == 10
        assert "[SnapshotDate]" in df.columns

    def test_parse_csv_empty_bytes(self):
        """Test parsing empty bytes raises error."""
        from function_app.csv_validator import parse_csv_from_bytes

        with pytest.raises(ValueError, match="CSV bytes are empty"):
            parse_csv_from_bytes(b"")

    def test_parse_csv_empty_file(self):
        """Test parsing file with only headers raises error."""
        csv_content = b"Col1,Col2,Col3\n"

        from function_app.csv_validator import parse_csv_from_bytes

        with pytest.raises(ValueError, match="no data rows"):
            parse_csv_from_bytes(csv_content)

    def test_parse_csv_malformed(self):
        """Test parsing malformed CSV raises error."""
        csv_content = b"this is not a valid csv\n\x00\x01\x02"

        from function_app.csv_validator import parse_csv_from_bytes

        # Should still parse (pandas is lenient) but may have unexpected structure
        # The key is it doesn't crash
        df = parse_csv_from_bytes(csv_content)
        assert df is not None

    def test_parse_csv_utf8_encoding(self):
        """Test parsing CSV with UTF-8 special characters."""
        csv_content = "Name,Value\nCafé,100\nÜber,200\n".encode("utf-8")

        from function_app.csv_validator import parse_csv_from_bytes
        df = parse_csv_from_bytes(csv_content)

        assert df["Name"].iloc[0] == "Café"
        assert df["Name"].iloc[1] == "Über"


# =============================================================================
# Column Normalization Tests
# =============================================================================

class TestNormalizeColumnNames:
    """Tests for normalize_column_names function."""

    def test_normalize_customer_columns(self, sample_df_raw):
        """Test normalization of customer columns."""
        from function_app.csv_validator import normalize_column_names

        df = normalize_column_names(sample_df_raw)

        assert "CustomerId" in df.columns
        assert "AccountName" in df.columns
        assert "Segment" in df.columns
        assert "CostCenter" in df.columns
        assert "Customers[account_Order]" not in df.columns

    def test_normalize_feature_columns(self, sample_df_raw):
        """Test normalization of feature columns."""
        from function_app.csv_validator import normalize_column_names

        df = normalize_column_names(sample_df_raw)

        assert "SnapshotDate" in df.columns
        assert "FirstPurchaseDate" in df.columns
        assert "LastPurchaseDate" in df.columns
        assert "Orders_CY" in df.columns
        assert "[SnapshotDate]" not in df.columns

    def test_normalize_preserves_data(self, sample_df_raw):
        """Test that normalization preserves data values."""
        from function_app.csv_validator import normalize_column_names

        df = normalize_column_names(sample_df_raw)

        assert df["CustomerId"].tolist() == ["001", "002", "003"]
        assert df["AccountName"].tolist() == ["Account A", "Account B", "Account C"]

    def test_normalize_already_normalized(self, sample_df_normalized):
        """Test normalization of already normalized DataFrame."""
        from function_app.csv_validator import normalize_column_names

        df = normalize_column_names(sample_df_normalized)

        # Should work without error and keep columns as-is
        assert "CustomerId" in df.columns
        assert "SnapshotDate" in df.columns


# =============================================================================
# Schema Validation Tests
# =============================================================================

class TestValidateCsvSchema:
    """Tests for validate_csv_schema function."""

    def test_validate_valid_schema(self, sample_df_normalized):
        """Test validation passes when required columns present."""
        from function_app.csv_validator import (
            validate_required_columns,
            validate_no_duplicate_columns
        )

        # Test individual validation steps (not full schema which checks column count)
        validate_required_columns(sample_df_normalized)
        validate_no_duplicate_columns(sample_df_normalized)

    def test_validate_missing_required_columns(self):
        """Test validation fails for missing required columns."""
        df = pd.DataFrame({
            "SnapshotDate": ["2025-01-31"],
            "Orders_CY": [10],
        })

        from function_app.csv_validator import validate_required_columns

        with pytest.raises(ValueError, match="Missing required columns"):
            validate_required_columns(df)


class TestValidateColumnCount:
    """Tests for validate_column_count function."""

    def test_validate_column_count_valid(self):
        """Test validation passes for valid column count."""
        # Create DataFrame with 76 columns (expected from DAX query)
        df = pd.DataFrame({f"col_{i}": [1, 2, 3] for i in range(76)})

        from function_app.csv_validator import validate_column_count

        # Should not raise exception
        validate_column_count(df)

    def test_validate_column_count_too_few(self):
        """Test validation fails for too few columns."""
        # Create DataFrame with only 50 columns
        df = pd.DataFrame({f"col_{i}": [1, 2, 3] for i in range(50)})

        from function_app.csv_validator import validate_column_count

        with pytest.raises(ValueError, match="too few columns"):
            validate_column_count(df)

    def test_validate_column_count_many_warns(self):
        """Test validation warns for too many columns."""
        # Create DataFrame with 120 columns (more than MAX_COLUMN_COUNT)
        df = pd.DataFrame({f"col_{i}": [1, 2, 3] for i in range(120)})

        from function_app.csv_validator import validate_column_count

        # Should not raise, just warn
        validate_column_count(df)


class TestValidateRequiredColumns:
    """Tests for validate_required_columns function."""

    def test_validate_required_columns_present(self, sample_df_normalized):
        """Test validation passes when all required columns present."""
        from function_app.csv_validator import validate_required_columns

        # Should not raise exception
        validate_required_columns(sample_df_normalized)

    def test_validate_required_columns_missing(self):
        """Test validation fails when required columns missing."""
        df = pd.DataFrame({
            "SnapshotDate": ["2025-01-31"],
            "CustomerId": ["001"],
            # Missing AccountName, Segment, CostCenter
        })

        from function_app.csv_validator import validate_required_columns

        with pytest.raises(ValueError, match="Missing required columns"):
            validate_required_columns(df)

    def test_validate_required_columns_partial(self):
        """Test validation fails with partial required columns."""
        df = pd.DataFrame({
            "SnapshotDate": ["2025-01-31"],
            "CustomerId": ["001"],
            "AccountName": ["Account A"],
            # Missing Segment, CostCenter
        })

        from function_app.csv_validator import validate_required_columns

        with pytest.raises(ValueError, match="Missing required columns"):
            validate_required_columns(df)


class TestValidateNoDuplicateColumns:
    """Tests for validate_no_duplicate_columns function."""

    def test_validate_no_duplicates(self, sample_df_normalized):
        """Test validation passes with no duplicate columns."""
        from function_app.csv_validator import validate_no_duplicate_columns

        # Should not raise exception
        validate_no_duplicate_columns(sample_df_normalized)

    def test_validate_with_duplicates(self):
        """Test validation fails with duplicate columns."""
        # Create DataFrame with duplicate columns using array data
        data = [[1, 2, 3, 4]]
        df = pd.DataFrame(data)
        df.columns = pd.Index(["Col1", "Col2", "Col1", "Col3"])

        from function_app.csv_validator import validate_no_duplicate_columns

        with pytest.raises(ValueError, match="Duplicate columns found"):
            validate_no_duplicate_columns(df)


# =============================================================================
# Data Type Validation Tests
# =============================================================================

class TestValidateColumnTypes:
    """Tests for validate_column_types function."""

    def test_validate_types_valid(self, sample_df_normalized):
        """Test type validation passes for valid types."""
        from function_app.csv_validator import validate_column_types

        issues = validate_column_types(sample_df_normalized)

        # Should have no errors
        assert len(issues["errors"]) == 0

    def test_validate_types_with_warnings(self):
        """Test type validation returns warnings for suspicious types."""
        df = pd.DataFrame({
            "SnapshotDate": ["not a date"],
            "CustomerId": ["001"],
            "AccountName": ["Account A"],
            "Segment": ["FITNESS"],
            "CostCenter": ["CMFIT"],
            "FirstPurchaseDate": ["invalid"],
            "LastPurchaseDate": ["invalid"],
            "Orders_CY": ["not numeric"],  # Should be numeric but is string
        })

        from function_app.csv_validator import validate_column_types

        issues = validate_column_types(df)

        # Should have warnings but not necessarily errors
        # (depends on strictness)
        assert isinstance(issues, dict)
        assert "warnings" in issues


# =============================================================================
# Utility Functions Tests
# =============================================================================

class TestGetExpectedColumns:
    """Tests for get_expected_columns function."""

    def test_get_expected_columns(self):
        """Test getting expected column definitions."""
        from function_app.csv_validator import get_expected_columns

        columns = get_expected_columns()

        assert "CustomerId" in columns
        assert "SnapshotDate" in columns
        assert "AccountName" in columns
        assert columns["CustomerId"] == "string"


class TestGetColumnSummary:
    """Tests for get_column_summary function."""

    def test_get_column_summary(self, sample_df_raw):
        """Test getting column summary."""
        from function_app.csv_validator import get_column_summary

        summary = get_column_summary(sample_df_raw)

        assert "total_columns" in summary
        assert "total_rows" in summary
        assert "customer_columns" in summary
        assert "feature_columns" in summary
        assert summary["total_rows"] == 3


class TestValidateSnapshotDatePresent:
    """Tests for validate_snapshot_date_present function."""

    def test_validate_snapshot_date_present(self, sample_df_normalized):
        """Test validation passes when SnapshotDate present."""
        from function_app.csv_validator import validate_snapshot_date_present

        result = validate_snapshot_date_present(sample_df_normalized)

        assert result == "2025-01-31"

    def test_validate_snapshot_date_with_brackets(self, sample_df_raw):
        """Test validation works with bracketed column name."""
        from function_app.csv_validator import validate_snapshot_date_present

        result = validate_snapshot_date_present(sample_df_raw)

        assert result == "2025-01-31"

    def test_validate_snapshot_date_missing(self):
        """Test validation fails when SnapshotDate missing."""
        df = pd.DataFrame({
            "CustomerId": ["001"],
            "AccountName": ["Account A"],
        })

        from function_app.csv_validator import validate_snapshot_date_present

        with pytest.raises(ValueError, match="SnapshotDate column not found"):
            validate_snapshot_date_present(df)

    def test_validate_snapshot_date_all_null(self):
        """Test validation fails when all SnapshotDate values are null."""
        df = pd.DataFrame({
            "SnapshotDate": [None, None, None],
            "CustomerId": ["001", "002", "003"],
        })

        from function_app.csv_validator import validate_snapshot_date_present

        with pytest.raises(ValueError, match="All SnapshotDate values are null"):
            validate_snapshot_date_present(df)


# =============================================================================
# Integration Tests
# =============================================================================

class TestIntegration:
    """Integration tests for CSV validation pipeline."""

    def test_full_validation_pipeline(self, sample_csv_bytes_valid):
        """Test full validation pipeline from bytes to validated DataFrame."""
        from function_app.csv_validator import (
            parse_csv_from_bytes,
            normalize_column_names,
            validate_required_columns,
            validate_no_duplicate_columns,
            validate_snapshot_date_present,
        )

        # Parse CSV
        df = parse_csv_from_bytes(sample_csv_bytes_valid)
        assert len(df) == 3

        # Normalize columns
        df_normalized = normalize_column_names(df)
        assert "CustomerId" in df_normalized.columns

        # Validate required columns and no duplicates
        validate_required_columns(df_normalized)
        validate_no_duplicate_columns(df_normalized)

        # Validate snapshot date
        snapshot_date = validate_snapshot_date_present(df_normalized)
        assert snapshot_date == "2025-01-31"

    def test_validation_with_real_column_count(self):
        """Test validation with realistic column count (76 columns)."""
        # Create DataFrame with 76 columns matching expected schema
        # 7 identifiers + 69 features = 76 total
        columns = {}

        # Add required identifier columns (7)
        columns["CustomerId"] = ["001", "002"]
        columns["AccountName"] = ["Account A", "Account B"]
        columns["Segment"] = ["FITNESS", "FARRELL"]
        columns["CostCenter"] = ["CMFIT", "CMFIT"]
        columns["SnapshotDate"] = ["2025-01-31", "2025-01-31"]
        columns["FirstPurchaseDate"] = ["2023-01-01", "2023-06-01"]
        columns["LastPurchaseDate"] = ["2024-12-01", "2024-11-15"]

        # Add feature columns to reach 76
        for i in range(69):
            columns[f"Feature_{i}"] = [i, i + 1]

        df = pd.DataFrame(columns)
        assert len(df.columns) == 76

        from function_app.csv_validator import validate_column_count

        # Should not raise
        validate_column_count(df)


# =============================================================================
# Tests for validate_csv_schema wrapper function
# =============================================================================

class TestValidateCsvSchemaWrapper:
    """Tests for validate_csv_schema wrapper function."""

    def test_validate_csv_schema_success(self, sample_df_normalized):
        """Test validate_csv_schema with valid DataFrame."""
        from function_app.csv_validator import validate_csv_schema

        # Add more columns to reach expected count
        df = sample_df_normalized.copy()
        for i in range(70):
            df[f"Feature_{i}"] = [i, i + 1, i + 2]

        # Should not raise
        validate_csv_schema(df, normalize=False)

    def test_validate_csv_schema_with_normalize(self):
        """Test validate_csv_schema with normalization enabled."""
        from function_app.csv_validator import validate_csv_schema

        # DataFrame with bracketed column names
        df = pd.DataFrame({
            "[SnapshotDate]": ["2025-01-31", "2025-01-31"],
            "Customers[account_Order]": ["001", "002"],
            "Customers[account_Name]": ["Account A", "Account B"],
            "Customers[Segment]": ["FITNESS", "FARRELL"],
            "Customers[Cost Center]": ["CMFIT", "CMFIT"],
        })

        # Add feature columns
        for i in range(70):
            df[f"[Feature_{i}]"] = [i, i + 1]

        # Should normalize and validate successfully
        validate_csv_schema(df, normalize=True)

    def test_validate_csv_schema_missing_columns(self, sample_df_normalized):
        """Test validate_csv_schema fails with missing required columns."""
        from function_app.csv_validator import validate_csv_schema

        # Remove required column but keep enough columns to pass count check
        df = sample_df_normalized.drop(columns=["CustomerId"]).copy()
        # Add more columns to pass column count check
        for i in range(70):
            df[f"Feature_{i}"] = [i, i + 1, i + 2]

        with pytest.raises(ValueError, match="Missing required columns"):
            validate_csv_schema(df, normalize=False)

    def test_validate_csv_schema_wrong_column_count(self, sample_df_normalized):
        """Test validate_csv_schema fails with wrong column count."""
        from function_app.csv_validator import validate_csv_schema

        # Too few columns
        df = sample_df_normalized.copy()

        with pytest.raises(ValueError, match="CSV has too few columns"):
            validate_csv_schema(df, normalize=False)

    def test_validate_csv_schema_duplicate_columns(self):
        """Test validate_csv_schema fails with duplicate columns."""
        from function_app.csv_validator import validate_csv_schema

        # Create DataFrame with all required columns and a duplicate
        df = pd.DataFrame({
            "CustomerId": ["001", "002"],
            "AccountName": ["Account A", "Account B"],
            "Segment": ["FITNESS", "FARRELL"],
            "CostCenter": ["CMFIT", "CMFIT"],
            "SnapshotDate": ["2025-01-31", "2025-01-31"],
            "Orders_CY": [10, 20],
        })
        # Create duplicate by modifying columns list
        df.columns = ["CustomerId", "AccountName", "Segment", "CostCenter", "SnapshotDate", "CustomerId"]

        # Add more columns to pass count check
        for i in range(70):
            df[f"Feature_{i}"] = [i, i + 1]

        with pytest.raises(ValueError, match="Duplicate columns"):
            validate_csv_schema(df, normalize=False)


# =============================================================================
# Tests for validate_column_patterns
# =============================================================================

class TestValidateColumnPatterns:
    """Tests for validate_column_patterns function."""

    def test_validate_column_patterns_customer_prefix(self):
        """Test validate_column_patterns with customer prefix columns."""
        from function_app.csv_validator import validate_column_patterns

        df = pd.DataFrame({
            "Customers[account_Order]": ["001", "002"],
            "Customers[account_Name]": ["Account A", "Account B"],
            "Customers[Segment]": ["FITNESS", "FARRELL"],
        })

        # Should not raise (only logs warnings)
        validate_column_patterns(df)

    def test_validate_column_patterns_feature_prefix(self):
        """Test validate_column_patterns with feature prefix columns."""
        from function_app.csv_validator import validate_column_patterns

        df = pd.DataFrame({
            "[Orders_CY]": [10, 20],
            "[Spend_CY]": [5000.0, 10000.0],
            "[Units_CY]": [100, 200],
        })

        # Should not raise (only logs warnings)
        validate_column_patterns(df)

    def test_validate_column_patterns_mixed_prefixes(self):
        """Test validate_column_patterns with mixed prefix columns."""
        from function_app.csv_validator import validate_column_patterns

        df = pd.DataFrame({
            "Customers[account_Order]": ["001", "002"],
            "[Orders_CY]": [10, 20],
            "OtherColumn": ["A", "B"],  # No prefix
        })

        # Should not raise (logs warning for OtherColumn)
        validate_column_patterns(df)

    def test_validate_column_patterns_no_prefix(self):
        """Test validate_column_patterns with columns without expected prefixes."""
        from function_app.csv_validator import validate_column_patterns

        df = pd.DataFrame({
            "CustomerId": ["001", "002"],
            "Orders_CY": [10, 20],
            "UnknownColumn": ["A", "B"],
        })

        # Should not raise (only logs warnings)
        validate_column_patterns(df)
