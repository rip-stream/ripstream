# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Artist model with metadata and relationships."""

from typing import Any, ForwardRef

from pydantic import Field, field_validator

from ripstream.models.artwork import Covers
from ripstream.models.base import (
    DownloadableMedia,
    MediaInfo,
    MetadataContainer,
    SearchableMedia,
)
from ripstream.models.enums import StreamingSource

# Forward references to avoid circular imports
AlbumRef = ForwardRef("Album")
TrackRef = ForwardRef("Track")


class ArtistInfo(MediaInfo):
    """Basic artist information from streaming sources."""

    name: str = Field(..., description="Artist name")
    sort_name: str | None = Field(None, description="Name for sorting purposes")
    disambiguation: str | None = Field(None, description="Disambiguation text")
    country: str | None = Field(None, description="Artist's country")
    formed_year: int | None = Field(None, description="Year the artist was formed")
    genres: list[str] = Field(default_factory=list, description="Musical genres")
    biography: str | None = Field(None, description="Artist biography")
    website: str | None = Field(None, description="Official website URL")
    social_links: dict[str, str] = Field(
        default_factory=dict, description="Social media links"
    )

    @field_validator("formed_year")
    @classmethod
    def validate_formed_year(cls, v: int | None) -> int | None:
        """Validate formed year is reasonable."""
        if v is not None and (v < 1800 or v > 2030):
            msg = f"Invalid formed year: {v}"
            raise ValueError(msg)
        return v

    def add_social_link(self, platform: str, url: str) -> None:
        """Add a social media link."""
        self.social_links[platform] = url

    def add_genre(self, genre: str) -> None:
        """Add a genre to the artist."""
        if genre not in self.genres:
            self.genres.append(genre)


class ArtistStats(MetadataContainer):
    """Statistical information about an artist."""

    total_albums: int = Field(default=0, description="Total number of albums")
    total_tracks: int = Field(default=0, description="Total number of tracks")
    total_plays: int | None = Field(None, description="Total play count")
    monthly_listeners: int | None = Field(None, description="Monthly listeners")
    followers: int | None = Field(None, description="Number of followers")
    popularity_score: float | None = Field(None, description="Popularity score (0-100)")

    @field_validator("popularity_score")
    @classmethod
    def validate_popularity_score(cls, v: float | None) -> float | None:
        """Validate popularity score is between 0 and 100."""
        if v is not None and (v < 0 or v > 100):
            msg = "Popularity score must be between 0 and 100"
            raise ValueError(msg)
        return v

    def update_stats(self, **kwargs: object) -> None:
        """Update statistics from source data."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)


class Artist(DownloadableMedia, SearchableMedia):
    """Complete artist model with all metadata and relationships."""

    info: ArtistInfo = Field(..., description="Basic artist information")
    covers: Covers = Field(default_factory=Covers, description="Artist cover images")
    stats: ArtistStats = Field(
        default_factory=ArtistStats, description="Artist statistics"
    )

    # Relationships (using string references to avoid circular imports)
    album_ids: list[str] = Field(default_factory=list, description="List of album IDs")
    featured_track_ids: list[str] = Field(
        default_factory=list, description="List of featured track IDs"
    )
    similar_artist_ids: list[str] = Field(
        default_factory=list, description="List of similar artist IDs"
    )

    # Filtering and organization
    is_various_artists: bool = Field(
        default=False, description="Whether this is a 'Various Artists' entry"
    )
    is_verified: bool = Field(
        default=False, description="Whether the artist is verified on the platform"
    )

    @classmethod
    def from_source_data(
        cls,
        source: StreamingSource,
        artist_id: str,
        data: dict[str, Any],
        **kwargs: object,
    ) -> "Artist":
        """Create an Artist from streaming source data."""
        # Extract basic info
        info = ArtistInfo(
            id=artist_id,
            source=source,
            name=data.get("name", "Unknown Artist"),
            sort_name=data.get("sort_name"),
            disambiguation=data.get("disambiguation"),
            country=data.get("country"),
            formed_year=data.get("formed_year"),
            genres=data.get("genres", []),
            biography=data.get("biography"),
            website=data.get("website"),
            url=data.get("url"),
        )

        # Extract covers
        covers = Covers()
        if "covers" in data or "images" in data:
            covers = data.get("covers") or data.get("images", [])
            # Implementation would parse cover data based on source format

        # Extract stats
        stats = ArtistStats()
        if "stats" in data and data["stats"] is not None:
            stats.update_stats(**data["stats"])

        artist = cls(
            info=info,
            covers=covers,
            stats=stats,
            album_ids=data.get("album_ids", []),
            featured_track_ids=data.get("featured_track_ids", []),
            similar_artist_ids=data.get("similar_artist_ids", []),
            is_various_artists=data.get("is_various_artists", False),
            is_verified=data.get("is_verified", False),
            **kwargs,
        )

        # Add raw metadata to stats (which inherits from MetadataContainer)
        artist.stats.add_raw_metadata("source_data", data)

        return artist

    @property
    def name(self) -> str:
        """Get the artist name."""
        return self.info.name

    @property
    def display_name(self) -> str:
        """Get the display name (with disambiguation if available)."""
        if self.info.disambiguation:
            return f"{self.info.name} ({self.info.disambiguation})"
        return self.info.name

    def add_album_id(self, album_id: str) -> None:
        """Add an album ID to the artist's discography."""
        if album_id not in self.album_ids:
            self.album_ids.append(album_id)
            self.stats.total_albums = len(self.album_ids)

    def add_featured_track_id(self, track_id: str) -> None:
        """Add a featured track ID."""
        if track_id not in self.featured_track_ids:
            self.featured_track_ids.append(track_id)

    def add_similar_artist_id(self, artist_id: str) -> None:
        """Add a similar artist ID."""
        if artist_id not in self.similar_artist_ids:
            self.similar_artist_ids.append(artist_id)

    def get_download_folder_name(self) -> str:
        """Get a safe folder name for downloading the artist's content."""
        # Clean the name for filesystem use
        safe_name = "".join(
            c for c in self.info.name if c.isalnum() or c in (" ", "-", "_")
        ).strip()
        return safe_name or f"Artist_{self.info.id}"

    def matches_search(self, query: str) -> bool:
        """Check if the artist matches a search query."""
        query_lower = query.lower()
        return (
            query_lower in self.info.name.lower()
            or (self.info.sort_name and query_lower in self.info.sort_name.lower())
            or any(query_lower in genre.lower() for genre in self.info.genres)
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.info.id,
            "source": self.info.source,
            "name": self.info.name,
            "display_name": self.display_name,
            "genres": self.info.genres,
            "country": self.info.country,
            "formed_year": self.info.formed_year,
            "album_count": self.stats.total_albums,
            "track_count": self.stats.total_tracks,
            "is_various_artists": self.is_various_artists,
            "is_verified": self.is_verified,
            "covers": self.covers.model_dump() if self.covers.has_images else None,
        }
