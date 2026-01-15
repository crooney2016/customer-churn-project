#!/usr/bin/env python3
"""
Unified local scoring script for churn prediction.

Can score a single CSV file, all CSV files in a directory, or all chunks in chunks/ folder.
Uses the shared scoring logic from function_app.scorer to avoid code duplication.

Usage:
    python score_customers.py                       # Score all files in chunks/ folder
    python score_customers.py <input_csv_path>      # Score a single CSV file
    python score_customers.py <directory_path>      # Score all CSVs in directory

Output:
    outputs/churn_scores_combined.csv - All scored records
    outputs/README.md - Project documentation
    outputs/model_conda.yml - Model environment configuration
"""

import argparse
import logging
import shutil
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

# Add function_app to path for imports before importing scorer
sys.path.insert(0, str(Path(__file__).parent / "function_app"))
from scorer import score_customers  # type: ignore[import-untyped] # pylint: disable=import-error,wrong-import-position

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def find_csv_files(input_path: Path) -> list:
    """
    Find CSV files from input path (file or directory).

    Args:
        input_path: Path to a CSV file or directory containing CSV files

    Returns:
        Sorted list of CSV file paths
    """
    if not input_path.exists():
        raise FileNotFoundError(f"Path not found: {input_path}")

    if input_path.is_file():
        if input_path.suffix.lower() != '.csv':
            raise ValueError(f"Input file must be a CSV file: {input_path}")
        return [input_path]

    # It's a directory - find all CSV files
    csv_files = sorted(input_path.glob("*.csv"))

    if not csv_files:
        raise FileNotFoundError(f"No CSV files found in {input_path}")

    # Sort numerically if filenames contain numbers
    try:
        csv_files = sorted(
            csv_files,
            key=lambda x: int(''.join(filter(str.isdigit, x.stem)) or '0')
        )
    except ValueError:
        # If numeric sorting fails, use alphabetical
        csv_files = sorted(csv_files)

    logger.info("Found %d CSV file(s) to process", len(csv_files))
    return csv_files


def process_files(csv_files: list) -> pd.DataFrame:
    """
    Process all CSV files, score them, and combine results.

    Args:
        csv_files: List of CSV file paths to process

    Returns:
        Combined DataFrame with all scored records
    """
    all_results = []
    total_rows = 0

    for idx, csv_file in enumerate(csv_files, 1):
        logger.info(
            "Processing file %d/%d: %s",
            idx,
            len(csv_files),
            csv_file.name
        )

        try:
            # Read CSV
            df = pd.read_csv(csv_file, low_memory=False)
            logger.info("  Loaded %d rows from %s", len(df), csv_file.name)

            # Score this file
            scored_df = score_customers(df)

            # Add source file metadata
            scored_df['SourceFile'] = csv_file.name

            all_results.append(scored_df)
            total_rows += len(scored_df)

            logger.info(
                "  Scored %d records (total so far: %d)",
                len(scored_df),
                total_rows
            )

        except Exception as e:
            logger.error(
                "Error processing file %s: %s",
                csv_file.name,
                str(e),
                exc_info=True
            )
            raise

    # Combine all results
    if len(all_results) == 1:
        combined_df = all_results[0]
        logger.info("Single file processed: %d records", len(combined_df))
    else:
        logger.info("Combining %d files into single DataFrame...", len(all_results))
        combined_df = pd.concat(all_results, ignore_index=True)
        logger.info("Combined %d total records", len(combined_df))

    # Add processing timestamp
    combined_df['ScoredAt'] = datetime.now()

    return combined_df


def copy_documentation(output_dir: Path) -> None:
    """
    Copy model documentation files to output directory.

    Args:
        output_dir: Path to output directory
    """
    project_root = Path(__file__).parent

    # Copy README.md
    readme_src = project_root / "README.md"
    if readme_src.exists():
        readme_dst = output_dir / "README.md"
        shutil.copy2(readme_src, readme_dst)
        logger.info("Copied README.md to output directory")

    # Copy model conda.yml
    conda_src = project_root / "model" / "conda.yml"
    if conda_src.exists():
        conda_dst = output_dir / "model_conda.yml"
        shutil.copy2(conda_src, conda_dst)
        logger.info("Copied model/conda.yml to output directory")


def write_output(
    combined_df: pd.DataFrame,
    output_dir: Path,
    output_name: str = "churn_scores_combined.csv"
) -> Path:
    """
    Write combined results to CSV file.

    Args:
        combined_df: Combined DataFrame with all scored records
        output_dir: Path to output directory
        output_name: Name of output CSV file

    Returns:
        Path to output CSV file
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / output_name

    logger.info("Writing results to %s...", output_file)
    combined_df.to_csv(output_file, index=False)

    logger.info("Successfully wrote %d records to %s", len(combined_df), output_file)
    return output_file


def print_summary(combined_df: pd.DataFrame) -> None:
    """
    Print summary statistics about the scored data.

    Args:
        combined_df: Combined DataFrame with scored records
    """
    logger.info("=" * 60)
    logger.info("SCORING SUMMARY")
    logger.info("=" * 60)
    logger.info("Total records scored: %d", len(combined_df))

    if 'RiskBand' in combined_df.columns:
        risk_dist = combined_df['RiskBand'].value_counts()
        logger.info("\nRisk Band Distribution:")
        for band, count in risk_dist.items():
            pct = (count / len(combined_df)) * 100
            logger.info("  %s: %d (%.1f%%)", band, count, pct)

    if 'ChurnRiskPct' in combined_df.columns:
        logger.info("\nChurn Risk Statistics:")
        logger.info("  Mean: %.4f", combined_df['ChurnRiskPct'].mean())
        logger.info("  Median: %.4f", combined_df['ChurnRiskPct'].median())
        logger.info("  Min: %.4f", combined_df['ChurnRiskPct'].min())
        logger.info("  Max: %.4f", combined_df['ChurnRiskPct'].max())

    if 'SnapshotDate' in combined_df.columns:
        logger.info("\nDate Range:")
        logger.info("  Earliest: %s", combined_df['SnapshotDate'].min())
        logger.info("  Latest: %s", combined_df['SnapshotDate'].max())

    if 'SourceFile' in combined_df.columns and combined_df['SourceFile'].nunique() > 1:
        logger.info("\nFiles Processed:")
        file_counts = combined_df['SourceFile'].value_counts()
        for filename, count in file_counts.items():
            logger.info("  %s: %d records", filename, count)

    logger.info("=" * 60)


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Score churn prediction model on CSV file(s)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python score_customers.py                      # Score all files in chunks/ folder
  python score_customers.py data/validate.csv     # Score a single file
  python score_customers.py chunks/                # Score all CSVs in chunks/ directory
        """
    )
    parser.add_argument(
        'input_path',
        nargs='?',
        default='chunks',
        help='Path to CSV file or directory containing CSV files (default: chunks/)'
    )
    parser.add_argument(
        '-o', '--output',
        default='outputs/churn_scores_combined.csv',
        help='Output CSV file path (default: outputs/churn_scores_combined.csv)'
    )

    args = parser.parse_args()

    project_root = Path(__file__).parent
    input_path = Path(args.input_path)
    if not input_path.is_absolute():
        input_path = project_root / input_path

    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = project_root / output_path

    output_dir = output_path.parent
    output_filename = output_path.name

    try:
        # Find CSV files to process
        csv_files = find_csv_files(input_path)

        # Process all files
        combined_df = process_files(csv_files)

        # Write output
        output_file = write_output(combined_df, output_dir, output_filename)

        # Copy documentation
        copy_documentation(output_dir)

        # Print summary
        print_summary(combined_df)

        logger.info("\n✓ Scoring completed successfully!")
        logger.info("Output file: %s", output_file)
        logger.info("Output directory: %s", output_dir)

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
