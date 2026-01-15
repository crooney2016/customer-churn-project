# SQL Rules

## Tables

### dbo.ChurnScoresHistory

System of record. Append-only.

```sql
CustomerId          NVARCHAR(50)    -- PK
SnapshotDate        DATE            -- PK
ChurnRiskPct        DECIMAL(5,4)
RiskBand            NVARCHAR(20)
Reason_1            NVARCHAR(255)
Reason_2            NVARCHAR(255)
Reason_3            NVARCHAR(255)
ScoredAt            DATETIME2
[...77 feature columns...]
```

Primary key: (CustomerId, SnapshotDate)

## Views

### dbo.vwCustomerCurrent

- Latest row per customer
- Derives Status via fnCalculateStatus

## Functions

### dbo.fnCalculateStatus

Input: FirstPurchaseDate, LastPurchaseDate

Returns:
- 'New': First purchase within 365 days
- 'Active': Last purchase within 365 days
- 'Churned': Last purchase > 365 days ago

### Reactivated

View compares current to prior snapshot:
- Prior = Churned AND Current = Active → Reactivated

## Procedures

### dbo.spInsertChurnScores

- INSERT with duplicate check
- Single transaction
- Rollback on failure

## Deployment Order

1. schema.sql
2. functions.sql
3. views.sql
4. procedures.sql

## Best Practices

- Parameterized queries only
- Include IF EXISTS checks
- Status in SQL, not Python
- Pivot/trends in Power BI DAX
