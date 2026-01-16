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
import os
import sys
import warnings
from pathlib import Path
from typing import Optional

# Suppress urllib3 SSL warnings
os.environ['PYTHONWARNINGS'] = 'ignore::UserWarning:urllib3'
warnings.filterwarnings("ignore", category=UserWarning, module="urllib3")

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

# Configure logging - suppress verbose library logs
logging.basicConfig(
    level=logging.WARNING,  # Only show warnings and errors by default
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)
# Set our logger to INFO for user-facing messages
logger.setLevel(logging.INFO)


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
        print(f"✗ Missing configuration: {', '.join(missing)}")
        print("  Please set these in your .env file")
        sys.exit(1)


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
            print(f"✗ Query file not found: {query_file}")
            sys.exit(1)
        return query_file.read_text(encoding="utf-8")

    if query_name:
        return load_dax_query_from_file(query_name)

    # Default: use config or default query
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
        print("=" * 60)
        print("DAX Query Test")
        print("=" * 60)
        validate_config()
        print("✓ Configuration validated")

        # Load query
        query = load_query(args.query_name, args.file)
        print(f"✓ Query loaded ({len(query)} characters)")

        # Get dataset ID
        dataset_id = args.dataset_id or config.PBI_DATASET_ID
        workspace_id = args.workspace_id or getattr(config, "PBI_WORKSPACE_ID", None)

        print(f"✓ Dataset: {dataset_id}")
        if workspace_id:
            print(f"✓ Workspace: {workspace_id}")

        # Execute query
        print("\nExecuting query...")
        df = execute_dax_query(
            query=query,
            dataset_id=dataset_id,
            timeout=args.timeout,
            workspace_id=workspace_id,
            validate_columns=not args.no_validate
        )

        # Display results
        print("\n" + "=" * 60)
        print("Query Results")
        print("=" * 60)
        print(f"✓ Rows: {len(df)}, Columns: {len(df.columns)}")

        if len(df) > 0:
            print(f"\nSample rows (first {args.sample_rows}):")
            print(df.head(args.sample_rows).to_string())

            print("\n" + "=" * 60)
            print("✓ Query executed successfully!")
            print("=" * 60)
        else:
            print("⚠ Query returned 0 rows")

    except KeyboardInterrupt:
        print("\n✗ Interrupted by user")
        sys.exit(1)
    except requests.exceptions.HTTPError as e:
        # Extract error details from HTTP response
        status_code = None
        error_code = "Unknown"
        
        if hasattr(e, 'response') and e.response is not None:
            status_code = e.response.status_code
            try:
                error_json = e.response.json()
                error_code = error_json.get("error", {}).get("code", "Unknown")
            except (ValueError, KeyError, AttributeError, TypeError):
                pass
        
        # Extract status code from error message if not in response
        if status_code is None:
            import re
            match = re.search(r'(\d{3})', str(e))
            status_code = match.group(1) if match else "Unknown"
        
        print(f"\n✗ Error: {status_code} {error_code}")
        print(f"  Endpoint: executeQueries")
        sys.exit(1)
    except (ValueError, RuntimeError) as e:
        print(f"\n✗ Error: {type(e).__name__}")
        print(f"  Reason: {str(e)}")
        sys.exit(1)
    except requests.exceptions.RequestException as e:
        print(f"\n✗ Network Error: {type(e).__name__}")
        print(f"  Reason: {str(e)}")
        sys.exit(1)
    except Exception as e:  # pylint: disable=broad-exception-caught
        print(f"\n✗ Unexpected error: {type(e).__name__}")
        print(f"  Reason: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
