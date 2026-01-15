import os
import pickle
import pandas as pd
import numpy as np

def init():
    """Called once when the deployment starts."""
    global model, model_columns
    
    model_dir = os.getenv("AZUREML_MODEL_DIR")
    model_path = os.path.join(model_dir, "model")
    
    model = pickle.load(open(os.path.join(model_path, "churn_model.pkl"), "rb"))
    model_columns = pickle.load(open(os.path.join(model_path, "model_columns.pkl"), "rb"))


def run(mini_batch):
    """Called for each batch of input data."""
    results = []
    
    for file_path in mini_batch:
        df = pd.read_csv(file_path)
        df = normalize_cols(df)
        
        # Score each row
        X = preprocess(df)
        X = X.reindex(columns=model_columns, fill_value=0)
        
        probs = model.predict_proba(X)[:, 1]
        
        # Build output - NO REASONS (fast)
        out = df[["CustomerId", "AccountName", "Segment", "CostCenter", "SnapshotDate"]].copy()
        out["ChurnRiskPct"] = probs
        out["RiskBand"] = out["ChurnRiskPct"].apply(risk_band)
        out["Reason_1"] = ""
        out["Reason_2"] = ""
        out["Reason_3"] = ""
        
        results.append(out)
    
    return pd.concat(results, ignore_index=True)


def normalize_cols(df):
    df = df.copy()
    df.columns = (
        df.columns.astype(str)
        .str.strip()
        .str.replace(r"^\[", "", regex=True)
        .str.replace(r"\]$", "", regex=True)
    )
    return df


def preprocess(df):
    """Match the training preprocessing exactly."""
    df = df.copy()
    
    if "Segment" in df.columns:
        df["Segment"] = df["Segment"].fillna("UNKNOWN").astype(str).str.strip()
    if "CostCenter" in df.columns:
        df["CostCenter"] = df["CostCenter"].fillna("UNKNOWN").astype(str).str.strip()
    
    drop_cols = ["CustomerId", "AccountName", "Segment", "CostCenter", 
                 "SnapshotDate", "FirstPurchaseDate", "LastPurchaseDate",
                 "WillChurn90"]
    
    X = df.drop(columns=[c for c in drop_cols if c in df.columns], errors="ignore")
    
    seg = df["Segment"] if "Segment" in df.columns else pd.Series(["UNKNOWN"] * len(df))
    cc = df["CostCenter"] if "CostCenter" in df.columns else pd.Series(["UNKNOWN"] * len(df))
    
    X = pd.concat([X, pd.get_dummies(seg, prefix="Segment")], axis=1)
    X = pd.concat([X, pd.get_dummies(cc, prefix="CostCenter")], axis=1)
    
    return X


def risk_band(prob):
    if prob >= 0.7:
        return "A - High Risk"
    elif prob >= 0.3:
        return "B - Medium Risk"
    else:
        return "C - Low Risk"