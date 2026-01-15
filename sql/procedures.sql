-- Churn Scoring System - Stored Procedures
-- Insert churn scores with duplicate check

IF OBJECT_ID('dbo.spInsertChurnScores', 'P') IS NOT NULL
    DROP PROCEDURE dbo.spInsertChurnScores;
GO

CREATE PROCEDURE dbo.spInsertChurnScores
    @CustomerId NVARCHAR(50),
    @SnapshotDate DATE,
    @ChurnRiskPct DECIMAL(5,4) = NULL,
    @RiskBand NVARCHAR(20) = NULL,
    @Reason_1 NVARCHAR(255) = NULL,
    @Reason_2 NVARCHAR(255) = NULL,
    @Reason_3 NVARCHAR(255) = NULL,
    @ScoredAt DATETIME2 = NULL,
    @AccountName NVARCHAR(255) = NULL,
    @Segment NVARCHAR(50) = NULL,
    @CostCenter NVARCHAR(50) = NULL,
    @FirstPurchaseDate DATE = NULL,
    @LastPurchaseDate DATE = NULL,
    @Orders_CY INT = NULL,
    @Orders_PY INT = NULL,
    @Orders_Lifetime INT = NULL,
    @Spend_CY DECIMAL(18,2) = NULL,
    @Spend_PY DECIMAL(18,2) = NULL,
    @Spend_Lifetime DECIMAL(18,2) = NULL,
    @Units_CY INT = NULL,
    @Units_PY INT = NULL,
    @Units_Lifetime INT = NULL,
    @AOV_CY DECIMAL(18,2) = NULL,
    @DaysSinceLast INT = NULL,
    @TenureDays INT = NULL,
    @Spend_Trend DECIMAL(18,6) = NULL,
    @Orders_Trend DECIMAL(18,6) = NULL,
    @Units_Trend DECIMAL(18,6) = NULL,
    @Uniforms_Units_CY INT = NULL,
    @Uniforms_Units_PY INT = NULL,
    @Uniforms_Units_Lifetime INT = NULL,
    @Uniforms_Spend_CY DECIMAL(18,2) = NULL,
    @Uniforms_Spend_PY DECIMAL(18,2) = NULL,
    @Uniforms_Spend_Lifetime DECIMAL(18,2) = NULL,
    @Uniforms_Orders_CY INT = NULL,
    @Uniforms_Orders_Lifetime INT = NULL,
    @Uniforms_DaysSinceLast INT = NULL,
    @Uniforms_Pct_of_Total_CY DECIMAL(18,6) = NULL,
    @Sparring_Units_CY INT = NULL,
    @Sparring_Units_PY INT = NULL,
    @Sparring_Units_Lifetime INT = NULL,
    @Sparring_Spend_CY DECIMAL(18,2) = NULL,
    @Sparring_Spend_PY DECIMAL(18,2) = NULL,
    @Sparring_Spend_Lifetime DECIMAL(18,2) = NULL,
    @Sparring_Orders_CY INT = NULL,
    @Sparring_Orders_Lifetime INT = NULL,
    @Sparring_DaysSinceLast INT = NULL,
    @Sparring_Pct_of_Total_CY DECIMAL(18,6) = NULL,
    @Belts_Units_CY INT = NULL,
    @Belts_Units_PY INT = NULL,
    @Belts_Units_Lifetime INT = NULL,
    @Belts_Spend_CY DECIMAL(18,2) = NULL,
    @Belts_Spend_PY DECIMAL(18,2) = NULL,
    @Belts_Spend_Lifetime DECIMAL(18,2) = NULL,
    @Belts_Orders_CY INT = NULL,
    @Belts_Orders_Lifetime INT = NULL,
    @Belts_DaysSinceLast INT = NULL,
    @Belts_Pct_of_Total_CY DECIMAL(18,6) = NULL,
    @Bags_Units_CY INT = NULL,
    @Bags_Units_PY INT = NULL,
    @Bags_Units_Lifetime INT = NULL,
    @Bags_Spend_CY DECIMAL(18,2) = NULL,
    @Bags_Spend_PY DECIMAL(18,2) = NULL,
    @Bags_Spend_Lifetime DECIMAL(18,2) = NULL,
    @Bags_Orders_CY INT = NULL,
    @Bags_Orders_Lifetime INT = NULL,
    @Bags_DaysSinceLast INT = NULL,
    @Bags_Pct_of_Total_CY DECIMAL(18,6) = NULL,
    @Customs_Units_CY INT = NULL,
    @Customs_Units_PY INT = NULL,
    @Customs_Units_Lifetime INT = NULL,
    @Customs_Spend_CY DECIMAL(18,2) = NULL,
    @Customs_Spend_PY DECIMAL(18,2) = NULL,
    @Customs_Spend_Lifetime DECIMAL(18,2) = NULL,
    @Customs_Orders_CY INT = NULL,
    @Customs_Orders_Lifetime INT = NULL,
    @Customs_DaysSinceLast INT = NULL,
    @Customs_Pct_of_Total_CY DECIMAL(18,6) = NULL,
    @CUBS_Categories_Active_CY INT = NULL,
    @CUBS_Categories_Active_PY INT = NULL,
    @CUBS_Categories_Ever INT = NULL,
    @CUBS_Categories_Trend DECIMAL(18,6) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    
    BEGIN TRANSACTION;
    
    BEGIN TRY
        -- Check for duplicate
        IF EXISTS (
            SELECT 1 
            FROM dbo.ChurnScoresHistory 
            WHERE CustomerId = @CustomerId 
                AND SnapshotDate = @SnapshotDate
        )
        BEGIN
            -- Update existing record
            UPDATE dbo.ChurnScoresHistory
            SET
                ChurnRiskPct = @ChurnRiskPct,
                RiskBand = @RiskBand,
                Reason_1 = @Reason_1,
                Reason_2 = @Reason_2,
                Reason_3 = @Reason_3,
                ScoredAt = @ScoredAt,
                AccountName = @AccountName,
                Segment = @Segment,
                CostCenter = @CostCenter,
                FirstPurchaseDate = @FirstPurchaseDate,
                LastPurchaseDate = @LastPurchaseDate,
                Orders_CY = @Orders_CY,
                Orders_PY = @Orders_PY,
                Orders_Lifetime = @Orders_Lifetime,
                Spend_CY = @Spend_CY,
                Spend_PY = @Spend_PY,
                Spend_Lifetime = @Spend_Lifetime,
                Units_CY = @Units_CY,
                Units_PY = @Units_PY,
                Units_Lifetime = @Units_Lifetime,
                AOV_CY = @AOV_CY,
                DaysSinceLast = @DaysSinceLast,
                TenureDays = @TenureDays,
                Spend_Trend = @Spend_Trend,
                Orders_Trend = @Orders_Trend,
                Units_Trend = @Units_Trend,
                Uniforms_Units_CY = @Uniforms_Units_CY,
                Uniforms_Units_PY = @Uniforms_Units_PY,
                Uniforms_Units_Lifetime = @Uniforms_Units_Lifetime,
                Uniforms_Spend_CY = @Uniforms_Spend_CY,
                Uniforms_Spend_PY = @Uniforms_Spend_PY,
                Uniforms_Spend_Lifetime = @Uniforms_Spend_Lifetime,
                Uniforms_Orders_CY = @Uniforms_Orders_CY,
                Uniforms_Orders_Lifetime = @Uniforms_Orders_Lifetime,
                Uniforms_DaysSinceLast = @Uniforms_DaysSinceLast,
                Uniforms_Pct_of_Total_CY = @Uniforms_Pct_of_Total_CY,
                Sparring_Units_CY = @Sparring_Units_CY,
                Sparring_Units_PY = @Sparring_Units_PY,
                Sparring_Units_Lifetime = @Sparring_Units_Lifetime,
                Sparring_Spend_CY = @Sparring_Spend_CY,
                Sparring_Spend_PY = @Sparring_Spend_PY,
                Sparring_Spend_Lifetime = @Sparring_Spend_Lifetime,
                Sparring_Orders_CY = @Sparring_Orders_CY,
                Sparring_Orders_Lifetime = @Sparring_Orders_Lifetime,
                Sparring_DaysSinceLast = @Sparring_DaysSinceLast,
                Sparring_Pct_of_Total_CY = @Sparring_Pct_of_Total_CY,
                Belts_Units_CY = @Belts_Units_CY,
                Belts_Units_PY = @Belts_Units_PY,
                Belts_Units_Lifetime = @Belts_Units_Lifetime,
                Belts_Spend_CY = @Belts_Spend_CY,
                Belts_Spend_PY = @Belts_Spend_PY,
                Belts_Spend_Lifetime = @Belts_Spend_Lifetime,
                Belts_Orders_CY = @Belts_Orders_CY,
                Belts_Orders_Lifetime = @Belts_Orders_Lifetime,
                Belts_DaysSinceLast = @Belts_DaysSinceLast,
                Belts_Pct_of_Total_CY = @Belts_Pct_of_Total_CY,
                Bags_Units_CY = @Bags_Units_CY,
                Bags_Units_PY = @Bags_Units_PY,
                Bags_Units_Lifetime = @Bags_Units_Lifetime,
                Bags_Spend_CY = @Bags_Spend_CY,
                Bags_Spend_PY = @Bags_Spend_PY,
                Bags_Spend_Lifetime = @Bags_Spend_Lifetime,
                Bags_Orders_CY = @Bags_Orders_CY,
                Bags_Orders_Lifetime = @Bags_Orders_Lifetime,
                Bags_DaysSinceLast = @Bags_DaysSinceLast,
                Bags_Pct_of_Total_CY = @Bags_Pct_of_Total_CY,
                Customs_Units_CY = @Customs_Units_CY,
                Customs_Units_PY = @Customs_Units_PY,
                Customs_Units_Lifetime = @Customs_Units_Lifetime,
                Customs_Spend_CY = @Customs_Spend_CY,
                Customs_Spend_PY = @Customs_Spend_PY,
                Customs_Spend_Lifetime = @Customs_Spend_Lifetime,
                Customs_Orders_CY = @Customs_Orders_CY,
                Customs_Orders_Lifetime = @Customs_Orders_Lifetime,
                Customs_DaysSinceLast = @Customs_DaysSinceLast,
                Customs_Pct_of_Total_CY = @Customs_Pct_of_Total_CY,
                CUBS_Categories_Active_CY = @CUBS_Categories_Active_CY,
                CUBS_Categories_Active_PY = @CUBS_Categories_Active_PY,
                CUBS_Categories_Ever = @CUBS_Categories_Ever,
                CUBS_Categories_Trend = @CUBS_Categories_Trend
            WHERE CustomerId = @CustomerId 
                AND SnapshotDate = @SnapshotDate;
        END
        ELSE
        BEGIN
            -- Insert new record
            INSERT INTO dbo.ChurnScoresHistory (
                CustomerId, SnapshotDate, ChurnRiskPct, RiskBand, Reason_1, Reason_2, Reason_3, ScoredAt,
                AccountName, Segment, CostCenter, FirstPurchaseDate, LastPurchaseDate,
                Orders_CY, Orders_PY, Orders_Lifetime,
                Spend_CY, Spend_PY, Spend_Lifetime,
                Units_CY, Units_PY, Units_Lifetime,
                AOV_CY, DaysSinceLast, TenureDays, Spend_Trend, Orders_Trend, Units_Trend,
                Uniforms_Units_CY, Uniforms_Units_PY, Uniforms_Units_Lifetime,
                Uniforms_Spend_CY, Uniforms_Spend_PY, Uniforms_Spend_Lifetime,
                Uniforms_Orders_CY, Uniforms_Orders_Lifetime, Uniforms_DaysSinceLast, Uniforms_Pct_of_Total_CY,
                Sparring_Units_CY, Sparring_Units_PY, Sparring_Units_Lifetime,
                Sparring_Spend_CY, Sparring_Spend_PY, Sparring_Spend_Lifetime,
                Sparring_Orders_CY, Sparring_Orders_Lifetime, Sparring_DaysSinceLast, Sparring_Pct_of_Total_CY,
                Belts_Units_CY, Belts_Units_PY, Belts_Units_Lifetime,
                Belts_Spend_CY, Belts_Spend_PY, Belts_Spend_Lifetime,
                Belts_Orders_CY, Belts_Orders_Lifetime, Belts_DaysSinceLast, Belts_Pct_of_Total_CY,
                Bags_Units_CY, Bags_Units_PY, Bags_Units_Lifetime,
                Bags_Spend_CY, Bags_Spend_PY, Bags_Spend_Lifetime,
                Bags_Orders_CY, Bags_Orders_Lifetime, Bags_DaysSinceLast, Bags_Pct_of_Total_CY,
                Customs_Units_CY, Customs_Units_PY, Customs_Units_Lifetime,
                Customs_Spend_CY, Customs_Spend_PY, Customs_Spend_Lifetime,
                Customs_Orders_CY, Customs_Orders_Lifetime, Customs_DaysSinceLast, Customs_Pct_of_Total_CY,
                CUBS_Categories_Active_CY, CUBS_Categories_Active_PY, CUBS_Categories_Ever, CUBS_Categories_Trend
            )
            VALUES (
                @CustomerId, @SnapshotDate, @ChurnRiskPct, @RiskBand, @Reason_1, @Reason_2, @Reason_3, @ScoredAt,
                @AccountName, @Segment, @CostCenter, @FirstPurchaseDate, @LastPurchaseDate,
                @Orders_CY, @Orders_PY, @Orders_Lifetime,
                @Spend_CY, @Spend_PY, @Spend_Lifetime,
                @Units_CY, @Units_PY, @Units_Lifetime,
                @AOV_CY, @DaysSinceLast, @TenureDays, @Spend_Trend, @Orders_Trend, @Units_Trend,
                @Uniforms_Units_CY, @Uniforms_Units_PY, @Uniforms_Units_Lifetime,
                @Uniforms_Spend_CY, @Uniforms_Spend_PY, @Uniforms_Spend_Lifetime,
                @Uniforms_Orders_CY, @Uniforms_Orders_Lifetime, @Uniforms_DaysSinceLast, @Uniforms_Pct_of_Total_CY,
                @Sparring_Units_CY, @Sparring_Units_PY, @Sparring_Units_Lifetime,
                @Sparring_Spend_CY, @Sparring_Spend_PY, @Sparring_Spend_Lifetime,
                @Sparring_Orders_CY, @Sparring_Orders_Lifetime, @Sparring_DaysSinceLast, @Sparring_Pct_of_Total_CY,
                @Belts_Units_CY, @Belts_Units_PY, @Belts_Units_Lifetime,
                @Belts_Spend_CY, @Belts_Spend_PY, @Belts_Spend_Lifetime,
                @Belts_Orders_CY, @Belts_Orders_Lifetime, @Belts_DaysSinceLast, @Belts_Pct_of_Total_CY,
                @Bags_Units_CY, @Bags_Units_PY, @Bags_Units_Lifetime,
                @Bags_Spend_CY, @Bags_Spend_PY, @Bags_Spend_Lifetime,
                @Bags_Orders_CY, @Bags_Orders_Lifetime, @Bags_DaysSinceLast, @Bags_Pct_of_Total_CY,
                @Customs_Units_CY, @Customs_Units_PY, @Customs_Units_Lifetime,
                @Customs_Spend_CY, @Customs_Spend_PY, @Customs_Spend_Lifetime,
                @Customs_Orders_CY, @Customs_Orders_Lifetime, @Customs_DaysSinceLast, @Customs_Pct_of_Total_CY,
                @CUBS_Categories_Active_CY, @CUBS_Categories_Active_PY, @CUBS_Categories_Ever, @CUBS_Categories_Trend
            );
        END
        
        COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0
            ROLLBACK TRANSACTION;
        
        DECLARE @ErrorMessage NVARCHAR(4000) = ERROR_MESSAGE();
        DECLARE @ErrorSeverity INT = ERROR_SEVERITY();
        DECLARE @ErrorState INT = ERROR_STATE();
        
        RAISERROR(@ErrorMessage, @ErrorSeverity, @ErrorState);
    END CATCH
END;
GO
