"""
SQL client for writing churn scores to database.
Uses azure-identity for authentication and pyodbc for connections.
"""

from datetime import datetime, date
from typing import Optional, Any
import pandas as pd
import pyodbc
from azure.identity import ManagedIdentityCredential

from .config import config


def get_connection() -> pyodbc.Connection:
    """Get SQL connection using Azure authentication."""
    connection_string = config.SQL_CONNECTION_STRING

    # Try Managed Identity first (for Azure Functions)
    try:
        credential = ManagedIdentityCredential()
        credential.get_token("https://database.windows.net/.default")

        # Add token to connection string if using Azure AD authentication
        # Note: pyodbc with Azure AD requires specific driver and connection string format
        # This is a simplified version - adjust based on your SQL authentication method
        conn = pyodbc.connect(connection_string, timeout=30)
    except (OSError, ConnectionError, TimeoutError):
        # Fallback to connection string authentication
        conn = pyodbc.connect(connection_string, timeout=30)

    return conn


def insert_churn_scores(df: pd.DataFrame) -> int:
    """
    Insert churn scores into database using stored procedure.

    Args:
        df: DataFrame with scored data (must include all required columns)

    Returns:
        Number of rows inserted/updated
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        rows_processed = 0

        # Convert DataFrame to list of dicts for easier processing
        for _, row in df.iterrows():
            # Prepare parameters for stored procedure
            # Extract values and handle None properly
            snapshot_date_val = row.get('SnapshotDate')
            first_purchase_val = row.get('FirstPurchaseDate')
            last_purchase_val = row.get('LastPurchaseDate')
            churn_risk_val = row.get('ChurnRiskPct')
            risk_band_val = row.get('RiskBand')
            reason_1_val = row.get('Reason_1')
            reason_2_val = row.get('Reason_2')
            reason_3_val = row.get('Reason_3')
            account_name_val = row.get('AccountName')
            segment_val = row.get('Segment')
            cost_center_val = row.get('CostCenter')

            # Helper function to safely convert date
            def safe_date_convert(val: Any) -> Optional[date]:
                if val is None:
                    return None
                try:
                    if pd.isna(val):  # type: ignore[arg-type]
                        return None
                    dt = pd.to_datetime(val)  # type: ignore[arg-type]
                    return dt.date()  # type: ignore[return-value]
                except (ValueError, TypeError):
                    return None

            # Helper function to safely convert to float
            def safe_float(val: Any) -> Optional[float]:
                if val is None:
                    return None
                try:
                    if pd.isna(val):  # type: ignore[arg-type]
                        return None
                    return float(val)  # type: ignore[arg-type]
                except (ValueError, TypeError):
                    return None

            # Helper function to safely convert to string
            def safe_str(val: Any) -> Optional[str]:
                if val is None:
                    return None
                try:
                    if pd.isna(val):  # type: ignore[arg-type]
                        return None
                    return str(val)  # type: ignore[arg-type]
                except (ValueError, TypeError):
                    return None

            params = {
                '@CustomerId': str(row.get('CustomerId', '')),
                '@SnapshotDate': safe_date_convert(snapshot_date_val),
                '@ChurnRiskPct': safe_float(churn_risk_val),
                '@RiskBand': safe_str(risk_band_val),
                '@Reason_1': safe_str(reason_1_val),
                '@Reason_2': safe_str(reason_2_val),
                '@Reason_3': safe_str(reason_3_val),
                '@ScoredAt': datetime.now(),
                '@AccountName': safe_str(account_name_val),
                '@Segment': safe_str(segment_val),
                '@CostCenter': safe_str(cost_center_val),
                '@FirstPurchaseDate': safe_date_convert(first_purchase_val),
                '@LastPurchaseDate': safe_date_convert(last_purchase_val),
            }

            # Add all feature columns
            feature_cols = [
                'Orders_CY', 'Orders_PY', 'Orders_Lifetime',
                'Spend_CY', 'Spend_PY', 'Spend_Lifetime',
                'Units_CY', 'Units_PY', 'Units_Lifetime',
                'AOV_CY', 'DaysSinceLast', 'TenureDays',
                'Spend_Trend', 'Orders_Trend', 'Units_Trend',
                'Uniforms_Units_CY', 'Uniforms_Units_PY', 'Uniforms_Units_Lifetime',
                'Uniforms_Spend_CY', 'Uniforms_Spend_PY', 'Uniforms_Spend_Lifetime',
                'Uniforms_Orders_CY', 'Uniforms_Orders_Lifetime',
                'Uniforms_DaysSinceLast', 'Uniforms_Pct_of_Total_CY',
                'Sparring_Units_CY', 'Sparring_Units_PY', 'Sparring_Units_Lifetime',
                'Sparring_Spend_CY', 'Sparring_Spend_PY', 'Sparring_Spend_Lifetime',
                'Sparring_Orders_CY', 'Sparring_Orders_Lifetime',
                'Sparring_DaysSinceLast', 'Sparring_Pct_of_Total_CY',
                'Belts_Units_CY', 'Belts_Units_PY', 'Belts_Units_Lifetime',
                'Belts_Spend_CY', 'Belts_Spend_PY', 'Belts_Spend_Lifetime',
                'Belts_Orders_CY', 'Belts_Orders_Lifetime',
                'Belts_DaysSinceLast', 'Belts_Pct_of_Total_CY',
                'Bags_Units_CY', 'Bags_Units_PY', 'Bags_Units_Lifetime',
                'Bags_Spend_CY', 'Bags_Spend_PY', 'Bags_Spend_Lifetime',
                'Bags_Orders_CY', 'Bags_Orders_Lifetime',
                'Bags_DaysSinceLast', 'Bags_Pct_of_Total_CY',
                'Customs_Units_CY', 'Customs_Units_PY', 'Customs_Units_Lifetime',
                'Customs_Spend_CY', 'Customs_Spend_PY', 'Customs_Spend_Lifetime',
                'Customs_Orders_CY', 'Customs_Orders_Lifetime',
                'Customs_DaysSinceLast', 'Customs_Pct_of_Total_CY',
                'CUBS_Categories_Active_CY', 'CUBS_Categories_Active_PY',
                'CUBS_Categories_Ever', 'CUBS_Categories_Trend',
            ]

            for col in feature_cols:
                param_name = f'@{col}'
                value = row.get(col)

                # Check if value is None or NaN
                if value is None or (isinstance(value, (float, int)) and pd.isna(value)):
                    params[param_name] = None
                    continue

                # Convert to appropriate type
                try:
                    if 'Pct' in col or 'Trend' in col:
                        params[param_name] = float(value)  # type: ignore[arg-type]
                    elif ('Date' in col or 'Days' in col or
                          col.endswith(('_CY', '_PY', '_Lifetime', '_Ever'))):
                        if 'Date' in col:
                            params[param_name] = safe_date_convert(value)
                        else:
                            params[param_name] = int(value)  # type: ignore[arg-type]
                    else:
                        params[param_name] = float(value)  # type: ignore[arg-type]
                except (ValueError, TypeError):
                    params[param_name] = None

            # Build stored procedure call
            sp_name = 'dbo.spInsertChurnScores'
            param_placeholders = ', '.join([f'{k}=?' for k in params])

            sql = f"EXEC {sp_name} {param_placeholders}"

            cursor.execute(sql, list(params.values()))
            rows_processed += 1

        conn.commit()
        return rows_processed

    except (OSError, ConnectionError, TimeoutError, ValueError) as e:
        if conn:
            conn.rollback()
        raise RuntimeError(f"Failed to insert churn scores: {str(e)}") from e
    finally:
        if conn:
            conn.close()
