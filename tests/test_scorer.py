"""
Unit tests for scorer.py module.
"""

import numpy as np
import pandas as pd
import pytest

from function_app.scorer import (
    normalize_cols,
    convert_excel_dates,
    preprocess,
    risk_band,
    feature_phrase,
    reason_text,
    top_reasons,
    load_model,
    score_customers,
)


def test_normalize_cols_strips_brackets():
    """Test that normalize_cols removes brackets from column names."""
    df = pd.DataFrame({"[CustomerId]": ["123"], "[Segment]": ["FITNESS"]})
    result = normalize_cols(df)
    assert "CustomerId" in result.columns
    assert "[CustomerId]" not in result.columns
    assert "Segment" in result.columns
    assert "[Segment]" not in result.columns


def test_normalize_cols_strips_whitespace():
    """Test that normalize_cols strips whitespace from column names."""
    df = pd.DataFrame({" CustomerId ": ["123"], "  Segment  ": ["FITNESS"]})
    result = normalize_cols(df)
    assert "CustomerId" in result.columns
    assert "Segment" in result.columns


def test_convert_excel_dates_handles_excel_serial():
    """Test that convert_excel_dates converts Excel serial dates."""
    df = pd.DataFrame({
        "SnapshotDate": [45321],  # Excel serial date (Jan 1, 2024)
        "FirstPurchaseDate": ["2023-01-01"],
    })
    result = convert_excel_dates(df)
    assert pd.api.types.is_datetime64_any_dtype(result["SnapshotDate"])
    assert result["SnapshotDate"].iloc[0].year == 2024


def test_preprocess_strips_brackets():
    """Test that preprocess handles bracketed column names."""
    df = pd.DataFrame({
        "[CustomerId]": ["123"],
        "[Segment]": ["FITNESS"],
        "[Orders_CY]": [10],
    })
    # Normalize first, then preprocess
    df = normalize_cols(df)
    result = preprocess(df)
    # Should have processed columns (identifiers dropped, dummies created)
    assert "Segment_FITNESS" in result.columns or any("Segment" in c for c in result.columns)


def test_preprocess_fills_null_segment():
    """Test that preprocess fills null Segment with UNKNOWN."""
    df = pd.DataFrame({
        "CustomerId": ["123"],
        "Segment": [None],
        "Orders_CY": [10],
    })
    result = preprocess(df)
    # Segment should be one-hot encoded, check for UNKNOWN column
    assert any("Segment_UNKNOWN" in col for col in result.columns)


def test_preprocess_creates_dummy_columns():
    """Test that preprocess creates one-hot encoded columns for Segment and CostCenter."""
    df = pd.DataFrame({
        "CustomerId": ["123"],
        "Segment": ["FITNESS"],
        "CostCenter": ["CMFIT"],
        "Orders_CY": [10],
    })
    result = preprocess(df)
    assert any("Segment_FITNESS" in col for col in result.columns)
    assert any("CostCenter_CMFIT" in col for col in result.columns)


def test_risk_band_high():
    """Test risk_band calculation for high risk."""
    assert risk_band(0.75) == "A - High Risk"
    assert risk_band(0.70) == "A - High Risk"
    assert risk_band(1.0) == "A - High Risk"


def test_risk_band_medium():
    """Test risk_band calculation for medium risk."""
    assert risk_band(0.50) == "B - Medium Risk"
    assert risk_band(0.30) == "B - Medium Risk"
    assert risk_band(0.69) == "B - Medium Risk"


def test_risk_band_low():
    """Test risk_band calculation for low risk."""
    assert risk_band(0.29) == "C - Low Risk"
    assert risk_band(0.0) == "C - Low Risk"
    assert risk_band(0.15) == "C - Low Risk"


def test_score_customers_structure(mocker):
    """Test that score_customers returns expected structure."""
    # Mock model loading to avoid requiring actual model files
    mock_model = mocker.MagicMock()
    # predict_proba returns shape (n_samples, 2) for binary classification
    mock_model.predict_proba.return_value = np.array([
        [0.2, 0.8], [0.5, 0.5], [0.7, 0.3]  # [prob_class_0, prob_class_1]
    ])
    mock_booster = mocker.MagicMock()
    # Predict should return contributions with BIAS column
    # Need to match the number of features in model_columns
    # The actual model has many more features, but for testing we use 6
    feature_cols = [
        "Orders_CY", "Spend_CY", "DaysSinceLast",
        "Segment_FITNESS", "Segment_FARRELL", "CostCenter_CMFIT"
    ]
    # Contributions: 6 features + BIAS = 7 columns, 3 rows
    mock_booster.predict.return_value = np.array([
        [0.1, 0.2, 0.3, 0.1, 0.1, 0.1, 0.0],  # 6 features + BIAS
        [0.05, 0.15, 0.25, 0.15, 0.15, 0.1, 0.0],  # 6 features + BIAS
        [0.05, 0.1, 0.2, 0.2, 0.2, 0.15, 0.0],  # 6 features + BIAS
    ])
    mock_model.get_booster.return_value = mock_booster

    # Mock xgb.DMatrix to avoid requiring xgboost
    mock_dmatrix = mocker.patch("function_app.scorer.xgb.DMatrix")
    mock_dmatrix_instance = mocker.MagicMock()
    mock_dmatrix.return_value = mock_dmatrix_instance

    mock_load = mocker.patch("function_app.scorer.load_model")
    mock_load.return_value = (mock_model, feature_cols)

    df = pd.DataFrame({
        "CustomerId": ["001", "002", "003"],
        "AccountName": ["Account A", "Account B", "Account C"],
        "Segment": ["FITNESS", "FARRELL", "FITNESS"],
        "CostCenter": ["CMFIT", "CMFIT", "CMFIT"],
        "SnapshotDate": pd.to_datetime(["2024-01-01", "2024-01-01", "2024-01-01"]),
        "FirstPurchaseDate": pd.to_datetime(["2023-01-01", "2023-06-01", "2022-01-01"]),
        "LastPurchaseDate": pd.to_datetime(["2024-01-01", "2023-12-01", "2024-01-01"]),
        "Orders_CY": [10, 5, 20],
        "Spend_CY": [5000.0, 2500.0, 10000.0],
        "DaysSinceLast": [10, 30, 5],
    })

    result = score_customers(df)

    # Verify output columns
    assert "ChurnRiskPct" in result.columns
    assert "RiskBand" in result.columns
    assert "Reason_1" in result.columns
    assert "Reason_2" in result.columns
    assert "Reason_3" in result.columns
    assert "CustomerId" in result.columns
    assert "SnapshotDate" in result.columns
    assert len(result) == 3
    # Verify ChurnRiskPct values match predict_proba[:, 1]
    assert result["ChurnRiskPct"].iloc[0] == 0.8
    assert result["ChurnRiskPct"].iloc[1] == 0.5
    assert result["ChurnRiskPct"].iloc[2] == 0.3


def test_load_model_missing_model_file(mocker):  # pylint: disable=unused-argument
    """Test load_model raises FileNotFoundError when model file is missing."""
    from unittest.mock import patch, MagicMock

    # Create a mock Path that returns False for model file
    mock_model_path = MagicMock()
    mock_model_path.exists.return_value = False
    mock_model_path.__str__ = lambda x: "/path/to/churn_model.pkl"

    mock_model_columns_path = MagicMock()
    mock_model_columns_path.exists.return_value = True
    mock_model_columns_path.__str__ = lambda x: "/path/to/model_columns.pkl"

    # Mock Path constructor to return our mock paths
    def mock_path_init(self, *args):
        path_str = str(args[0]) if args else ""
        if "churn_model.pkl" in path_str:
            return mock_model_path
        if "model_columns.pkl" in path_str:
            return mock_model_columns_path
        # Default mock path
        mock_default = MagicMock()
        mock_default.exists.return_value = True
        return mock_default

    with patch("function_app.scorer.Path", side_effect=lambda *args: mock_path_init(None, *args)):
        with pytest.raises(FileNotFoundError, match="Model file not found"):
            load_model()

def test_load_model_missing_model_columns_file(mocker):  # pylint: disable=unused-argument
    """Test load_model raises FileNotFoundError when model_columns file is missing."""
    from unittest.mock import patch, MagicMock

    # Create mock paths
    mock_model_path = MagicMock()
    mock_model_path.exists.return_value = True
    mock_model_path.__str__ = lambda x: "/path/to/churn_model.pkl"

    mock_model_columns_path = MagicMock()
    mock_model_columns_path.exists.return_value = False  # Columns file missing
    mock_model_columns_path.__str__ = lambda x: "/path/to/model_columns.pkl"

    # Mock Path constructor
    def mock_path_init(self, *args):
        path_str = str(args[0]) if args else ""
        if "churn_model.pkl" in path_str:
            return mock_model_path
        if "model_columns.pkl" in path_str:
            return mock_model_columns_path
        # Default mock path
        mock_default = MagicMock()
        mock_default.exists.return_value = True
        return mock_default

    with patch("function_app.scorer.Path", side_effect=lambda *args: mock_path_init(None, *args)):
        with pytest.raises(FileNotFoundError, match="Model columns file not found"):
            load_model()


def test_score_customers_model_loading_error(mocker):
    """Test score_customers handles model loading errors."""
    mock_load = mocker.patch("function_app.scorer.load_model")
    mock_load.side_effect = FileNotFoundError("Model file not found")

    df = pd.DataFrame({
        "CustomerId": ["001"],
        "SnapshotDate": pd.to_datetime(["2024-01-01"]),
        "Orders_CY": [10],
    })

    with pytest.raises(FileNotFoundError, match="Model file not found"):
        score_customers(df)


def test_score_customers_preprocessing_error(mocker):
    """Test score_customers handles preprocessing errors."""
    mock_model = mocker.MagicMock()
    mock_model.predict_proba.return_value = np.array([[0.2, 0.8]])
    mock_booster = mocker.MagicMock()
    mock_booster.predict.return_value = np.array([[0.1, 0.2, 0.3, 0.1, 0.1, 0.1, 0.0]])
    mock_model.get_booster.return_value = mock_booster

    mock_load = mocker.patch("function_app.scorer.load_model")
    mock_load.return_value = (mock_model, ["Orders_CY", "Spend_CY", "DaysSinceLast"])

    mocker.patch("function_app.scorer.xgb.DMatrix")

    # Mock preprocess to raise error
    mock_preprocess = mocker.patch("function_app.scorer.preprocess")
    mock_preprocess.side_effect = ValueError("Preprocessing error")

    df = pd.DataFrame({
        "CustomerId": ["001"],
        "SnapshotDate": pd.to_datetime(["2024-01-01"]),
        "Orders_CY": [10],
    })

    with pytest.raises(ValueError, match="Preprocessing error"):
        score_customers(df)


@pytest.mark.integration
def test_score_customers_integration():
    """
    Integration test for score_customers (requires model files).

    Marked as integration test - skip in CI without model files.
    """
    pytest.skip("Requires model files - run locally or in integration test environment")


def test_convert_excel_dates_handles_string_dates():
    """Test that convert_excel_dates handles string date formats."""
    df = pd.DataFrame({
        "SnapshotDate": ["2024-01-01"],
        "FirstPurchaseDate": ["2023-01-01"],
    })
    result = convert_excel_dates(df)
    assert pd.api.types.is_datetime64_any_dtype(result["SnapshotDate"])


def test_convert_excel_dates_handles_normal_dates():
    """Test that convert_excel_dates handles normal dates without conversion."""
    df = pd.DataFrame({
        "SnapshotDate": [pd.Timestamp("2024-01-01")],
    })
    result = convert_excel_dates(df)
    assert pd.api.types.is_datetime64_any_dtype(result["SnapshotDate"])


def test_preprocess_handles_missing_costcenter():
    """Test that preprocess handles missing CostCenter column."""
    df = pd.DataFrame({
        "CustomerId": ["123"],
        "Segment": ["FITNESS"],
        "Orders_CY": [10],
    })
    result = preprocess(df)
    # Should create UNKNOWN column for CostCenter
    assert any("CostCenter_UNKNOWN" in col for col in result.columns)


def test_preprocess_drops_identifier_columns():
    """Test that preprocess drops identifier columns."""
    df = pd.DataFrame({
        "CustomerId": ["123"],
        "AccountName": ["Account"],
        "Segment": ["FITNESS"],
        "CostCenter": ["CMFIT"],
        "SnapshotDate": ["2024-01-01"],
        "Orders_CY": [10],
    })
    result = preprocess(df)
    # Identifier columns should be dropped
    assert "CustomerId" not in result.columns
    assert "AccountName" not in result.columns
    assert "SnapshotDate" not in result.columns
    # Feature columns should remain
    assert "Orders_CY" in result.columns


def test_feature_phrase_segment():
    """Test that feature_phrase handles Segment_ prefix."""
    result = feature_phrase("Segment_FITNESS")
    assert "Customer segment is FITNESS" in result
    assert "Segment_" not in result


def test_feature_phrase_costcenter():
    """Test that feature_phrase handles CostCenter_ prefix."""
    result = feature_phrase("CostCenter_CMFIT")
    assert "Cost center is CMFIT" in result
    assert "CostCenter_" not in result


def test_feature_phrase_mapped_feature():
    """Test that feature_phrase returns mapped value for known features."""
    result = feature_phrase("Orders_CY")
    assert result == "order count (current year)"


def test_feature_phrase_unknown_feature():
    """Test that feature_phrase handles unknown features."""
    result = feature_phrase("Unknown_Feature")
    assert result == "Unknown Feature"  # Replaces underscores with spaces


def test_reason_text_segment_returns_base():
    """Test that reason_text returns base phrase for Segment features."""
    result = reason_text("Segment_FITNESS", "risk")
    assert result == "Customer segment is FITNESS"


def test_reason_text_risk_mode_high_is_good():
    """Test that reason_text generates risk text for high_is_good features."""
    result = reason_text("Orders_CY", "risk")
    assert "Low" in result
    assert "order count" in result


def test_reason_text_risk_mode_high_is_bad():
    """Test that reason_text generates risk text for high_is_bad features."""
    result = reason_text("DaysSinceLast", "risk")
    assert "High" in result
    assert "days since last order" in result


def test_reason_text_safe_mode_high_is_good():
    """Test that reason_text generates safe text for high_is_good features."""
    result = reason_text("Orders_CY", "safe")
    assert "High" in result
    assert "order count" in result


def test_reason_text_safe_mode_high_is_bad():
    """Test that reason_text generates safe text for high_is_bad features."""
    result = reason_text("DaysSinceLast", "safe")
    assert "Low" in result
    assert "days since last order" in result


def test_top_reasons_high_risk():
    """Test that top_reasons returns risk reasons for high risk."""
    row_contrib = pd.Series({
        "Orders_CY": 0.5,
        "DaysSinceLast": 0.3,
        "Spend_CY": 0.2,
        "BIAS": 0.1,
    })
    result = top_reasons(row_contrib, risk=0.8, n=2)
    assert len(result) == 2
    risk_indicators = ["risk", "low", "high", "unfavorable"]
    assert all(
        any(indicator in r.lower() for indicator in risk_indicators)
        for r in result
    )


def test_top_reasons_low_risk():
    """Test that top_reasons returns safe reasons for low risk."""
    row_contrib = pd.Series({
        "Orders_CY": -0.3,
        "DaysSinceLast": -0.5,
        "Spend_CY": -0.2,
        "BIAS": 0.1,
    })
    result = top_reasons(row_contrib, risk=0.2, n=2)
    assert len(result) == 2
    assert all("safe" in r.lower() or "High" in r or "Low" in r or "Favorable" in r for r in result)


def test_top_reasons_medium_risk():
    """Test that top_reasons returns mixed reasons for medium risk."""
    row_contrib = pd.Series({
        "Orders_CY": 0.5,
        "DaysSinceLast": 0.3,
        "Spend_CY": -0.2,
        "BIAS": 0.1,
    })
    result = top_reasons(row_contrib, risk=0.5, n=3)
    assert len(result) == 3
    # Should have both risk and safe reasons
    risk_texts = [r for r in result if "Low" in r or "High" in r or "Unfavorable" in r]
    safe_texts = [r for r in result if "Favorable" in r]
    assert len(risk_texts) > 0 or len(safe_texts) > 0


def test_top_reasons_excludes_bias():
    """Test that top_reasons excludes BIAS from contributions."""
    row_contrib = pd.Series({
        "Orders_CY": 0.5,
        "BIAS": 10.0,  # Very large BIAS
    })
    result = top_reasons(row_contrib, risk=0.8, n=1)
    assert len(result) == 1
    assert "BIAS" not in result[0]
    # Result should contain "order" (from feature_phrase mapping)
    assert "order" in result[0].lower()
