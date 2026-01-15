-- Churn Scoring System - Scalar Functions
-- Calculate customer status based on purchase dates

IF OBJECT_ID('dbo.fnCalculateStatus', 'FN') IS NOT NULL
    DROP FUNCTION dbo.fnCalculateStatus;
GO

CREATE FUNCTION dbo.fnCalculateStatus (
    @FirstPurchaseDate DATE,
    @LastPurchaseDate DATE
)
RETURNS NVARCHAR(20)
AS
BEGIN
    DECLARE @Status NVARCHAR(20);
    DECLARE @DaysSinceFirst INT;
    DECLARE @DaysSinceLast INT;
    
    -- Handle NULL dates
    IF @FirstPurchaseDate IS NULL AND @LastPurchaseDate IS NULL
        RETURN 'Unknown';
    
    -- Calculate days since first purchase
    IF @FirstPurchaseDate IS NOT NULL
        SET @DaysSinceFirst = DATEDIFF(DAY, @FirstPurchaseDate, GETDATE());
    ELSE
        SET @DaysSinceFirst = NULL;
    
    -- Calculate days since last purchase
    IF @LastPurchaseDate IS NOT NULL
        SET @DaysSinceLast = DATEDIFF(DAY, @LastPurchaseDate, GETDATE());
    ELSE
        SET @DaysSinceLast = NULL;
    
    -- Determine status
    -- 'New': FirstPurchaseDate within 365 days
    IF @DaysSinceFirst IS NOT NULL AND @DaysSinceFirst <= 365
        SET @Status = 'New'
    -- 'Active': LastPurchaseDate within 365 days
    ELSE IF @DaysSinceLast IS NOT NULL AND @DaysSinceLast <= 365
        SET @Status = 'Active'
    -- 'Churned': LastPurchaseDate > 365 days ago
    ELSE IF @DaysSinceLast IS NOT NULL AND @DaysSinceLast > 365
        SET @Status = 'Churned'
    ELSE
        SET @Status = 'Unknown';
    
    RETURN @Status;
END;
GO
