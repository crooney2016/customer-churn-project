"""
Scoring module for churn prediction.
Loads model, preprocesses data, scores, and generates reasons.
"""

import pickle
from pathlib import Path
from typing import Tuple
import pandas as pd
import numpy as np
import xgboost as xgb


def normalize_cols(df: pd.DataFrame) -> pd.DataFrame:
    """Strip whitespace and remove square brackets from column names."""
    df = df.copy()
    df.columns = (
        df.columns.astype(str)
        .str.strip()
        .str.replace(r"^\[", "", regex=True)
        .str.replace(r"\]$", "", regex=True)
    )
    return df


def convert_excel_dates(df: pd.DataFrame) -> pd.DataFrame:
    """Convert Excel serial dates (values > 40000) to datetime."""
    df = df.copy()
    date_cols = ["SnapshotDate", "FirstPurchaseDate", "LastPurchaseDate"]

    for col in date_cols:
        if col in df.columns:
            if df[col].dtype in [np.int64, np.float64]:
                mask = df[col] > 40000
                if mask.any():
                    excel_dates = (
                        pd.Timestamp('1899-12-30') +
                        pd.to_timedelta(df.loc[mask, col], unit='D')
                    )
                    df[col] = pd.to_datetime(df[col], errors='coerce')
                    df.loc[mask, col] = excel_dates
            else:
                df[col] = pd.to_datetime(df[col], errors='coerce')

    return df


def preprocess(df: pd.DataFrame) -> pd.DataFrame:
    """Preprocess DataFrame for model scoring."""
    df = df.copy()

    if "AccountName" in df.columns:
        df["AccountName"] = df["AccountName"].fillna("").astype(str).str.strip()
    if "Segment" in df.columns:
        df["Segment"] = df["Segment"].fillna("UNKNOWN").astype(str).str.strip()
    if "CostCenter" in df.columns:
        df["CostCenter"] = df["CostCenter"].fillna("UNKNOWN").astype(str).str.strip()

    drop_cols = [
        "CustomerId", "AccountName", "Segment", "CostCenter",
        "SnapshotDate", "FirstPurchaseDate", "LastPurchaseDate",
        "WillChurn90"
    ]

    # X is standard ML convention for feature matrix
    X = df.drop(columns=[c for c in drop_cols if c in df.columns], errors="ignore")  # pylint: disable=invalid-name

    seg_default = pd.Series(["UNKNOWN"] * len(df), index=df.index)
    seg = df["Segment"] if "Segment" in df.columns else seg_default
    cc_default = pd.Series(["UNKNOWN"] * len(df), index=df.index)
    cc = df["CostCenter"] if "CostCenter" in df.columns else cc_default

    X = pd.concat([X, pd.get_dummies(seg, prefix="Segment")], axis=1)  # pylint: disable=invalid-name
    X = pd.concat([X, pd.get_dummies(cc, prefix="CostCenter")], axis=1)  # pylint: disable=invalid-name

    return X


def risk_band(prob: float) -> str:
    """Calculate risk band from probability."""
    if prob >= 0.7:
        return "A - High Risk"
    elif prob >= 0.3:
        return "B - Medium Risk"
    else:
        return "C - Low Risk"


def feature_phrase(name: str) -> str:
    """Base phrase for a feature (no polarity)."""
    if name.startswith("Segment_"):
        return f"Customer segment is {name.replace('Segment_', '')}"
    if name.startswith("CostCenter_"):
        return f"Cost center is {name.replace('CostCenter_', '')}"

    mapping = {
        "Orders_CY": "order count (current year)",
        "Orders_PY": "order count (prior year)",
        "Orders_Lifetime": "lifetime order count",
        "Spend_CY": "spend (current year)",
        "Spend_PY": "spend (prior year)",
        "Spend_Lifetime": "lifetime spend",
        "Units_CY": "units purchased (current year)",
        "Units_PY": "units purchased (prior year)",
        "Units_Lifetime": "lifetime units",
        "AOV_CY": "average order value",
        "DaysSinceLast": "days since last order",
        "TenureDays": "customer tenure (days)",
        "Uniforms_Units_CY": "uniforms units (current year)",
        "Uniforms_Spend_CY": "uniforms spend (current year)",
        "Uniforms_Orders_CY": "uniforms orders (current year)",
        "Uniforms_Pct_of_Total_CY": "uniforms % of total spend",
        "Uniforms_DaysSinceLast": "days since last uniforms order",
        "Sparring_Units_CY": "sparring units (current year)",
        "Sparring_Spend_CY": "sparring spend (current year)",
        "Sparring_Orders_CY": "sparring orders (current year)",
        "Sparring_Pct_of_Total_CY": "sparring % of total spend",
        "Sparring_DaysSinceLast": "days since last sparring order",
        "Belts_Units_CY": "belts units (current year)",
        "Belts_Spend_CY": "belts spend (current year)",
        "Belts_Orders_CY": "belts orders (current year)",
        "Belts_Pct_of_Total_CY": "belts % of total spend",
        "Belts_DaysSinceLast": "days since last belts order",
        "Bags_Units_CY": "bags units (current year)",
        "Bags_Spend_CY": "bags spend (current year)",
        "Bags_Orders_CY": "bags orders (current year)",
        "Bags_Pct_of_Total_CY": "bags % of total spend",
        "Bags_DaysSinceLast": "days since last bags order",
        "Customs_Units_CY": "customs units (current year)",
        "Customs_Spend_CY": "customs spend (current year)",
        "Customs_Orders_CY": "customs orders (current year)",
        "Customs_Pct_of_Total_CY": "customs % of total spend",
        "Customs_DaysSinceLast": "days since last customs order",
        "CUBS_Categories_Active_CY": "product categories active (current year)",
        "CUBS_Categories_Active_PY": "product categories active (prior year)",
        "CUBS_Categories_Ever": "product categories ever purchased",
    }
    return mapping.get(name, name.replace("_", " "))


def reason_text(feature: str, mode: str) -> str:
    """Generate reason text. mode: 'risk' (drivers) or 'safe' (protective)."""
    base = feature_phrase(feature)

    if feature.startswith("Segment_") or feature.startswith("CostCenter_"):
        return base

    high_is_good = [
        "Orders_CY", "Orders_PY", "Orders_Lifetime",
        "Spend_CY", "Spend_PY", "Spend_Lifetime",
        "Units_CY", "Units_PY", "Units_Lifetime",
        "AOV_CY", "TenureDays",
        "Uniforms_Units_CY", "Uniforms_Spend_CY", "Uniforms_Orders_CY",
        "Sparring_Units_CY", "Sparring_Spend_CY", "Sparring_Orders_CY",
        "Belts_Units_CY", "Belts_Spend_CY", "Belts_Orders_CY",
        "Bags_Units_CY", "Bags_Spend_CY", "Bags_Orders_CY",
        "Customs_Units_CY", "Customs_Spend_CY", "Customs_Orders_CY",
        "CUBS_Categories_Active_CY", "CUBS_Categories_Active_PY",
        "CUBS_Categories_Ever",
    ]

    high_is_bad = [
        "DaysSinceLast",
        "Uniforms_DaysSinceLast", "Sparring_DaysSinceLast",
        "Belts_DaysSinceLast", "Bags_DaysSinceLast", "Customs_DaysSinceLast",
    ]

    if mode == "risk":
        if feature in high_is_good:
            return f"Low {base}"
        if feature in high_is_bad:
            return f"High {base}"
        return f"Unfavorable {base}"
    else:
        if feature in high_is_good:
            return f"High {base}"
        if feature in high_is_bad:
            return f"Low {base}"
        return f"Favorable {base}"


def top_reasons(row_contrib: pd.Series, risk: float, n: int = 3) -> list:
    """Generate top N reasons from feature contributions."""
    s = row_contrib.drop(labels=["BIAS"], errors="ignore")

    if risk >= 0.7:
        feats = [str(f) for f in s.sort_values(ascending=False).head(n).index.tolist()]
        return [reason_text(f, "risk") for f in feats]

    if risk < 0.3:
        feats = [str(f) for f in s.sort_values(ascending=True).head(n).index.tolist()]
        return [reason_text(f, "safe") for f in feats]

    pos = [str(f) for f in s.sort_values(ascending=False).head(2).index.tolist()]
    neg = [str(f) for f in s.sort_values(ascending=True).head(1).index.tolist()]
    risk_reasons = [reason_text(f, "risk") for f in pos]
    safe_reasons = [reason_text(f, "safe") for f in neg]
    return (risk_reasons + safe_reasons)[:n]


def load_model() -> Tuple[object, list]:
    """Load XGBoost model and model columns."""
    model_dir = Path(__file__).parent / "model"
    model_path = model_dir / "churn_model.pkl"
    model_columns_path = model_dir / "model_columns.pkl"

    if not model_path.exists():
        raise FileNotFoundError(f"Model file not found: {model_path}")
    if not model_columns_path.exists():
        raise FileNotFoundError(
            f"Model columns file not found: {model_columns_path}"
        )

    with open(model_path, "rb") as f:
        model = pickle.load(f)
    with open(model_columns_path, "rb") as f:
        model_columns = pickle.load(f)

    return model, model_columns


def score_customers(df: pd.DataFrame) -> pd.DataFrame:
    """
    Score customers and generate reasons.

    Args:
        df: Input DataFrame with 77 DAX feature columns

    Returns:
        DataFrame with ChurnRiskPct, RiskBand, Reason_1-3, and all original columns
    """
    # Normalize and preprocess
    df = normalize_cols(df)
    df = convert_excel_dates(df)

    # Store original columns
    id_cols = [
        "CustomerId", "AccountName", "Segment", "CostCenter", "SnapshotDate"
    ]
    original_df = df[id_cols].copy()
    exclude_cols = ["FirstPurchaseDate", "LastPurchaseDate", "WillChurn90"]
    feature_cols = [
        c for c in df.columns
        if c not in id_cols + exclude_cols
    ]

    # Preprocess features
    # X is standard ML convention for feature matrix
    X = preprocess(df)  # pylint: disable=invalid-name

    # Load model
    model, model_columns = load_model()

    # Align columns
    X = X.reindex(columns=model_columns, fill_value=0)  # pylint: disable=invalid-name

    # Score
    probs = model.predict_proba(X)[:, 1]  # type: ignore[attr-defined]  # pylint: disable=invalid-name

    # Generate reasons
    dm = xgb.DMatrix(X)  # pylint: disable=invalid-name
    contrib = model.get_booster().predict(dm, pred_contribs=True)  # type: ignore[attr-defined]
    columns_list = list(X.columns) + ["BIAS"]  # pylint: disable=invalid-name
    contrib_df = pd.DataFrame(contrib, columns=columns_list)  # type: ignore[call-overload]

    reasons_rows = []
    for i in range(len(X)):  # pylint: disable=invalid-name
        reasons_rows.append(
            top_reasons(contrib_df.iloc[i], float(probs[i]), n=3)
        )

    reasons_df = pd.DataFrame(
        reasons_rows, columns=["Reason_1", "Reason_2", "Reason_3"]  # type: ignore[call-overload]
    )

    # Build output
    output = original_df.copy()
    output["ChurnRiskPct"] = probs
    output["RiskBand"] = output["ChurnRiskPct"].apply(risk_band)  # type: ignore[union-attr]
    output = pd.concat([output, reasons_df], axis=1)

    # Add all original feature columns
    for col in feature_cols:
        if col in df.columns:
            output[col] = df[col]

    return output
