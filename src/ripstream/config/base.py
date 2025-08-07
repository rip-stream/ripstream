# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Base configuration classes with common functionality."""

from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class BaseConfig(BaseModel):
    """Base configuration class with common settings."""

    model_config = ConfigDict(
        # Enable validation on assignment
        validate_assignment=True,
        # Use enum values instead of enum objects in serialization
        use_enum_values=True,
        # Allow extra fields for extensibility
        extra="forbid",
        # Validate default values
        validate_default=True,
        # Enable arbitrary types for complex objects
        arbitrary_types_allowed=True,
    )


class ServiceConfig(BaseConfig):
    """Base configuration for streaming services."""

    quality: int = Field(..., description="Audio quality setting")


class AuthenticatedServiceConfig(ServiceConfig):
    """Base configuration for services requiring authentication."""

    # Common authentication fields
    email_or_userid: str = Field(
        default="", description="Email address or user ID for authentication"
    )
    password_or_token: str = Field(
        default="", description="Password or authentication token"
    )

    @field_validator("email_or_userid", "password_or_token")
    @classmethod
    def validate_auth_fields(cls, v: str) -> str:
        """Validate authentication fields are strings."""
        return str(v).strip()

    def get_decoded_credentials(self) -> dict[str, Any]:
        """Get decoded credentials for this service."""
        from ripstream.core.utils import decode_secret

        credentials = {
            "email_or_userid": decode_secret(self.email_or_userid),
            "password_or_token": decode_secret(self.password_or_token),
        }

        # Add any additional fields that don't need decoding
        for field_name in self.__class__.model_fields:
            if field_name not in ["email_or_userid", "password_or_token", "quality"]:
                credentials[field_name] = getattr(self, field_name)

        return credentials


class TokenBasedServiceConfig(ServiceConfig):
    """Base configuration for services using token-based authentication."""

    access_token: str = Field(default="", description="Access token for API")
    refresh_token: str = Field(default="", description="Refresh token for API")
    token_expiry: str = Field(default="", description="Token expiry timestamp")

    @field_validator("access_token", "refresh_token", "token_expiry")
    @classmethod
    def validate_token_fields(cls, v: str) -> str:
        """Validate token fields are strings."""
        return str(v).strip()

    def get_decoded_credentials(self) -> dict[str, Any]:
        """Get decoded credentials for this service."""
        from ripstream.core.utils import decode_secret

        credentials = {
            "access_token": decode_secret(self.access_token),
            "refresh_token": decode_secret(self.refresh_token),
            "token_expiry": self.token_expiry,  # This doesn't need decoding
        }

        # Add any additional fields that don't need decoding
        for field_name in self.__class__.model_fields:
            if field_name not in [
                "access_token",
                "refresh_token",
                "token_expiry",
                "quality",
            ]:
                credentials[field_name] = getattr(self, field_name)

        return credentials


class PathConfig(BaseConfig):
    """Base configuration for path-related settings."""

    @field_validator("*", mode="before")
    @classmethod
    def validate_paths(cls, v: Any, info) -> Any:
        """Convert string paths to Path objects where appropriate."""
        if info.field_name and "path" in info.field_name.lower() and isinstance(v, str):
            return Path(v).expanduser().resolve()
        return v


class DownloadableConfig(BaseConfig):
    """Base configuration for services that support downloads."""

    download_videos: bool = Field(
        default=False, description="Whether to download videos"
    )
    download_booklets: bool = Field(
        default=False, description="Whether to download booklets/PDFs"
    )
