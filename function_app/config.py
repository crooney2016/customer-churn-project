"""
Configuration module for Azure Function App.
Loads settings from environment variables using Pydantic Settings.
"""

from pathlib import Path
from typing import Optional
from pydantic import Field, ValidationError
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

    Architecture:
        Blob trigger → Parse CSV → Score → SQL Upsert → Produce HTML

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

    # Azure Blob Storage
    BLOB_STORAGE_CONNECTION_STRING: str = Field(
        ...,
        description="Azure Blob Storage connection string",
        min_length=1,
    )
    BLOB_STORAGE_CONTAINER_NAME: str = Field(
        default="churn-feature-data",
        description="Blob container name for feature data",
    )

    # Optional: Logic App endpoint for sending HTML results
    # If set, the function will POST HTML content to this endpoint
    LOGIC_APP_ENDPOINT: Optional[str] = Field(
        default=None,
        description="Optional Logic App HTTP endpoint for HTML output",
    )

    def validate(self) -> None:  # pylint: disable=arguments-renamed
        """
        Validate that required configuration is present.

        Note: Pydantic validates on instantiation, but this method is kept
        for backward compatibility and explicit validation calls.
        """
        required_fields = [
            "SQL_CONNECTION_STRING",
            "BLOB_STORAGE_CONNECTION_STRING",
        ]

        missing = []
        for field in required_fields:
            value = getattr(self, field, None)
            if not value:
                missing.append(field)

        if missing:
            raise ValueError(f"Missing required configuration: {', '.join(missing)}")


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
