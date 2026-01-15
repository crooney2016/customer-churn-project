"""
Split a large CSV file into smaller chunks for Azure ML batch processing.
Usage: python scripts/split_csv.py input.csv --rows 50000 --output-dir data/
"""

import argparse
import os
from pathlib import Path

import pandas as pd


def split_csv(input_file, rows_per_file=50000, output_dir="data"):
    """Split a CSV file into smaller chunks."""

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    # Read the full CSV
    print(f"Reading {input_file}...")
    df = pd.read_csv(input_file, low_memory=False)
    total_rows = len(df)
    print(f"Total rows: {total_rows}")

    # Calculate number of chunks
    num_chunks = (total_rows // rows_per_file) + (1 if total_rows % rows_per_file else 0)
    print(f"Splitting into {num_chunks} files of up to {rows_per_file} rows each...")

    # Get base filename
    base_name = Path(input_file).stem

    # Split and save
    for i in range(num_chunks):
        start_idx = i * rows_per_file
        end_idx = min((i + 1) * rows_per_file, total_rows)

        chunk = df.iloc[start_idx:end_idx]
        output_file = os.path.join(output_dir, f"{base_name}_part{i+1:03d}.csv")

        chunk.to_csv(output_file, index=False)
        print(f"  Wrote {output_file} ({len(chunk)} rows)")

    print(f"\nDone! {num_chunks} files created in {output_dir}/")
    return num_chunks


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Split CSV into smaller chunks")
    parser.add_argument("input_file", help="Input CSV file path")
    parser.add_argument(
        "--rows",
        type=int,
        default=50000,
        help="Rows per output file (default: 50000)"
    )
    parser.add_argument(
        "--output-dir",
        default="data",
        help="Output directory (default: data/)"
    )

    args = parser.parse_args()
    split_csv(args.input_file, args.rows, args.output_dir)
