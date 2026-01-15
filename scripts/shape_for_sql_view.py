#!/usr/bin/env python3
"""
Shape scored data to match SQL view output (vwCustomerCurrent).

This script replicates the SQL view logic locally so you can explore
the data in the same format it will appear in Power BI after SQL processing.

Key transformations:
1. Get latest snapshot per customer (like SQL ROW_NUMBER window function)
2. Calculate Status (New/Active/Churned/Reactivated) like fnCalculateStatus
3. Remove SourceFile column (local processing artifact)
4. Order columns to match SQL view structure
5. Output ready for Power BI exploration

Usage:
    python scripts/shape_for_sql_view.py [input_csv] [output_csv]

    Defaults:
    - Input: outputs/churn_scores_combined.csv
    - Output: outputs/churn_scores_sql_view.csv
"""

import argparse
import logging
import sys
import time
from pathlib import Path

import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def calculate_status(first_purchase_date: pd.Series, last_purchase_date: pd.Series) -> pd.Series:
    """
    Calculate customer status like SQL fnCalculateStatus function.

    Logic:
    - 'New': FirstPurchaseDate within 365 days
    - 'Active': LastPurchaseDate within 365 days
    - 'Churned': LastPurchaseDate > 365 days ago
    - 'Unknown': Missing dates

    Args:
        first_purchase_date: Series of first purchase dates
        last_purchase_date: Series of last purchase dates

    Returns:
        Series of status strings
    """
    today = pd.Timestamp.now().normalize()
    status = pd.Series('Unknown', index=first_purchase_date.index)

    # Calculate days since first purchase
    days_since_first = (today - pd.to_datetime(first_purchase_date)).dt.days
    days_since_last = (today - pd.to_datetime(last_purchase_date)).dt.days

    # 'New': FirstPurchaseDate within 365 days
    new_mask = days_since_first.notna() & (days_since_first <= 365)
    status[new_mask] = 'New'

    # 'Active': LastPurchaseDate within 365 days (but not New)
    active_mask = days_since_last.notna() & (days_since_last <= 365) & ~new_mask
    status[active_mask] = 'Active'

    # 'Churned': LastPurchaseDate > 365 days ago
    churned_mask = days_since_last.notna() & (days_since_last > 365) & ~new_mask
    status[churned_mask] = 'Churned'

    return status


def shape_like_sql_view(df: pd.DataFrame) -> pd.DataFrame:
    """
    Transform data to match SQL vwCustomerCurrent view structure.

    Args:
        df: Combined scored DataFrame with all records

    Returns:
        DataFrame shaped like SQL view output
    """
    logger.info("Shaping data to match SQL view structure...")

    # Ensure dates are datetime
    if 'SnapshotDate' in df.columns:
        df['SnapshotDate'] = pd.to_datetime(df['SnapshotDate']).dt.date
    if 'FirstPurchaseDate' in df.columns:
        df['FirstPurchaseDate'] = pd.to_datetime(df['FirstPurchaseDate']).dt.date
    if 'LastPurchaseDate' in df.columns:
        df['LastPurchaseDate'] = pd.to_datetime(df['LastPurchaseDate']).dt.date

    # Step 1: Get latest snapshot per customer (like SQL ROW_NUMBER)
    logger.info("Getting latest snapshot per customer...")
    df_sorted = df.sort_values(['CustomerId', 'SnapshotDate'], ascending=[True, False])
    df_latest = df_sorted.groupby('CustomerId').first().reset_index()

    logger.info(
        "Reduced from %d records to %d customers (latest snapshot each)",
        len(df),
        len(df_latest)
    )

    # Step 2: Calculate Status (like fnCalculateStatus)
    logger.info("Calculating customer status...")
    if 'FirstPurchaseDate' in df_latest.columns and 'LastPurchaseDate' in df_latest.columns:
        df_latest['Status'] = calculate_status(
            df_latest['FirstPurchaseDate'],
            df_latest['LastPurchaseDate']
        )
    else:
        logger.warning(
            "FirstPurchaseDate or LastPurchaseDate missing - cannot calculate Status. "
            "Setting all to 'Unknown'"
        )
        df_latest['Status'] = 'Unknown'

    # Step 3: Check for Reactivated customers
    # (Was Churned in previous snapshot, now Active)
    logger.info("Identifying reactivated customers...")
    # Note: Full reactivation detection requires historical data with LAG() window function
    # Since we only have latest snapshot, SQL will handle reactivation with full history

    # Step 4: Remove SourceFile column (local processing artifact)
    if 'SourceFile' in df_latest.columns:
        df_latest = df_latest.drop(columns=['SourceFile'])
        logger.info("Removed SourceFile column (local processing artifact)")

    # Step 5: Order columns to match SQL view structure
    # SQL view order: ID cols, score cols, identity cols, dates, status, then all features
    id_cols = ['CustomerId', 'SnapshotDate']
    score_cols = ['ChurnRiskPct', 'RiskBand', 'Reason_1', 'Reason_2', 'Reason_3', 'ScoredAt']
    identity_cols = ['AccountName', 'Segment', 'CostCenter']
    date_cols = ['FirstPurchaseDate', 'LastPurchaseDate']

    # Feature columns (all remaining columns except Status)
    feature_cols = [
        c for c in df_latest.columns
        if c not in id_cols + score_cols + identity_cols + date_cols + ['Status']
    ]

    # SQL view column order
    column_order = (
        id_cols +
        score_cols +
        identity_cols +
        date_cols +
        ['Status'] +
        sorted(feature_cols)  # Sort features alphabetically for consistency
    )

    # Reorder columns (only include columns that exist)
    available_cols = [c for c in column_order if c in df_latest.columns]
    df_shaped = df_latest[available_cols].copy()

    logger.info(
        "Shaped data with %d columns matching SQL view structure",
        len(df_shaped.columns)
    )

    return df_shaped


def print_summary(df: pd.DataFrame) -> None:
    """Print summary statistics about the shaped data."""
    logger.info("=" * 60)
    logger.info("SQL VIEW SHAPE SUMMARY")
    logger.info("=" * 60)
    logger.info("Total customers: %d", len(df))

    if 'Status' in df.columns:
        status_dist = df['Status'].value_counts()
        logger.info("\nStatus Distribution:")
        for status, count in status_dist.items():
            pct = (count / len(df)) * 100
            logger.info("  %s: %d (%.1f%%)", status, count, pct)

    if 'RiskBand' in df.columns:
        risk_dist = df['RiskBand'].value_counts()
        logger.info("\nRisk Band Distribution:")
        for band, count in risk_dist.items():
            pct = (count / len(df)) * 100
            logger.info("  %s: %d (%.1f%%)", band, count, pct)

    if 'ChurnRiskPct' in df.columns:
        logger.info("\nChurn Risk Statistics:")
        logger.info("  Mean: %.4f", df['ChurnRiskPct'].mean())
        logger.info("  Median: %.4f", df['ChurnRiskPct'].median())
        logger.info("  Min: %.4f", df['ChurnRiskPct'].min())
        logger.info("  Max: %.4f", df['ChurnRiskPct'].max())

    logger.info("=" * 60)


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Shape scored data to match SQL view output",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/shape_for_sql_view.py
  python scripts/shape_for_sql_view.py outputs/churn_scores_combined.csv
  python scripts/shape_for_sql_view.py input.csv output.csv
        """
    )
    parser.add_argument(
        'input_file',
        nargs='?',
        default='outputs/churn_scores_combined.csv',
        help='Input CSV file (default: outputs/churn_scores_combined.csv)'
    )
    parser.add_argument(
        '-o', '--output',
        default='outputs/churn_scores_sql_view.csv',
        help='Output CSV file (default: outputs/churn_scores_sql_view.csv)'
    )

    args = parser.parse_args()

    # From scripts/, go up one level to project root
    project_root = Path(__file__).parent.parent
    input_path = Path(args.input_file)
    if not input_path.is_absolute():
        input_path = project_root / input_path

    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = project_root / output_path

    try:
        start_time = time.time()
        logger.info("=" * 60)
        logger.info("Shaping data to match SQL view structure")
        logger.info("=" * 60)
        logger.info("Input file: %s", input_path)
        logger.info("Output file: %s", output_path)

        # Load input
        logger.info("Loading input data...")
        load_start = time.time()
        df = pd.read_csv(input_path, low_memory=False)
        load_time = time.time() - load_start
        logger.info("Loaded %d records in %.2f seconds", len(df), load_time)

        # Shape data
        df_shaped = shape_like_sql_view(df)

        # Print summary
        print_summary(df_shaped)

        # Write output
        logger.info("Writing output file...")
        write_start = time.time()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        df_shaped.to_csv(output_path, index=False)
        write_time = time.time() - write_start

        file_size_mb = output_path.stat().st_size / (1024 * 1024)
        logger.info(
            "Successfully wrote %d records (%.2f MB) to %s in %.2f seconds",
            len(df_shaped),
            file_size_mb,
            output_path,
            write_time
        )

        total_time = time.time() - start_time
        logger.info("=" * 60)
        logger.info("✓ Shaping completed successfully!")
        logger.info("Total execution time: %.2f seconds", total_time)
        logger.info("Output file: %s", output_path)
        logger.info("=" * 60)
        logger.info("")
        logger.info("This file matches the structure of SQL view: dbo.vwCustomerCurrent")
        logger.info("Ready for Power BI exploration!")

    except FileNotFoundError as e:
        logger.error("File not found: %s", str(e))
        sys.exit(1)
    except (ValueError, KeyError, pd.errors.EmptyDataError) as e:
        logger.error("Data processing error: %s", str(e), exc_info=True)
        sys.exit(1)
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.error("Unexpected error: %s", str(e), exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
