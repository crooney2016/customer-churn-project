#!/usr/bin/env python3
"""
Test script for executing DAX queries using dax_client.

Usage:
    python scripts/test_dax_query.py <query_name>
    python scripts/test_dax_query.py churn_features
    python scripts/test_dax_query.py churn_features_dax_multimonth

Or with a custom query file:
    python scripts/test_dax_query.py --file path/to/query.dax

The script will:
1. Load environment variables from .env file
2. Load the DAX query (from dax/ directory or custom file)
3. Execute the query against Power BI
4. Display results summary and sample rows
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional

import requests

# Add function_app to path so we can import it
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# pylint: disable=wrong-import-position
from function_app.config import config
from function_app.dax_client import (
    execute_dax_query,
    load_dax_query_from_file,
    get_dax_query_from_dataset
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def validate_config() -> None:
    """Validate that required Power BI configuration is present."""
    required_pbi_config = [
        "PBI_TENANT_ID",
        "PBI_CLIENT_ID",
        "PBI_CLIENT_SECRET",
        "PBI_DATASET_ID",
    ]

    missing = []
    for key in required_pbi_config:
        value = getattr(config, key)
        if not value:
            missing.append(key)

    if missing:
        logger.error("Missing required Power BI configuration: %s", ", ".join(missing))
        logger.error("Please set these in your .env file")
        sys.exit(1)

    logger.info("Configuration validated successfully")


def load_query(query_name: Optional[str] = None, query_file: Optional[Path] = None) -> str:
    """
    Load DAX query from file or query name.

    Args:
        query_name: Name of query file in dax/ directory (without .dax extension)
        query_file: Path to custom DAX query file

    Returns:
        DAX query string
    """
    if query_file:
        if not query_file.exists():
            logger.error("Query file not found: %s", query_file)
            sys.exit(1)
        logger.info("Loading query from file: %s", query_file)
        return query_file.read_text(encoding="utf-8")

    if query_name:
        logger.info("Loading query: %s", query_name)
        return load_dax_query_from_file(query_name)

    # Default: use config or default query
    logger.info("Using default query from config")
    return get_dax_query_from_dataset()


def main() -> None:
    """Main function to execute DAX query test."""
    parser = argparse.ArgumentParser(
        description="Test DAX query execution against Power BI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Use query name from dax/ directory
  python scripts/test_dax_query.py churn_features

  # Use custom query file
  python scripts/test_dax_query.py --file /path/to/query.dax

  # Use default query from config
  python scripts/test_dax_query.py
        """
    )

    parser.add_argument(
        "query_name",
        nargs="?",
        help="Name of DAX query file in dax/ directory (without .dax extension). "
             "Options: churn_features, churn_features_dax_multimonth"
    )

    parser.add_argument(
        "--file",
        type=Path,
        help="Path to custom DAX query file"
    )

    parser.add_argument(
        "--dataset-id",
        help="Override dataset ID from config"
    )

    parser.add_argument(
        "--workspace-id",
        help="Override workspace ID from config (optional)"
    )

    parser.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="Request timeout in seconds (default: 300)"
    )

    parser.add_argument(
        "--no-validate",
        action="store_true",
        help="Skip column validation"
    )

    parser.add_argument(
        "--sample-rows",
        type=int,
        default=5,
        help="Number of sample rows to display (default: 5)"
    )

    args = parser.parse_args()

    try:
        # Validate configuration
        logger.info("=" * 60)
        logger.info("DAX Query Test Script")
        logger.info("=" * 60)
        validate_config()

        # Load query
        query = load_query(args.query_name, args.file)
        logger.info("Query loaded: %d characters", len(query))
        logger.debug("Query preview: %s...", query[:200])

        # Get dataset ID
        dataset_id = args.dataset_id or config.PBI_DATASET_ID
        workspace_id = args.workspace_id or getattr(config, "PBI_WORKSPACE_ID", None)

        logger.info("Executing query against dataset: %s", dataset_id)
        if workspace_id:
            logger.info("Using workspace: %s", workspace_id)

        # Execute query
        df = execute_dax_query(
            query=query,
            dataset_id=dataset_id,
            timeout=args.timeout,
            workspace_id=workspace_id,
            validate_columns=not args.no_validate
        )

        # Display results
        logger.info("=" * 60)
        logger.info("Query Results")
        logger.info("=" * 60)
        logger.info("Rows returned: %d", len(df))
        logger.info("Columns: %d", len(df.columns))

        if len(df) > 0:
            logger.info("\nColumn names:")
            for i, col in enumerate(df.columns, 1):
                logger.info("  %d. %s", i, col)

            logger.info("\nSample rows (first %d):", args.sample_rows)
            logger.info("\n%s", df.head(args.sample_rows).to_string())

            # Show data types
            logger.info("\nData types:")
            logger.info("\n%s", df.dtypes.to_string())

            # Show summary statistics for numeric columns
            numeric_cols = df.select_dtypes(include=['number']).columns
            if len(numeric_cols) > 0:
                logger.info("\nSummary statistics (numeric columns):")
                logger.info("\n%s", df[numeric_cols].describe().to_string())

            logger.info("\n%s", "=" * 60)
            logger.info("Query executed successfully!")
            logger.info("=" * 60)
        else:
            logger.warning("Query returned 0 rows")

    except KeyboardInterrupt:
        logger.info("\nInterrupted by user")
        sys.exit(1)
    except (ValueError, RuntimeError, requests.exceptions.RequestException) as e:
        # Catch specific exceptions from dax_client and requests
        logger.error("Error executing query: %s", str(e), exc_info=True)
        sys.exit(1)
    except Exception as e:  # pylint: disable=broad-exception-caught
        # Catch any other unexpected errors to provide user-friendly message
        logger.error("Unexpected error executing query: %s", str(e), exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
