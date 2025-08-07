# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Album model with track relationships and metadata."""

from typing import Any, ForwardRef

from pydantic import Field, field_validator

from ripstream.models.artwork import Covers
from ripstream.models.base import (
    DownloadableMedia,
    MediaInfo,
    MetadataContainer,
    SearchableMedia,
)
from ripstream.models.enums import AlbumType, StreamingSource

# Forward references to avoid circular imports
ArtistRef = ForwardRef("Artist")
TrackRef = ForwardRef("Track")


class AlbumInfo(MediaInfo, MetadataContainer):
    """Basic album information from streaming sources."""

    title: str = Field(..., description="Album title")
    sort_title: str | None = Field(None, description="Title for sorting purposes")
    album_type: AlbumType = Field(default=AlbumType.ALBUM, description="Type of album")

    # Release information
    release_date: str | None = Field(None, description="Release date (YYYY-MM-DD)")
    release_year: int | None = Field(None, description="Release year")
    original_release_date: str | None = Field(None, description="Original release date")

    # Catalog information
    catalog_number: str | None = Field(None, description="Catalog number")
    barcode: str | None = Field(None, description="Barcode/UPC")
    label: str | None = Field(None, description="Record label")

    # Content information
    total_tracks: int = Field(default=0, description="Total number of tracks")
    total_discs: int = Field(default=1, description="Total number of discs")
    total_duration_seconds: float | None = Field(
        None, description="Total album duration"
    )
    hires: bool | None = Field(None, description="Whether album is high resolution")
    is_explicit: bool = Field(
        default=False, description="Whether album contains explicit content"
    )

    # Metadata
    genres: list[str] = Field(default_factory=list, description="Album genres")
    description: str | None = Field(None, description="Album description")
    copyright: str | None = Field(None, description="Copyright information")

    @field_validator("release_year")
    @classmethod
    def validate_release_year(cls, v: int | None) -> int | None:
        """Validate release year is reasonable."""
        if v is not None and (v < 1800 or v > 2030):
            msg = f"Invalid release year: {v}"
            raise ValueError(msg)
        return v

    @field_validator("total_tracks", "total_discs")
    @classmethod
    def validate_positive_counts(cls, v: int) -> int:
        """Validate counts are positive."""
        if v < 0:
            msg = "Track and disc counts must be non-negative"
            raise ValueError(msg)
        return v

    @property
    def duration_formatted(self) -> str | None:
        """Get total duration in HH:MM:SS format."""
        if self.total_duration_seconds is None:
            return None

        hours = int(self.total_duration_seconds // 3600)
        minutes = int((self.total_duration_seconds % 3600) // 60)
        seconds = int(self.total_duration_seconds % 60)

        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        return f"{minutes:02d}:{seconds:02d}"

    def add_genre(self, genre: str) -> None:
        """Add a genre to the album."""
        if genre not in self.genres:
            self.genres.append(genre)


class AlbumCredits(MetadataContainer):
    """Credits and personnel information for an album."""

    # Primary credits
    artist: str = Field(..., description="Primary album artist")
    album_artist: str | None = Field(
        None, description="Album artist (for compilations)"
    )

    # Production credits
    producer: str | None = Field(None, description="Producer")
    executive_producer: str | None = Field(None, description="Executive producer")
    engineer: str | None = Field(None, description="Engineer")
    mixer: str | None = Field(None, description="Mixer")
    mastered_by: str | None = Field(None, description="Mastering engineer")

    # Additional credits
    additional_credits: dict[str, list[str]] = Field(
        default_factory=dict, description="Additional credits (role -> list of people)"
    )

    def add_credit(self, role: str, person: str) -> None:
        """Add a credit for a specific role."""
        if role not in self.additional_credits:
            self.additional_credits[role] = []
        if person not in self.additional_credits[role]:
            self.additional_credits[role].append(person)

    @property
    def display_artist(self) -> str:
        """Get the display artist (album_artist if available, otherwise artist)."""
        return self.album_artist or self.artist


class AlbumStats(MetadataContainer):
    """Statistical information about an album."""

    total_plays: int | None = Field(
        None, description="Total play count across all tracks"
    )
    popularity_score: float | None = Field(None, description="Popularity score (0-100)")
    rating: float | None = Field(None, description="User rating (0-5)")
    review_count: int | None = Field(None, description="Number of reviews")
    average_rating: float | None = Field(None, description="Average user rating")

    @field_validator("popularity_score")
    @classmethod
    def validate_popularity_score(cls, v: float | None) -> float | None:
        """Validate popularity score is between 0 and 100."""
        if v is not None and (v < 0 or v > 100):
            msg = "Popularity score must be between 0 and 100"
            raise ValueError(msg)
        return v

    @field_validator("rating", "average_rating")
    @classmethod
    def validate_rating(cls, v: float | None) -> float | None:
        """Validate rating is between 0 and 5."""
        if v is not None and (v < 0 or v > 5):
            msg = "Rating must be between 0 and 5"
            raise ValueError(msg)
        return v


def _create_covers() -> Covers:
    """Return a default Covers instance."""
    return Covers()  # type: ignore


def _create_album_stats() -> AlbumStats:
    """Return a default AlbumStats instance."""
    return AlbumStats()  # type: ignore


class Album(DownloadableMedia, SearchableMedia):
    """Complete album model with all metadata and track relationships."""

    info: AlbumInfo = Field(..., description="Basic album information")
    credits: AlbumCredits = Field(..., description="Album credits and personnel")
    covers: Covers = Field(
        default_factory=_create_covers, description="Album cover images"
    )
    stats: AlbumStats = Field(
        default_factory=_create_album_stats, description="Album statistics"
    )

    # Additional materials
    booklets: list[dict[str, Any]] = Field(
        default_factory=list, description="Album booklets and additional materials"
    )

    # Relationships (using string references to avoid circular imports)
    artist_ids: list[str] = Field(
        default_factory=list, description="Associated artist IDs"
    )
    track_ids: list[str] = Field(default_factory=list, description="Track IDs in order")

    # Organization
    tags: list[str] = Field(default_factory=list, description="User-defined tags")
    is_favorite: bool = Field(default=False, description="Whether marked as favorite")
    is_compilation: bool = Field(
        default=False, description="Whether this is a compilation"
    )
    is_various_artists: bool = Field(
        default=False, description="Whether this is a various artists album"
    )

    # Download organization
    download_folder: str | None = Field(None, description="Custom download folder path")

    @classmethod
    def from_source_data(
        cls,
        source: StreamingSource,
        album_id: str,
        data: dict[str, Any],
        **kwargs: object,
    ) -> "Album":
        """Create an Album from streaming source data."""
        # Extract basic info
        info = AlbumInfo(
            id=album_id,
            source=source,
            title=data.get("title", "Unknown Album"),
            sort_title=data.get("sort_title"),
            album_type=AlbumType(data.get("album_type", "album")),
            release_date=data.get("release_date"),
            release_year=data.get("release_year"),
            original_release_date=data.get("original_release_date"),
            catalog_number=data.get("catalog_number"),
            barcode=data.get("barcode"),
            label=data.get("label"),
            total_tracks=data.get("total_tracks", 0),
            total_discs=data.get("total_discs", 1),
            total_duration_seconds=data.get("total_duration"),
            genres=data.get("genres", []),
            description=data.get("description"),
            copyright=data.get("copyright"),
            url=data.get("url"),
            hires=data.get("hires", False),
            is_explicit=data.get("is_explicit", False),
        )

        # Extract credits
        album_credits = AlbumCredits(
            artist=data.get("artist", "Unknown Artist"),
            album_artist=data.get("album_artist"),
            producer=data.get("producer"),
            executive_producer=data.get("executive_producer"),
            engineer=data.get("engineer"),
            mixer=data.get("mixer"),
            mastered_by=data.get("mastered_by"),
        )

        # Extract covers
        covers = data.get("covers", Covers())  # type: ignore
        if not isinstance(covers, Covers):
            # If covers is not already a Covers object, create an empty one
            covers = Covers()  # type: ignore

        # Extract stats
        stats = AlbumStats(  # type: ignore
            popularity_score=data.get("popularity"),
            rating=data.get("rating"),
            review_count=data.get("review_count"),
            average_rating=data.get("average_rating"),
        )

        album = cls(
            info=info,
            credits=album_credits,
            covers=covers,
            stats=stats,
            artist_ids=data.get("artist_ids", []),
            track_ids=data.get("track_ids", []),
            is_compilation=data.get("is_compilation", False),
            is_various_artists=data.get("is_various_artists", False),
            **kwargs,
        )

        # Add raw metadata
        album.info.add_raw_metadata("source_data", data)

        return album

    @property
    def title(self) -> str:
        """Get the album title."""
        return self.info.title

    @property
    def artist(self) -> str:
        """Get the primary artist."""
        return self.credits.artist

    @property
    def display_artist(self) -> str:
        """Get the display artist."""
        return self.credits.display_artist

    @property
    def duration_formatted(self) -> str | None:
        """Get formatted total duration."""
        return self.info.duration_formatted

    @property
    def is_multi_disc(self) -> bool:
        """Check if this is a multi-disc album."""
        return self.info.total_discs > 1

    def add_track_id(self, track_id: str, position: int | None = None) -> None:
        """Add a track ID to the album."""
        if track_id not in self.track_ids:
            if position is not None:
                self.track_ids.insert(position, track_id)
            else:
                self.track_ids.append(track_id)
            self.info.total_tracks = len(self.track_ids)

    def remove_track_id(self, track_id: str) -> None:
        """Remove a track ID from the album."""
        if track_id in self.track_ids:
            self.track_ids.remove(track_id)
            self.info.total_tracks = len(self.track_ids)

    def add_artist_id(self, artist_id: str) -> None:
        """Add an associated artist ID."""
        if artist_id not in self.artist_ids:
            self.artist_ids.append(artist_id)

    def add_tag(self, tag: str) -> None:
        """Add a user-defined tag."""
        if tag not in self.tags:
            self.tags.append(tag)

    def toggle_favorite(self) -> None:
        """Toggle favorite status."""
        self.is_favorite = not self.is_favorite

    def get_download_folder_name(self) -> str:
        """Get a safe folder name for downloading the album."""
        if self.download_folder:
            return self.download_folder

        # Create safe folder name
        safe_artist = "".join(
            c
            for c in self.credits.display_artist
            if c.isalnum() or c in (" ", "-", "_")
        ).strip()
        safe_title = "".join(
            c for c in self.info.title if c.isalnum() or c in (" ", "-", "_")
        ).strip()

        folder_name = f"{safe_artist} - {safe_title}"
        if self.info.release_year:
            folder_name += f" ({self.info.release_year})"

        return folder_name or f"Album_{self.info.id}"

    def get_disc_track_ids(self, disc_number: int) -> list[str]:
        """Get track IDs for a specific disc (placeholder - would need track disc info)."""
        # This would require access to track information to filter by disc
        # For now, return all tracks if disc 1, empty otherwise
        return self.track_ids if disc_number == 1 else []

    def matches_search(self, query: str) -> bool:
        """Check if the album matches a search query."""
        query_lower = query.lower()
        return (
            query_lower in self.info.title.lower()
            or query_lower in self.credits.artist.lower()
            or (
                self.credits.album_artist is not None
                and query_lower in self.credits.album_artist.lower()
            )
            or any(query_lower in genre.lower() for genre in self.info.genres)
            or (self.info.label is not None and query_lower in self.info.label.lower())
            or (
                self.info.description is not None
                and query_lower in self.info.description.lower()
            )
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.info.id,
            "source": self.info.source,
            "title": self.info.title,
            "artist": self.credits.artist,
            "display_artist": self.display_artist,
            "album_artist": self.credits.album_artist,
            "album_type": self.info.album_type,
            "release_date": self.info.release_date,
            "release_year": self.info.release_year,
            "label": self.info.label,
            "total_tracks": self.info.total_tracks,
            "total_discs": self.info.total_discs,
            "duration": self.info.total_duration_seconds,
            "duration_formatted": self.duration_formatted,
            "genres": self.info.genres,
            "is_compilation": self.is_compilation,
            "is_various_artists": self.is_various_artists,
            "is_multi_disc": self.is_multi_disc,
            "popularity_score": self.stats.popularity_score,
            "rating": self.stats.rating,
            "is_favorite": self.is_favorite,
            "download_status": self.status,
            "covers": self.covers.model_dump() if self.covers.has_images else None,
        }
