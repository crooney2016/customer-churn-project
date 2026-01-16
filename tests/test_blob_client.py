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
def mock_config(mocker):
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
        """Test delete blob that doesn't exist."""
        from azure.core.exceptions import ResourceNotFoundError

        _, _, mock_blob = mock_blob_service_client
        mock_blob.delete_blob.side_effect = ResourceNotFoundError("Blob not found")

        mocker.patch("function_app.blob_client._get_blob_client", return_value=mock_blob)
        from function_app.blob_client import delete_blob

        with pytest.raises(ResourceNotFoundError):
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

    def test_copy_blob_success(self, _mock_config, mocker):
        """Test successful blob copy."""
        mock_source_blob = mocker.MagicMock()
        mock_dest_blob = mocker.MagicMock()
        mock_source_blob.url = "https://test.blob.core.windows.net/container/source.csv"

        mock_get_blob = mocker.patch("function_app.blob_client._get_blob_client")
        mock_get_blob.side_effect = [mock_source_blob, mock_dest_blob]

        from function_app.blob_client import copy_blob

        copy_blob("container", "source.csv", "container", "dest.csv")

        mock_dest_blob.start_copy_from_url.assert_called_once_with(mock_source_blob.url)


class TestMoveBlob:
    """Tests for move_blob function."""

    def test_move_blob_success(self, _mock_config, mocker):
        """Test successful blob move."""
        mock_copy = mocker.patch("function_app.blob_client.copy_blob")
        mock_delete = mocker.patch("function_app.blob_client.delete_blob")

        from function_app.blob_client import move_blob

        move_blob("container", "source.csv", "container", "dest.csv")

        mock_copy.assert_called_once_with("container", "source.csv", "container", "dest.csv")
        mock_delete.assert_called_once_with("container", "source.csv")


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
        mock_list.assert_called_once_with("container", prefix="processing/")
