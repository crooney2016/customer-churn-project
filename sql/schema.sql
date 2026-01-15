-- Churn Scoring System - Database Schema
-- System of record table for historical churn scores

IF OBJECT_ID('dbo.ChurnScoresHistory', 'U') IS NOT NULL
    DROP TABLE dbo.ChurnScoresHistory;
GO

CREATE TABLE dbo.ChurnScoresHistory (
    -- Primary key columns
    CustomerId          NVARCHAR(50)    NOT NULL,
    SnapshotDate        DATE            NOT NULL,
    
    -- Score columns
    ChurnRiskPct        DECIMAL(5,4)    NULL,
    RiskBand            NVARCHAR(20)    NULL,
    Reason_1            NVARCHAR(255)    NULL,
    Reason_2            NVARCHAR(255)    NULL,
    Reason_3            NVARCHAR(255)    NULL,
    ScoredAt            DATETIME2       NULL,
    
    -- Identity columns
    AccountName         NVARCHAR(255)   NULL,
    Segment             NVARCHAR(50)    NULL,
    CostCenter          NVARCHAR(50)    NULL,
    
    -- Date columns
    FirstPurchaseDate   DATE            NULL,
    LastPurchaseDate   DATE            NULL,
    
    -- Aggregate features (Orders)
    Orders_CY           INT             NULL,
    Orders_PY           INT             NULL,
    Orders_Lifetime      INT             NULL,
    
    -- Aggregate features (Spend)
    Spend_CY            DECIMAL(18,2)   NULL,
    Spend_PY            DECIMAL(18,2)   NULL,
    Spend_Lifetime      DECIMAL(18,2)   NULL,
    
    -- Aggregate features (Units)
    Units_CY            INT             NULL,
    Units_PY            INT             NULL,
    Units_Lifetime      INT             NULL,
    
    -- Aggregate features (Other)
    AOV_CY              DECIMAL(18,2)   NULL,
    DaysSinceLast       INT             NULL,
    TenureDays          INT             NULL,
    Spend_Trend         DECIMAL(18,6)   NULL,
    Orders_Trend        DECIMAL(18,6)   NULL,
    Units_Trend         DECIMAL(18,6)   NULL,
    
    -- Uniforms category features
    Uniforms_Units_CY           INT             NULL,
    Uniforms_Units_PY           INT             NULL,
    Uniforms_Units_Lifetime     INT             NULL,
    Uniforms_Spend_CY           DECIMAL(18,2)   NULL,
    Uniforms_Spend_PY           DECIMAL(18,2)   NULL,
    Uniforms_Spend_Lifetime     DECIMAL(18,2)   NULL,
    Uniforms_Orders_CY          INT             NULL,
    Uniforms_Orders_Lifetime    INT             NULL,
    Uniforms_DaysSinceLast      INT             NULL,
    Uniforms_Pct_of_Total_CY    DECIMAL(18,6)   NULL,
    
    -- Sparring category features
    Sparring_Units_CY           INT             NULL,
    Sparring_Units_PY           INT             NULL,
    Sparring_Units_Lifetime     INT             NULL,
    Sparring_Spend_CY           DECIMAL(18,2)   NULL,
    Sparring_Spend_PY           DECIMAL(18,2)   NULL,
    Sparring_Spend_Lifetime     DECIMAL(18,2)   NULL,
    Sparring_Orders_CY          INT             NULL,
    Sparring_Orders_Lifetime    INT             NULL,
    Sparring_DaysSinceLast      INT             NULL,
    Sparring_Pct_of_Total_CY    DECIMAL(18,6)   NULL,
    
    -- Belts category features
    Belts_Units_CY              INT             NULL,
    Belts_Units_PY              INT             NULL,
    Belts_Units_Lifetime         INT             NULL,
    Belts_Spend_CY              DECIMAL(18,2)   NULL,
    Belts_Spend_PY              DECIMAL(18,2)   NULL,
    Belts_Spend_Lifetime         DECIMAL(18,2)   NULL,
    Belts_Orders_CY             INT             NULL,
    Belts_Orders_Lifetime        INT             NULL,
    Belts_DaysSinceLast          INT             NULL,
    Belts_Pct_of_Total_CY        DECIMAL(18,6)   NULL,
    
    -- Bags category features
    Bags_Units_CY               INT             NULL,
    Bags_Units_PY               INT             NULL,
    Bags_Units_Lifetime          INT             NULL,
    Bags_Spend_CY               DECIMAL(18,2)   NULL,
    Bags_Spend_PY               DECIMAL(18,2)   NULL,
    Bags_Spend_Lifetime          DECIMAL(18,2)   NULL,
    Bags_Orders_CY              INT             NULL,
    Bags_Orders_Lifetime         INT             NULL,
    Bags_DaysSinceLast           INT             NULL,
    Bags_Pct_of_Total_CY         DECIMAL(18,6)   NULL,
    
    -- Customs category features
    Customs_Units_CY            INT             NULL,
    Customs_Units_PY             INT             NULL,
    Customs_Units_Lifetime       INT             NULL,
    Customs_Spend_CY             DECIMAL(18,2)   NULL,
    Customs_Spend_PY             DECIMAL(18,2)   NULL,
    Customs_Spend_Lifetime       DECIMAL(18,2)   NULL,
    Customs_Orders_CY           INT             NULL,
    Customs_Orders_Lifetime      INT             NULL,
    Customs_DaysSinceLast        INT             NULL,
    Customs_Pct_of_Total_CY      DECIMAL(18,6)   NULL,
    
    -- CUBS breadth features
    CUBS_Categories_Active_CY    INT             NULL,
    CUBS_Categories_Active_PY    INT             NULL,
    CUBS_Categories_Ever         INT             NULL,
    CUBS_Categories_Trend        DECIMAL(18,6)   NULL,
    
    -- Primary key constraint
    CONSTRAINT PK_ChurnScoresHistory PRIMARY KEY (CustomerId, SnapshotDate)
);
GO

-- Create index on SnapshotDate for efficient date-based queries
CREATE NONCLUSTERED INDEX IX_ChurnScoresHistory_SnapshotDate 
    ON dbo.ChurnScoresHistory (SnapshotDate DESC);
GO

-- Create index on CustomerId for efficient customer lookups
CREATE NONCLUSTERED INDEX IX_ChurnScoresHistory_CustomerId 
    ON dbo.ChurnScoresHistory (CustomerId, SnapshotDate DESC);
GO
