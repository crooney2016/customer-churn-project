"""
Email client module - generates HTML and POSTs to Logic App endpoint.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import requests
from jinja2 import Environment, FileSystemLoader, TemplateError, TemplateNotFound

from .config import config

logger = logging.getLogger(__name__)

# Template directory path
TEMPLATE_DIR = Path(__file__).parent / "templates" / "emails"

# Initialize Jinja2 environment
try:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=True,
        trim_blocks=True,
        lstrip_blocks=True
    )
except OSError as e:
    logger.warning("Failed to initialize Jinja2 environment: %s", str(e))
    env = None


def _render_template(template_name: str, context: dict[str, Any]) -> str:
    """Render an HTML template with the provided context."""
    if env is None:
        raise RuntimeError("Jinja2 environment not initialized")

    template = env.get_template(template_name)
    return template.render(**context)


def _post_html(html_content: str, subject: str) -> None:
    """POST HTML content to Logic App endpoint."""
    endpoint = config.LOGIC_APP_ENDPOINT
    if not endpoint:
        logger.info("No LOGIC_APP_ENDPOINT configured, skipping POST")
        return

    payload = {"subject": subject, "body": html_content}

    try:
        response = requests.post(endpoint, json=payload, timeout=30)
        response.raise_for_status()
        logger.info("Posted HTML to Logic App: %s", subject)
    except requests.exceptions.RequestException as e:
        logger.error("Failed to POST to Logic App: %s", str(e))
        # Don't raise - pipeline shouldn't fail due to notification issues


def send_success_email(
    row_count: int,
    snapshot_date: str,
    duration_seconds: float,
    risk_distribution: dict[str, int],
    avg_risk: Optional[float] = None,
    median_risk: Optional[float] = None,
    top_reasons: Optional[dict[str, int]] = None,
    model_auc: Optional[float] = None,
    model_version: Optional[str] = None
) -> None:
    """Generate success HTML and POST to Logic App."""
    try:
        context = {
            "row_count": row_count,
            "snapshot_date": snapshot_date,
            "duration_seconds": duration_seconds,
            "risk_distribution": risk_distribution,
            "avg_risk": avg_risk,
            "median_risk": median_risk,
            "top_reasons": top_reasons or {},
            "model_auc": model_auc,
            "model_version": model_version or "Latest",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
        }

        html = _render_template("success.html", context)
        subject = f"Churn Prediction - Success ({snapshot_date})"
        _post_html(html, subject)

    except (TemplateNotFound, TemplateError, RuntimeError) as e:
        logger.error("Failed to render success template: %s", str(e))


def send_failure_email(error_type: str, error_message: str, step: str) -> None:
    """Generate failure HTML and POST to Logic App."""
    try:
        context = {
            "error_type": error_type,
            "error_message": error_message,
            "step": step,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
        }

        html = _render_template("failure.html", context)
        subject = f"Churn Prediction - Failure (Step: {step})"
        _post_html(html, subject)

    except (TemplateNotFound, TemplateError, RuntimeError) as e:
        logger.error("Failed to render failure template: %s", str(e))
