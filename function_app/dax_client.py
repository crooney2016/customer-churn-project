"""
Power BI DAX query execution client.
Uses MSAL for authentication and Power BI REST API.
"""

import logging
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, TypeVar

import pandas as pd
import requests
from msal import ConfidentialClientApplication

from .config import config

# Configure logging per logging.md
logger = logging.getLogger(__name__)

# Constants per python.md
DEFAULT_DAX_TIMEOUT = 300  # 5 minutes
MAX_DAX_TIMEOUT = 600  # 10 minutes
MAX_ROWS_PER_QUERY = 100000  # Power BI API limit per power-bi.md
MAX_VALUES_PER_QUERY = 1000000  # Power BI API limit per power-bi.md
MAX_RETRIES = 3  # Per error-handling.md
BASE_RETRY_DELAY = 1.0  # Base delay for exponential backoff

# Required identifier columns per dax.md
REQUIRED_IDENTIFIER_COLUMNS = [
    "CustomerId",
    "AccountName",
    "Segment",
    "CostCenter",
    "SnapshotDate"
]

# Expected column count per dax.md (77 columns: 5 identifiers + 3 dates + ~69 features)
EXPECTED_COLUMN_COUNT = 77
MIN_COLUMN_COUNT = 70  # Allow some variance
MAX_COLUMN_COUNT = 85  # Warn if too many

T = TypeVar('T')


def retry_with_backoff(
    func: Callable[[], T],
    max_attempts: int = MAX_RETRIES,
    base_delay: float = BASE_RETRY_DELAY,
    operation_name: str = "operation"
) -> T:
    """
    Retry function with exponential backoff per error-handling.md.

    Args:
        func: Function to retry
        max_attempts: Maximum number of retry attempts (default: 3)
        base_delay: Base delay in seconds for exponential backoff (default: 1.0)
        operation_name: Name of operation for logging context

    Returns:
        Result of func()

    Raises:
        RuntimeError: If max retries exceeded
        Exception: Re-raises last exception if all retries fail
    """
    last_exception: Optional[Exception] = None

    for attempt in range(max_attempts):
        try:
            return func()
        except requests.exceptions.HTTPError as e:
            # Handle rate limiting (429) separately - check HTTPError first
            # since it's a subclass of RequestException
            if e.response is not None and e.response.status_code == 429:
                retry_after = int(e.response.headers.get("Retry-After", 60))
                if attempt == max_attempts - 1:
                    logger.error(
                        "Rate limited and max retries exceeded for %s",
                        operation_name,
                        exc_info=True
                    )
                    raise

                logger.warning(
                    "Rate limited (429) for %s. Retrying after %d seconds (attempt %d/%d)...",
                    operation_name,
                    retry_after,
                    attempt + 1,
                    max_attempts
                )
                time.sleep(retry_after)
                last_exception = e
            else:
                # Non-retryable HTTP errors (400, 401, 403, etc.)
                logger.error(
                    "Non-retryable HTTP error for %s: %s",
                    operation_name,
                    str(e),
                    exc_info=True
                )
                raise
        except (
            requests.exceptions.Timeout,
            requests.exceptions.ConnectionError,
            requests.exceptions.RequestException
        ) as e:
            last_exception = e
            if attempt == max_attempts - 1:
                logger.error(
                    "Max retries (%d) exceeded for %s: %s",
                    max_attempts,
                    operation_name,
                    str(e),
                    exc_info=True
                )
                raise

            delay = base_delay * (2 ** attempt)
            logger.warning(
                "Attempt %d/%d failed for %s: %s. Retrying in %.1f seconds...",
                attempt + 1,
                max_attempts,
                operation_name,
                str(e),
                delay
            )
            time.sleep(delay)

    if last_exception:
        raise RuntimeError(f"Max retries exceeded for {operation_name}") from last_exception

    raise RuntimeError(f"Unexpected retry loop exit for {operation_name}")


def normalize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """
    Remove brackets from column names per dax.md rules.

    DAX returns: {"[CustomerId]": "001"}
    Python expects: {"CustomerId": "001"}

    Args:
        df: DataFrame with bracketed column names

    Returns:
        DataFrame with normalized column names (brackets removed)
    """
    df.columns = [
        col.strip('[]') if isinstance(col, str) else col
        for col in df.columns
    ]
    return df


def validate_dax_columns(df: pd.DataFrame) -> None:
    """
    Validate DAX output matches expected schema per dax.md rules.

    Args:
        df: DataFrame from DAX query

    Raises:
        ValueError: If required columns are missing or column count is unexpected
    """
    # Normalize column names first (remove brackets)
    df_normalized = df.copy()
    df_normalized.columns = [
        col.strip('[]') if isinstance(col, str) else col
        for col in df_normalized.columns
    ]

    # Check required identifier columns per dax.md
    missing = [
        col for col in REQUIRED_IDENTIFIER_COLUMNS
        if col not in df_normalized.columns
    ]

    if missing:
        error_msg = (
            f"Missing required columns: {missing}. "
            f"Found columns: {list(df_normalized.columns)[:10]}..."
        )
        logger.error(error_msg)
        raise ValueError(error_msg)

    # Per dax.md: Should have ~77 total columns (5 identifiers + 3 dates + ~69 features)
    column_count = len(df_normalized.columns)
    logger.info(
        "DAX query returned %d columns, %d rows",
        column_count,
        len(df)
    )

    if column_count < MIN_COLUMN_COUNT:
        logger.warning(
            "Expected ~%d columns per dax.md, got %d. This may indicate a schema issue.",
            EXPECTED_COLUMN_COUNT,
            column_count
        )
    elif column_count > MAX_COLUMN_COUNT:
        logger.warning(
            "Expected ~%d columns per dax.md, got %d. This may indicate a schema change.",
            EXPECTED_COLUMN_COUNT,
            column_count
        )


def get_access_token() -> str:
    """
    Get access token for Power BI using service principal.

    Returns:
        Access token string

    Raises:
        RuntimeError: If token acquisition fails
    """
    logger.info("Acquiring Power BI access token...")

    app = ConfidentialClientApplication(
        client_id=config.PBI_CLIENT_ID,
        client_credential=config.PBI_CLIENT_SECRET,
        authority=f"https://login.microsoftonline.com/{config.PBI_TENANT_ID}"
    )

    scope = "https://analysis.windows.net/powerbi/api/.default"

    def _acquire_token() -> str:
        result: Optional[Dict[str, Any]] = app.acquire_token_for_client(scopes=[scope])

        if result is None:
            error_msg = "Failed to acquire token: No response from authentication service"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

        if not isinstance(result, dict):
            error_msg = "Failed to acquire token: Invalid response type"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

        if "access_token" not in result:
            error_desc: str = str(result.get('error_description', 'Unknown error'))
            error_msg = f"Failed to acquire token: {error_desc}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

        access_token: Any = result.get("access_token")
        if not access_token or not isinstance(access_token, str):
            error_msg = "Failed to acquire token: access_token is missing or invalid"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

        logger.info("Access token acquired successfully")
        return str(access_token)

    # Per error-handling.md: Retry transient errors
    return retry_with_backoff(_acquire_token, operation_name="token acquisition")


def _execute_single_dax_query(
    query: str,
    dataset_id: str,
    timeout: int = DEFAULT_DAX_TIMEOUT,
    workspace_id: Optional[str] = None
) -> pd.DataFrame:
    """
    Execute a single DAX query against Power BI dataset (internal helper).

    Args:
        query: DAX query string
        dataset_id: Power BI dataset ID
        timeout: Request timeout in seconds
        workspace_id: Optional workspace ID (uses default workspace if None)

    Returns:
        pandas DataFrame with query results

    Raises:
        ValueError: If query returns no results or invalid response
        requests.exceptions.HTTPError: If API request fails
    """
    access_token = get_access_token()

    # Build URL with or without workspace per power-bi.md
    if workspace_id:
        url = (
            f"https://api.powerbi.com/v1.0/myorg/groups/{workspace_id}"
            f"/datasets/{dataset_id}/executeQueries"
        )
    else:
        url = f"https://api.powerbi.com/v1.0/myorg/datasets/{dataset_id}/executeQueries"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    payload = {
        "queries": [
            {
                "query": query
            }
        ],
        "serializerSettings": {
            "includeNulls": True
        }
    }

    def _make_request() -> pd.DataFrame:
        logger.debug(
            "Executing DAX query against dataset %s (query length: %d characters)",
            dataset_id,
            len(query)
        )

        response = requests.post(url, headers=headers, json=payload, timeout=timeout)

        # Handle rate limiting explicitly
        if response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", 60))
            error_msg = (
                f"Rate limited (429) for dataset {dataset_id}. "
                f"Retry-After: {retry_after} seconds"
            )
            logger.warning(error_msg)
            raise requests.exceptions.HTTPError(error_msg, response=response)

        response.raise_for_status()
        result = response.json()

        if "results" not in result or len(result["results"]) == 0:
            error_msg = (
                f"No results returned from DAX query. "
                f"Dataset: {dataset_id}, Query length: {len(query)} characters"
            )
            logger.error(error_msg)
            raise ValueError(error_msg)

        # Parse results into DataFrame
        tables = result["results"][0].get("tables", [])
        if not tables:
            error_msg = (
                f"No tables in DAX query results. "
                f"Dataset: {dataset_id}, Response keys: {list(result.keys())}"
            )
            logger.error(error_msg)
            raise ValueError(error_msg)

        # Convert to DataFrame
        table = tables[0]
        rows = table.get("rows", [])

        if not rows:
            logger.info("DAX query returned empty result set")
            return pd.DataFrame()

        # Extract column names
        columns = [col["name"] for col in table.get("columns", [])]

        # Construct DataFrame from dict for better type safety
        if rows and isinstance(rows[0], dict):
            # Rows are dicts - use directly
            df = pd.DataFrame(rows)
        else:
            # Rows are lists - convert to dict first
            df = pd.DataFrame({
                col: [row[i] for row in rows]
                for i, col in enumerate(columns)
            })

        # Normalize column names (remove brackets per dax.md)
        df = normalize_column_names(df)

        row_count = len(df)
        column_count = len(df.columns)
        logger.info(
            "DAX query returned %d rows with %d columns",
            row_count,
            column_count
        )

        # Check if we hit the row limit (indicates need for pagination)
        if row_count >= MAX_ROWS_PER_QUERY - 100:  # Allow small buffer
            logger.warning(
                "Query returned %d rows, close to API limit of %d. "
                "Consider using pagination for larger datasets.",
                row_count,
                MAX_ROWS_PER_QUERY
            )

        return df

    # Per error-handling.md: Retry transient errors
    return retry_with_backoff(
        _make_request,
        operation_name=f"DAX query execution (dataset: {dataset_id})"
    )


def execute_dax_query(
    query: str,
    dataset_id: Optional[str] = None,
    timeout: int = DEFAULT_DAX_TIMEOUT,
    workspace_id: Optional[str] = None,
    validate_columns: bool = True
) -> pd.DataFrame:
    """
    Execute DAX query against Power BI dataset with pagination support.

    Handles Power BI API limits (100k rows or 1M values per query) by executing
    a single query. For datasets larger than the limit, use execute_dax_query_paginated()
    with appropriate chunking strategy.

    Args:
        query: DAX query string
        dataset_id: Power BI dataset ID (defaults to config.PBI_DATASET_ID)
        timeout: Request timeout in seconds (default: 300)
        workspace_id: Optional workspace ID (uses default workspace if None)
        validate_columns: Whether to validate column schema per dax.md (default: True)

    Returns:
        pandas DataFrame with query results (columns normalized, brackets removed)

    Raises:
        ValueError: If query returns no results, invalid response, or schema validation fails
        RuntimeError: If token acquisition or request fails after retries
    """
    if dataset_id is None:
        dataset_id = config.PBI_DATASET_ID

    logger.info(
        "Executing DAX query against dataset %s (timeout: %ds)",
        dataset_id,
        timeout
    )

    df = _execute_single_dax_query(query, dataset_id, timeout, workspace_id)

    # Validate columns per dax.md if requested
    if validate_columns and len(df) > 0:
        validate_dax_columns(df)

    return df


def execute_dax_query_paginated(
    base_query: str,
    chunking_strategy: Callable[[str, int], str],
    dataset_id: Optional[str] = None,
    timeout: int = DEFAULT_DAX_TIMEOUT,
    workspace_id: Optional[str] = None,
    validate_columns: bool = True
) -> pd.DataFrame:
    """
    Execute DAX query with pagination support for datasets exceeding 100k rows.

    Since Power BI API doesn't support skip/top pagination, this function uses
    a chunking strategy to split the query into multiple smaller queries that
    each stay under the 100k row limit.

    Args:
        base_query: Base DAX query string (will be modified by chunking_strategy)
        chunking_strategy: Function that takes (base_query, chunk_index) and returns
                          modified query for that chunk. Should add filters to limit
                          results (e.g., date ranges, customer ID ranges).
        dataset_id: Power BI dataset ID (defaults to config.PBI_DATASET_ID)
        timeout: Request timeout in seconds per chunk (default: 300)
        workspace_id: Optional workspace ID (uses default workspace if None)
        validate_columns: Whether to validate column schema per dax.md (default: True)

    Returns:
        Combined pandas DataFrame with all chunk results

    Raises:
        ValueError: If query returns no results, invalid response, or schema validation fails
        RuntimeError: If token acquisition or request fails after retries

    Example:
        ```python
        def chunk_by_date_range(base_query: str, chunk_index: int) -> str:
            # Add date filter for this chunk
            start_date = datetime(2024, 1, 1) + timedelta(days=chunk_index * 30)
            end_date = start_date + timedelta(days=30)
            return (
                f"{base_query} WHERE [SnapshotDate] >= "
                f"DATE({start_date.year}, {start_date.month}, {start_date.day}) "
                f"AND [SnapshotDate] < "
                f"DATE({end_date.year}, {end_date.month}, {end_date.day})"
            )

        df = execute_dax_query_paginated(
            base_query="EVALUATE churn_features",
            chunking_strategy=chunk_by_date_range,
            dataset_id="abc-123"
        )
        ```
    """
    if dataset_id is None:
        dataset_id = config.PBI_DATASET_ID

    logger.info(
        "Executing paginated DAX query against dataset %s",
        dataset_id
    )

    all_chunks: List[pd.DataFrame] = []
    chunk_index = 0
    total_rows = 0

    while True:
        logger.info("Executing chunk %d...", chunk_index + 1)

        # Get chunked query
        chunked_query = chunking_strategy(base_query, chunk_index)

        try:
            # Execute chunk
            chunk_df = _execute_single_dax_query(
                chunked_query,
                dataset_id,
                timeout,
                workspace_id
            )

            if len(chunk_df) == 0:
                logger.info("Chunk %d returned 0 rows, stopping pagination", chunk_index + 1)
                break

            all_chunks.append(chunk_df)
            total_rows += len(chunk_df)
            logger.info(
                "Chunk %d completed: %d rows (total so far: %d)",
                chunk_index + 1,
                len(chunk_df),
                total_rows
            )

            # If chunk is smaller than limit, we've likely reached the end
            if len(chunk_df) < MAX_ROWS_PER_QUERY - 1000:
                logger.info(
                    "Chunk %d returned %d rows (< %d), assuming last chunk",
                    chunk_index + 1,
                    len(chunk_df),
                    MAX_ROWS_PER_QUERY
                )
                break

            chunk_index += 1

        except ValueError as e:
            # If chunk returns no results, stop pagination
            if "No results returned" in str(e):
                logger.info("Chunk %d returned no results, stopping pagination", chunk_index + 1)
                break
            raise

    if not all_chunks:
        logger.warning("No chunks returned data")
        return pd.DataFrame()

    # Combine all chunks
    logger.info("Combining %d chunks into single DataFrame...", len(all_chunks))
    combined_df = pd.concat(all_chunks, ignore_index=True)

    logger.info(
        "Pagination complete: %d total rows from %d chunks",
        len(combined_df),
        len(all_chunks)
    )

    # Validate columns per dax.md if requested
    if validate_columns and len(combined_df) > 0:
        validate_dax_columns(combined_df)

    return combined_df


def load_dax_query_from_file(query_name: str = "churn_features") -> str:
    """
    Load DAX query from dax/ directory files.

    Args:
        query_name: Name of the DAX query file (without .dax extension).
                   Options: "churn_features" or "churn_features_dax_multimonth"
                   Defaults to "churn_features"

    Returns:
        DAX query string from the file

    Raises:
        FileNotFoundError: If the DAX query file doesn't exist
    """
    logger.info("Loading DAX query from file: %s", query_name)

    # Get project root (parent of function_app directory)
    project_root = Path(__file__).parent.parent
    query_path = project_root / "dax" / f"{query_name}.dax"

    if not query_path.exists():
        error_msg = (
            f"DAX query file not found: {query_path}. "
            f"Available options: churn_features, churn_features_dax_multimonth"
        )
        logger.error(error_msg)
        raise FileNotFoundError(error_msg)

    query_text = query_path.read_text(encoding="utf-8")
    logger.info(
        "DAX query loaded from %s (%d characters)",
        query_path,
        len(query_text)
    )

    return query_text


def get_dax_query_from_dataset(query_name: Optional[str] = None) -> str:
    """
    Get DAX query by loading from dax/ directory file.

    This is a convenience wrapper around load_dax_query_from_file.

    Args:
        query_name: Name of the DAX query file (without .dax extension).
                   If None, uses config.DAX_QUERY_NAME or defaults to "churn_features"

    Returns:
        DAX query string from the file
    """
    if query_name is None:
        query_name = config.DAX_QUERY_NAME or "churn_features"

    return load_dax_query_from_file(query_name)
