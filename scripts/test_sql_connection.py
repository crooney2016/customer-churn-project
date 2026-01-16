#!/usr/bin/env python3
"""
Test script for SQL database connection.

Usage:
    python scripts/test_sql_connection.py

The script will:
1. Load environment variables from .env file
2. Validate SQL configuration
3. Establish a connection to the database
4. Execute a simple test query
5. Display connection information and results
"""

import logging
import os
import sys
from pathlib import Path

# Add function_app to path so we can import it
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

# pylint: disable=wrong-import-position
import pymssql

# Configure logging - suppress verbose library logs
logging.basicConfig(
    level=logging.WARNING,  # Only show warnings and errors by default
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)
# Set our logger to INFO for user-facing messages
logger.setLevel(logging.INFO)


def validate_config() -> str:
    """Validate that required SQL configuration is present."""
    connection_string = os.getenv('SQL_CONNECTION_STRING')
    if not connection_string:
        print("✗ Missing configuration: SQL_CONNECTION_STRING")
        print("  Please set this in your .env file or environment variables")
        sys.exit(1)
    return connection_string


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


def get_connection(connection_string: str):
    """
    Get SQL connection using connection string.
    
    Args:
        connection_string: SQL Server connection string (format: Server=hostname;Port=1433;Database=dbname;UID=username;PWD=password;)
        
    Returns:
        pymssql connection object
    """
    logger.debug("Establishing SQL database connection")
    conn_params = _parse_connection_string(connection_string)
    conn = pymssql.connect(**conn_params, timeout=60)
    logger.debug("SQL connection established successfully")
    return conn


def test_connection() -> None:
    """Test SQL connection and execute a simple query."""
    conn = None
    try:
        # Validate configuration
        print("=" * 60)
        print("SQL Connection Test")
        print("=" * 60)
        connection_string = validate_config()
        print("✓ Configuration validated")

        # Mask connection string for display (show only first few chars)
        conn_str_preview = connection_string[:50] + "..." if len(connection_string) > 50 else connection_string
        print(f"✓ Connection string: {conn_str_preview}")

        # Establish connection
        print("\nEstablishing connection...")
        conn = get_connection(connection_string)
        print("✓ Connection established successfully")

        # Create cursor
        cursor = conn.cursor()

        # Test query 1: Simple SELECT
        print("\nExecuting test query: SELECT 1")
        cursor.execute("SELECT 1 AS test_value")
        result = cursor.fetchone()
        if result:
            print(f"✓ Query result: {result[0]}")

        # Test query 2: Get SQL Server version
        print("\nExecuting test query: SELECT @@VERSION")
        cursor.execute("SELECT @@VERSION AS version")
        version_result = cursor.fetchone()
        if version_result:
            version_str = version_result[0]
            # Display first line of version string
            version_first_line = version_str.split('\n')[0] if '\n' in version_str else version_str
            print(f"✓ SQL Server version: {version_first_line[:80]}...")

        # Test query 3: Get current database name
        print("\nExecuting test query: SELECT DB_NAME()")
        cursor.execute("SELECT DB_NAME() AS database_name")
        db_result = cursor.fetchone()
        if db_result:
            print(f"✓ Current database: {db_result[0]}")

        # Test query 4: Get server name
        print("\nExecuting test query: SELECT @@SERVERNAME")
        cursor.execute("SELECT @@SERVERNAME AS server_name")
        server_result = cursor.fetchone()
        if server_result:
            print(f"✓ Server name: {server_result[0]}")

        cursor.close()

        print("\n" + "=" * 60)
        print("✓ SQL connection test completed successfully!")
        print("=" * 60)

    except Exception as e:  # pylint: disable=broad-exception-caught
        print("\n" + "=" * 60)
        print(f"✗ Connection test failed: {type(e).__name__}")
        print(f"  Error: {str(e)}")
        
        # If it's a connection error, provide helpful info
        if "connection" in str(e).lower() or "authentication" in str(e).lower():
            print("\nNote: pymssql uses FreeTDS (no ODBC driver installation needed).")
            print("Ensure your connection string has: Server=...;Database=...;UID=...;PWD=...;")
        
        print("=" * 60)
        sys.exit(1)
    finally:
        if conn:
            conn.close()
            print("✓ Connection closed")


def main() -> None:
    """Main function to execute SQL connection test."""
    try:
        test_connection()
    except KeyboardInterrupt:
        print("\n✗ Interrupted by user")
        sys.exit(1)
    except Exception as e:  # pylint: disable=broad-exception-caught
        print(f"\n✗ Unexpected error: {type(e).__name__}")
        print(f"  Reason: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
