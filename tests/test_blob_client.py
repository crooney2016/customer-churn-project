"""
Tests for blob_client module.
Tests blob storage operations including CRUD, copy/move, and workflow operations.
"""

import pytest


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_blob_service_client(mocker):
    """Mock BlobServiceClient for testing."""
    mock_service = mocker.MagicMock()
    mock_container = mocker.MagicMock()
    mock_blob = mocker.MagicMock()

    mock_service.get_container_client.return_value = mock_container
    mock_service.get_blob_client.return_value = mock_blob

    return mock_service, mock_container, mock_blob


@pytest.fixture
def sample_csv_bytes():
    """Sample CSV file content as bytes."""
    csv_content = (
        "[SnapshotDate],Customers[account_Order],Customers[account_Name],"
        "Customers[Segment],Customers[Cost Center],[FirstPurchaseDate],"
        "[LastPurchaseDate],[Orders_CY],[Spend_CY]\n"
        "2025-01-31,001,Account A,FITNESS,CMFIT,2023-01-01,2024-12-01,10,5000.00\n"
        "2025-01-31,002,Account B,FARRELL,CMFIT,2023-06-01,2024-11-15,5,2500.00\n"
        "2025-01-31,003,Account C,FITNESS,CMFIT,2022-01-01,2025-01-01,20,10000.00\n"
    )
    return csv_content.encode("utf-8")


@pytest.fixture
def _mock_config(mocker):
    """Mock config with blob storage settings."""
    mock = mocker.patch("function_app.blob_client.config")
    mock.BLOB_STORAGE_CONNECTION_STRING = (
        "DefaultEndpointsProtocol=https;AccountName=test;"
        "AccountKey=key;EndpointSuffix=core.windows.net"
    )
    mock.BLOB_STORAGE_CONTAINER_NAME = "churn-feature-data"
    return mock


# =============================================================================
# Basic Operations Tests
# =============================================================================

class TestGetBlobServiceClient:
    """Tests for _get_blob_service_client function."""

    def test_get_blob_service_client_missing_connection_string(self, mocker):
        """Test _get_blob_service_client raises ValueError when connection string is missing."""
        mock_config = mocker.patch("function_app.blob_client.config")
        mock_config.BLOB_STORAGE_CONNECTION_STRING = None

        from function_app.blob_client import _get_blob_service_client

        with pytest.raises(ValueError, match="BLOB_STORAGE_CONNECTION_STRING not configured"):
            _get_blob_service_client()


class TestReadBlobBytes:
    """Tests for read_blob_bytes function."""

    def test_read_blob_bytes_success(self, _mock_config, mock_blob_service_client, mocker):
        """Test successful blob read."""
        _, _, mock_blob = mock_blob_service_client
        test_data = b"test content"

        mock_download = mocker.MagicMock()
        mock_download.readall.return_value = test_data
        mock_blob.download_blob.return_value = mock_download

        mocker.patch("function_app.blob_client._get_blob_client", return_value=mock_blob)
        from function_app.blob_client import read_blob_bytes

        result = read_blob_bytes("container", "blob.csv")

        assert result == test_data
        mock_blob.download_blob.assert_called_once()

    def test_read_blob_bytes_not_found(
        self, _mock_config, mock_blob_service_client, mocker
    ):
        """Test read blob that doesn't exist."""
        from azure.core.exceptions import ResourceNotFoundError

        _, _, mock_blob = mock_blob_service_client
        mock_blob.download_blob.side_effect = ResourceNotFoundError("Blob not found")

        mocker.patch("function_app.blob_client._get_blob_client", return_value=mock_blob)
        from function_app.blob_client import read_blob_bytes

        with pytest.raises(ResourceNotFoundError):
            read_blob_bytes("container", "nonexistent.csv")


class TestReadBlobText:
    """Tests for read_blob_text function."""

    def test_read_blob_text_success(self, _mock_config, mock_blob_service_client, mocker):
        """Test successful text blob read."""
        _, _, mock_blob = mock_blob_service_client
        test_data = b"test text content"

        mock_download = mocker.MagicMock()
        mock_download.readall.return_value = test_data
        mock_blob.download_blob.return_value = mock_download

        mocker.patch("function_app.blob_client._get_blob_client", return_value=mock_blob)
        from function_app.blob_client import read_blob_text

        result = read_blob_text("container", "blob.txt")

        assert result == "test text content"


class TestWriteBlobBytes:
    """Tests for write_blob_bytes function."""

    def test_write_blob_bytes_success(
        self, _mock_config, mock_blob_service_client, mocker
    ):
        """Test successful blob write."""
        _, _, mock_blob = mock_blob_service_client
        test_data = b"test content"

        mocker.patch("function_app.blob_client._get_blob_client", return_value=mock_blob)
        from function_app.blob_client import write_blob_bytes

        write_blob_bytes("container", "blob.csv", test_data)

        mock_blob.upload_blob.assert_called_once_with(
            test_data,
            content_type="application/octet-stream",
            overwrite=True
        )


class TestDeleteBlob:
    """Tests for delete_blob function."""

    def test_delete_blob_success(self, _mock_config, mock_blob_service_client, mocker):
        """Test successful blob deletion."""
        _, _, mock_blob = mock_blob_service_client

        mocker.patch("function_app.blob_client._get_blob_client", return_value=mock_blob)
        from function_app.blob_client import delete_blob

        delete_blob("container", "blob.csv")

        mock_blob.delete_blob.assert_called_once()

    def test_delete_blob_not_found(self, _mock_config, mock_blob_service_client, mocker):
        """Test delete blob that doesn't exist logs warning but doesn't raise."""
        from azure.core.exceptions import ResourceNotFoundError

        _, _, mock_blob = mock_blob_service_client
        mock_blob.delete_blob.side_effect = ResourceNotFoundError("Blob not found")

        mocker.patch("function_app.blob_client._get_blob_client", return_value=mock_blob)
        from function_app.blob_client import delete_blob

        # Should not raise - logs warning instead
        delete_blob("container", "nonexistent.csv")


class TestBlobExists:
    """Tests for blob_exists function."""

    def test_blob_exists_true(self, _mock_config, mock_blob_service_client, mocker):
        """Test blob_exists returns True when blob exists."""
        _, _, mock_blob = mock_blob_service_client
        mock_blob.exists.return_value = True

        mocker.patch("function_app.blob_client._get_blob_client", return_value=mock_blob)
        from function_app.blob_client import blob_exists

        result = blob_exists("container", "blob.csv")

        assert result is True
        mock_blob.exists.assert_called_once()

    def test_blob_exists_false(self, _mock_config, mock_blob_service_client, mocker):
        """Test blob_exists returns False when blob doesn't exist."""
        _, _, mock_blob = mock_blob_service_client
        mock_blob.exists.return_value = False

        mocker.patch("function_app.blob_client._get_blob_client", return_value=mock_blob)
        from function_app.blob_client import blob_exists

        result = blob_exists("container", "nonexistent.csv")

        assert result is False


class TestCopyBlob:
    """Tests for copy_blob function."""

    def test_copy_blob_success(self, mocker):
        """Test successful blob copy (read source, write to dest)."""
        # Mock config
        _mock_config = mocker.patch("function_app.blob_client.config")
        _mock_config.BLOB_STORAGE_CONNECTION_STRING = "test"

        # Mock read_blob_bytes
        mocker.patch(
            "function_app.blob_client.read_blob_bytes",
            return_value=b"test content"
        )

        # Mock get_blob_properties to return mock blob properties with content_type
        mock_props = mocker.MagicMock()
        mock_props.content_settings.content_type = "text/csv"
        mocker.patch(
            "function_app.blob_client.get_blob_properties",
            return_value=mock_props
        )

        mock_write = mocker.patch("function_app.blob_client.write_blob_bytes")

        from function_app.blob_client import copy_blob

        copy_blob("container", "source.csv", "container", "dest.csv")

        mock_write.assert_called_once_with(
            "container", "dest.csv", b"test content", "text/csv", True
        )

    def test_copy_blob_missing_content_type(self, mocker):
        """Test copy_blob handles missing content_type gracefully."""
        # Mock config
        _mock_config = mocker.patch("function_app.blob_client.config")
        _mock_config.BLOB_STORAGE_CONNECTION_STRING = "test"

        # Mock read_blob_bytes
        mocker.patch(
            "function_app.blob_client.read_blob_bytes",
            return_value=b"test content"
        )

        # Mock get_blob_properties to return None for content_type
        mock_props = mocker.MagicMock()
        mock_props.content_settings.content_type = None
        mocker.patch(
            "function_app.blob_client.get_blob_properties",
            return_value=mock_props
        )

        mock_write = mocker.patch("function_app.blob_client.write_blob_bytes")

        from function_app.blob_client import copy_blob

        copy_blob("container", "source.csv", "container", "dest.csv")

        # Should use default content_type
        mock_write.assert_called_once_with(
            "container", "dest.csv", b"test content", "application/octet-stream", True
        )

    def test_copy_blob_resource_not_found(self, mocker):
        """Test copy_blob handles ResourceNotFoundError when getting properties."""
        # Mock config
        _mock_config = mocker.patch("function_app.blob_client.config")
        _mock_config.BLOB_STORAGE_CONNECTION_STRING = "test"

        # Mock read_blob_bytes
        mocker.patch(
            "function_app.blob_client.read_blob_bytes",
            return_value=b"test content"
        )

        # Mock get_blob_properties to raise ResourceNotFoundError
        from azure.core.exceptions import ResourceNotFoundError
        mocker.patch(
            "function_app.blob_client.get_blob_properties",
            side_effect=ResourceNotFoundError("Blob not found")
        )

        mock_write = mocker.patch("function_app.blob_client.write_blob_bytes")

        from function_app.blob_client import copy_blob

        copy_blob("container", "source.csv", "container", "dest.csv")

        # Should use default content_type when ResourceNotFoundError
        mock_write.assert_called_once_with(
            "container", "dest.csv", b"test content", "application/octet-stream", True
        )


class TestMoveBlob:
    """Tests for move_blob function."""

    def test_move_blob_success(self, _mock_config, mocker):
        """Test successful blob move."""
        mock_copy = mocker.patch("function_app.blob_client.copy_blob")
        mock_delete = mocker.patch("function_app.blob_client.delete_blob")

        from function_app.blob_client import move_blob

        move_blob("container", "source.csv", "container", "dest.csv")

        # copy_blob is called with overwrite=True by default
        mock_copy.assert_called_once()
        mock_delete.assert_called_once_with("container", "source.csv")


class TestRenameBlob:
    """Tests for rename_blob function."""

    def test_rename_blob_success(self, _mock_config, mocker):
        """Test successful blob rename."""
        mock_move = mocker.patch("function_app.blob_client.move_blob")

        from function_app.blob_client import rename_blob

        rename_blob("container", "old_name.csv", "new_name.csv")

        mock_move.assert_called_once_with(
            "container", "old_name.csv", "container", "new_name.csv", True
        )


class TestListBlobs:
    """Tests for list_blobs function."""

    def test_list_blobs_success(self, _mock_config, mock_blob_service_client, mocker):
        """Test successful blob listing."""
        _, mock_container, _ = mock_blob_service_client

        mock_blob1 = mocker.MagicMock()
        mock_blob2 = mocker.MagicMock()
        mock_blob1.name = "file1.csv"
        mock_blob2.name = "file2.csv"

        mock_container.list_blobs.return_value = [mock_blob1, mock_blob2]

        mocker.patch(
            "function_app.blob_client._get_container_client",
            return_value=mock_container
        )
        from function_app.blob_client import list_blobs

        result = list_blobs("container")

        assert result == ["file1.csv", "file2.csv"]

    def test_list_blobs_with_prefix(self, _mock_config, mock_blob_service_client, mocker):
        """Test blob listing with prefix filter."""
        _, mock_container, _ = mock_blob_service_client

        mock_blob = mocker.MagicMock()
        mock_blob.name = "prefix/file.csv"
        mock_container.list_blobs.return_value = [mock_blob]

        mocker.patch(
            "function_app.blob_client._get_container_client",
            return_value=mock_container
        )
        from function_app.blob_client import list_blobs

        result = list_blobs("container", prefix="prefix/")

        assert result == ["prefix/file.csv"]
        mock_container.list_blobs.assert_called_once_with(name_starts_with="prefix/")

    def test_list_blobs_with_name_starts_with(self, _mock_config, mock_blob_service_client, mocker):
        """Test blob listing with name_starts_with filter."""
        _, mock_container, _ = mock_blob_service_client

        mock_blob = mocker.MagicMock()
        mock_blob.name = "file1.csv"

        mock_container.list_blobs.return_value = [mock_blob]

        mocker.patch(
            "function_app.blob_client._get_container_client",
            return_value=mock_container
        )
        from function_app.blob_client import list_blobs

        result = list_blobs("container", name_starts_with="file")

        assert result == ["file1.csv"]
        mock_container.list_blobs.assert_called_once_with(
            name_starts_with="file"
        )

    def test_list_blobs_with_both_prefix_and_name_starts_with(
        self, _mock_config, mock_blob_service_client, mocker
    ):
        """Test blob listing with both prefix and name_starts_with filters."""
        _, mock_container, _ = mock_blob_service_client

        mock_blob = mocker.MagicMock()
        mock_blob.name = "folder/file1.csv"

        mock_container.list_blobs.return_value = [mock_blob]

        mocker.patch(
            "function_app.blob_client._get_container_client",
            return_value=mock_container
        )
        from function_app.blob_client import list_blobs

        result = list_blobs("container", prefix="folder/", name_starts_with="file")

        assert result == ["folder/file1.csv"]
        # Should combine prefix and name_starts_with
        mock_container.list_blobs.assert_called_once_with(name_starts_with="folder/file")


class TestListBlobsWithProperties:
    """Tests for list_blobs_with_properties function."""

    def test_list_blobs_with_properties_success(
        self, _mock_config, mock_blob_service_client, mocker
    ):
        """Test successful blob listing with properties."""
        _, mock_container, _ = mock_blob_service_client

        mock_blob = mocker.MagicMock()
        mock_blob.name = "file1.csv"
        mock_blob.size = 1024
        mock_blob.last_modified = "2024-01-01T00:00:00Z"
        mock_blob.creation_time = "2024-01-01T00:00:00Z"
        mock_content_settings = mocker.MagicMock()
        mock_content_settings.content_type = "text/csv"
        mock_blob.content_settings = mock_content_settings

        mock_container.list_blobs.return_value = [mock_blob]

        mocker.patch(
            "function_app.blob_client._get_container_client",
            return_value=mock_container
        )
        from function_app.blob_client import list_blobs_with_properties

        result = list_blobs_with_properties("container", prefix="prefix/")

        assert len(result) == 1
        assert result[0]["name"] == "file1.csv"
        assert result[0]["size"] == 1024
        assert result[0]["content_type"] == "text/csv"

    def test_list_blobs_with_properties_no_content_type(
        self, _mock_config, mock_blob_service_client, mocker
    ):
        """Test list_blobs_with_properties handles missing content_type."""
        _, mock_container, _ = mock_blob_service_client

        mock_blob = mocker.MagicMock()
        mock_blob.name = "file1.csv"
        mock_blob.size = 1024
        mock_blob.last_modified = "2024-01-01T00:00:00Z"
        mock_blob.creation_time = "2024-01-01T00:00:00Z"
        mock_blob.content_settings = None

        mock_container.list_blobs.return_value = [mock_blob]

        mocker.patch(
            "function_app.blob_client._get_container_client",
            return_value=mock_container
        )
        from function_app.blob_client import list_blobs_with_properties

        result = list_blobs_with_properties("container")

        assert len(result) == 1
        assert result[0]["name"] == "file1.csv"
        assert result[0]["content_type"] is None


class TestDeleteBlobPrefix:
    """Tests for delete_blob_prefix function."""

    def test_delete_blob_prefix_success(self, _mock_config, mocker):
        """Test successful deletion of blobs with prefix."""
        mock_list = mocker.patch("function_app.blob_client.list_blobs")
        mock_list.return_value = ["prefix/file1.csv", "prefix/file2.csv"]

        mock_delete = mocker.patch("function_app.blob_client.delete_blob")
        mock_delete.side_effect = [True, True]

        from function_app.blob_client import delete_blob_prefix

        count = delete_blob_prefix("container", "prefix/")

        assert count == 2
        assert mock_delete.call_count == 2

    def test_delete_blob_prefix_partial_failure(self, _mock_config, mocker):
        """Test delete_blob_prefix handles partial deletion failures."""
        mock_list = mocker.patch("function_app.blob_client.list_blobs")
        mock_list.return_value = ["prefix/file1.csv", "prefix/file2.csv"]

        mock_delete = mocker.patch("function_app.blob_client.delete_blob")
        mock_delete.side_effect = [True, False]  # Second delete fails

        from function_app.blob_client import delete_blob_prefix

        count = delete_blob_prefix("container", "prefix/")

        assert count == 1  # Only first deletion succeeded
        assert mock_delete.call_count == 2


# =============================================================================
# Workflow Operations Tests
# =============================================================================

class TestMoveToProcessed:
    """Tests for move_to_processed function."""

    def test_move_to_processed_success(self, _mock_config, mocker):
        """Test successful move to processed folder."""
        mock_move = mocker.patch("function_app.blob_client.move_blob")

        from function_app.blob_client import move_to_processed

        move_to_processed("container", "input/file.csv", "2025-01-31")

        # Verify move_blob was called (processed name includes snapshot date)
        assert mock_move.called
        call_args = mock_move.call_args[0]
        assert call_args[0] == "container"
        assert call_args[1] == "input/file.csv"
        assert call_args[2] == "container"
        assert "processed/" in call_args[3]
        assert "2025-01-31" in call_args[3]


class TestMoveToError:
    """Tests for move_to_error function."""

    def test_move_to_error_success(self, _mock_config, mocker):
        """Test successful move to error folder."""
        mock_move = mocker.patch("function_app.blob_client.move_blob")

        from function_app.blob_client import move_to_error

        move_to_error("container", "input/file.csv")

        mock_move.assert_called_once_with(
            "container",
            "input/file.csv",
            "container",
            "error/file.csv"
        )


class TestGetProcessingFolderBlobs:
    """Tests for get_processing_folder_blobs function."""

    def test_get_processing_folder_blobs(self, _mock_config, mocker):
        """Test getting blobs from processing folder."""
        mock_list = mocker.patch("function_app.blob_client.list_blobs")
        mock_list.return_value = [
            "processing/file1.csv",
            "processing/file2.csv"
        ]

        from function_app.blob_client import get_processing_folder_blobs

        result = get_processing_folder_blobs("container")

        assert result == ["processing/file1.csv", "processing/file2.csv"]
        mock_list.assert_called_once_with("container")


# =============================================================================
# Tests for extract_snapshot_date_from_csv
# =============================================================================

def test_extract_snapshot_date_from_csv_success(_mock_config):
    """Test extracting snapshot date from CSV with valid date."""
    from function_app.blob_client import extract_snapshot_date_from_csv

    csv_content = (
        "SnapshotDate,CustomerId,Orders_CY\n"
        "2025-01-31,001,10\n"
    ).encode("utf-8")

    result = extract_snapshot_date_from_csv(csv_content)
    assert result == "2025-01-31"


def test_extract_snapshot_date_from_csv_with_brackets(_mock_config):
    """Test extracting snapshot date from CSV with bracketed column name."""
    from function_app.blob_client import extract_snapshot_date_from_csv

    csv_content = (
        "[SnapshotDate],CustomerId,Orders_CY\n"
        "2025-01-31,001,10\n"
    ).encode("utf-8")

    result = extract_snapshot_date_from_csv(csv_content)
    assert result == "2025-01-31"


def test_extract_snapshot_date_from_csv_datetime_format(_mock_config):
    """Test extracting snapshot date from CSV with datetime format."""
    from function_app.blob_client import extract_snapshot_date_from_csv

    csv_content = (
        "SnapshotDate,CustomerId,Orders_CY\n"
        "2025-01-31 12:00:00,001,10\n"
    ).encode("utf-8")

    result = extract_snapshot_date_from_csv(csv_content)
    assert result == "2025-01-31"


def test_extract_snapshot_date_from_csv_missing_column(_mock_config):
    """Test extracting snapshot date when column is missing."""
    from function_app.blob_client import extract_snapshot_date_from_csv

    csv_content = (
        "CustomerId,Orders_CY\n"
        "001,10\n"
    ).encode("utf-8")

    result = extract_snapshot_date_from_csv(csv_content)
    assert result is None


def test_extract_snapshot_date_from_csv_null_value(_mock_config):
    """Test extracting snapshot date when value is null."""
    from function_app.blob_client import extract_snapshot_date_from_csv

    csv_content = (
        "SnapshotDate,CustomerId,Orders_CY\n"
        ",001,10\n"
    ).encode("utf-8")

    result = extract_snapshot_date_from_csv(csv_content)
    assert result is None


def test_extract_snapshot_date_from_csv_invalid_date(_mock_config):
    """Test extracting snapshot date with invalid date format."""
    from function_app.blob_client import extract_snapshot_date_from_csv

    csv_content = (
        "SnapshotDate,CustomerId,Orders_CY\n"
        "invalid-date,001,10\n"
    ).encode("utf-8")

    result = extract_snapshot_date_from_csv(csv_content)
    assert result is None


def test_extract_snapshot_date_from_csv_parse_error(_mock_config):
    """Test extracting snapshot date with malformed CSV."""
    from function_app.blob_client import extract_snapshot_date_from_csv

    # Invalid CSV content
    csv_content = b"invalid csv content\nwith\nbroken\nformat"

    result = extract_snapshot_date_from_csv(csv_content)
    assert result is None


# =============================================================================
# Tests for helper functions
# =============================================================================

def test_get_container_client(_mock_config, mock_blob_service_client):
    """Test _get_container_client returns ContainerClient."""
    from function_app.blob_client import _get_container_client

    mock_service, mock_container, _ = mock_blob_service_client

    from unittest.mock import patch

    with patch(
        "function_app.blob_client._get_blob_service_client",
        return_value=mock_service
    ):
        result = _get_container_client("test-container")
        assert result == mock_container
        mock_service.get_container_client.assert_called_once_with("test-container")


def test_get_blob_client(_mock_config, mock_blob_service_client):
    """Test _get_blob_client returns BlobClient."""
    from function_app.blob_client import _get_blob_client
    from unittest.mock import patch

    mock_service, _, mock_blob = mock_blob_service_client

    with patch(
        "function_app.blob_client._get_blob_service_client",
        return_value=mock_service
    ):
        result = _get_blob_client("test-container", "test-blob.csv")
        assert result == mock_blob
        mock_service.get_blob_client.assert_called_once_with(
            container="test-container",
            blob="test-blob.csv"
        )


# =============================================================================
# Edge Case Tests for Error Handling
# =============================================================================

class TestBlobClientEdgeCases:
    """Edge case tests for error handling paths."""

    def test_get_blob_service_client_empty_connection_string(self, mocker):
        """Test _get_blob_service_client raises ValueError for empty string (line 71)."""
        mock_config = mocker.patch("function_app.blob_client.config")
        mock_config.BLOB_STORAGE_CONNECTION_STRING = ""  # Empty string

        from function_app.blob_client import _get_blob_service_client

        with pytest.raises(ValueError, match="BLOB_STORAGE_CONNECTION_STRING not configured"):
            _get_blob_service_client()

    def test_write_blob_text_handles_encoding_error(self, _mock_config, mocker):
        """Test write_blob_text handles encoding errors (line 215-216)."""
        mock_write_bytes = mocker.patch("function_app.blob_client.write_blob_bytes")

        from function_app.blob_client import write_blob_text

        # Normal case should work
        write_blob_text("container", "blob.txt", "test text", encoding="utf-8")
        mock_write_bytes.assert_called_once()

        # Test with different encoding
        mock_write_bytes.reset_mock()
        write_blob_text("container", "blob.txt", "test text", encoding="latin-1")
        mock_write_bytes.assert_called_once()

    def test_get_blob_properties_raises_resource_not_found(
        self, _mock_config, mock_blob_service_client, mocker
    ):
        """Test get_blob_properties raises ResourceNotFoundError.

        Tests error handling when blob doesn't exist (lines 274-275).
        """
        from azure.core.exceptions import ResourceNotFoundError
        _, _, mock_blob = mock_blob_service_client

        # Make get_blob_properties raise ResourceNotFoundError
        mock_blob.get_blob_properties.side_effect = ResourceNotFoundError("Blob not found")

        mocker.patch(
            "function_app.blob_client._get_blob_client",
            return_value=mock_blob
        )

        from function_app.blob_client import get_blob_properties

        with pytest.raises(ResourceNotFoundError, match="Blob not found"):
            get_blob_properties("container", "nonexistent.csv")
