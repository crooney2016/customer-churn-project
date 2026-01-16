"""
Configuration module for Azure Function App.
Loads settings from environment variables using Pydantic Settings.
"""

from pathlib import Path
from typing import List, Optional
from pydantic import Field, ValidationError, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

try:
    from dotenv import load_dotenv
    # Load .env file from project root (parent of function_app directory)
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    # python-dotenv not installed, skip .env loading
    pass


class Config(BaseSettings):
    """
    Application configuration from environment variables.

    Uses Pydantic Settings for type-safe configuration with automatic validation.
    """

    model_config = SettingsConfigDict(
        env_file=None,  # We handle .env loading manually via python-dotenv
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Ignore extra environment variables
    )

    # SQL Database
    SQL_CONNECTION_STRING: str = Field(
        ...,
        description="SQL Server connection string",
        min_length=1,
    )

    # Power BI (DAX queries and dataset refresh)
    PBI_TENANT_ID: str = Field(
        ...,
        description="Power BI tenant ID",
        min_length=1,
    )
    PBI_CLIENT_ID: str = Field(
        ...,
        description="Power BI service principal client ID",
        min_length=1,
    )
    PBI_CLIENT_SECRET: str = Field(
        ...,
        description="Power BI service principal client secret",
        min_length=1,
    )
    PBI_WORKSPACE_ID: str = Field(
        ...,
        description="Power BI workspace ID",
        min_length=1,
    )
    PBI_DATASET_ID: str = Field(
        ...,
        description="Power BI dataset ID",
        min_length=1,
    )
    DAX_QUERY_NAME: Optional[str] = Field(
        default=None,
        description="Name of DAX query file (without .dax extension)",
    )

    # Azure Blob Storage
    BLOB_STORAGE_CONNECTION_STRING: str = Field(
        default="",
        description="Azure Blob Storage connection string",
    )
    BLOB_STORAGE_CONTAINER_NAME: str = Field(
        default="churn-feature-data",
        description="Blob container name for feature data",
    )

    # Email (Microsoft Graph API)
    EMAIL_TENANT_ID: str = Field(
        ...,
        description="Email tenant ID (Microsoft Graph API)",
        min_length=1,
    )
    EMAIL_CLIENT_ID: str = Field(
        ...,
        description="Email service principal client ID",
        min_length=1,
    )
    EMAIL_CLIENT_SECRET: str = Field(
        ...,
        description="Email service principal client secret",
        min_length=1,
    )
    EMAIL_SENDER: str = Field(
        ...,
        description="Email sender address",
        min_length=1,
    )
    EMAIL_RECIPIENTS: str = Field(
        ...,
        description="Comma-separated list of email recipients",
        min_length=1,
    )

    @field_validator("EMAIL_RECIPIENTS")
    @classmethod
    def validate_email_recipients(cls, v: str) -> str:
        """Validate email recipients string is not empty after parsing."""
        recipients = [r.strip() for r in v.split(",") if r.strip()]
        if not recipients:
            raise ValueError("EMAIL_RECIPIENTS must contain at least one recipient")
        return v

    def validate(self) -> None:
        """
        Validate that required configuration is present.

        Note: Pydantic validates on instantiation, but this method is kept
        for backward compatibility and explicit validation calls.
        """
        # Pydantic already validates required fields on instantiation
        # This method ensures all fields are non-empty
        required_fields = [
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
        for field in required_fields:
            value = getattr(self, field, None)
            if not value:
                missing.append(field)

        if missing:
            raise ValueError(f"Missing required configuration: {', '.join(missing)}")

    def get_email_recipients(self) -> List[str]:
        """Parse comma-separated email recipients."""
        return [r.strip() for r in self.EMAIL_RECIPIENTS.split(",") if r.strip()]


# Global config instance
# Pydantic will automatically validate and raise ValidationError if required fields are missing
try:
    config = Config()
except ValidationError as e:
    # Provide helpful error message for missing configuration
    error_messages = []
    for err in e.errors():
        field_path = ".".join(str(loc) for loc in err.get("loc", []))
        msg = err.get("msg", "Unknown error")
        error_messages.append(f"{field_path}: {msg}")
    error_details = "; ".join(error_messages)
    raise ValueError(
        f"Configuration validation failed: {error_details}. "
        "Please ensure all required environment variables are set."
    ) from e
except Exception as e:
    # Catch any other exceptions during config loading
    raise ValueError(
        f"Configuration validation failed: {str(e)}. "
        "Please ensure all required environment variables are set."
    ) from e
