"""
Power BI DAX query execution client.
Uses MSAL for authentication and Power BI REST API.
"""

import logging
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import pandas as pd
import requests
from msal import ConfidentialClientApplication
from tenacity import (
    retry,
    stop_after_attempt,
    retry_if_exception_type,
    RetryCallState,
    before_sleep_log,
    after_log,
)

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


def _wait_for_429_or_exponential(retry_state: RetryCallState) -> float:
    """
    Custom wait function that handles 429 rate limiting with Retry-After header,
    otherwise uses exponential backoff.

    Args:
        retry_state: Tenacity RetryCallState with exception info

    Returns:
        Wait time in seconds
    """
    if retry_state.outcome and retry_state.outcome.failed:
        exception = retry_state.outcome.exception()
        if (
            isinstance(exception, requests.exceptions.HTTPError)
            and exception.response is not None
            and exception.response.status_code == 429
        ):
            retry_after = int(exception.response.headers.get("Retry-After", 60))
            logger.warning(
                "Rate limited (429). Retrying after %d seconds (attempt %d/%d)...",
                retry_after,
                retry_state.attempt_number,
                MAX_RETRIES
            )
            return float(retry_after)

    # Default exponential backoff for other retries
    wait_time = min(BASE_RETRY_DELAY * (2 ** (retry_state.attempt_number - 1)), 60)
    return wait_time


def _should_retry_exception(exception: BaseException) -> bool:
    """
    Determine if exception should be retried.

    Retries:
    - Network errors (Timeout, ConnectionError)
    - HTTP 429 (rate limiting)
    - HTTP 5xx (server errors)

    Does not retry:
    - HTTP 4xx client errors (except 429)
    - Other RequestException subtypes (checked after HTTPError)
    """
    # Handle HTTP errors first (HTTPError is a subclass of RequestException)
    if isinstance(exception, requests.exceptions.HTTPError):
        if exception.response is None:
            return False
        status_code = exception.response.status_code
        # Retry rate limiting and server errors
        return status_code == 429 or 500 <= status_code < 600

    # Retry network/connection errors (but not HTTPError, already handled above)
    if isinstance(exception, (
        requests.exceptions.Timeout,
        requests.exceptions.ConnectionError,
    )):
        return True

    # Don't retry other RequestException subtypes (e.g., TooManyRedirects)
    # unless they're the specific types we want to retry
    return False


# Configure retry decorator for transient errors per error-handling.md
retry_transient = retry(
    stop=stop_after_attempt(MAX_RETRIES),
    wait=_wait_for_429_or_exponential,
    retry=retry_if_exception_type(Exception)(_should_retry_exception),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    after=after_log(logger, logging.ERROR),
    reraise=True,
)


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


@retry_transient
def get_access_token() -> str:
    """
    Get access token for Power BI using service principal.

    Returns:
        Access token string

    Raises:
        RuntimeError: If token acquisition fails
    """
    app = ConfidentialClientApplication(
        client_id=config.PBI_CLIENT_ID,
        client_credential=config.PBI_CLIENT_SECRET,
        authority=f"https://login.microsoftonline.com/{config.PBI_TENANT_ID}"
    )

    scope = "https://analysis.windows.net/powerbi/api/.default"

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

    return str(access_token)


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

    # Build URL - prefer workspace-scoped endpoint if provided
    # Service principals may need explicit workspace context
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

    @retry_transient
    def _make_request() -> pd.DataFrame:
        logger.debug(
            "Executing DAX query against dataset %s (query length: %d characters)",
            dataset_id,
            len(query)
        )

        response = requests.post(url, headers=headers, json=payload, timeout=timeout)

        # Handle rate limiting explicitly (will be caught by retry decorator)
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

        # Check if we hit the row limit (indicates need for pagination)
        row_count = len(df)
        if row_count >= MAX_ROWS_PER_QUERY - 100:  # Allow small buffer
            logger.warning(
                "Query returned %d rows, close to API limit of %d. "
                "Consider using pagination for larger datasets.",
                row_count,
                MAX_ROWS_PER_QUERY
            )

        return df

    # Per error-handling.md: Retry transient errors
    return _make_request()


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
        from datetime import datetime, timedelta

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
