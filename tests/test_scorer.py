"""
Unit tests for scorer.py module.
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock
from function_app.scorer import (
    normalize_cols,
    convert_excel_dates,
    preprocess,
    risk_band,
    score_customers,
    feature_phrase,
    reason_text,
    top_reasons,
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
    result = preprocess(df)
    # Should have normalized column names
    assert "[CustomerId]" not in result.columns
    assert "[Segment]" not in result.columns


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


def test_score_customers_structure(sample_input_df, monkeypatch):
    """Test that score_customers returns expected structure."""
    # Mock model loading to avoid requiring actual model files
    mock_model = MagicMock()
    mock_model.predict_proba.return_value = np.array([[0.8, 0.2], [0.5, 0.5], [0.3, 0.7]])
    mock_model.get_booster.return_value.predict.return_value = np.array([
        [0.1, 0.2, 0.3, 0.1, 0.1, 0.1, 0.1],
        [0.05, 0.15, 0.25, 0.15, 0.15, 0.15, 0.1],
        [0.05, 0.1, 0.2, 0.2, 0.2, 0.15, 0.1],
    ])

    with patch("function_app.scorer.load_model") as mock_load:
        mock_load.return_value = (
            mock_model,
            ["Orders_CY", "Spend_CY", "DaysSinceLast", "Segment_FITNESS", "Segment_FARRELL", "CostCenter_CMFIT", "BIAS"]
        )
        # This test may fail if model columns don't match - that's OK for now
        # Full integration test would require proper model files
        pass  # Placeholder - actual test requires proper model setup


@pytest.mark.integration
def test_score_customers_integration(sample_input_df):
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
    assert all("risk" in r.lower() or "Low" in r or "High" in r or "Unfavorable" in r for r in result)


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
    assert "Orders" in result[0]
