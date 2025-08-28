# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Qobuz-specific models and data structures."""

from typing import Any

from pydantic import BaseModel, Field

from ripstream.models.base import RipStreamBaseModel


class QobuzCredentials(BaseModel):
    """Qobuz authentication credentials."""

    email_or_userid: str = Field(..., description="Email address or user ID")
    password_or_token: str = Field(..., description="Password or auth token")
    app_id: str | None = Field(None, description="Qobuz app ID")
    secrets: list[str] = Field(default_factory=list, description="App secrets")
    use_auth_token: bool = Field(default=False, description="Whether to use auth token")


class QobuzQuality(BaseModel):
    """Qobuz quality information."""

    format_id: int = Field(..., description="Qobuz format ID")
    quality_name: str = Field(..., description="Quality display name")
    bitrate: int | None = Field(None, description="Bitrate in kbps")
    bit_depth: int | None = Field(None, description="Bit depth")
    sampling_rate: int | None = Field(None, description="Sampling rate in Hz")
    codec: str = Field(..., description="Audio codec")
    is_lossless: bool = Field(..., description="Whether quality is lossless")


class QobuzApiResponse(RipStreamBaseModel):
    """Base class for Qobuz API responses."""

    # Raw response data for debugging and future use
    raw_data: dict[str, Any] = Field(
        default_factory=dict, description="Raw API response"
    )


class QobuzTrackResponse(QobuzApiResponse):
    """Qobuz track API response."""

    # Basic track info
    title: str = Field(..., description="Track title")
    version: str | None = Field(None, description="Track version")
    duration: int = Field(..., description="Duration in seconds")
    track_number: int = Field(..., description="Track number")
    disc_number: int = Field(default=1, description="Disc number")

    # Artist info
    performer: dict[str, Any] | None = Field(
        None, description="Performer information (optional in some responses)"
    )
    composer: dict[str, Any] | None = Field(None, description="Composer information")

    # Album info
    album: dict[str, Any] = Field(..., description="Album information")

    # Quality and format
    maximum_bit_depth: int | None = Field(None, description="Maximum bit depth")
    maximum_sampling_rate: float | None = Field(
        None, description="Maximum sampling rate"
    )

    # Identifiers
    isrc: str | None = Field(None, description="ISRC code")

    # Metadata
    copyright: str | None = Field(None, description="Copyright information")
    parental_warning: bool = Field(default=False, description="Parental warning flag")

    # Artwork
    image: dict[str, Any] | None = Field(None, description="Cover artwork URLs")

    # Qobuz specific
    purchasable: bool = Field(default=True, description="Whether track is purchasable")
    streamable: bool = Field(default=True, description="Whether track is streamable")
    previewable: bool = Field(default=True, description="Whether track has preview")

    @property
    def artist_name(self) -> str:
        """Get the primary artist name."""
        if not self.performer:
            return "Unknown Artist"
        return self.performer.get("name", "Unknown Artist")

    @property
    def album_title(self) -> str:
        """Get the album title."""
        return self.album.get("title", "Unknown Album")

    @property
    def album_artist(self) -> str:
        """Get the album artist."""
        return self.album.get("artist", {}).get("name", self.artist_name)

    def get_cover_urls(self) -> dict[str, str]:
        """Extract cover artwork URLs from the API response."""
        if not self.image:
            return {}

        urls = {}
        # Extract different sizes following ripstream pattern
        if "large" in self.image:
            urls["large"] = self.image["large"]
            # Generate original size URL by replacing 600 with org
            urls["original"] = "org".join(self.image["large"].rsplit("600", 1))
        if "small" in self.image:
            urls["small"] = self.image["small"]
        if "thumbnail" in self.image:
            urls["thumbnail"] = self.image["thumbnail"]

        return urls


class QobuzAlbumResponse(QobuzApiResponse):
    """Qobuz album API response."""

    # Basic album info
    title: str = Field(..., description="Album title")
    version: str | None = Field(None, description="Album version")
    duration: int = Field(..., description="Total duration in seconds")
    tracks_count: int = Field(..., description="Number of tracks")

    # Artist info
    artist: dict[str, Any] = Field(..., description="Artist information")

    # Release info
    release_date_original: str | None = Field(None, description="Original release date")
    release_date_download: str | None = Field(None, description="Download release date")
    release_date_stream: str | None = Field(None, description="Stream release date")

    # Quality info
    maximum_bit_depth: int | None = Field(None, description="Maximum bit depth")
    maximum_sampling_rate: float | None = Field(
        None, description="Maximum sampling rate"
    )
    hires: bool | None = Field(None, description="Whether album is high resolution")

    # Label and catalog
    label: dict[str, Any] | None = Field(None, description="Record label information")
    upc: str | None = Field(None, description="UPC code")

    # Genre and style
    genre: dict[str, Any] | None = Field(None, description="Genre information")
    genres_list: list[str] = Field(default_factory=list, description="List of genres")

    # Metadata
    copyright: str | None = Field(None, description="Copyright information")
    parental_warning: bool = Field(default=False, description="Parental warning flag")
    description: str | None = Field(None, description="Album description")

    # Artwork
    image: dict[str, Any] | None = Field(None, description="Cover artwork URLs")

    # Additional materials
    goodies: list[dict[str, Any]] = Field(
        default_factory=list, description="Booklets and additional materials"
    )

    # Qobuz specific
    purchasable: bool = Field(default=True, description="Whether album is purchasable")
    streamable: bool = Field(default=True, description="Whether album is streamable")
    previewable: bool = Field(default=True, description="Whether album has previews")

    # Tracks
    tracks: dict[str, Any] | None = Field(None, description="Tracks information")

    @property
    def artist_name(self) -> str:
        """Get the primary artist name."""
        return self.artist.get("name", "Unknown Artist")

    @property
    def label_name(self) -> str | None:
        """Get the label name."""
        return self.label.get("name") if self.label else None

    @property
    def genre_name(self) -> str | None:
        """Get the primary genre name."""
        return self.genre.get("name") if self.genre else None

    def get_cover_urls(self) -> dict[str, str]:
        """Extract cover artwork URLs from the API response."""
        if not self.image:
            return {}

        urls = {}
        # Extract different sizes following ripstream pattern
        if "large" in self.image:
            urls["large"] = self.image["large"]
            # Generate original size URL by replacing 600 with org
            urls["original"] = "org".join(self.image["large"].rsplit("600", 1))
        if "small" in self.image:
            urls["small"] = self.image["small"]
        if "thumbnail" in self.image:
            urls["thumbnail"] = self.image["thumbnail"]

        return urls

    def get_booklets(self) -> list[dict[str, Any]]:
        """Extract booklet/PDF information from goodies."""
        if not self.goodies:
            return []

        return [
            {
                "url": goodie.get("url", ""),
                "name": goodie.get("name", "booklet.pdf"),
                "file_format_id": goodie.get("file_format_id"),
                "description": goodie.get("description", ""),
            }
            for goodie in self.goodies
            if goodie.get("file_format_id") == 21  # PDF format
        ]


class QobuzArtistResponse(QobuzApiResponse):
    """Qobuz artist API response."""

    # Basic artist info
    name: str = Field(..., description="Artist name")
    slug: str | None = Field(None, description="Artist slug")
    biography: dict[str, Any] | None = Field(None, description="Artist biography")

    # Metadata
    albums_count: int = Field(default=0, description="Number of albums")

    # Artwork
    image: dict[str, Any] | None = Field(None, description="Artist artwork URLs")

    # Albums
    albums: dict[str, Any] | None = Field(None, description="Albums information")

    def get_cover_urls(self) -> dict[str, str]:
        """Extract cover artwork URLs from the API response."""
        if not self.image:
            return {}

        urls = {}
        # Extract different sizes following ripstream pattern
        if "large" in self.image:
            urls["large"] = self.image["large"]
            # Generate original size URL by replacing 600 with org
            urls["original"] = "org".join(self.image["large"].rsplit("600", 1))
        if "small" in self.image:
            urls["small"] = self.image["small"]
        if "thumbnail" in self.image:
            urls["thumbnail"] = self.image["thumbnail"]

        return urls


class QobuzPlaylistResponse(QobuzApiResponse):
    """Qobuz playlist API response."""

    # Basic playlist info
    name: str = Field(..., description="Playlist name")
    description: str | None = Field(None, description="Playlist description")
    duration: int = Field(..., description="Total duration in seconds")
    tracks_count: int = Field(..., description="Number of tracks")

    # Owner info
    owner: dict[str, Any] = Field(..., description="Playlist owner information")

    # Metadata
    is_public: bool = Field(default=False, description="Whether playlist is public")
    is_collaborative: bool = Field(
        default=False, description="Whether playlist is collaborative"
    )
    created_at: int | None = Field(None, description="Creation timestamp")
    updated_at: int | None = Field(None, description="Last update timestamp")

    # Tracks
    tracks: dict[str, Any] | None = Field(None, description="Tracks information")

    @property
    def owner_name(self) -> str:
        """Get the owner name."""
        return self.owner.get("name", "Unknown Owner")


class QobuzSearchResult(RipStreamBaseModel):
    """Qobuz search result container."""

    query: str = Field(..., description="Search query")
    albums: dict[str, Any] | None = Field(None, description="Album search results")
    tracks: dict[str, Any] | None = Field(None, description="Track search results")
    artists: dict[str, Any] | None = Field(None, description="Artist search results")
    playlists: dict[str, Any] | None = Field(
        None, description="Playlist search results"
    )


class QobuzDownloadInfo(RipStreamBaseModel):
    """Qobuz download information."""

    url: str = Field(..., description="Download URL")
    format_id: int = Field(..., description="Format ID")
    mime_type: str = Field(..., description="MIME type")
    restrictions: list[dict[str, Any]] = Field(
        default_factory=list, description="Download restrictions"
    )

    @property
    def has_restrictions(self) -> bool:
        """Check if download has restrictions."""
        return len(self.restrictions) > 0

    @property
    def restriction_codes(self) -> list[str]:
        """Get list of restriction codes."""
        return [r.get("code", "") for r in self.restrictions]
