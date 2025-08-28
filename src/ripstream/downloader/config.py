# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Configuration classes for the downloader module."""

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator

from ripstream.downloader.enums import RetryStrategy


class DownloadBehaviorSettings(BaseModel):
    """Settings for individual download behavior."""

    # Connection settings
    timeout_seconds: float = Field(
        default=120.0, description="Download timeout in seconds"
    )
    chunk_size: int = Field(default=8192, description="Download chunk size in bytes")
    max_concurrent_chunks: int = Field(
        default=1, description="Maximum concurrent chunks per download"
    )

    # Retry settings
    max_retries: int = Field(default=3, description="Maximum number of retry attempts")
    retry_strategy: RetryStrategy = Field(
        default=RetryStrategy.EXPONENTIAL, description="Retry strategy to use"
    )
    retry_delay: float = Field(
        default=1.0, description="Base delay between retries in seconds"
    )
    retry_backoff_factor: float = Field(
        default=2.0, description="Backoff factor for exponential retry"
    )

    # Rate limiting
    max_requests_per_second: float = Field(
        default=10.0, description="Maximum requests per second"
    )
    rate_limit_burst: int = Field(default=5, description="Rate limit burst allowance")

    # File handling
    overwrite_existing: bool = Field(
        default=False, description="Whether to overwrite existing files"
    )
    create_directories: bool = Field(
        default=True, description="Whether to create missing directories"
    )
    temp_file_suffix: str = Field(
        default=".tmp", description="Suffix for temporary files during download"
    )

    # Validation
    verify_checksums: bool = Field(
        default=True, description="Whether to verify file checksums"
    )
    verify_file_size: bool = Field(
        default=True, description="Whether to verify file sizes"
    )

    @field_validator("timeout_seconds", "retry_delay")
    @classmethod
    def validate_positive_time(cls, v: float) -> float:
        """Validate time values are positive."""
        if v <= 0:
            msg = "Time values must be positive"
            raise ValueError(msg)
        return v

    @field_validator("chunk_size", "max_concurrent_chunks", "max_retries")
    @classmethod
    def validate_positive_int(cls, v: int) -> int:
        """Validate integer values are positive."""
        if v <= 0:
            msg = "Integer values must be positive"
            raise ValueError(msg)
        return v

    @field_validator("max_requests_per_second")
    @classmethod
    def validate_positive_rate(cls, v: float) -> float:
        """Validate rate limit is positive."""
        if v <= 0:
            msg = "Rate limit must be positive"
            raise ValueError(msg)
        return v


class DownloaderConfig(BaseModel):
    """Main configuration for the downloader system."""

    # Directory settings
    download_directory: Path = Field(
        default=Path("./downloads"), description="Base download directory"
    )
    temp_directory: Path = Field(
        default=Path("./temp"), description="Temporary files directory"
    )

    # Queue settings
    max_concurrent_downloads: int = Field(
        default=3, description="Maximum concurrent downloads"
    )
    queue_size_limit: int = Field(
        default=1000, description="Maximum items in download queue"
    )

    # Default settings
    default_behavior: DownloadBehaviorSettings = Field(
        default_factory=DownloadBehaviorSettings,
        description="Default download behavior settings",
    )

    # Session settings
    user_agent: str = Field(
        default="RipStream/1.0", description="User agent for HTTP requests"
    )
    session_timeout: float = Field(
        default=300.0, description="Session timeout in seconds"
    )

    # Storage settings
    min_free_space_mb: int = Field(
        default=100, description="Minimum free space required in MB"
    )
    cleanup_temp_files: bool = Field(
        default=True, description="Whether to cleanup temporary files"
    )

    # Logging settings
    log_progress_interval: float = Field(
        default=1.0, description="Progress logging interval in seconds"
    )
    log_level: str = Field(default="INFO", description="Logging level")

    # Advanced settings
    enable_resume: bool = Field(
        default=True, description="Whether to enable download resume"
    )
    enable_compression: bool = Field(
        default=True, description="Whether to enable HTTP compression"
    )
    verify_ssl: bool = Field(
        default=True, description="Whether to verify SSL certificates"
    )

    # Custom headers
    custom_headers: dict[str, str] = Field(
        default_factory=dict, description="Custom HTTP headers"
    )

    # Source-specific settings
    source_settings: dict[str, dict[str, Any]] = Field(
        default_factory=dict, description="Source-specific configuration"
    )

    @field_validator(
        "max_concurrent_downloads", "queue_size_limit", "min_free_space_mb"
    )
    @classmethod
    def validate_positive_int(cls, v: int) -> int:
        """Validate integer values are positive."""
        if v <= 0:
            msg = "Integer values must be positive"
            raise ValueError(msg)
        return v

    @field_validator("session_timeout", "log_progress_interval")
    @classmethod
    def validate_positive_time(cls, v: float) -> float:
        """Validate time values are positive."""
        if v <= 0:
            msg = "Time values must be positive"
            raise ValueError(msg)
        return v

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level is valid."""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v.upper() not in valid_levels:
            msg = f"Log level must be one of {valid_levels}"
            raise ValueError(msg)
        return v.upper()

    def get_behavior_for_source(self, source: str) -> DownloadBehaviorSettings:
        """Get download behavior settings for a specific source."""
        base_settings = self.default_behavior.model_copy()

        if source in self.source_settings:
            source_config = self.source_settings[source]
            # Update base settings with source-specific overrides
            for key, value in source_config.items():
                if hasattr(base_settings, key):
                    setattr(base_settings, key, value)

        return base_settings

    def ensure_directories(self) -> None:
        """Ensure required directories exist."""
        self.download_directory.mkdir(parents=True, exist_ok=True)
        self.temp_directory.mkdir(parents=True, exist_ok=True)

    def get_download_path(self, filename: str, subfolder: str | None = None) -> Path:
        """Get the full download path for a file."""
        base_path = self.download_directory
        if subfolder:
            base_path = base_path / subfolder
        return base_path / filename

    def get_temp_path(self, filename: str) -> Path:
        """Get the temporary file path for a download."""
        return (
            self.temp_directory / f"{filename}{self.default_behavior.temp_file_suffix}"
        )

    def add_source_setting(
        self, source: str, key: str, value: str | float | bool
    ) -> None:
        """Add a source-specific setting."""
        if source not in self.source_settings:
            self.source_settings[source] = {}
        self.source_settings[source][key] = value

    def remove_source_setting(self, source: str, key: str | None = None) -> None:
        """Remove source-specific settings."""
        if source in self.source_settings:
            if key is None:
                # Remove all settings for the source
                del self.source_settings[source]
            elif key in self.source_settings[source]:
                # Remove specific setting
                del self.source_settings[source][key]
                # Clean up empty source config
                if not self.source_settings[source]:
                    del self.source_settings[source]

    def to_dict(self) -> dict[str, Any]:
        """Convert configuration to dictionary."""
        return self.model_dump(mode="json")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DownloaderConfig":
        """Create configuration from dictionary."""
        return cls.model_validate(data)
