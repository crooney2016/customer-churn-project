"""
Email notification client using Microsoft Graph API.
Sends success and failure notifications.
"""

from typing import Optional, Dict
from datetime import datetime
import requests
from msal import ConfidentialClientApplication
from .config import config


def get_graph_access_token() -> str:
    """Get access token for Microsoft Graph API."""
    app = ConfidentialClientApplication(
        client_id=config.EMAIL_CLIENT_ID,
        client_credential=config.EMAIL_CLIENT_SECRET,
        authority=f"https://login.microsoftonline.com/{config.EMAIL_TENANT_ID}"
    )

    result = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])

    if "access_token" not in result:
        error_desc = result.get('error_description', 'Unknown error')
        raise RuntimeError(f"Failed to acquire Graph token: {error_desc}")

    return result["access_token"]


def send_email(
    subject: str,
    body: str,
    recipients: Optional[list[str]] = None
) -> None:
    """
    Send email via Microsoft Graph API.

    Args:
        subject: Email subject
        body: Email body (HTML or plain text)
        recipients: List of recipient email addresses (defaults to config recipients)
    """
    if recipients is None:
        recipients = config.get_email_recipients()

    access_token = get_graph_access_token()

    url = f"https://graph.microsoft.com/v1.0/users/{config.EMAIL_SENDER}/sendMail"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    message = {
        "message": {
            "subject": subject,
            "body": {
                "contentType": "HTML",
                "content": body
            },
            "toRecipients": [{"emailAddress": {"address": r}} for r in recipients]
        }
    }

    response = requests.post(url, headers=headers, json=message, timeout=30)
    response.raise_for_status()


def send_success_email(
    row_count: int,
    snapshot_date: str,
    duration_seconds: float,
    risk_distribution: Dict[str, int]
) -> None:
    """Send success notification email."""
    total = sum(risk_distribution.values())

    subject = f"[SUCCESS] Churn Scoring - {datetime.now().strftime('%Y-%m-%d')}"

    high_risk = risk_distribution.get('A - High Risk', 0)
    med_risk = risk_distribution.get('B - Medium Risk', 0)
    low_risk = risk_distribution.get('C - Low Risk', 0)

    body = f"""
    <html>
    <body>
        <h2>Churn Scoring Completed Successfully</h2>
        <p><strong>Rows scored:</strong> {row_count:,}</p>
        <p><strong>Snapshot date:</strong> {snapshot_date}</p>
        <p><strong>Duration:</strong> {duration_seconds:.1f}s</p>

        <h3>Risk Distribution:</h3>
        <ul>
            <li>A - High Risk: {high_risk:,} ({high_risk/total*100:.1f}%)</li>
            <li>B - Medium Risk: {med_risk:,} ({med_risk/total*100:.1f}%)</li>
            <li>C - Low Risk: {low_risk:,} ({low_risk/total*100:.1f}%)</li>
        </ul>

        <p><em>Generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</em></p>
    </body>
    </html>
    """

    send_email(subject, body)


def send_failure_email(
    error_type: str,
    error_message: str,
    step: str
) -> None:
    """Send failure notification email."""
    subject = f"[FAILED] Churn Scoring - {datetime.now().strftime('%Y-%m-%d')}"

    body = f"""
    <html>
    <body>
        <h2>Churn Scoring Failed</h2>
        <p><strong>Error Type:</strong> {error_type}</p>
        <p><strong>Message:</strong> {error_message}</p>
        <p><strong>Step:</strong> {step}</p>
        <p><strong>Timestamp:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>

        <p>Check Application Insights for full trace.</p>
    </body>
    </html>
    """

    send_email(subject, body)
