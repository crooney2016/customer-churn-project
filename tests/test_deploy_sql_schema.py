"""
Unit tests for scripts/deploy_sql_schema.py module.
"""

import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest


@pytest.fixture
def mock_sql_connection(mocker):
    """Mock SQL connection and cursor for testing."""
    mock_conn = mocker.MagicMock()
    mock_cursor = mocker.MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_conn.commit.return_value = None
    mock_conn.rollback.return_value = None
    return mock_conn, mock_cursor


@pytest.fixture
def sample_connection_string():
    """Sample SQL connection string."""
    return "Server=test-server;Port=1433;Database=testdb;UID=testuser;PWD=testpass;"


def test_parse_connection_string():
    """Test _parse_connection_string function."""
    from scripts.deploy_sql_schema import _parse_connection_string

    conn_str = "Server=test-server;Port=1433;Database=testdb;UID=testuser;PWD=testpass;"
    result = _parse_connection_string(conn_str)

    assert result["server"] == "test-server"
    assert result["port"] == 1433
    assert result["database"] == "testdb"
    assert result["user"] == "testuser"
    assert result["password"] == "testpass"


def test_parse_connection_string_minimal():
    """Test _parse_connection_string with minimal connection string."""
    from scripts.deploy_sql_schema import _parse_connection_string

    conn_str = "Server=test-server;"
    result = _parse_connection_string(conn_str)

    assert result["server"] == "test-server"
    assert "port" not in result or result.get("port") is None


def test_extract_username(sample_connection_string):
    """Test extract_username function."""
    from scripts.deploy_sql_schema import extract_username

    username = extract_username(sample_connection_string)
    assert username == "testuser"


def test_extract_username_missing():
    """Test extract_username raises error when username missing."""
    from scripts.deploy_sql_schema import extract_username

    conn_str = "Server=test-server;Database=testdb;"
    with pytest.raises(ValueError, match="Could not extract username"):
        extract_username(conn_str)


def test_get_connection(mocker, sample_connection_string, mock_sql_connection):
    """Test get_connection function."""
    from scripts.deploy_sql_schema import get_connection

    mock_conn, _ = mock_sql_connection
    mock_connect = mocker.patch("scripts.deploy_sql_schema.pymssql.connect")
    mock_connect.return_value = mock_conn

    with patch.dict(os.environ, {"SQL_CONNECTION_STRING": sample_connection_string}):
        conn = get_connection()

    assert conn == mock_conn
    mock_connect.assert_called_once()


def test_get_connection_missing_env():
    """Test get_connection raises error when env var missing."""
    from scripts.deploy_sql_schema import get_connection

    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ValueError, match="SQL_CONNECTION_STRING"):
            get_connection()


def test_grant_permissions(mock_sql_connection):
    """Test grant_permissions function."""
    from scripts.deploy_sql_schema import grant_permissions

    mock_conn, mock_cursor = mock_sql_connection

    grant_permissions(mock_conn, "testuser")

    # Verify ALTER ROLE statement was executed (now grants db_owner role)
    assert mock_cursor.execute.call_count == 1  # db_owner
    assert mock_conn.commit.called


def test_grant_permissions_already_member(mock_sql_connection):
    """Test grant_permissions handles already-member error gracefully."""
    from scripts.deploy_sql_schema import grant_permissions
    import pymssql

    mock_conn, mock_cursor = mock_sql_connection
    # Simulate "already a member" error
    mock_cursor.execute.side_effect = [
        pymssql.Error("User is already a member"),
        None,  # Second role succeeds
        None,  # Third role succeeds
    ]

    # Should not raise
    grant_permissions(mock_conn, "testuser")
    assert mock_conn.commit.called


def test_verify_permissions(mock_sql_connection):
    """Test verify_permissions function."""
    from scripts.deploy_sql_schema import verify_permissions

    mock_conn, mock_cursor = mock_sql_connection

    # Mock successful permission tests
    mock_cursor.fetchone.side_effect = [
        (1,),  # SELECT test
        (1,),  # INSERT test
        ("UPDATED",),  # UPDATE test
        (0,),  # DELETE test
        (1,),  # DDL test
    ]

    # Should not raise
    verify_permissions(mock_conn, "testuser")
    assert mock_conn.commit.called


def test_verify_permissions_fails_select(mock_sql_connection):
    """Test verify_permissions fails when DDL permission test fails."""
    from scripts.deploy_sql_schema import verify_permissions
    import pymssql

    mock_conn, mock_cursor = mock_sql_connection

    # Mock DDL test failure (verify_permissions now tests DDL, not SELECT)
    mock_cursor.execute.side_effect = pymssql.Error("DDL permission failed")

    with pytest.raises(RuntimeError, match="Permission verification failed"):
        verify_permissions(mock_conn, "testuser")


def test_execute_sql_file(mock_sql_connection, mocker):
    """Test execute_sql_file function."""
    from scripts.deploy_sql_schema import execute_sql_file

    mock_conn, mock_cursor = mock_sql_connection

    sql_content = """
    CREATE TABLE TestTable (Id INT);
    GO
    INSERT INTO TestTable VALUES (1);
    GO
    """
    sql_file = Path("/tmp/test.sql")

    mocker.patch("builtins.open", mocker.mock_open(read_data=sql_content))
    execute_sql_file(mock_conn, sql_file)

    # Verify execute was called for each batch (2 batches)
    assert mock_cursor.execute.call_count >= 2
    assert mock_conn.commit.called


def test_execute_sql_file_handles_go_statements(mock_sql_connection, mocker):
    """Test execute_sql_file properly splits GO statements."""
    from scripts.deploy_sql_schema import execute_sql_file

    mock_conn, mock_cursor = mock_sql_connection

    sql_content = "SELECT 1; GO SELECT 2; GO SELECT 3;"
    sql_file = Path("/tmp/test.sql")

    mocker.patch("builtins.open", mocker.mock_open(read_data=sql_content))
    execute_sql_file(mock_conn, sql_file)

    # Should execute 3 batches
    assert mock_cursor.execute.call_count == 3


def test_execute_sql_file_handles_already_exists(mock_sql_connection, mocker):
    """Test execute_sql_file handles 'already exists' errors gracefully."""
    from scripts.deploy_sql_schema import execute_sql_file
    import pymssql

    mock_conn, mock_cursor = mock_sql_connection
    # Simulate "already exists" error
    mock_cursor.execute.side_effect = pymssql.Error("Object already exists")

    sql_content = "CREATE TABLE TestTable (Id INT);"
    sql_file = Path("/tmp/test.sql")

    mocker.patch("builtins.open", mocker.mock_open(read_data=sql_content))
    # Should not raise (idempotent)
    execute_sql_file(mock_conn, sql_file)


def test_main_success(mocker, sample_connection_string, mock_sql_connection):
    """Test main function success path."""
    from scripts.deploy_sql_schema import main

    mock_conn, _ = mock_sql_connection
    mock_get_conn = mocker.patch("scripts.deploy_sql_schema.get_connection")
    mock_grant = mocker.patch("scripts.deploy_sql_schema.grant_permissions")
    mock_verify = mocker.patch("scripts.deploy_sql_schema.verify_permissions")
    mock_execute = mocker.patch("scripts.deploy_sql_schema.execute_sql_file")
    mock_get_conn.return_value = mock_conn

    mocker.patch("scripts.deploy_sql_schema.extract_username", return_value="testuser")
    mocker.patch("scripts.deploy_sql_schema.project_root", Path("/tmp"))
    mocker.patch("pathlib.Path.exists", return_value=True)

    with patch.dict(os.environ, {"SQL_CONNECTION_STRING": sample_connection_string}):
        main()

    # Verify execution order
    mock_get_conn.assert_called_once()
    mock_grant.assert_called_once()
    mock_verify.assert_called_once()
    assert mock_execute.call_count >= 1  # At least one SQL file executed


def test_main_missing_connection_string():
    """Test main function fails when connection string missing."""
    from scripts.deploy_sql_schema import main

    with patch.dict(os.environ, {}, clear=True):
        with patch.object(sys, "exit") as mock_exit:
            main()
            # May be called multiple times due to validation
            assert mock_exit.called
            # At least one call should be with exit code 1
            assert any(call[0][0] == 1 for call in mock_exit.call_args_list)


def test_main_permission_grant_fails(mocker, sample_connection_string, mock_sql_connection):
    """Test main function handles permission grant failure."""
    from scripts.deploy_sql_schema import main

    mock_conn, _ = mock_sql_connection
    mock_get_conn = mocker.patch("scripts.deploy_sql_schema.get_connection")
    mock_grant = mocker.patch("scripts.deploy_sql_schema.grant_permissions")
    mock_get_conn.return_value = mock_conn
    mock_grant.side_effect = Exception("Permission grant failed")

    mocker.patch("scripts.deploy_sql_schema.extract_username", return_value="testuser")

    with patch.dict(os.environ, {"SQL_CONNECTION_STRING": sample_connection_string}):
        with patch.object(sys, "exit") as mock_exit:
            main()
            mock_exit.assert_called_once_with(1)
            assert mock_conn.rollback.called
