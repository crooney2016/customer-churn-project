"""
CSV validation and data processing module for churn prediction pipeline.
Handles CSV parsing, schema validation, and data transformation.
"""

import io
import logging
from typing import Any, Optional

import pandas as pd

# Configure logging per logging.md
logger = logging.getLogger(__name__)

# =============================================================================
# Schema Definition
# =============================================================================

# Expected column count for scoring model
# 7 identifiers + 12 aggregate + 3 trend + 50 category (10x5) + 4 breadth = 76
EXPECTED_COLUMN_COUNT = 76
MIN_COLUMN_COUNT = 70  # Allow some variance
MAX_COLUMN_COUNT = 85  # Warn if too many

# Required identifier columns (after normalization - brackets stripped)
# These are needed for scoring and SQL upsert
REQUIRED_IDENTIFIER_COLUMNS = [
    "CustomerId",      # From Customers[account_Order]
    "AccountName",     # From Customers[account_Name]
    "Segment",         # From Customers[Segment]
    "CostCenter",      # From Customers[Cost Center]
    "SnapshotDate",    # From [SnapshotDate]
]

# Date columns (optional but needed for SQL Status calculation)
DATE_COLUMNS = [
    "FirstPurchaseDate",  # From [FirstPurchaseDate]
    "LastPurchaseDate",   # From [LastPurchaseDate]
]

# Column name mappings (raw CSV name -> normalized name)
# Used when raw CSV has bracket notation from Power BI export format
# Clean CSV format outputs names directly (CustomerId, SnapshotDate, etc.)
COLUMN_NAME_MAPPINGS = {
    "Customers[account_Order]": "CustomerId",
    "Customers[account_Name]": "AccountName",
    "Customers[Segment]": "Segment",
    "Customers[Cost Center]": "CostCenter",
    "[SnapshotDate]": "SnapshotDate",
    "[FirstPurchaseDate]": "FirstPurchaseDate",
    "[LastPurchaseDate]": "LastPurchaseDate",
}

# Expected column prefixes (for validation before normalization)
# These are for Power BI bracket format - clean format has direct column names
CUSTOMER_COLUMN_PREFIX = "Customers["
FEATURE_COLUMN_PREFIX = "["


# =============================================================================
# CSV Parsing
# =============================================================================

def parse_csv_from_bytes(
    csv_bytes: bytes,
    encoding: str = "utf-8"
) -> pd.DataFrame:
    """
    Parse CSV bytes to DataFrame.

    Args:
        csv_bytes: CSV file content as bytes
        encoding: Text encoding (default: utf-8)

    Returns:
        pandas DataFrame with parsed data

    Raises:
        ValueError: If CSV is empty or cannot be parsed
    """
    if not csv_bytes:
        raise ValueError("CSV bytes are empty")

    try:
        # Parse CSV from bytes
        df = pd.read_csv(io.BytesIO(csv_bytes), encoding=encoding)

        if len(df) == 0:
            raise ValueError("CSV file contains no data rows")

        logger.info(
            "Parsed CSV with %d rows and %d columns",
            len(df),
            len(df.columns)
        )

        return df

    except pd.errors.EmptyDataError as e:
        raise ValueError(f"CSV file is empty: {str(e)}") from e
    except pd.errors.ParserError as e:
        raise ValueError(f"CSV parsing error: {str(e)}") from e
    except UnicodeDecodeError as e:
        raise ValueError(f"CSV encoding error (expected {encoding}): {str(e)}") from e


# =============================================================================
# Column Normalization
# =============================================================================

def normalize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize column names by stripping brackets and table prefixes.

    This function:
    - Removes 'Customers[' prefix and ']' suffix from customer columns
    - Removes '[' prefix and ']' suffix from feature columns
    - Maps specific columns to expected names (e.g., account_Order -> CustomerId)

    Args:
        df: DataFrame with raw column names

    Returns:
        DataFrame with normalized column names
    """
    df = df.copy()

    new_columns = []
    for col in df.columns:
        col_str = str(col).strip()

        # Check if it's a customer column: Customers[column_name]
        if col_str.startswith("Customers[") and col_str.endswith("]"):
            # Extract column name inside brackets
            inner = col_str[10:-1]  # Remove "Customers[" and "]"

            # Apply specific mappings
            if inner == "account_Order":
                new_col = "CustomerId"
            elif inner == "account_Name":
                new_col = "AccountName"
            elif inner == "Cost Center":
                new_col = "CostCenter"
            else:
                new_col = inner

        # Check if it's a feature column: [column_name]
        elif col_str.startswith("[") and col_str.endswith("]"):
            new_col = col_str[1:-1]  # Remove brackets

        else:
            # Keep as-is
            new_col = col_str

        new_columns.append(new_col)

    df.columns = new_columns

    logger.debug(
        "Normalized %d column names",
        len(new_columns)
    )

    return df


# =============================================================================
# Schema Validation
# =============================================================================

def validate_csv_schema(df: pd.DataFrame, normalize: bool = True) -> None:
    """
    Validate CSV structure matches expected schema.

    This is the main validation function that performs all checks:
    - Column count within expected range
    - Required columns present
    - Column name patterns valid
    - No duplicate columns

    Args:
        df: DataFrame to validate
        normalize: Whether to normalize column names before validation (default: True)

    Raises:
        ValueError: If validation fails with details about the issue
    """
    logger.info("Validating CSV schema...")

    # Normalize if requested
    if normalize:
        df = normalize_column_names(df)

    # Run all validation checks
    validate_column_count(df)
    validate_required_columns(df)
    validate_no_duplicate_columns(df)

    logger.info(
        "CSV schema validation passed: %d rows, %d columns",
        len(df),
        len(df.columns)
    )


def validate_column_count(df: pd.DataFrame) -> None:
    """
    Validate column count is within expected range.

    Args:
        df: DataFrame to validate

    Raises:
        ValueError: If column count is outside expected range
    """
    column_count = len(df.columns)

    if column_count < MIN_COLUMN_COUNT:
        raise ValueError(
            f"CSV has too few columns: {column_count}. "
            f"Expected at least {MIN_COLUMN_COUNT} columns. "
            f"Found columns: {list(df.columns)[:10]}..."
        )

    if column_count > MAX_COLUMN_COUNT:
        logger.warning(
            "CSV has more columns than expected: %d (expected ~%d). "
            "This may indicate schema changes.",
            column_count,
            EXPECTED_COLUMN_COUNT
        )

    logger.debug(
        "Column count validation passed: %d columns (expected ~%d)",
        column_count,
        EXPECTED_COLUMN_COUNT
    )


def validate_required_columns(df: pd.DataFrame) -> None:
    """
    Validate that all required identifier columns are present.

    Args:
        df: DataFrame to validate (should be normalized)

    Raises:
        ValueError: If required columns are missing
    """
    missing_columns = []

    for col in REQUIRED_IDENTIFIER_COLUMNS:
        if col not in df.columns:
            missing_columns.append(col)

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {missing_columns}. "
            f"Available columns: {list(df.columns)[:20]}..."
        )

    logger.debug(
        "Required columns validation passed: all %d required columns present",
        len(REQUIRED_IDENTIFIER_COLUMNS)
    )


def validate_no_duplicate_columns(df: pd.DataFrame) -> None:
    """
    Validate that there are no duplicate column names.

    Args:
        df: DataFrame to validate

    Raises:
        ValueError: If duplicate columns are found
    """
    columns = list(df.columns)
    seen: set[str] = set()
    duplicates: list[str] = []

    for col in columns:
        if col in seen:
            duplicates.append(col)
        seen.add(col)

    if duplicates:
        raise ValueError(
            f"Duplicate columns found: {duplicates}. "
            "Each column name must be unique."
        )

    logger.debug("No duplicate columns found")


def validate_column_patterns(df: pd.DataFrame) -> None:
    """
    Validate column names follow expected patterns before normalization.

    Checks that columns have expected prefixes:
    - Customer columns: Customers[...]
    - Feature columns: [...]

    Args:
        df: DataFrame to validate (before normalization)

    Raises:
        ValueError: If unexpected column patterns are found
    """
    customer_cols = []
    feature_cols = []
    other_cols = []

    for col in df.columns:
        col_str = str(col)
        if col_str.startswith(CUSTOMER_COLUMN_PREFIX):
            customer_cols.append(col_str)
        elif col_str.startswith(FEATURE_COLUMN_PREFIX):
            feature_cols.append(col_str)
        else:
            other_cols.append(col_str)

    if other_cols:
        logger.warning(
            "Found %d columns without expected prefix patterns: %s",
            len(other_cols),
            other_cols[:5]
        )

    logger.debug(
        "Column patterns: %d customer, %d feature, %d other",
        len(customer_cols),
        len(feature_cols),
        len(other_cols)
    )


# =============================================================================
# Data Type Validation
# =============================================================================

def validate_column_types(df: pd.DataFrame) -> dict[str, list[str]]:
    """
    Validate data types match expected schema.

    Args:
        df: DataFrame to validate (should be normalized)

    Returns:
        Dictionary with 'warnings' and 'errors' lists
    """
    issues: dict[str, list[str]] = {"warnings": [], "errors": []}

    # Check date columns can be parsed
    for col in DATE_COLUMNS:
        if col in df.columns:
            try:
                # Try to parse as datetime
                pd.to_datetime(df[col], errors='coerce')
            except (ValueError, TypeError, OverflowError) as e:
                issues["warnings"].append(
                    f"Date column '{col}' may have invalid values: {str(e)}"
                )

    # Check numeric columns are numeric
    numeric_patterns = [
        "Orders_", "Spend_", "Units_", "AOV_", "Days", "Tenure",
        "Pct_", "Trend", "Categories_"
    ]

    for col in df.columns:
        for pattern in numeric_patterns:
            if pattern in col:
                if not pd.api.types.is_numeric_dtype(df[col]):
                    # Check if it can be converted
                    try:
                        pd.to_numeric(df[col], errors='coerce')
                    except (ValueError, TypeError):
                        issues["warnings"].append(
                            f"Column '{col}' expected to be numeric but has type {df[col].dtype}"
                        )
                break

    if issues["warnings"]:
        logger.warning(
            "Data type validation found %d warnings: %s",
            len(issues["warnings"]),
            issues["warnings"][:3]
        )

    if issues["errors"]:
        logger.error(
            "Data type validation found %d errors: %s",
            len(issues["errors"]),
            issues["errors"]
        )

    return issues


# =============================================================================
# Utility Functions
# =============================================================================

def get_expected_columns() -> dict[str, str]:
    """
    Get dictionary of expected column names and their types.

    Returns:
        Dictionary mapping column names to expected types
    """
    columns = {}

    # Identifier columns (strings)
    for col in REQUIRED_IDENTIFIER_COLUMNS:
        columns[col] = "string"

    # Date columns
    for col in DATE_COLUMNS:
        columns[col] = "datetime"

    # Numeric feature columns (common patterns)
    numeric_patterns = [
        ("Orders_CY", "int"),
        ("Orders_PY", "int"),
        ("Orders_Lifetime", "int"),
        ("Spend_CY", "float"),
        ("Spend_PY", "float"),
        ("Spend_Lifetime", "float"),
        ("Units_CY", "int"),
        ("Units_PY", "int"),
        ("Units_Lifetime", "int"),
        ("AOV_CY", "float"),
        ("DaysSinceLast", "int"),
        ("TenureDays", "int"),
    ]

    for col, dtype in numeric_patterns:
        columns[col] = dtype

    return columns


def get_column_summary(df: pd.DataFrame) -> dict[str, Any]:
    """
    Get summary of DataFrame columns for diagnostics.

    Args:
        df: DataFrame to summarize

    Returns:
        Dictionary with column statistics
    """
    customer_cols = [c for c in df.columns if str(c).startswith("Customers[")]
    feature_cols = [
        c for c in df.columns
        if str(c).startswith("[") and not str(c).startswith("Customers[")
    ]
    other_cols = [c for c in df.columns if c not in customer_cols and c not in feature_cols]

    return {
        "total_columns": len(df.columns),
        "total_rows": len(df),
        "customer_columns": len(customer_cols),
        "feature_columns": len(feature_cols),
        "other_columns": len(other_cols),
        "null_counts": df.isnull().sum().to_dict(),
        "dtypes": df.dtypes.astype(str).to_dict(),
    }


def validate_snapshot_date_present(df: pd.DataFrame) -> Optional[str]:
    """
    Validate that SnapshotDate column exists and extract its value.

    Args:
        df: DataFrame to check (may be normalized or not)

    Returns:
        Snapshot date string or None if not found

    Raises:
        ValueError: If SnapshotDate column is missing or all values are null
    """
    # Check for SnapshotDate in various forms
    snapshot_col = None
    for col in df.columns:
        col_str = str(col)
        if "SnapshotDate" in col_str:
            snapshot_col = col
            break

    if snapshot_col is None:
        raise ValueError(
            "SnapshotDate column not found in DataFrame. "
            f"Available columns: {list(df.columns)[:10]}..."
        )

    # Check that we have at least one non-null value
    if bool(df[snapshot_col].isnull().all()):
        raise ValueError("All SnapshotDate values are null")

    # Get the first non-null value
    first_value = df[snapshot_col].dropna().iloc[0]

    # Format as string
    try:
        if isinstance(first_value, str):
            return first_value[:10]  # Return YYYY-MM-DD portion
        else:
            return pd.to_datetime(first_value).strftime("%Y-%m-%d")
    except (ValueError, TypeError, AttributeError) as e:
        logger.warning("Could not format SnapshotDate: %s", str(e))
        return str(first_value)
