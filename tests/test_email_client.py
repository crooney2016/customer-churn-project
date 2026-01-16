"""
Unit tests for email_client.py module.
"""

import pytest
from unittest.mock import patch, MagicMock
from function_app.email_client import (
    get_graph_access_token,
    send_email,
    send_success_email,
    send_failure_email,
)


def test_get_graph_access_token_success(monkeypatch):
    """Test that get_graph_access_token returns token on success."""
    mock_app = MagicMock()
    mock_app.acquire_token_for_client.return_value = {
        "access_token": "mock_access_token"
    }

    with patch("function_app.email_client.ConfidentialClientApplication", return_value=mock_app):
        with patch("function_app.email_client.config") as mock_config:
            mock_config.EMAIL_CLIENT_ID = "test_client_id"
            mock_config.EMAIL_CLIENT_SECRET = "test_secret"
            mock_config.EMAIL_TENANT_ID = "test_tenant_id"

            token = get_graph_access_token()
            assert token == "mock_access_token"


def test_get_graph_access_token_raises_on_no_token(monkeypatch):
    """Test that get_graph_access_token raises when token is missing."""
    mock_app = MagicMock()
    mock_app.acquire_token_for_client.return_value = {
        "error": "invalid_client",
        "error_description": "Client authentication failed"
    }

    with patch("function_app.email_client.ConfidentialClientApplication", return_value=mock_app):
        with patch("function_app.email_client.config") as mock_config:
            mock_config.EMAIL_CLIENT_ID = "test_client_id"
            mock_config.EMAIL_CLIENT_SECRET = "test_secret"
            mock_config.EMAIL_TENANT_ID = "test_tenant_id"

            with pytest.raises(RuntimeError, match="Failed to acquire Graph token"):
                get_graph_access_token()


@patch("function_app.email_client.get_graph_access_token")
@patch("function_app.email_client.requests.post")
@patch("function_app.email_client.config")
def test_send_email_success(mock_config, mock_post, mock_get_token):
    """Test that send_email sends email successfully."""
    mock_config.EMAIL_SENDER = "sender@example.com"
    mock_config.get_email_recipients.return_value = ["recipient@example.com"]
    mock_get_token.return_value = "mock_token"
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response

    send_email("Test Subject", "Test Body")

    mock_post.assert_called_once()
    call_args = mock_post.call_args
    assert call_args[1]["headers"]["Authorization"] == "Bearer mock_token"
    assert call_args[1]["json"]["message"]["subject"] == "Test Subject"
    assert call_args[1]["json"]["message"]["body"]["content"] == "Test Body"


@patch("function_app.email_client.get_graph_access_token")
@patch("function_app.email_client.requests.post")
@patch("function_app.email_client.config")
def test_send_email_with_custom_recipients(mock_config, mock_post, mock_get_token):
    """Test that send_email uses custom recipients when provided."""
    mock_config.EMAIL_SENDER = "sender@example.com"
    mock_get_token.return_value = "mock_token"
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response

    custom_recipients = ["custom1@example.com", "custom2@example.com"]
    send_email("Test Subject", "Test Body", recipients=custom_recipients)

    call_args = mock_post.call_args
    recipients = call_args[1]["json"]["message"]["toRecipients"]
    assert len(recipients) == 2
    assert recipients[0]["emailAddress"]["address"] == "custom1@example.com"
    assert recipients[1]["emailAddress"]["address"] == "custom2@example.com"


@patch("function_app.email_client.send_email")
def test_send_success_email(mock_send_email):
    """Test that send_success_email formats and sends success email correctly."""
    risk_distribution = {
        "A - High Risk": 100,
        "B - Medium Risk": 200,
        "C - Low Risk": 300,
    }

    send_success_email(
        row_count=600,
        snapshot_date="2024-01-01",
        duration_seconds=45.5,
        risk_distribution=risk_distribution
    )

    mock_send_email.assert_called_once()
    call_args = mock_send_email.call_args
    subject = call_args[0][0]
    body = call_args[0][1]

    assert "[SUCCESS]" in subject
    assert "600" in body
    assert "2024-01-01" in body
    assert "45.5" in body
    assert "A - High Risk: 100" in body
    assert "B - Medium Risk: 200" in body
    assert "C - Low Risk: 300" in body


@patch("function_app.email_client.send_email")
def test_send_success_email_with_zero_counts(mock_send_email):
    """Test that send_success_email handles zero risk counts."""
    risk_distribution = {
        "A - High Risk": 0,
        "B - Medium Risk": 0,
        "C - Low Risk": 100,
    }

    send_success_email(
        row_count=100,
        snapshot_date="2024-01-01",
        duration_seconds=10.0,
        risk_distribution=risk_distribution
    )

    mock_send_email.assert_called_once()
    call_args = mock_send_email.call_args
    body = call_args[0][1]

    assert "A - High Risk: 0" in body
    assert "B - Medium Risk: 0" in body
    assert "C - Low Risk: 100" in body


@patch("function_app.email_client.send_email")
def test_send_failure_email(mock_send_email):
    """Test that send_failure_email formats and sends failure email correctly."""
    send_failure_email(
        error_type="ValueError",
        error_message="Test error message",
        step="dax_query"
    )

    mock_send_email.assert_called_once()
    call_args = mock_send_email.call_args
    subject = call_args[0][0]
    body = call_args[0][1]

    assert "[FAILED]" in subject
    assert "ValueError" in body
    assert "Test error message" in body
    assert "dax_query" in body
    assert "Application Insights" in body
