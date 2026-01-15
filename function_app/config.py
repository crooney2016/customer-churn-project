"""
Configuration module for Azure Function App.
Loads settings from environment variables.
"""

import os
from pathlib import Path
from typing import Optional

try:
    from dotenv import load_dotenv
    # Load .env file from project root (parent of function_app directory)
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    # python-dotenv not installed, skip .env loading
    pass


class Config:
    """Application configuration from environment variables."""
    # SQL Database
    SQL_CONNECTION_STRING: str = os.getenv("SQL_CONNECTION_STRING", "")

    # Power BI (DAX queries and dataset refresh)
    PBI_TENANT_ID: str = os.getenv("PBI_TENANT_ID", "")
    PBI_CLIENT_ID: str = os.getenv("PBI_CLIENT_ID", "")
    PBI_CLIENT_SECRET: str = os.getenv("PBI_CLIENT_SECRET", "")
    PBI_WORKSPACE_ID: str = os.getenv("PBI_WORKSPACE_ID", "")
    PBI_DATASET_ID: str = os.getenv("PBI_DATASET_ID", "")
    DAX_QUERY_NAME: Optional[str] = os.getenv("DAX_QUERY_NAME", None)

    # Email (Microsoft Graph API)
    EMAIL_TENANT_ID: str = os.getenv("EMAIL_TENANT_ID", "")
    EMAIL_CLIENT_ID: str = os.getenv("EMAIL_CLIENT_ID", "")
    EMAIL_CLIENT_SECRET: str = os.getenv("EMAIL_CLIENT_SECRET", "")
    EMAIL_SENDER: str = os.getenv("EMAIL_SENDER", "")
    EMAIL_RECIPIENTS: str = os.getenv("EMAIL_RECIPIENTS", "")  # Comma-separated

    def validate(self) -> None:
        """Validate that required configuration is present."""
        required = [
            "SQL_CONNECTION_STRING",
            "PBI_TENANT_ID",
            "PBI_CLIENT_ID",
            "PBI_CLIENT_SECRET",
            "PBI_WORKSPACE_ID",
            "PBI_DATASET_ID",
            "EMAIL_TENANT_ID",
            "EMAIL_CLIENT_ID",
            "EMAIL_CLIENT_SECRET",
            "EMAIL_SENDER",
            "EMAIL_RECIPIENTS",
        ]

        missing = []
        for key in required:
            value = getattr(self, key)
            if not value:
                missing.append(key)

        if missing:
            raise ValueError(f"Missing required configuration: {', '.join(missing)}")

    def get_email_recipients(self) -> list[str]:
        """Parse comma-separated email recipients."""
        return [r.strip() for r in self.EMAIL_RECIPIENTS.split(",") if r.strip()]


# Global config instance
config = Config()
