"""
Azure Blob Storage client for churn prediction pipeline.
Comprehensive utility with CRUD operations, directory management,
and file workflow operations (copy, move, delete, list).
"""

import io
import logging
from typing import Any, Dict, List, Optional

import pandas as pd
from azure.core.exceptions import ResourceNotFoundError
from azure.storage.blob import (  # pylint: disable=no-name-in-module
    BlobClient,
    BlobProperties,
    BlobServiceClient,
    ContainerClient,
)
from tenacity import (
    retry,
    stop_after_attempt,
    retry_if_exception_type,
    wait_exponential,
    before_sleep_log,
    after_log,
)

from .config import config

# Configure logging per logging.md
logger = logging.getLogger(__name__)

# Constants
MAX_RETRIES = 3
BASE_RETRY_DELAY = 1.0
DEFAULT_CONTAINER = "churn-feature-data"
PROCESSED_FOLDER = "processed"
ERROR_FOLDER = "error"

# Retry decorator for transient errors
retry_transient = retry(
    stop=stop_after_attempt(MAX_RETRIES),
    wait=wait_exponential(multiplier=BASE_RETRY_DELAY, min=BASE_RETRY_DELAY, max=60),
    retry=retry_if_exception_type((
        ConnectionError,
        TimeoutError,
        IOError,
    )),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    after=after_log(logger, logging.ERROR),
    reraise=True,
)


def _get_blob_service_client() -> BlobServiceClient:
    """
    Get authenticated BlobServiceClient using connection string from config.

    Returns:
        BlobServiceClient instance

    Raises:
        ValueError: If connection string is not configured
    """
    connection_string = config.BLOB_STORAGE_CONNECTION_STRING
    if not connection_string:
        raise ValueError(
            "BLOB_STORAGE_CONNECTION_STRING not configured. "
            "Please set this environment variable."
        )
    return BlobServiceClient.from_connection_string(connection_string)


def _get_container_client(container_name: str) -> ContainerClient:
    """
    Get ContainerClient for specified container.

    Args:
        container_name: Name of the container

    Returns:
        ContainerClient instance
    """
    service_client = _get_blob_service_client()
    return service_client.get_container_client(container_name)


def _get_blob_client(container_name: str, blob_name: str) -> BlobClient:
    """
    Get BlobClient for specified blob.

    Args:
        container_name: Name of the container
        blob_name: Name of the blob (including any folder prefix)

    Returns:
        BlobClient instance
    """
    service_client = _get_blob_service_client()
    return service_client.get_blob_client(container=container_name, blob=blob_name)


# =============================================================================
# Basic Operations
# =============================================================================

@retry_transient
def read_blob_bytes(container_name: str, blob_name: str) -> bytes:
    """
    Read blob as bytes.

    Args:
        container_name: Name of the container
        blob_name: Name of the blob

    Returns:
        Blob content as bytes

    Raises:
        ResourceNotFoundError: If blob does not exist
    """
    logger.debug("Reading blob '%s' from container '%s'", blob_name, container_name)
    blob_client = _get_blob_client(container_name, blob_name)

    download_stream = blob_client.download_blob()
    data = download_stream.readall()

    logger.debug(
        "Read %d bytes from blob '%s'",
        len(data),
        blob_name
    )
    return data


@retry_transient
def read_blob_text(
    container_name: str,
    blob_name: str,
    encoding: str = "utf-8"
) -> str:
    """
    Read blob as text.

    Args:
        container_name: Name of the container
        blob_name: Name of the blob
        encoding: Text encoding (default: utf-8)

    Returns:
        Blob content as string
    """
    data = read_blob_bytes(container_name, blob_name)
    return data.decode(encoding)


@retry_transient
def write_blob_bytes(
    container_name: str,
    blob_name: str,
    data: bytes,
    content_type: str = "application/octet-stream",
    overwrite: bool = True
) -> None:
    """
    Write bytes to blob.

    Args:
        container_name: Name of the container
        blob_name: Name of the blob
        data: Bytes to write
        content_type: MIME type of the content
        overwrite: Whether to overwrite existing blob (default: True)

    Raises:
        azure.core.exceptions.ResourceExistsError: If blob exists and overwrite is False
    """
    logger.debug(
        "Writing %d bytes to blob '%s' in container '%s'",
        len(data),
        blob_name,
        container_name
    )
    blob_client = _get_blob_client(container_name, blob_name)

    blob_client.upload_blob(
        data,
        content_type=content_type,
        overwrite=overwrite
    )

    logger.debug("Successfully wrote blob '%s'", blob_name)


@retry_transient
def write_blob_text(
    container_name: str,
    blob_name: str,
    text: str,
    encoding: str = "utf-8",
    content_type: str = "text/plain",
    overwrite: bool = True
) -> None:
    """
    Write text to blob.

    Args:
        container_name: Name of the container
        blob_name: Name of the blob
        text: Text to write
        encoding: Text encoding (default: utf-8)
        content_type: MIME type of the content
        overwrite: Whether to overwrite existing blob (default: True)
    """
    data = text.encode(encoding)
    write_blob_bytes(container_name, blob_name, data, content_type, overwrite)


@retry_transient
def delete_blob(container_name: str, blob_name: str) -> bool:
    """
    Delete a blob.

    Args:
        container_name: Name of the container
        blob_name: Name of the blob

    Returns:
        True if blob was deleted, False if it didn't exist
    """
    logger.debug("Deleting blob '%s' from container '%s'", blob_name, container_name)
    blob_client = _get_blob_client(container_name, blob_name)

    try:
        blob_client.delete_blob()
        logger.debug("Successfully deleted blob '%s'", blob_name)
        return True
    except ResourceNotFoundError:
        logger.warning("Blob '%s' not found for deletion", blob_name)
        return False


@retry_transient
def blob_exists(container_name: str, blob_name: str) -> bool:
    """
    Check if a blob exists.

    Args:
        container_name: Name of the container
        blob_name: Name of the blob

    Returns:
        True if blob exists, False otherwise
    """
    blob_client = _get_blob_client(container_name, blob_name)
    return blob_client.exists()


@retry_transient
def get_blob_properties(container_name: str, blob_name: str) -> BlobProperties:
    """
    Get blob properties/metadata.

    Args:
        container_name: Name of the container
        blob_name: Name of the blob

    Returns:
        BlobProperties object with metadata

    Raises:
        ResourceNotFoundError: If blob does not exist
    """
    blob_client = _get_blob_client(container_name, blob_name)
    return blob_client.get_blob_properties()


# =============================================================================
# Copy/Move Operations
# =============================================================================

@retry_transient
def copy_blob(
    source_container: str,
    source_blob: str,
    dest_container: str,
    dest_blob: str,
    overwrite: bool = True
) -> None:
    """
    Copy a blob to a new location.

    Args:
        source_container: Source container name
        source_blob: Source blob name
        dest_container: Destination container name
        dest_blob: Destination blob name
        overwrite: Whether to overwrite existing blob (default: True)
    """
    logger.debug(
        "Copying blob '%s/%s' to '%s/%s'",
        source_container,
        source_blob,
        dest_container,
        dest_blob
    )

    # Read source blob
    data = read_blob_bytes(source_container, source_blob)

    # Get source content type
    try:
        source_props = get_blob_properties(source_container, source_blob)
        content_type = source_props.content_settings.content_type or "application/octet-stream"
    except (ResourceNotFoundError, AttributeError):
        content_type = "application/octet-stream"

    # Write to destination
    write_blob_bytes(dest_container, dest_blob, data, content_type, overwrite)

    logger.debug("Successfully copied blob to '%s/%s'", dest_container, dest_blob)


def move_blob(
    source_container: str,
    source_blob: str,
    dest_container: str,
    dest_blob: str,
    overwrite: bool = True
) -> None:
    """
    Move a blob to a new location (copy + delete).

    Args:
        source_container: Source container name
        source_blob: Source blob name
        dest_container: Destination container name
        dest_blob: Destination blob name
        overwrite: Whether to overwrite existing blob (default: True)
    """
    logger.info(
        "Moving blob '%s/%s' to '%s/%s'",
        source_container,
        source_blob,
        dest_container,
        dest_blob
    )

    # Copy first
    copy_blob(source_container, source_blob, dest_container, dest_blob, overwrite)

    # Then delete source
    delete_blob(source_container, source_blob)

    logger.info("Successfully moved blob to '%s/%s'", dest_container, dest_blob)


def rename_blob(
    container_name: str,
    old_name: str,
    new_name: str,
    overwrite: bool = True
) -> None:
    """
    Rename a blob (move within same container).

    Args:
        container_name: Container name
        old_name: Current blob name
        new_name: New blob name
        overwrite: Whether to overwrite existing blob (default: True)
    """
    move_blob(container_name, old_name, container_name, new_name, overwrite)


# =============================================================================
# Directory/Folder Operations
# =============================================================================

@retry_transient
def list_blobs(
    container_name: str,
    prefix: str = "",
    name_starts_with: str = ""
) -> List[str]:
    """
    List blobs in a container, optionally filtered by prefix.

    Args:
        container_name: Name of the container
        prefix: Filter blobs starting with this prefix (folder)
        name_starts_with: Additional filter for blob names

    Returns:
        List of blob names
    """
    container_client = _get_container_client(container_name)

    # Combine prefix filters
    effective_prefix = prefix
    if name_starts_with and prefix:
        effective_prefix = f"{prefix.rstrip('/')}/{name_starts_with}"
    elif name_starts_with:
        effective_prefix = name_starts_with

    blobs = container_client.list_blobs(name_starts_with=effective_prefix)
    blob_names = [blob.name for blob in blobs]

    logger.debug(
        "Listed %d blobs in '%s' with prefix '%s'",
        len(blob_names),
        container_name,
        effective_prefix
    )
    return blob_names


@retry_transient
def list_blobs_with_properties(
    container_name: str,
    prefix: str = ""
) -> List[Dict[str, Any]]:
    """
    List blobs with their properties/metadata.

    Args:
        container_name: Name of the container
        prefix: Filter blobs starting with this prefix

    Returns:
        List of dictionaries with blob info (name, size, last_modified, content_type)
    """
    container_client = _get_container_client(container_name)
    blobs = container_client.list_blobs(name_starts_with=prefix)

    result = []
    for blob in blobs:
        result.append({
            "name": blob.name,
            "size": blob.size,
            "last_modified": blob.last_modified,
            "content_type": blob.content_settings.content_type if blob.content_settings else None,
            "creation_time": blob.creation_time,
        })

    return result


def delete_blob_prefix(container_name: str, prefix: str) -> int:
    """
    Delete all blobs with a given prefix.

    Args:
        container_name: Name of the container
        prefix: Prefix to match (folder)

    Returns:
        Number of blobs deleted
    """
    blob_names = list_blobs(container_name, prefix=prefix)
    count = 0

    for blob_name in blob_names:
        if delete_blob(container_name, blob_name):
            count += 1

    logger.info(
        "Deleted %d blobs with prefix '%s' from container '%s'",
        count,
        prefix,
        container_name
    )
    return count


# =============================================================================
# Workflow Operations
# =============================================================================

def get_processing_folder_blobs(
    container_name: str = DEFAULT_CONTAINER
) -> List[str]:
    """
    Get list of CSV files in the main processing folder (root).

    Args:
        container_name: Name of the container

    Returns:
        List of blob names in the root folder (excluding processed/ and error/)
    """
    all_blobs = list_blobs(container_name)

    # Filter to only include root-level CSV files (not in processed/ or error/)
    root_blobs = [
        blob for blob in all_blobs
        if not blob.startswith(f"{PROCESSED_FOLDER}/")
        and not blob.startswith(f"{ERROR_FOLDER}/")
        and blob.endswith(".csv")
    ]

    return root_blobs


def get_processed_folder_blobs(
    container_name: str = DEFAULT_CONTAINER
) -> List[str]:
    """
    Get list of files in the processed/ folder.

    Args:
        container_name: Name of the container

    Returns:
        List of blob names in processed/ folder
    """
    return list_blobs(container_name, prefix=f"{PROCESSED_FOLDER}/")


def get_error_folder_blobs(
    container_name: str = DEFAULT_CONTAINER
) -> List[str]:
    """
    Get list of files in the error/ folder.

    Args:
        container_name: Name of the container

    Returns:
        List of blob names in error/ folder
    """
    return list_blobs(container_name, prefix=f"{ERROR_FOLDER}/")


def extract_snapshot_date_from_csv(csv_bytes: bytes) -> Optional[str]:
    """
    Extract snapshot date from CSV content.

    Reads the first row to find the SnapshotDate column value.

    Args:
        csv_bytes: CSV file content as bytes

    Returns:
        Snapshot date string (YYYY-MM-DD format) or None if not found
    """
    try:
        # Read just the first few rows to get the snapshot date
        df = pd.read_csv(io.BytesIO(csv_bytes), nrows=1)

        # Look for SnapshotDate column (with or without brackets)
        snapshot_col = None
        for col in df.columns:
            if "SnapshotDate" in col:
                snapshot_col = col
                break

        if snapshot_col is None:
            logger.warning("SnapshotDate column not found in CSV")
            return None

        # Get the value and format it
        snapshot_value = df[snapshot_col].iloc[0]

        if pd.isna(snapshot_value):
            logger.warning("SnapshotDate value is null")
            return None

        # Handle different date formats
        snapshot_str = str(snapshot_value)

        # If it's already in YYYY-MM-DD format, use it directly
        if len(snapshot_str) >= 10 and snapshot_str[4] == "-" and snapshot_str[7] == "-":
            return snapshot_str[:10]

        # Try to parse as datetime
        try:
            parsed_date = pd.to_datetime(snapshot_value)
            return parsed_date.strftime("%Y-%m-%d")
        except (ValueError, TypeError):
            logger.warning("Could not parse SnapshotDate value: %s", snapshot_value)
            return None

    except (pd.errors.ParserError, UnicodeDecodeError, KeyError, IndexError) as e:
        logger.error("Error extracting snapshot date from CSV: %s", str(e))
        return None


def move_to_processed(
    container_name: str,
    blob_name: str,
    snapshot_date: str
) -> str:
    """
    Move file to processed/ folder with snapshot date suffix.

    Args:
        container_name: Name of the container
        blob_name: Original blob name
        snapshot_date: Snapshot date (YYYY-MM-DD format)

    Returns:
        New blob name in processed/ folder
    """
    # Parse original blob name
    parsed = parse_blob_name(blob_name)
    base_name = parsed["base_name"]
    extension = parsed["extension"]

    # Build new name: processed/features-{snapshot_date}-{original_base}.csv
    new_name = build_blob_name(
        folder=PROCESSED_FOLDER,
        base_name=base_name,
        suffix=f"-{snapshot_date}",
        extension=extension
    )

    logger.info(
        "Moving '%s' to processed folder as '%s'",
        blob_name,
        new_name
    )

    move_blob(container_name, blob_name, container_name, new_name)

    return new_name


def move_to_error(
    container_name: str,
    blob_name: str
) -> str:
    """
    Move file to error/ folder (preserves original name).

    Args:
        container_name: Name of the container
        blob_name: Original blob name

    Returns:
        New blob name in error/ folder
    """
    # Parse original blob name
    parsed = parse_blob_name(blob_name)
    base_name = parsed["base_name"]
    extension = parsed["extension"]

    # Build new name: error/{original_name}
    new_name = build_blob_name(
        folder=ERROR_FOLDER,
        base_name=base_name,
        suffix="",
        extension=extension
    )

    logger.info(
        "Moving '%s' to error folder as '%s'",
        blob_name,
        new_name
    )

    move_blob(container_name, blob_name, container_name, new_name)

    return new_name


# =============================================================================
# Utility Functions
# =============================================================================

def parse_blob_name(blob_name: str) -> Dict[str, str]:
    """
    Parse blob name into components.

    Args:
        blob_name: Full blob name (may include folder prefix)

    Returns:
        Dictionary with 'folder', 'base_name', 'extension' keys
    """
    # Split by forward slash to get folder
    parts = blob_name.rsplit("/", 1)
    if len(parts) == 2:
        folder = parts[0]
        filename = parts[1]
    else:
        folder = ""
        filename = blob_name

    # Split filename by extension
    if "." in filename:
        name_parts = filename.rsplit(".", 1)
        base_name = name_parts[0]
        extension = f".{name_parts[1]}"
    else:
        base_name = filename
        extension = ""

    return {
        "folder": folder,
        "base_name": base_name,
        "extension": extension,
        "filename": filename,
    }


def build_blob_name(
    folder: str,
    base_name: str,
    suffix: str = "",
    extension: str = ".csv"
) -> str:
    """
    Build blob name with folder prefix.

    Args:
        folder: Folder prefix (empty string for root)
        base_name: Base file name
        suffix: Suffix to append (e.g., "-2025-12-31")
        extension: File extension (default: .csv)

    Returns:
        Full blob name with folder prefix
    """
    filename = f"{base_name}{suffix}{extension}"

    if folder:
        return f"{folder}/{filename}"
    return filename
