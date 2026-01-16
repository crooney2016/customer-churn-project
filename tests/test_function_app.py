"""
Unit tests for function_app.py module.
Tests the blob-triggered pipeline and HTTP endpoints.
"""

import pytest
import pandas as pd


class TestRunPipeline:
    """Tests for the _run_pipeline function."""

    def test_run_pipeline_success(self, mocker, sample_input_df, sample_scored_df):
        """Test successful pipeline execution."""
        # Mock all dependencies
        mocker.patch(
            "function_app.function_app.extract_snapshot_date_from_csv",
            return_value="2025-01-31"
        )
        mocker.patch(
            "function_app.function_app.parse_csv_from_bytes",
            return_value=sample_input_df
        )
        mocker.patch("function_app.function_app.validate_csv_schema")
        mocker.patch(
            "function_app.function_app.normalize_column_names",
            return_value=sample_input_df
        )
        mocker.patch(
            "function_app.function_app.score_customers",
            return_value=sample_scored_df
        )
        mocker.patch(
            "function_app.function_app.insert_churn_scores",
            return_value=len(sample_scored_df)
        )
        mocker.patch(
            "function_app.function_app.move_to_processed",
            return_value="processed/file_2025-01-31.csv"
        )
        mocker.patch("function_app.function_app.send_success_email")

        from function_app.function_app import _run_pipeline

        result = _run_pipeline(b"csv,data", "test.csv", "container")

        assert result["status"] == "success"
        assert result["rows_scored"] == 3
        assert result["snapshot_date"] == "2025-01-31"
        assert "duration_seconds" in result

    def test_run_pipeline_empty_csv_raises_error(self, mocker, sample_input_df):  # pylint: disable=unused-argument
        """Test pipeline fails on empty CSV."""
        empty_df = pd.DataFrame()

        mocker.patch(
            "function_app.function_app.extract_snapshot_date_from_csv",
            return_value="2025-01-31"
        )
        mocker.patch(
            "function_app.function_app.parse_csv_from_bytes",
            return_value=empty_df
        )
        mocker.patch("function_app.function_app.move_to_error")
        mocker.patch("function_app.function_app.send_failure_email")

        from function_app.function_app import _run_pipeline

        with pytest.raises(ValueError, match="no data rows"):
            _run_pipeline(b"csv,data", "test.csv", "container")

    def test_run_pipeline_moves_to_error_on_failure(self, mocker):
        """Test that failed files are moved to error folder."""
        mocker.patch(
            "function_app.function_app.extract_snapshot_date_from_csv",
            side_effect=ValueError("Parse error")
        )
        mock_move_error = mocker.patch("function_app.function_app.move_to_error")
        mocker.patch("function_app.function_app.send_failure_email")

        from function_app.function_app import _run_pipeline

        with pytest.raises(ValueError):
            _run_pipeline(b"bad,data", "test.csv", "container")

        mock_move_error.assert_called_once_with("container", "test.csv")

    def test_run_pipeline_sends_failure_email_on_error(self, mocker):
        """Test that failure email is sent on pipeline error."""
        mocker.patch(
            "function_app.function_app.extract_snapshot_date_from_csv",
            side_effect=ConnectionError("DB connection failed")
        )
        mocker.patch("function_app.function_app.move_to_error")
        mock_send_failure = mocker.patch("function_app.function_app.send_failure_email")

        from function_app.function_app import _run_pipeline

        with pytest.raises(ConnectionError):
            _run_pipeline(b"csv,data", "test.csv", "container")

        mock_send_failure.assert_called_once()
        call_kwargs = mock_send_failure.call_args[1]
        assert call_kwargs["error_type"] == "ConnectionError"
        assert "DB connection failed" in call_kwargs["error_message"]


class TestProcessChurnCsv:
    """Tests for the blob trigger handler."""

    def test_skips_processed_folder(self, mocker):
        """Test that files in processed folder are skipped."""
        mock_blob = mocker.MagicMock()
        mock_blob.name = "processed/old_file.csv"
        mock_blob.read.return_value = b"data"

        # Import after mocking to avoid import errors
        from function_app.function_app import process_churn_csv

        # Should not raise, just skip
        process_churn_csv(mock_blob)

        # Verify blob.read was NOT called (skipped)
        mock_blob.read.assert_not_called()

    def test_skips_error_folder(self, mocker):
        """Test that files in error folder are skipped."""
        mock_blob = mocker.MagicMock()
        mock_blob.name = "error/bad_file.csv"
        mock_blob.read.return_value = b"data"

        from function_app.function_app import process_churn_csv

        process_churn_csv(mock_blob)

        mock_blob.read.assert_not_called()

    def test_skips_non_csv_files(self, mocker):
        """Test that non-CSV files are skipped."""
        mock_blob = mocker.MagicMock()
        mock_blob.name = "test.json"
        mock_blob.read.return_value = b"data"

        from function_app.function_app import process_churn_csv

        process_churn_csv(mock_blob)

        mock_blob.read.assert_not_called()

    def test_processes_csv_file(self, mocker):
        """Test that CSV files are processed."""
        mock_blob = mocker.MagicMock()
        mock_blob.name = "features.csv"
        mock_blob.read.return_value = b"csv,data"

        # Mock the pipeline
        mock_run = mocker.patch("function_app.function_app._run_pipeline")
        mock_run.return_value = {"rows_scored": 100}

        from function_app.function_app import process_churn_csv

        process_churn_csv(mock_blob)

        mock_blob.read.assert_called_once()
        mock_run.assert_called_once_with(
            b"csv,data",
            "features.csv",
            "churn-feature-data"
        )

    def test_handles_empty_blob(self, mocker):
        """Test that empty blobs are handled gracefully."""
        mock_blob = mocker.MagicMock()
        mock_blob.name = "empty.csv"
        mock_blob.read.return_value = b""

        from function_app.function_app import process_churn_csv

        # Should not raise, just log and return
        process_churn_csv(mock_blob)


class TestExtractBlobName:
    """Tests for the _extract_blob_name helper function."""

    def test_extract_from_full_url(self):
        """Test extracting blob name from full URL."""
        from function_app.function_app import _extract_blob_name

        url = "https://storage.blob.core.windows.net/container/path/to/file.csv"
        result = _extract_blob_name(url, "container")

        assert result == "path/to/file.csv"

    def test_extract_from_blob_name(self):
        """Test that plain blob names are returned as-is."""
        from function_app.function_app import _extract_blob_name

        result = _extract_blob_name("file.csv", "container")

        assert result == "file.csv"

    def test_extract_from_url_without_container(self):
        """Test extracting blob name when container not in URL."""
        from function_app.function_app import _extract_blob_name

        url = "https://storage.blob.core.windows.net/other/file.csv"
        result = _extract_blob_name(url, "container")

        # Falls back to last path segment
        assert result == "file.csv"


class TestHealthCheck:
    """Tests for the health check endpoint."""

    def test_health_check_returns_ok(self, mocker):
        """Test that health check returns OK."""
        mock_req = mocker.MagicMock()

        from function_app.function_app import health_check

        response = health_check(mock_req)

        assert response.status_code == 200
        assert response.get_body().decode() == "OK"


class TestScoreHttp:
    """Tests for the HTTP trigger endpoint."""

    def test_score_http_requires_blob_url(self, mocker):
        """Test that HTTP endpoint requires blob_url."""
        mock_req = mocker.MagicMock()
        mock_req.get_json.return_value = {}

        from function_app.function_app import score_http

        response = score_http(mock_req)

        assert response.status_code == 400
        assert "blob_url" in response.get_body().decode()

    def test_score_http_handles_invalid_json(self, mocker):
        """Test that HTTP endpoint handles invalid JSON."""
        mock_req = mocker.MagicMock()
        mock_req.get_json.side_effect = ValueError("Invalid JSON")

        from function_app.function_app import score_http

        response = score_http(mock_req)

        assert response.status_code == 400
        assert "JSON" in response.get_body().decode()

    def test_score_http_success(self, mocker):
        """Test successful HTTP trigger."""
        mock_req = mocker.MagicMock()
        mock_req.get_json.return_value = {"blob_url": "test.csv"}

        mocker.patch(
            "function_app.function_app.read_blob_bytes",
            return_value=b"csv,data"
        )
        mocker.patch(
            "function_app.function_app._run_pipeline",
            return_value={"rows_scored": 100, "snapshot_date": "2025-01-31"}
        )

        from function_app.function_app import score_http

        response = score_http(mock_req)

        assert response.status_code == 200
        assert "100" in response.get_body().decode()

    def test_score_http_pipeline_failure(self, mocker):
        """Test HTTP trigger handles pipeline failures."""
        mock_req = mocker.MagicMock()
        mock_req.get_json.return_value = {"blob_url": "test.csv"}

        mocker.patch(
            "function_app.function_app.read_blob_bytes",
            return_value=b"csv,data"
        )
        mocker.patch(
            "function_app.function_app._run_pipeline",
            side_effect=ValueError("Pipeline error")
        )

        from function_app.function_app import score_http

        response = score_http(mock_req)

        assert response.status_code == 500
        assert "Pipeline failed" in response.get_body().decode()


# Legacy pipeline has been removed - no tests needed
