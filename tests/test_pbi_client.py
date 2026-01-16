"""
Unit tests for pbi_client.py module.
"""

import pytest
import time
from unittest.mock import patch, MagicMock
from function_app.pbi_client import trigger_dataset_refresh, wait_for_refresh_completion


@patch("function_app.pbi_client.get_access_token")
@patch("function_app.pbi_client.requests.post")
@patch("function_app.pbi_client.config")
def test_trigger_dataset_refresh_success(mock_config, mock_post, mock_get_token):
    """Test that trigger_dataset_refresh triggers refresh successfully."""
    mock_config.PBI_WORKSPACE_ID = "test_workspace_id"
    mock_config.PBI_DATASET_ID = "test_dataset_id"
    mock_get_token.return_value = "mock_token"
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.headers.get.return_value = "refresh_id_123"
    mock_post.return_value = mock_response

    refresh_id = trigger_dataset_refresh()

    mock_post.assert_called_once()
    call_args = mock_post.call_args
    assert "test_workspace_id" in call_args[0][0]
    assert "test_dataset_id" in call_args[0][0]
    assert call_args[1]["headers"]["Authorization"] == "Bearer mock_token"
    assert refresh_id == "refresh_id_123"


@patch("function_app.pbi_client.get_access_token")
@patch("function_app.pbi_client.requests.post")
@patch("function_app.pbi_client.config")
def test_trigger_dataset_refresh_with_custom_dataset_id(mock_config, mock_post, mock_get_token):
    """Test that trigger_dataset_refresh uses custom dataset_id when provided."""
    mock_config.PBI_WORKSPACE_ID = "test_workspace_id"
    mock_get_token.return_value = "mock_token"
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.headers.get.return_value = "refresh_id_456"
    mock_post.return_value = mock_response

    refresh_id = trigger_dataset_refresh(dataset_id="custom_dataset_id")

    call_args = mock_post.call_args
    assert "custom_dataset_id" in call_args[0][0]
    assert refresh_id == "refresh_id_456"


@patch("function_app.pbi_client.get_access_token")
@patch("function_app.pbi_client.requests.get")
@patch("function_app.pbi_client.config")
@patch("time.sleep")
def test_wait_for_refresh_completion_success(mock_sleep, mock_config, mock_get, mock_get_token):
    """Test that wait_for_refresh_completion returns True when refresh completes."""
    mock_config.PBI_WORKSPACE_ID = "test_workspace_id"
    mock_config.PBI_DATASET_ID = "test_dataset_id"
    mock_get_token.return_value = "mock_token"

    # First call returns "InProgress", second call returns "Completed"
    mock_response_in_progress = MagicMock()
    mock_response_in_progress.json.return_value = {
        "value": [{"status": "InProgress"}]
    }
    mock_response_completed = MagicMock()
    mock_response_completed.json.return_value = {
        "value": [{"status": "Completed"}]
    }
    mock_get.side_effect = [mock_response_in_progress, mock_response_completed]

    result = wait_for_refresh_completion(timeout=600)

    assert result is True
    assert mock_get.call_count == 2


@patch("function_app.pbi_client.get_access_token")
@patch("function_app.pbi_client.requests.get")
@patch("function_app.pbi_client.config")
@patch("time.sleep")
def test_wait_for_refresh_completion_failed(mock_sleep, mock_config, mock_get, mock_get_token):
    """Test that wait_for_refresh_completion raises on Failed status."""
    mock_config.PBI_WORKSPACE_ID = "test_workspace_id"
    mock_config.PBI_DATASET_ID = "test_dataset_id"
    mock_get_token.return_value = "mock_token"

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "value": [{
            "status": "Failed",
            "serviceExceptionJson": {"error": "Refresh failed"}
        }]
    }
    mock_get.return_value = mock_response

    with pytest.raises(RuntimeError, match="Dataset refresh failed"):
        wait_for_refresh_completion(timeout=600)


@patch("function_app.pbi_client.get_access_token")
@patch("function_app.pbi_client.requests.get")
@patch("function_app.pbi_client.config")
@patch("function_app.pbi_client.time.time")
def test_wait_for_refresh_completion_timeout(mock_time, mock_config, mock_get, mock_get_token):
    """Test that wait_for_refresh_completion returns False on timeout."""
    mock_config.PBI_WORKSPACE_ID = "test_workspace_id"
    mock_config.PBI_DATASET_ID = "test_dataset_id"
    mock_get_token.return_value = "mock_token"

    # Mock time.time() to simulate timeout
    start_time = 1000.0
    mock_time.side_effect = [start_time, start_time + 601]  # First call, then timeout
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "value": [{"status": "InProgress"}]
    }
    mock_get.return_value = mock_response

    # Simulate timeout by making elapsed time exceed timeout
    result = wait_for_refresh_completion(timeout=600)

    assert result is False
