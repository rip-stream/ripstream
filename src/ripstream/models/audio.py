# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Audio-related models for quality, format, and technical information."""

from typing import Any

from pydantic import Field, field_validator

from ripstream.models.base import RipStreamBaseModel
from ripstream.models.enums import AudioQuality


class AudioInfo(RipStreamBaseModel):
    """Technical audio information."""

    quality: AudioQuality = Field(..., description="Audio quality level")
    bit_depth: int | None = Field(None, description="Bit depth (e.g., 16, 24)")
    sampling_rate: int | float | None = Field(
        None, description="Sampling rate in Hz (e.g., 44100, 96000)"
    )
    bitrate: int | None = Field(None, description="Bitrate in kbps")
    codec: str | None = Field(None, description="Audio codec (e.g., FLAC, MP3, AAC)")
    container: str | None = Field(
        None, description="Container format (e.g., FLAC, M4A)"
    )
    duration_seconds: float | None = Field(None, description="Duration in seconds")
    file_size_bytes: int | None = Field(None, description="File size in bytes")
    is_lossless: bool | None = Field(None, description="Whether the audio is lossless")
    is_explicit: bool = Field(default=False, description="Whether content is explicit")

    @field_validator("bit_depth")
    @classmethod
    def validate_bit_depth(cls, v: int | None) -> int | None:
        """Validate bit depth is a reasonable value."""
        if v is not None and v not in [8, 16, 24, 32]:
            msg = f"Invalid bit depth: {v}. Must be 8, 16, 24, or 32"
            raise ValueError(msg)
        return v

    @field_validator("duration_seconds")
    @classmethod
    def validate_duration(cls, v: float | None) -> float | None:
        """Validate duration is positive."""
        if v is not None and v < 0:
            msg = "Duration must be positive"
            raise ValueError(msg)
        return v

    @property
    def duration_formatted(self) -> str | None:
        """Get duration in MM:SS format."""
        if self.duration_seconds is None:
            return None

        minutes = int(self.duration_seconds // 60)
        seconds = int(self.duration_seconds % 60)
        return f"{minutes:02d}:{seconds:02d}"

    @property
    def file_size_mb(self) -> float | None:
        """Get file size in megabytes."""
        if self.file_size_bytes is None:
            return None
        return round(self.file_size_bytes / (1024 * 1024), 2)

    def update_from_source_data(self, source_data: dict[str, Any]) -> None:
        """Update audio info from streaming source data."""
        # This method can be overridden by source-specific implementations
        if "bit_depth" in source_data:
            self.bit_depth = source_data["bit_depth"]
        if "sampling_rate" in source_data:
            self.sampling_rate = source_data["sampling_rate"]
        if "bitrate" in source_data:
            self.bitrate = source_data["bitrate"]
        if "duration" in source_data:
            self.duration_seconds = source_data["duration"]


class DownloadableAudio(RipStreamBaseModel):
    """Information about downloadable audio content."""

    download_url: str | None = Field(None, description="Direct download URL")
    stream_url: str | None = Field(None, description="Streaming URL")
    expires_at: str | None = Field(None, description="URL expiration time")
    requires_auth: bool = Field(
        default=True, description="Whether authentication is required"
    )
    max_download_attempts: int = Field(
        default=3, description="Maximum download retry attempts"
    )
    chunk_size: int = Field(default=8192, description="Download chunk size in bytes")
    headers: dict[str, str] = Field(
        default_factory=dict, description="Required HTTP headers"
    )

    @property
    def is_expired(self) -> bool:
        """Check if the download URL has expired."""
        if self.expires_at is None:
            return False
        # Implementation would check against current time
        # For now, return False as placeholder
        return False

    def add_header(self, key: str, value: str) -> None:
        """Add a required HTTP header."""
        self.headers[key] = value

    def get_download_config(self) -> dict[str, Any]:
        """Get configuration for downloading this audio."""
        return {
            "url": self.download_url or self.stream_url,
            "headers": self.headers,
            "chunk_size": self.chunk_size,
            "max_attempts": self.max_download_attempts,
            "requires_auth": self.requires_auth,
        }
