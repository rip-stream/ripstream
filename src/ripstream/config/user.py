# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""User configuration classes for general settings."""

from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator

from ripstream.config.base import BaseConfig
from ripstream.config.services import (
    DeezerConfig,
    QobuzConfig,
    SoundCloudConfig,
    TidalConfig,
    YouTubeConfig,
)


class DownloadsConfig(BaseConfig):
    """Configuration for download settings."""

    folder: Path = Field(
        default=Path("/media/nas/plex3/music"),
        description="Folder where tracks are downloaded to",
    )
    source_subdirectories: bool = Field(
        default=False,
        description="Put albums in source-specific folders (Qobuz, Tidal, etc.)",
    )
    disc_subdirectories: bool = Field(
        default=True,
        description="Put multi-disc albums into 'Disc N' subfolders",
    )
    concurrency: bool = Field(
        default=True,
        description="Download and convert tracks concurrently instead of sequentially",
    )
    max_connections: int = Field(
        default=6,
        description="Maximum number of tracks to download at once (-1 for no limit)",
    )
    requests_per_minute: int = Field(
        default=60,
        description="Max API requests per source per minute (-1 for no limit)",
    )
    verify_ssl: bool = Field(
        default=True,
        description="Verify SSL certificates for API connections",
    )
    # Download behavior settings
    timeout_seconds: float = Field(
        default=120.0,
        description="Download timeout in seconds (per request)",
    )
    max_retries: int = Field(
        default=3,
        description="Maximum number of retry attempts for failed downloads",
    )
    retry_delay: float = Field(
        default=1.0,
        description="Base delay between retries in seconds",
    )
    chunk_size: int = Field(
        default=8192,
        description="Download chunk size in bytes",
    )
    probe_audio_technicals: bool = Field(
        default=False,
        description=(
            "Probe downloaded files for technical info (bitrate, channels, etc.).\n"
            "This may be slow for some file types."
        ),
    )

    @field_validator("max_connections", "requests_per_minute")
    @classmethod
    def validate_connection_limits(cls, v: int) -> int:
        """Validate connection limits are valid (-1 or positive)."""
        if v < -1 or v == 0:
            msg = "Connection limits must be -1 (no limit) or positive"
            raise ValueError(msg)
        return v

    @field_validator("max_retries", "chunk_size")
    @classmethod
    def validate_positive_int(cls, v: int) -> int:
        """Validate integer values are positive."""
        if v <= 0:
            msg = "Integer values must be positive"
            raise ValueError(msg)
        return v

    @field_validator("retry_delay")
    @classmethod
    def validate_positive_float(cls, v: float) -> float:
        """Validate float values are positive."""
        if v <= 0:
            msg = "Float values must be positive"
            raise ValueError(msg)
        return v

    @field_validator("timeout_seconds")
    @classmethod
    def validate_timeout_seconds(cls, v: float) -> float:
        """Validate timeout is positive and reasonably bounded."""
        if v <= 0:
            msg = "Timeout must be positive"
            raise ValueError(msg)
        # Hard cap to avoid absurd values
        return float(v)

    @field_validator("folder", mode="before")
    @classmethod
    def validate_download_folder(cls, v) -> Path:
        """Convert string path to Path object and expand user."""
        if isinstance(v, str):
            return Path(v).expanduser()
        return v


class DatabaseConfig(BaseConfig):
    """Configuration for database settings."""

    downloads_enabled: bool = Field(
        default=True,
        description="Create database to track downloaded tracks and skip duplicates",
    )
    database_path: Path = Field(
        default=Path("~/.config/ripstream/downloads.db"),
        description="Path to the downloads database",
    )
    history_limit: int = Field(
        default=25,
        description="Maximum number of download history items to display in UI",
    )
    session_snapshot_items_cap: int = Field(
        default=1000,
        description="Maximum number of items to store in session snapshot (0 for unlimited)",
    )

    @field_validator("database_path", mode="before")
    @classmethod
    def validate_db_paths(cls, v) -> Path:
        """Convert string paths to Path objects and expand user."""
        if isinstance(v, str):
            return Path(v).expanduser()
        if isinstance(v, Path):
            return v.expanduser()
        return v

    @field_validator("history_limit")
    @classmethod
    def validate_history_limit(cls, v: int) -> int:
        """Validate history limit is positive."""
        if v <= 0:
            msg = "History limit must be positive"
            raise ValueError(msg)
        return v

    @field_validator("session_snapshot_items_cap")
    @classmethod
    def validate_session_snapshot_cap(cls, v: int) -> int:
        """Validate cap is non-negative (0 means unlimited)."""
        if v < 0:
            msg = "Session snapshot items cap must be 0 (unlimited) or positive"
            raise ValueError(msg)
        return v


class ConversionConfig(BaseConfig):
    """Configuration for audio conversion settings."""

    enabled: bool = Field(
        default=False, description="Convert tracks to a codec after downloading"
    )
    codec: Literal["FLAC", "ALAC", "OPUS", "MP3", "VORBIS", "AAC"] = Field(
        default="ALAC", description="Target codec for conversion"
    )
    sampling_rate: int = Field(
        default=48000,
        description="Target sampling rate in Hz (tracks downsampled if higher)",
    )
    bit_depth: Literal[16, 24] = Field(
        default=24,
        description="Target bit depth (only applied when source is higher)",
    )
    lossy_bitrate: int = Field(
        default=320, description="Bitrate for lossy codecs in kbps"
    )

    @field_validator("sampling_rate")
    @classmethod
    def validate_sampling_rate(cls, v: int) -> int:
        """Validate sampling rate is positive."""
        if v <= 0:
            msg = "Sampling rate must be positive"
            raise ValueError(msg)
        return v

    @field_validator("lossy_bitrate")
    @classmethod
    def validate_bitrate(cls, v: int) -> int:
        """Validate bitrate is positive."""
        if v <= 0:
            msg = "Bitrate must be positive"
            raise ValueError(msg)
        return v


class QobuzFiltersConfig(BaseConfig):
    """Configuration for Qobuz artist discography filters."""

    extras: bool = Field(
        default=False, description="Remove Collectors Editions, live recordings, etc."
    )
    repeats: bool = Field(
        default=False,
        description="Pick highest quality from albums with identical titles",
    )
    non_albums: bool = Field(default=False, description="Remove EPs and Singles")
    features: bool = Field(
        default=False, description="Remove albums whose artist is not the one requested"
    )
    non_studio_albums: bool = Field(default=False, description="Skip non-studio albums")
    non_remaster: bool = Field(
        default=False, description="Only download remastered albums"
    )


class ArtworkConfig(BaseConfig):
    """Configuration for artwork handling."""

    embed: bool = Field(default=True, description="Write artwork to audio file")
    embed_size: Literal["thumbnail", "small", "large", "original"] = Field(
        default="large",
        description="Size of embedded artwork (original can be up to 30MB)",
    )
    embed_max_width: int = Field(
        default=-1,
        description="Max width/height of embedded art in pixels (-1 for no limit)",
    )
    save_artwork: bool = Field(
        default=True, description="Save cover image as separate JPG file"
    )
    saved_max_width: int = Field(
        default=-1,
        description="Max width/height of saved art in pixels (-1 for no limit)",
    )

    @field_validator("embed_max_width", "saved_max_width")
    @classmethod
    def validate_max_width(cls, v: int) -> int:
        """Validate max width is -1 or positive."""
        if v < -1 or v == 0:
            msg = "Max width must be -1 (no limit) or positive"
            raise ValueError(msg)
        return v


class MetadataConfig(BaseConfig):
    """Configuration for metadata handling."""

    set_playlist_to_album: bool = Field(
        default=True,
        description="Set ALBUM field to playlist name for playlist tracks",
    )
    renumber_playlist_tracks: bool = Field(
        default=True,
        description="Set track number to playlist position instead of album position",
    )
    exclude: list[str] = Field(
        default_factory=list, description="Metadata tags to exclude from files"
    )
    embed: bool = Field(default=True, description="Embed metadata in audio files")
    save: bool = Field(default=True, description="Save metadata to separate files")
    format: Literal["ID3v2.3", "ID3v2.4", "MP4", "Vorbis", "AAC"] = Field(
        default="ID3v2.4", description="Metadata format for embedded files"
    )

    @field_validator("format")
    @classmethod
    def validate_format(cls, v: str) -> str:
        """Validate format is valid."""
        if v not in ["ID3v2.3", "ID3v2.4", "MP4", "Vorbis", "AAC"]:
            msg = "Invalid format"
            raise ValueError(msg)
        return v


class FilepathsConfig(BaseConfig):
    """Configuration for file and folder naming."""

    add_singles_to_folder: bool = Field(
        default=False,
        description="Create folders for single tracks using folder_format template",
    )
    folder_format: str = Field(
        default="{albumartist} - {title} ({year}) [{container}] [{bit_depth}B-{sampling_rate}kHz]",
        description="Template for folder names",
    )
    track_format: str = Field(
        default="{tracknumber:02}. {artist} - {title}{explicit}",
        description="Template for track filenames",
    )
    restrict_characters: bool = Field(
        default=False, description="Only allow printable ASCII characters in filenames"
    )
    truncate_to: int | bool = Field(
        default=120,
        description="Truncate filenames longer than this (False to disable)",
    )

    @field_validator("truncate_to")
    @classmethod
    def validate_truncate_to(cls, v: int | bool) -> int | bool:
        """Validate truncate_to is False or positive integer."""
        if isinstance(v, bool):
            return v
        if isinstance(v, int) and v <= 0:
            msg = "Truncate length must be positive or False"
            raise ValueError(msg)
        return v


class LastFMConfig(BaseConfig):
    """Configuration for Last.fm playlist downloads."""

    source: str = Field(
        default="qobuz", description="Primary source to search for tracks"
    )
    fallback_source: str = Field(
        default="", description="Fallback source if primary fails"
    )


class CLIConfig(BaseConfig):
    """Configuration for CLI interface."""

    text_output: bool = Field(
        default=True, description="Print download status messages to screen"
    )
    progress_bars: bool = Field(
        default=True, description="Show resolve and download progress bars"
    )
    max_search_results: int = Field(
        default=25, description="Maximum search results in interactive menu"
    )

    @field_validator("max_search_results")
    @classmethod
    def validate_max_results(cls, v: int) -> int:
        """Validate max search results is positive."""
        if v <= 0:
            msg = "Max search results must be positive"
            raise ValueError(msg)
        return v


class MiscConfig(BaseConfig):
    """Configuration for miscellaneous settings."""

    version: str = Field(default="2.0.6", description="Config file version identifier")
    check_for_updates: bool = Field(
        default=True, description="Check for new ripstream versions"
    )


class UserConfig(BaseConfig):
    """Main user configuration containing all sections."""

    # General settings
    downloads: DownloadsConfig = Field(
        default_factory=DownloadsConfig, description="Download settings"
    )
    database: DatabaseConfig = Field(
        default_factory=DatabaseConfig, description="Database settings"
    )
    conversion: ConversionConfig = Field(
        default_factory=ConversionConfig, description="Audio conversion settings"
    )
    artwork: ArtworkConfig = Field(
        default_factory=ArtworkConfig, description="Artwork handling settings"
    )
    metadata: MetadataConfig = Field(
        default_factory=MetadataConfig, description="Metadata handling settings"
    )
    filepaths: FilepathsConfig = Field(
        default_factory=FilepathsConfig, description="File and folder naming settings"
    )
    lastfm: LastFMConfig = Field(
        default_factory=LastFMConfig, description="Last.fm integration settings"
    )
    cli: CLIConfig = Field(
        default_factory=CLIConfig, description="CLI interface settings"
    )
    misc: MiscConfig = Field(
        default_factory=MiscConfig, description="Miscellaneous settings"
    )

    # Service configurations
    qobuz: QobuzConfig = Field(
        default_factory=QobuzConfig, description="Qobuz service configuration"
    )
    tidal: TidalConfig = Field(
        default_factory=TidalConfig, description="Tidal service configuration"
    )
    deezer: DeezerConfig = Field(
        default_factory=DeezerConfig, description="Deezer service configuration"
    )
    soundcloud: SoundCloudConfig = Field(
        default_factory=SoundCloudConfig, description="SoundCloud service configuration"
    )
    youtube: YouTubeConfig = Field(
        default_factory=YouTubeConfig, description="YouTube service configuration"
    )

    # Qobuz-specific filters
    qobuz_filters: QobuzFiltersConfig = Field(
        default_factory=QobuzFiltersConfig,
        description="Qobuz discography filtering settings",
    )

    @classmethod
    def from_toml_file(cls, file_path: Path | str) -> "UserConfig":
        """Load configuration from a TOML file."""
        import tomllib

        if isinstance(file_path, str):
            file_path = Path(file_path)

        with file_path.open("rb") as f:
            data = tomllib.load(f)

        return cls.model_validate(data)

    @classmethod
    def from_json_file(cls, file_path: Path | str) -> "UserConfig":
        """Load configuration from a JSON file."""
        import json

        if isinstance(file_path, str):
            file_path = Path(file_path)

        with file_path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        return cls.model_validate(data)

    def to_dict(self) -> dict:
        """Convert configuration to dictionary for serialization."""
        return self.model_dump(mode="json")

    def to_json_file(self, file_path: Path | str) -> None:
        """Save configuration to a JSON file."""
        import json

        if isinstance(file_path, str):
            file_path = Path(file_path)

        # Ensure parent directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)

        with file_path.open("w", encoding="utf-8") as f:
            json.dump(self.model_dump(mode="json"), f, indent=2, ensure_ascii=False)

    def get_service_config(self, service_name: str):
        """Get configuration for a specific service."""
        service_map = {
            "qobuz": self.qobuz,
            "tidal": self.tidal,
            "deezer": self.deezer,
            "soundcloud": self.soundcloud,
            "youtube": self.youtube,
        }

        if service_name.lower() not in service_map:
            msg = f"Unknown service: {service_name}"
            raise ValueError(msg)

        return service_map[service_name.lower()]
