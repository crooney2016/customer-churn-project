#!/usr/bin/env python3
"""
Local script to score all chunk files and combine into one output file.

Processes all CSV files in the chunks/ folder, scores them using the churn model,
and combines results into a single CSV file in the outputs/ directory.
Includes model documentation files in the output directory.

Usage:
    python score_chunks.py

Output:
    outputs/churn_scores_combined.csv - All scored records from all chunks
    outputs/README.md - Project documentation
    outputs/model_conda.yml - Model environment configuration
"""

import logging
import shutil
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

# Add function_app to path for imports
# Import scorer directly to avoid SQL dependencies
sys.path.insert(0, str(Path(__file__).parent / "function_app"))
from scorer import score_customers  # pylint: disable=import-error

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def find_chunk_files(chunks_dir: Path) -> list:
    """
    Find all CSV files in the chunks directory and sort them numerically.

    Args:
        chunks_dir: Path to the chunks directory

    Returns:
        Sorted list of CSV file paths
    """
    if not chunks_dir.exists():
        raise FileNotFoundError(f"Chunks directory not found: {chunks_dir}")

    csv_files = sorted(
        chunks_dir.glob("*.csv"),
        key=lambda x: int(''.join(filter(str.isdigit, x.stem)) or '0')
    )

    if not csv_files:
        raise FileNotFoundError(f"No CSV files found in {chunks_dir}")

    logger.info("Found %d chunk files to process", len(csv_files))
    return csv_files


def process_chunks(chunks_dir: Path, output_dir: Path) -> pd.DataFrame:
    """
    Process all chunk files, score them, and combine results.

    Args:
        chunks_dir: Path to directory containing chunk CSV files
        output_dir: Path to output directory

    Returns:
        Combined DataFrame with all scored records
    """
    chunk_files = find_chunk_files(chunks_dir)
    all_results = []
    total_rows = 0

    for idx, chunk_file in enumerate(chunk_files, 1):
        logger.info(
            "Processing chunk %d/%d: %s",
            idx,
            len(chunk_files),
            chunk_file.name
        )

        try:
            # Read chunk
            df = pd.read_csv(chunk_file, low_memory=False)
            logger.info("  Loaded %d rows from %s", len(df), chunk_file.name)

            # Score this chunk
            scored_df = score_customers(df)

            # Add source file metadata
            scored_df['SourceFile'] = chunk_file.name

            all_results.append(scored_df)
            total_rows += len(scored_df)

            logger.info(
                "  Scored %d records (total so far: %d)",
                len(scored_df),
                total_rows
            )

        except Exception as e:
            logger.error(
                "Error processing chunk %s: %s",
                chunk_file.name,
                str(e),
                exc_info=True
            )
            raise

    # Combine all results
    logger.info("Combining %d chunks into single DataFrame...", len(all_results))
    combined_df = pd.concat(all_results, ignore_index=True)

    # Add processing timestamp
    combined_df['ScoredAt'] = datetime.now()

    logger.info("Combined %d total records", len(combined_df))
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


def write_output(combined_df: pd.DataFrame, output_dir: Path) -> Path:
    """
    Write combined results to CSV file.

    Args:
        combined_df: Combined DataFrame with all scored records
        output_dir: Path to output directory

    Returns:
        Path to output CSV file
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "churn_scores_combined.csv"

    logger.info("Writing combined results to %s...", output_file)
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

    logger.info("=" * 60)


def main():
    """Main entry point for the script."""
    project_root = Path(__file__).parent
    chunks_dir = project_root / "chunks"
    output_dir = project_root / "outputs"

    try:
        # Process all chunks
        combined_df = process_chunks(chunks_dir, output_dir)

        # Write output
        output_file = write_output(combined_df, output_dir)

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
