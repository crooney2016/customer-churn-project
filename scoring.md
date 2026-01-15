# Scoring Rules

## Input Handling

- Strip brackets: [Column] → Column
- Excel dates (>40000) → datetime
- Null Segment/CostCenter → "UNKNOWN"

## Preprocessing

1. Strip column brackets
2. Convert Excel dates
3. Fill null categoricals
4. One-hot encode Segment/CostCenter
5. Align to model_columns.pkl
6. Fill missing columns with 0

## Scoring

```python
probs = model.predict_proba(X)[:, 1]
```

## Risk Bands

- A (High): >= 0.7
- B (Medium): >= 0.3
- C (Low): < 0.3

## Reasons

Use XGBoost contributions (not SHAP):

```python
dm = xgb.DMatrix(X)
contrib = model.get_booster().predict(dm, pred_contribs=True)
```

- High Risk: Top 3 positive contributors
- Low Risk: Top 3 negative contributors
- Medium Risk: Top 2 positive + 1 negative

## Output Column Order

```
CustomerId, AccountName, Segment, CostCenter, SnapshotDate,
ChurnRiskPct, RiskBand, Reason_1, Reason_2, Reason_3, ScoredAt,
[...77 DAX features...]
```

## Reason Mapping

```
Orders_CY      → "Low/High order count (current year)"
DaysSinceLast  → "High/Low days since last order"
Spend_Lifetime → "Low/High lifetime spend"
Segment_X      → "Customer segment is X"
```
