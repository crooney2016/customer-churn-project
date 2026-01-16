"""
Tests for email_client module.
Tests template rendering and HTML generation.
"""

from datetime import datetime
from unittest.mock import patch

import pytest

from function_app.email_client import (
    send_success_email,
    send_failure_email,
    _render_template,
    _post_html,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def output_dir(tmp_path):
    """Create output directory for static HTML files."""
    output = tmp_path / "email_previews"
    output.mkdir()
    return output


@pytest.fixture
def mock_config(mocker):
    """Mock config with endpoint."""
    mock = mocker.patch("function_app.email_client.config")
    mock.LOGIC_APP_ENDPOINT = "https://logic-app.example.com/email"
    return mock


@pytest.fixture
def sample_success_context():
    """Sample context for success email."""
    return {
        "row_count": 1523,
        "snapshot_date": "2025-01-31",
        "duration_seconds": 45.67,
        "risk_distribution": {"High": 250, "Medium": 750, "Low": 523},
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
    }


@pytest.fixture
def sample_failure_context():
    """Sample context for failure email."""
    return {
        "error_type": "ValueError",
        "error_message": "CSV file contains no data rows",
        "step": "parse_csv",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
    }


# =============================================================================
# Template Rendering Tests
# =============================================================================

def test_render_success_template(sample_success_context):
    """Test rendering success email template."""
    html = _render_template("success.html", sample_success_context)

    assert html is not None
    assert len(html) > 0
    assert "2025-01-31" in html


def test_render_failure_template(sample_failure_context):
    """Test rendering failure email template."""
    html = _render_template("failure.html", sample_failure_context)

    assert html is not None
    assert len(html) > 0
    assert "ValueError" in html
    assert "parse_csv" in html


def test_render_template_not_found():
    """Test that missing template raises exception."""
    with pytest.raises(Exception):
        _render_template("nonexistent.html", {})


# =============================================================================
# POST HTML Tests
# =============================================================================

@patch("function_app.email_client.requests.post")
def test_post_html_success(mock_post, mock_config):  # pylint: disable=unused-argument
    """Test successful HTML POST."""
    # mock_config fixture sets up config.LOGIC_APP_ENDPOINT
    mock_post.return_value.raise_for_status.return_value = None

    _post_html("<html>Test</html>", "Test Subject")

    mock_post.assert_called_once()
    call_args = mock_post.call_args
    assert call_args[0][0] == "https://logic-app.example.com/email"
    assert call_args[1]["json"]["subject"] == "Test Subject"
    assert call_args[1]["json"]["body"] == "<html>Test</html>"


def test_post_html_no_endpoint(mocker):
    """Test that missing endpoint skips POST gracefully."""
    mock_config = mocker.patch("function_app.email_client.config")
    mock_config.LOGIC_APP_ENDPOINT = None

    # Should not raise, just skip
    _post_html("<html>Test</html>", "Test Subject")


@patch("function_app.email_client.requests.post")
def test_post_html_error_logged_not_raised(mock_post, mock_config):  # pylint: disable=unused-argument
    """Test that POST errors are logged but not raised."""
    import requests
    mock_post.side_effect = requests.exceptions.ConnectionError("Failed")

    # Should not raise
    _post_html("<html>Test</html>", "Test Subject")


# =============================================================================
# Send Email Functions Tests
# =============================================================================

@patch("function_app.email_client._post_html")
def test_send_success_email(mock_post, mock_config):  # pylint: disable=unused-argument
    """Test send_success_email generates HTML and posts."""
    send_success_email(
        row_count=100,
        snapshot_date="2025-01-31",
        duration_seconds=10.0,
        risk_distribution={"High": 50}
    )

    assert mock_post.called
    call_args = mock_post.call_args[0]
    assert "Success" in call_args[1]  # Subject
    assert len(call_args[0]) > 0  # HTML body


@patch("function_app.email_client._post_html")
def test_send_failure_email(mock_post, mock_config):  # pylint: disable=unused-argument
    """Test send_failure_email generates HTML and posts."""
    send_failure_email(
        error_type="ValueError",
        error_message="Test error",
        step="test_step"
    )

    assert mock_post.called
    call_args = mock_post.call_args[0]
    assert "Failure" in call_args[1]  # Subject
    assert len(call_args[0]) > 0  # HTML body


@patch("function_app.email_client._post_html")
def test_send_success_email_template_error_handled(mock_post, mocker):
    """Test that template errors don't crash."""
    from jinja2 import TemplateNotFound
    mocker.patch(
        "function_app.email_client._render_template",
        side_effect=TemplateNotFound("missing.html")
    )

    # Should not raise
    send_success_email(
        row_count=100,
        snapshot_date="2025-01-31",
        duration_seconds=10.0,
        risk_distribution={}
    )

    assert not mock_post.called


@patch("function_app.email_client._post_html")
def test_send_failure_email_template_error_handled(mock_post, mocker):
    """Test that template errors don't crash."""
    from jinja2 import TemplateNotFound
    mocker.patch(
        "function_app.email_client._render_template",
        side_effect=TemplateNotFound("missing.html")
    )

    # Should not raise
    send_failure_email(
        error_type="Error",
        error_message="msg",
        step="step"
    )

    assert not mock_post.called
