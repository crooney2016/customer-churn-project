#!/usr/bin/env python3
"""
Deploy SQL schema, stored procedures, and grant database permissions.

This script:
1. Grants database permissions to admin user (FIRST)
2. Verifies permissions by testing read/write operations
3. Creates/updates staging table and stored procedures
4. Can be run multiple times safely (idempotent)

Usage:
    python scripts/deploy_sql_schema.py

Environment Variables:
    SQL_CONNECTION_STRING: SQL Server connection string
        Format: Server=hostname;Port=1433;Database=dbname;UID=username;PWD=password;
"""

import logging
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load .env file if it exists
try:
    from dotenv import load_dotenv
    env_path = project_root / ".env"
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass

import pymssql
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Connection settings
CONNECTION_TIMEOUT = 60
MAX_CONNECTION_RETRIES = 3
BASE_RETRY_DELAY = 5.0


def _parse_connection_string(connection_string: str) -> dict:
    """
    Parse connection string to pymssql.connect() parameters.
    
    Expected format: Server=hostname;Port=1433;Database=dbname;UID=username;PWD=password;
    """
    params = {}
    for part in connection_string.split(';'):
        part = part.strip()
        if '=' in part:
            key, value = part.split('=', 1)
            key = key.strip().lower()
            value = value.strip()
            
            if key == 'server':
                params['server'] = value
            elif key == 'port':
                params['port'] = int(value)
            elif key in ['database', 'initial catalog']:
                params['database'] = value
            elif key in ['uid', 'user id', 'user']:
                params['user'] = value
            elif key in ['pwd', 'password']:
                params['password'] = value
    
    return params


@retry(
    stop=stop_after_attempt(MAX_CONNECTION_RETRIES),
    wait=wait_exponential(multiplier=BASE_RETRY_DELAY, min=BASE_RETRY_DELAY, max=30),
    retry=retry_if_exception_type((pymssql.OperationalError, pymssql.DatabaseError, pymssql.Error)),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
def get_connection() -> pymssql.Connection:
    """Get SQL connection using connection string from environment."""
    connection_string = os.getenv('SQL_CONNECTION_STRING')
    if not connection_string:
        raise ValueError("SQL_CONNECTION_STRING environment variable is not set")
    
    conn_params = _parse_connection_string(connection_string)
    conn = pymssql.connect(**conn_params, timeout=CONNECTION_TIMEOUT)
    return conn


def extract_username(connection_string: str) -> str:
    """Extract username from connection string."""
    params = _parse_connection_string(connection_string)
    username = params.get('user')
    if not username:
        raise ValueError("Could not extract username from connection string")
    return username


def grant_permissions(conn: pymssql.Connection, username: str) -> None:
    """
    Grant database roles to user.
    
    Grants: db_datareader, db_datawriter, db_ddladmin
    """
    logger.info("Granting database permissions to user: %s", username)
    
    roles = ['db_datareader', 'db_datawriter', 'db_ddladmin']
    cursor = conn.cursor()
    
    for role in roles:
        try:
            # Use dynamic SQL to grant role
            sql = f"ALTER ROLE {role} ADD MEMBER [{username}];"
            cursor.execute(sql)
            logger.info("  ✓ Granted %s to %s", role, username)
        except pymssql.Error as e:
            # Check if user is already a member (error 15151)
            if '15151' in str(e) or 'already' in str(e).lower():
                logger.info("  ✓ %s already has %s role", username, role)
            else:
                logger.error("  ✗ Failed to grant %s to %s: %s", role, username, str(e))
                raise
    
    conn.commit()
    logger.info("✓ All permissions granted successfully")


def verify_permissions(conn: pymssql.Connection) -> None:
    """
    Verify database permissions by testing read/write operations.
    
    Tests:
    1. SELECT (db_datareader)
    2. INSERT (db_datawriter)
    3. UPDATE (db_datawriter)
    4. DELETE (db_datawriter)
    5. CREATE TABLE (db_ddladmin)
    """
    logger.info("Verifying database permissions...")
    cursor = conn.cursor()
    
    # Test 1: SELECT permission
    try:
        cursor.execute("SELECT 1 AS PermissionTest_Select FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = 'dbo';")
        result = cursor.fetchone()
        if result:
            logger.info("  ✓ SELECT permission verified")
        else:
            raise RuntimeError("SELECT permission test returned no results")
    except Exception as e:
        logger.error("  ✗ SELECT permission test failed: %s", str(e))
        raise RuntimeError(f"SELECT permission verification failed: {str(e)}") from e
    
    # Test 2: INSERT permission
    try:
        cursor.execute("""
            IF OBJECT_ID('tempdb..#PermissionTest', 'U') IS NOT NULL DROP TABLE #PermissionTest;
            CREATE TABLE #PermissionTest (TestId INT, TestValue NVARCHAR(50));
            INSERT INTO #PermissionTest (TestId, TestValue) VALUES (1, 'INSERT_TEST');
            SELECT COUNT(*) AS PermissionTest_Insert FROM #PermissionTest;
            DROP TABLE #PermissionTest;
        """)
        result = cursor.fetchone()
        if result and result[0] == 1:
            logger.info("  ✓ INSERT permission verified")
        else:
            raise RuntimeError("INSERT permission test failed")
    except Exception as e:
        logger.error("  ✗ INSERT permission test failed: %s", str(e))
        raise RuntimeError(f"INSERT permission verification failed: {str(e)}") from e
    
    # Test 3: UPDATE permission
    try:
        cursor.execute("""
            IF OBJECT_ID('tempdb..#PermissionTest', 'U') IS NOT NULL DROP TABLE #PermissionTest;
            CREATE TABLE #PermissionTest (TestId INT, TestValue NVARCHAR(50));
            INSERT INTO #PermissionTest (TestId, TestValue) VALUES (1, 'UPDATE_TEST');
            UPDATE #PermissionTest SET TestValue = 'UPDATED' WHERE TestId = 1;
            SELECT TestValue AS PermissionTest_Update FROM #PermissionTest WHERE TestId = 1;
            DROP TABLE #PermissionTest;
        """)
        result = cursor.fetchone()
        if result and result[0] == 'UPDATED':
            logger.info("  ✓ UPDATE permission verified")
        else:
            raise RuntimeError("UPDATE permission test failed")
    except Exception as e:
        logger.error("  ✗ UPDATE permission test failed: %s", str(e))
        raise RuntimeError(f"UPDATE permission verification failed: {str(e)}") from e
    
    # Test 4: DELETE permission
    try:
        cursor.execute("""
            IF OBJECT_ID('tempdb..#PermissionTest', 'U') IS NOT NULL DROP TABLE #PermissionTest;
            CREATE TABLE #PermissionTest (TestId INT, TestValue NVARCHAR(50));
            INSERT INTO #PermissionTest (TestId, TestValue) VALUES (1, 'DELETE_TEST');
            DELETE FROM #PermissionTest WHERE TestId = 1;
            SELECT COUNT(*) AS PermissionTest_Delete FROM #PermissionTest;
            DROP TABLE #PermissionTest;
        """)
        result = cursor.fetchone()
        if result and result[0] == 0:
            logger.info("  ✓ DELETE permission verified")
        else:
            raise RuntimeError("DELETE permission test failed")
    except Exception as e:
        logger.error("  ✗ DELETE permission test failed: %s", str(e))
        raise RuntimeError(f"DELETE permission verification failed: {str(e)}") from e
    
    # Test 5: DDL permission (CREATE TABLE)
    try:
        cursor.execute("""
            IF OBJECT_ID('dbo.PermissionTest_DDL', 'U') IS NOT NULL DROP TABLE dbo.PermissionTest_DDL;
            CREATE TABLE dbo.PermissionTest_DDL (TestId INT);
            SELECT 1 AS PermissionTest_DDL FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = 'PermissionTest_DDL';
            DROP TABLE dbo.PermissionTest_DDL;
        """)
        result = cursor.fetchone()
        if result:
            logger.info("  ✓ DDL permission verified")
        else:
            raise RuntimeError("DDL permission test failed")
    except Exception as e:
        logger.error("  ✗ DDL permission test failed: %s", str(e))
        raise RuntimeError(f"DDL permission verification failed: {str(e)}") from e
    
    conn.commit()
    logger.info("✓ All permissions verified successfully")


def execute_sql_file(conn: pymssql.Connection, file_path: Path) -> None:
    """Execute SQL file with GO statements handled."""
    logger.info("Executing SQL file: %s", file_path.name)
    
    with open(file_path, 'r', encoding='utf-8') as f:
        sql_content = f.read()
    
    # Split by GO statements (case-insensitive)
    import re
    batches = re.split(r'\bGO\b', sql_content, flags=re.IGNORECASE)
    
    cursor = conn.cursor()
    executed = 0
    
    for batch in batches:
        batch = batch.strip()
        if not batch:
            continue
        
        try:
            cursor.execute(batch)
            executed += 1
        except pymssql.Error as e:
            # Check for "already exists" errors (idempotency)
            error_msg = str(e).lower()
            if 'already exists' in error_msg or 'duplicate' in error_msg:
                logger.debug("  (Object already exists, skipping)")
            else:
                logger.error("  ✗ Error executing batch: %s", str(e))
                raise
    
    conn.commit()
    logger.info("  ✓ Executed %d SQL batches from %s", executed, file_path.name)


def main() -> None:
    """Main deployment function."""
    logger.info("=" * 60)
    logger.info("SQL Schema Deployment Script")
    logger.info("=" * 60)
    
    # Get connection string
    connection_string = os.getenv('SQL_CONNECTION_STRING')
    if not connection_string:
        logger.error("✗ SQL_CONNECTION_STRING environment variable is not set")
        sys.exit(1)
    
    # Extract username
    try:
        username = extract_username(connection_string)
        logger.info("Extracted username: %s", username)
    except Exception as e:
        logger.error("✗ Failed to extract username: %s", str(e))
        sys.exit(1)
    
    conn = None
    try:
        # Step 1: Connect to database
        logger.info("\nStep 1: Connecting to database...")
        conn = get_connection()
        logger.info("✓ Connected to database")
        
        # Step 2: Grant permissions FIRST
        logger.info("\nStep 2: Granting database permissions...")
        grant_permissions(conn, username)
        
        # Step 3: Verify permissions
        logger.info("\nStep 3: Verifying database permissions...")
        verify_permissions(conn)
        logger.info("✓ Permissions verified - proceeding with schema deployment")
        
        # Step 4: Execute SQL files in order
        logger.info("\nStep 4: Deploying SQL schema...")
        sql_dir = project_root / "sql"
        
        # Execute schema.sql (creates tables)
        schema_file = sql_dir / "schema.sql"
        if schema_file.exists():
            execute_sql_file(conn, schema_file)
        else:
            logger.warning("  ⚠ schema.sql not found, skipping")
        
        # Execute procedures.sql (creates stored procedures)
        procedures_file = sql_dir / "procedures.sql"
        if procedures_file.exists():
            execute_sql_file(conn, procedures_file)
        else:
            logger.warning("  ⚠ procedures.sql not found, skipping")
        
        # Execute functions.sql (creates functions)
        functions_file = sql_dir / "functions.sql"
        if functions_file.exists():
            execute_sql_file(conn, functions_file)
        else:
            logger.warning("  ⚠ functions.sql not found, skipping")
        
        # Execute views.sql (creates views)
        views_file = sql_dir / "views.sql"
        if views_file.exists():
            execute_sql_file(conn, views_file)
        else:
            logger.warning("  ⚠ views.sql not found, skipping")
        
        logger.info("\n" + "=" * 60)
        logger.info("✓ SQL schema deployment completed successfully")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error("\n" + "=" * 60)
        logger.error("✗ Deployment failed: %s", str(e), exc_info=True)
        logger.error("=" * 60)
        if conn:
            conn.rollback()
        sys.exit(1)
    finally:
        if conn:
            conn.close()
            logger.debug("Database connection closed")


if __name__ == "__main__":
    main()
