-- Churn Scoring System - Database Permissions
-- Grants database roles to admin user and verifies permissions
-- This script should be run FIRST before creating any tables/procedures
-- 
-- Usage: Replace @AdminUser with the actual database username from connection string
-- Example: EXEC sp_grant_permissions @AdminUser = 'your_username'

-- =============================================================================
-- Grant Database Roles
-- =============================================================================

-- Grant read access (SELECT on all tables)
-- Grant write access (INSERT, UPDATE, DELETE on all tables)
-- Grant DDL access (CREATE, ALTER, DROP on tables/procedures/functions)

-- Note: Replace @AdminUser with actual username from connection string
-- This will be parameterized in the deployment script

-- Example GRANT statements (will be executed dynamically in deployment script):
-- ALTER ROLE db_datareader ADD MEMBER @AdminUser;
-- ALTER ROLE db_datawriter ADD MEMBER @AdminUser;
-- ALTER ROLE db_ddladmin ADD MEMBER @AdminUser;

-- =============================================================================
-- Permission Verification Queries
-- =============================================================================

-- These queries test that permissions are working correctly
-- They should be run AFTER granting permissions to verify access

-- Test 1: Verify SELECT permission (db_datareader)
-- SELECT 1 AS PermissionTest_Select FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = 'dbo';

-- Test 2: Verify INSERT permission (db_datawriter)
-- Create a temporary test table and insert a row
-- IF OBJECT_ID('tempdb..#PermissionTest', 'U') IS NOT NULL DROP TABLE #PermissionTest;
-- CREATE TABLE #PermissionTest (TestId INT, TestValue NVARCHAR(50));
-- INSERT INTO #PermissionTest (TestId, TestValue) VALUES (1, 'INSERT_TEST');
-- SELECT COUNT(*) AS PermissionTest_Insert FROM #PermissionTest;
-- DROP TABLE #PermissionTest;

-- Test 3: Verify UPDATE permission (db_datawriter)
-- IF OBJECT_ID('tempdb..#PermissionTest', 'U') IS NOT NULL DROP TABLE #PermissionTest;
-- CREATE TABLE #PermissionTest (TestId INT, TestValue NVARCHAR(50));
-- INSERT INTO #PermissionTest (TestId, TestValue) VALUES (1, 'UPDATE_TEST');
-- UPDATE #PermissionTest SET TestValue = 'UPDATED' WHERE TestId = 1;
-- SELECT TestValue AS PermissionTest_Update FROM #PermissionTest WHERE TestId = 1;
-- DROP TABLE #PermissionTest;

-- Test 4: Verify DELETE permission (db_datawriter)
-- IF OBJECT_ID('tempdb..#PermissionTest', 'U') IS NOT NULL DROP TABLE #PermissionTest;
-- CREATE TABLE #PermissionTest (TestId INT, TestValue NVARCHAR(50));
-- INSERT INTO #PermissionTest (TestId, TestValue) VALUES (1, 'DELETE_TEST');
-- DELETE FROM #PermissionTest WHERE TestId = 1;
-- SELECT COUNT(*) AS PermissionTest_Delete FROM #PermissionTest;
-- DROP TABLE #PermissionTest;

-- Test 5: Verify DDL permission (db_ddladmin) - Create a test table
-- IF OBJECT_ID('dbo.PermissionTest_DDL', 'U') IS NOT NULL DROP TABLE dbo.PermissionTest_DDL;
-- CREATE TABLE dbo.PermissionTest_DDL (TestId INT);
-- SELECT 1 AS PermissionTest_DDL FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'PermissionTest_DDL';
-- DROP TABLE dbo.PermissionTest_DDL;

-- =============================================================================
-- Notes
-- =============================================================================

-- These queries are commented out because they will be executed dynamically
-- by the deployment script (scripts/deploy_sql_schema.py) which will:
-- 1. Extract username from connection string
-- 2. Grant permissions using dynamic SQL
-- 3. Execute verification queries
-- 4. Fail early if any verification fails
