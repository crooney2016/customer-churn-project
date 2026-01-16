"""
Unit tests for function_app.py module.
"""

import pytest
from unittest.mock import patch, MagicMock
from function_app.function_app import run_monthly_pipeline


@patch("function_app.function_app.send_success_email")
@patch("function_app.function_app.wait_for_refresh_completion")
@patch("function_app.function_app.trigger_dataset_refresh")
@patch("function_app.function_app.insert_churn_scores")
@patch("function_app.function_app.score_customers")
@patch("function_app.function_app.execute_dax_query")
@patch("function_app.function_app.get_dax_query_from_dataset")
@patch("function_app.function_app.config")
def test_run_monthly_pipeline_success(
    mock_config,
    mock_get_query,
    mock_execute_dax,
    mock_score,
    mock_insert,
    mock_trigger_refresh,
    mock_wait_refresh,
    mock_send_success,
    sample_input_df,
    sample_scored_df
):
    """Test that run_monthly_pipeline executes all steps successfully."""
    import pandas as pd

    # Setup mocks
    mock_config.validate.return_value = None
    mock_get_query.return_value = "EVALUATE churn_features"
    mock_execute_dax.return_value = sample_input_df
    mock_score.return_value = sample_scored_df
    mock_insert.return_value = len(sample_scored_df)
    mock_trigger_refresh.return_value = "refresh_id_123"
    mock_wait_refresh.return_value = True

    # Run pipeline
    result = run_monthly_pipeline()

    # Verify all steps were called
    mock_config.validate.assert_called_once()
    mock_get_query.assert_called_once()
    mock_execute_dax.assert_called_once()
    mock_score.assert_called_once()
    mock_insert.assert_called_once()
    mock_trigger_refresh.assert_called_once()
    mock_wait_refresh.assert_called_once()
    mock_send_success.assert_called_once()

    # Verify result structure
    assert result["status"] == "success"
    assert result["rows_scored"] == len(sample_scored_df)
    assert result["rows_written"] == len(sample_scored_df)
    assert "duration_seconds" in result
    assert "risk_distribution" in result


@patch("function_app.function_app.send_failure_email")
@patch("function_app.function_app.execute_dax_query")
@patch("function_app.function_app.get_dax_query_from_dataset")
@patch("function_app.function_app.config")
def test_run_monthly_pipeline_fails_on_empty_dax_result(
    mock_config,
    mock_get_query,
    mock_execute_dax,
    mock_send_failure
):
    """Test that run_monthly_pipeline fails when DAX query returns no rows."""
    import pandas as pd

    # Setup mocks
    mock_config.validate.return_value = None
    mock_get_query.return_value = "EVALUATE churn_features"
    mock_execute_dax.return_value = pd.DataFrame()  # Empty DataFrame

    # Run pipeline - should raise ValueError
    with pytest.raises(ValueError, match="DAX query returned no rows"):
        run_monthly_pipeline()

    # Verify failure email was sent
    mock_send_failure.assert_called_once()
    call_args = mock_send_failure.call_args
    assert call_args[1]["step"] == "dax_query"


@patch("function_app.function_app.send_failure_email")
@patch("function_app.function_app.execute_dax_query")
@patch("function_app.function_app.get_dax_query_from_dataset")
@patch("function_app.function_app.config")
def test_run_monthly_pipeline_handles_pbi_refresh_failure_gracefully(
    mock_config,
    mock_get_query,
    mock_execute_dax,
    mock_send_failure,
    sample_input_df,
    sample_scored_df
):
    """Test that run_monthly_pipeline continues even if PBI refresh monitoring fails."""
    from unittest.mock import patch as mock_patch

    with mock_patch("function_app.function_app.score_customers", return_value=sample_scored_df), \
         mock_patch("function_app.function_app.insert_churn_scores", return_value=len(sample_scored_df)), \
         mock_patch("function_app.function_app.trigger_dataset_refresh", return_value="refresh_id"), \
         mock_patch("function_app.function_app.wait_for_refresh_completion", side_effect=TimeoutError("Timeout")), \
         mock_patch("function_app.function_app.send_success_email") as mock_send_success:

        # Setup mocks
        mock_config.validate.return_value = None
        mock_get_query.return_value = "EVALUATE churn_features"
        mock_execute_dax.return_value = sample_input_df

        # Run pipeline - should succeed despite refresh timeout
        result = run_monthly_pipeline()

        # Verify success email was still sent
        mock_send_success.assert_called_once()
        assert result["status"] == "success"
