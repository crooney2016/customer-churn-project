#!/usr/bin/env python3
"""
One-time script for loading historical churn scores (2023-2025).
Uses same scoring and SQL logic as the Function App.
"""

import sys
import os
import pandas as pd
from pathlib import Path
from datetime import datetime
import logging

# Add function_app to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from function_app.scorer import score_customers
from function_app.sql_client import insert_churn_scores
from function_app.config import config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def load_historical_data(input_path: str, batch_size: int = 1000) -> None:
    """
    Load and score historical data in batches.
    
    Args:
        input_path: Path to CSV file with historical data
        batch_size: Number of rows to process per batch
    """
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")
    
    # Validate configuration
    try:
        config.validate()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        logger.error("Please set required environment variables or create .env file")
        sys.exit(1)
    
    logger.info(f"Loading historical data from {input_path}...")
    
    # Read CSV in chunks for memory efficiency
    total_rows = 0
    total_scored = 0
    
    try:
        for chunk_num, chunk_df in enumerate(pd.read_csv(input_path, chunksize=batch_size), 1):
            logger.info(f"Processing batch {chunk_num} ({len(chunk_df)} rows)...")
            
            try:
                # Score this batch
                scored_df = score_customers(chunk_df)
                
                # Write to SQL
                rows_written = insert_churn_scores(scored_df)
                
                total_rows += len(chunk_df)
                total_scored += rows_written
                
                logger.info(f"Batch {chunk_num} completed: {rows_written} rows written")
                
            except Exception as e:
                logger.error(f"Error processing batch {chunk_num}: {str(e)}")
                logger.error("Continuing with next batch...")
                continue
        
        logger.info(f"Backfill completed successfully!")
        logger.info(f"Total rows processed: {total_rows}")
        logger.info(f"Total rows written: {total_scored}")
        
    except Exception as e:
        logger.error(f"Backfill failed: {str(e)}")
        raise


def main():
    if len(sys.argv) != 2:
        print("Usage: python local_backfill.py <historical_data.csv>")
        print("\nExample:")
        print("  python local_backfill.py data/historical_churn_data.csv")
        sys.exit(1)
    
    input_path = sys.argv[1]
    
    try:
        load_historical_data(input_path)
    except Exception as e:
        logger.error(f"Backfill failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
