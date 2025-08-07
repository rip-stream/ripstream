# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Service-specific configuration classes."""

from pathlib import Path
from typing import Any

from pydantic import Field, field_validator

from ripstream.config.base import (
    AuthenticatedServiceConfig,
    DownloadableConfig,
    ServiceConfig,
    TokenBasedServiceConfig,
)


class QobuzConfig(AuthenticatedServiceConfig, DownloadableConfig):
    """Configuration for Qobuz streaming service."""

    # Quality: 1: 320kbps MP3, 2: 16/44.1, 3: 24/<=96, 4: 24/>=96
    quality: int = Field(default=4, description="Audio quality (1-4)")
    download_booklets: bool = Field(
        default=True, description="Download booklet PDFs included with albums"
    )

    # Authentication settings
    use_auth_token: bool = Field(
        default=False, description="Use auth token instead of email/password"
    )

    # API settings (should not be changed by users)
    app_id: str = Field(default="798273057", description="Qobuz app ID")
    secrets: list[str] = Field(
        default=[],
        description="Qobuz API secrets",
    )

    @field_validator("quality")
    @classmethod
    def validate_qobuz_quality(cls, v: int) -> int:
        """Validate Qobuz quality is between 1-4."""
        if not 1 <= v <= 4:
            msg = "Qobuz quality must be between 1-4"
            raise ValueError(msg)
        return v


class TidalConfig(TokenBasedServiceConfig, DownloadableConfig):
    """Configuration for Tidal streaming service."""

    # Quality: 0: 256kbps AAC, 1: 320kbps AAC, 2: 16/44.1 "HiFi" FLAC, 3: 24/44.1 "MQA" FLAC
    quality: int = Field(default=3, description="Audio quality (0-3)")
    download_videos: bool = Field(
        default=True, description="Download videos included in Video Albums"
    )

    # Additional Tidal-specific fields
    user_id: str = Field(default="", description="Tidal user ID")
    country_code: str = Field(default="", description="Tidal country code")

    @field_validator("quality")
    @classmethod
    def validate_tidal_quality(cls, v: int) -> int:
        """Validate Tidal quality is between 0-3."""
        if not 0 <= v <= 3:
            msg = "Tidal quality must be between 0-3"
            raise ValueError(msg)
        return v


class DeezerConfig(ServiceConfig):
    """Configuration for Deezer streaming service."""

    # Quality: 0, 1, or 2 (only applies to paid subscriptions)
    quality: int = Field(default=2, description="Audio quality (0-2)")

    # Authentication
    arl: str = Field(
        default="",
        description="Authentication cookie for Deezer account",
    )

    # Deezloader settings
    use_deezloader: bool = Field(
        default=True, description="Use deezloader for free 320kbps MP3 downloads"
    )
    deezloader_warnings: bool = Field(
        default=True,
        description="Warn when paid account not logged in and falling back to deezloader",
    )

    @field_validator("quality")
    @classmethod
    def validate_deezer_quality(cls, v: int) -> int:
        """Validate Deezer quality is between 0-2."""
        if not 0 <= v <= 2:
            msg = "Deezer quality must be between 0-2"
            raise ValueError(msg)
        return v

    def get_decoded_credentials(self) -> dict[str, Any]:
        """Get decoded credentials for this service."""
        from ripstream.core.utils import decode_secret

        credentials = {
            "arl": decode_secret(self.arl),
        }

        # Add any additional fields that don't need decoding
        for field_name in self.__class__.model_fields:
            if field_name not in ["arl", "quality"]:
                credentials[field_name] = getattr(self, field_name)

        return credentials


class SoundCloudConfig(ServiceConfig):
    """Configuration for SoundCloud streaming service."""

    # Only quality 0 is available
    quality: int = Field(default=0, description="Audio quality (only 0 available)")

    # API settings that change periodically
    client_id: str = Field(default="", description="SoundCloud client ID")
    app_version: str = Field(default="", description="SoundCloud app version")

    @field_validator("quality")
    @classmethod
    def validate_soundcloud_quality(cls, v: int) -> int:
        """Validate SoundCloud quality is 0."""
        if v != 0:
            msg = "SoundCloud quality must be 0 (only option available)"
            raise ValueError(msg)
        return v

    def get_decoded_credentials(self) -> dict[str, Any]:
        """Get decoded credentials for this service."""
        # SoundCloud doesn't use encoded credentials, just return as-is
        credentials = {}

        # Add all fields except quality
        for field_name in self.__class__.model_fields:
            if field_name != "quality":
                credentials[field_name] = getattr(self, field_name)

        return credentials


class YouTubeConfig(ServiceConfig, DownloadableConfig):
    """Configuration for YouTube streaming service."""

    # Only quality 0 is available
    quality: int = Field(default=0, description="Audio quality (only 0 available)")
    download_videos: bool = Field(
        default=False, description="Download video along with audio"
    )

    # Video download path
    video_downloads_folder: Path = Field(
        default=Path("~/RipstreamDownloads/YouTubeVideos"),
        description="Path to download videos to",
    )

    @field_validator("quality")
    @classmethod
    def validate_youtube_quality(cls, v: int) -> int:
        """Validate YouTube quality is 0."""
        if v != 0:
            msg = "YouTube quality must be 0 (only option available)"
            raise ValueError(msg)
        return v

    @field_validator("video_downloads_folder", mode="before")
    @classmethod
    def validate_video_path(cls, v) -> Path:
        """Convert string path to Path object and expand user."""
        if isinstance(v, str):
            return Path(v).expanduser().resolve()
        return v

    def get_decoded_credentials(self) -> dict[str, Any]:
        """Get decoded credentials for this service."""
        # YouTube doesn't use encoded credentials, just return as-is
        credentials = {}

        # Add all fields except quality
        for field_name in self.__class__.model_fields:
            if field_name != "quality":
                credentials[field_name] = getattr(self, field_name)

        return credentials
