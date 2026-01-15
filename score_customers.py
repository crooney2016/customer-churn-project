#!/usr/bin/env python3
"""
Local scoring script for churn prediction.

Usage:
    python score_customers.py <input_csv_path>

Output:
    outputs/churn_scores.csv with all 77 features + ChurnRiskPct, RiskBand, Reason_1-3, ScoredAt
"""

import sys
import os
import pickle
import pandas as pd
import numpy as np
import xgboost as xgb
from datetime import datetime
from pathlib import Path


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
            # Check if values are Excel serial dates (numeric and > 40000)
            if df[col].dtype in [np.int64, np.float64]:
                mask = df[col] > 40000
                if mask.any():
                    # Excel serial date: days since 1899-12-30 (Excel's epoch)
                    # Excel incorrectly treats 1900 as leap year, so we use 1899-12-30
                    # Convert to datetime and assign to new series to avoid dtype warning
                    excel_dates = pd.Timestamp('1899-12-30') + pd.to_timedelta(df.loc[mask, col], unit='D')
                    # Convert entire column to datetime, then update Excel dates
                    df[col] = pd.to_datetime(df[col], errors='coerce')
                    df.loc[mask, col] = excel_dates
            else:
                # Try to parse as datetime string
                df[col] = pd.to_datetime(df[col], errors='coerce')
    
    return df


def preprocess(df: pd.DataFrame) -> pd.DataFrame:
    """Preprocess DataFrame for model scoring."""
    df = df.copy()
    
    # Clean categorical columns
    if "AccountName" in df.columns:
        df["AccountName"] = df["AccountName"].fillna("").astype(str).str.strip()
    if "Segment" in df.columns:
        df["Segment"] = df["Segment"].fillna("UNKNOWN").astype(str).str.strip()
    if "CostCenter" in df.columns:
        df["CostCenter"] = df["CostCenter"].fillna("UNKNOWN").astype(str).str.strip()
    
    # Drop non-feature columns
    drop_cols = [
        "CustomerId", "AccountName", "Segment", "CostCenter",
        "SnapshotDate", "FirstPurchaseDate", "LastPurchaseDate",
        "WillChurn90"
    ]
    
    X = df.drop(columns=[c for c in drop_cols if c in df.columns], errors="ignore")
    
    # One-hot encode Segment and CostCenter
    seg = df["Segment"] if "Segment" in df.columns else pd.Series(["UNKNOWN"] * len(df), index=df.index)
    cc = df["CostCenter"] if "CostCenter" in df.columns else pd.Series(["UNKNOWN"] * len(df), index=df.index)
    
    X = pd.concat([X, pd.get_dummies(seg, prefix="Segment")], axis=1)
    X = pd.concat([X, pd.get_dummies(cc, prefix="CostCenter")], axis=1)
    
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
        # Aggregate features
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
        
        # CUBS category features
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
        
        # Breadth features
        "CUBS_Categories_Active_CY": "product categories active (current year)",
        "CUBS_Categories_Active_PY": "product categories active (prior year)",
        "CUBS_Categories_Ever": "product categories ever purchased",
    }
    return mapping.get(name, name.replace("_", " "))


def reason_text(feature: str, mode: str) -> str:
    """Generate reason text. mode: 'risk' (drivers) or 'safe' (protective)."""
    base = feature_phrase(feature)
    
    # Segment/CostCenter: keep as-is
    if feature.startswith("Segment_") or feature.startswith("CostCenter_"):
        return base
    
    # Features where HIGH value = LOW risk (protective)
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
        "CUBS_Categories_Active_CY", "CUBS_Categories_Active_PY", "CUBS_Categories_Ever",
    ]
    
    # Features where HIGH value = HIGH risk
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
    else:  # safe
        if feature in high_is_good:
            return f"High {base}"
        if feature in high_is_bad:
            return f"Low {base}"
        return f"Favorable {base}"


def top_reasons(row_contrib: pd.Series, risk: float, n: int = 3) -> list:
    """Generate top N reasons from feature contributions."""
    s = row_contrib.drop(labels=["BIAS"], errors="ignore")
    
    if risk >= 0.7:
        # High risk: top positive contributors
        feats = s.sort_values(ascending=False).head(n).index.tolist()
        return [reason_text(f, "risk") for f in feats]
    
    if risk < 0.3:
        # Low risk: top negative contributors (protective)
        feats = s.sort_values(ascending=True).head(n).index.tolist()
        return [reason_text(f, "safe") for f in feats]
    
    # Medium: 2 risk drivers + 1 protective
    pos = s.sort_values(ascending=False).head(2).index.tolist()
    neg = s.sort_values(ascending=True).head(1).index.tolist()
    return ([reason_text(f, "risk") for f in pos] + [reason_text(f, "safe") for f in neg])[:n]


def generate_reasons(model, X: pd.DataFrame, probs: np.ndarray) -> pd.DataFrame:
    """Generate reasons using XGBoost contributions."""
    # Get feature contributions
    dm = xgb.DMatrix(X)
    contrib = model.get_booster().predict(dm, pred_contribs=True)
    contrib_df = pd.DataFrame(contrib, columns=list(X.columns) + ["BIAS"])
    
    # Generate reasons for each row
    reasons_rows = []
    for i in range(len(X)):
        reasons_rows.append(top_reasons(contrib_df.iloc[i], float(probs[i]), n=3))
    
    return pd.DataFrame(reasons_rows, columns=["Reason_1", "Reason_2", "Reason_3"])


def main():
    if len(sys.argv) != 2:
        print("Usage: python score_customers.py <input_csv_path>")
        sys.exit(1)
    
    input_path = sys.argv[1]
    if not os.path.exists(input_path):
        print(f"Error: Input file not found: {input_path}")
        sys.exit(1)
    
    # Load model
    model_dir = Path("model")
    model_path = model_dir / "churn_model.pkl"
    model_columns_path = model_dir / "model_columns.pkl"
    
    if not model_path.exists():
        print(f"Error: Model file not found: {model_path}")
        sys.exit(1)
    if not model_columns_path.exists():
        print(f"Error: Model columns file not found: {model_columns_path}")
        sys.exit(1)
    
    print("Loading model...")
    with open(model_path, "rb") as f:
        model = pickle.load(f)
    with open(model_columns_path, "rb") as f:
        model_columns = pickle.load(f)
    
    # Load and preprocess input data
    print(f"Loading input data from {input_path}...")
    df = pd.read_csv(input_path)
    
    print("Normalizing column names...")
    df = normalize_cols(df)
    
    print("Converting Excel dates...")
    df = convert_excel_dates(df)
    
    # Store original columns for output
    id_cols = ["CustomerId", "AccountName", "Segment", "CostCenter", "SnapshotDate"]
    original_df = df[id_cols].copy()
    
    # Get all 77 original feature columns (excluding ID columns and target)
    feature_cols = [c for c in df.columns if c not in id_cols + ["FirstPurchaseDate", "LastPurchaseDate", "WillChurn90"]]
    
    print("Preprocessing features...")
    X = preprocess(df)
    
    # Align columns to model_columns.pkl order
    X = X.reindex(columns=model_columns, fill_value=0)
    
    # Score
    print("Scoring customers...")
    probs = model.predict_proba(X)[:, 1]
    
    # Generate reasons
    print("Generating reasons...")
    reasons_df = generate_reasons(model, X, probs)
    
    # Build output DataFrame
    output = original_df.copy()
    output["ChurnRiskPct"] = probs
    output["RiskBand"] = output["ChurnRiskPct"].apply(risk_band)
    output = pd.concat([output, reasons_df], axis=1)
    output["ScoredAt"] = datetime.now()
    
    # Add all 77 original DAX features
    for col in feature_cols:
        if col in df.columns:
            output[col] = df[col]
    
    # Ensure correct column order: ID cols + score cols + all 77 features
    output_cols = id_cols + ["ChurnRiskPct", "RiskBand", "Reason_1", "Reason_2", "Reason_3", "ScoredAt"] + feature_cols
    output = output[[c for c in output_cols if c in output.columns]]
    
    # Write output
    output_dir = Path("outputs")
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / "churn_scores.csv"
    
    print(f"Writing output to {output_path}...")
    output.to_csv(output_path, index=False)
    
    print(f"Successfully scored {len(output)} customers")
    print(f"Risk distribution:")
    print(output["RiskBand"].value_counts())


if __name__ == "__main__":
    main()
