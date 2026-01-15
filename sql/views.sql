-- Churn Scoring System - Views
-- Latest row per customer with calculated Status

IF OBJECT_ID('dbo.vwCustomerCurrent', 'V') IS NOT NULL
    DROP VIEW dbo.vwCustomerCurrent;
GO

CREATE VIEW dbo.vwCustomerCurrent
AS
WITH LatestSnapshots AS (
    SELECT 
        CustomerId,
        SnapshotDate,
        ROW_NUMBER() OVER (
            PARTITION BY CustomerId 
            ORDER BY SnapshotDate DESC
        ) AS RowNum
    FROM dbo.ChurnScoresHistory
),
CurrentSnapshot AS (
    SELECT 
        h.*,
        LAG(dbo.fnCalculateStatus(h.FirstPurchaseDate, h.LastPurchaseDate)) OVER (
            PARTITION BY h.CustomerId 
            ORDER BY h.SnapshotDate
        ) AS PriorStatus
    FROM dbo.ChurnScoresHistory h
    INNER JOIN LatestSnapshots ls 
        ON h.CustomerId = ls.CustomerId 
        AND h.SnapshotDate = ls.SnapshotDate
    WHERE ls.RowNum = 1
)
SELECT 
    CustomerId,
    SnapshotDate,
    ChurnRiskPct,
    RiskBand,
    Reason_1,
    Reason_2,
    Reason_3,
    ScoredAt,
    AccountName,
    Segment,
    CostCenter,
    FirstPurchaseDate,
    LastPurchaseDate,
    -- Calculate current status
    CASE 
        WHEN PriorStatus = 'Churned' 
            AND dbo.fnCalculateStatus(FirstPurchaseDate, LastPurchaseDate) = 'Active'
        THEN 'Reactivated'
        ELSE dbo.fnCalculateStatus(FirstPurchaseDate, LastPurchaseDate)
    END AS Status,
    -- All feature columns
    Orders_CY,
    Orders_PY,
    Orders_Lifetime,
    Spend_CY,
    Spend_PY,
    Spend_Lifetime,
    Units_CY,
    Units_PY,
    Units_Lifetime,
    AOV_CY,
    DaysSinceLast,
    TenureDays,
    Spend_Trend,
    Orders_Trend,
    Units_Trend,
    Uniforms_Units_CY,
    Uniforms_Units_PY,
    Uniforms_Units_Lifetime,
    Uniforms_Spend_CY,
    Uniforms_Spend_PY,
    Uniforms_Spend_Lifetime,
    Uniforms_Orders_CY,
    Uniforms_Orders_Lifetime,
    Uniforms_DaysSinceLast,
    Uniforms_Pct_of_Total_CY,
    Sparring_Units_CY,
    Sparring_Units_PY,
    Sparring_Units_Lifetime,
    Sparring_Spend_CY,
    Sparring_Spend_PY,
    Sparring_Spend_Lifetime,
    Sparring_Orders_CY,
    Sparring_Orders_Lifetime,
    Sparring_DaysSinceLast,
    Sparring_Pct_of_Total_CY,
    Belts_Units_CY,
    Belts_Units_PY,
    Belts_Units_Lifetime,
    Belts_Spend_CY,
    Belts_Spend_PY,
    Belts_Spend_Lifetime,
    Belts_Orders_CY,
    Belts_Orders_Lifetime,
    Belts_DaysSinceLast,
    Belts_Pct_of_Total_CY,
    Bags_Units_CY,
    Bags_Units_PY,
    Bags_Units_Lifetime,
    Bags_Spend_CY,
    Bags_Spend_PY,
    Bags_Spend_Lifetime,
    Bags_Orders_CY,
    Bags_Orders_Lifetime,
    Bags_DaysSinceLast,
    Bags_Pct_of_Total_CY,
    Customs_Units_CY,
    Customs_Units_PY,
    Customs_Units_Lifetime,
    Customs_Spend_CY,
    Customs_Spend_PY,
    Customs_Spend_Lifetime,
    Customs_Orders_CY,
    Customs_Orders_Lifetime,
    Customs_DaysSinceLast,
    Customs_Pct_of_Total_CY,
    CUBS_Categories_Active_CY,
    CUBS_Categories_Active_PY,
    CUBS_Categories_Ever,
    CUBS_Categories_Trend
FROM CurrentSnapshot;
GO
