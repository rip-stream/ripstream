# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Track model with detailed metadata and audio information."""

from typing import Any, ForwardRef

from pydantic import Field, field_validator

from ripstream.models.artwork import Covers
from ripstream.models.audio import AudioInfo, DownloadableAudio
from ripstream.models.base import (
    DownloadableMedia,
    MediaInfo,
    MetadataContainer,
    SearchableMedia,
)
from ripstream.models.enums import StreamingSource

# Forward references to avoid circular imports
AlbumRef = ForwardRef("Album")
ArtistRef = ForwardRef("Artist")


class TrackInfo(MediaInfo, MetadataContainer):
    """Basic track information from streaming sources."""

    title: str = Field(..., description="Track title")
    sort_title: str | None = Field(None, description="Title for sorting purposes")
    version: str | None = Field(
        None, description="Track version (e.g., 'Remix', 'Live')"
    )
    work: str | None = Field(None, description="Classical work title")
    movement: str | None = Field(None, description="Classical movement")

    # Track positioning
    track_number: int = Field(default=1, description="Track number within album")
    disc_number: int = Field(default=1, description="Disc number for multi-disc albums")
    total_tracks: int | None = Field(None, description="Total tracks on the disc/album")
    total_discs: int | None = Field(None, description="Total discs in the album")

    # Identifiers
    isrc: str | None = Field(None, description="International Standard Recording Code")
    upc: str | None = Field(None, description="Universal Product Code")

    # Metadata
    lyrics: str | None = Field(None, description="Track lyrics")
    language: str | None = Field(None, description="Lyrics language")
    copyright: str | None = Field(None, description="Copyright information")

    @field_validator("track_number", "disc_number")
    @classmethod
    def validate_positive_numbers(cls, v: int) -> int:
        """Validate track and disc numbers are positive."""
        if v < 1:
            msg = "Track and disc numbers must be positive"
            raise ValueError(msg)
        return v

    @property
    def full_title(self) -> str:
        """Get the full title including work and version."""
        parts = []
        if self.work:
            parts.append(self.work)
        parts.append(self.title)
        if self.version:
            parts.append(f"({self.version})")
        return ": ".join(parts) if self.work else " ".join(parts)

    @property
    def position_string(self) -> str:
        """Get track position as string (e.g., '1.05' for disc 1, track 5)."""
        return f"{self.disc_number}.{self.track_number:02d}"


class TrackCredits(MetadataContainer):
    """Credits and personnel information for a track."""

    # Primary credits
    artist: str = Field(..., description="Primary performing artist")
    album_artist: str | None = Field(
        None, description="Album artist (may differ from track artist)"
    )
    composer: str | None = Field(None, description="Composer")
    lyricist: str | None = Field(None, description="Lyricist")
    producer: str | None = Field(None, description="Producer")

    # Additional credits
    featured_artists: list[str] = Field(
        default_factory=list, description="Featured artists"
    )
    additional_credits: dict[str, list[str]] = Field(
        default_factory=dict, description="Additional credits (role -> list of people)"
    )

    def add_featured_artist(self, artist: str) -> None:
        """Add a featured artist."""
        if artist not in self.featured_artists:
            self.featured_artists.append(artist)

    def add_credit(self, role: str, person: str) -> None:
        """Add a credit for a specific role."""
        if role not in self.additional_credits:
            self.additional_credits[role] = []
        if person not in self.additional_credits[role]:
            self.additional_credits[role].append(person)

    @property
    def display_artist(self) -> str:
        """Get the display artist including featured artists."""
        if not self.featured_artists:
            return self.artist
        featured = ", ".join(self.featured_artists)
        return f"{self.artist} (feat. {featured})"


class Track(DownloadableMedia, SearchableMedia):
    """Complete track model with all metadata and audio information."""

    info: TrackInfo = Field(..., description="Basic track information")
    credits: TrackCredits = Field(..., description="Track credits and personnel")
    audio: AudioInfo = Field(..., description="Audio technical information")
    covers: Covers = Field(default_factory=Covers, description="Track cover images")
    downloadable: DownloadableAudio | None = Field(
        None, description="Download information"
    )

    # Relationships (using string references to avoid circular imports)
    album_id: str | None = Field(None, description="Parent album ID")
    artist_ids: list[str] = Field(
        default_factory=list, description="Associated artist IDs"
    )

    # Additional metadata
    release_date: str | None = Field(None, description="Track release date")
    genres: list[str] = Field(default_factory=list, description="Track genres")
    tags: list[str] = Field(default_factory=list, description="User-defined tags")

    # Playback and popularity
    play_count: int = Field(default=0, description="Number of times played")
    popularity_score: float | None = Field(None, description="Popularity score (0-100)")
    is_favorite: bool = Field(default=False, description="Whether marked as favorite")

    @field_validator("popularity_score")
    @classmethod
    def validate_popularity_score(cls, v: float | None) -> float | None:
        """Validate popularity score is between 0 and 100."""
        if v is not None and (v < 0 or v > 100):
            msg = "Popularity score must be between 0 and 100"
            raise ValueError(msg)
        return v

    @classmethod
    def from_source_data(
        cls,
        source: StreamingSource,
        track_id: str,
        data: dict[str, Any],
        album_data: dict[str, Any] | None = None,
        **kwargs: object,
    ) -> "Track":
        """Create a Track from streaming source data."""
        # Extract basic info
        info = TrackInfo(
            id=track_id,
            source=source,
            title=data.get("title", "Unknown Track"),
            sort_title=data.get("sort_title"),
            version=data.get("version"),
            work=data.get("work"),
            movement=data.get("movement"),
            track_number=data.get("track_number", 1),
            disc_number=data.get("disc_number", 1),
            total_tracks=data.get("total_tracks"),
            total_discs=data.get("total_discs"),
            isrc=data.get("isrc"),
            upc=data.get("upc"),
            lyrics=data.get("lyrics"),
            language=data.get("language"),
            copyright=data.get("copyright"),
            url=data.get("url"),
        )

        # Extract credits
        track_credits = TrackCredits(
            artist=data.get("artist", "Unknown Artist"),
            album_artist=data.get("album_artist")
            or (album_data.get("artist") if album_data else None),
            composer=data.get("composer"),
            lyricist=data.get("lyricist"),
            producer=data.get("producer"),
            featured_artists=data.get("featured_artists", []),
        )

        # Extract audio info
        audio = AudioInfo(
            quality=data.get("quality", 0),
            bit_depth=data.get("bit_depth"),
            sampling_rate=data.get("sampling_rate"),
            bitrate=data.get("bitrate"),
            codec=data.get("codec"),
            container=data.get("container"),
            duration_seconds=data.get("duration"),
            file_size_bytes=data.get("file_size"),
            is_lossless=data.get("is_lossless"),
            is_explicit=data.get("is_explicit", False),
        )

        # TODO: Extract covers

        track = cls(
            info=info,
            credits=track_credits,
            audio=audio,
            covers=Covers(),
            album_id=data.get("album_id"),
            artist_ids=data.get("artist_ids", []),
            release_date=data.get("release_date"),
            genres=data.get("genres", []),
            popularity_score=data.get("popularity"),
            **kwargs,
        )

        # Add raw metadata
        track.info.add_raw_metadata("source_data", data)
        if album_data:
            track.info.add_raw_metadata("album_data", album_data)

        return track

    @property
    def title(self) -> str:
        """Get the track title."""
        return self.info.title

    @property
    def display_title(self) -> str:
        """Get the full display title."""
        return self.info.full_title

    @property
    def artist(self) -> str:
        """Get the primary artist."""
        return self.credits.artist

    @property
    def display_artist(self) -> str:
        """Get the display artist including featured artists."""
        return self.credits.display_artist

    @property
    def duration_formatted(self) -> str | None:
        """Get formatted duration."""
        return self.audio.duration_formatted

    def add_genre(self, genre: str) -> None:
        """Add a genre to the track."""
        if genre not in self.genres:
            self.genres.append(genre)

    def add_tag(self, tag: str) -> None:
        """Add a user-defined tag."""
        if tag not in self.tags:
            self.tags.append(tag)

    def add_artist_id(self, artist_id: str) -> None:
        """Add an associated artist ID."""
        if artist_id not in self.artist_ids:
            self.artist_ids.append(artist_id)

    def increment_play_count(self) -> None:
        """Increment the play count."""
        self.play_count += 1

    def toggle_favorite(self) -> None:
        """Toggle favorite status."""
        self.is_favorite = not self.is_favorite

    def get_filename(
        self, format_string: str = "{track_number:02d} - {artist} - {title}"
    ) -> str:
        """Generate a filename for the track."""
        # Clean values for filesystem use
        safe_artist = "".join(
            c for c in self.credits.artist if c.isalnum() or c in (" ", "-", "_")
        ).strip()
        safe_title = "".join(
            c for c in self.info.title if c.isalnum() or c in (" ", "-", "_")
        ).strip()

        filename = format_string.format(
            track_number=self.info.track_number,
            disc_number=self.info.disc_number,
            artist=safe_artist or "Unknown Artist",
            title=safe_title or "Unknown Track",
            album_artist=self.credits.album_artist or safe_artist or "Unknown Artist",
        )

        # Add file extension based on audio format
        extension = self.audio.container or "flac"
        return f"{filename}.{extension.lower()}"

    def matches_search(self, query: str) -> bool:
        """Check if the track matches a search query."""
        query_lower = query.lower()
        return (
            query_lower in self.info.title.lower()
            or query_lower in self.credits.artist.lower()
            or (
                self.credits.album_artist
                and query_lower in self.credits.album_artist.lower()
            )
            or any(
                query_lower in artist.lower()
                for artist in self.credits.featured_artists
            )
            or any(query_lower in genre.lower() for genre in self.genres)
            or (self.info.lyrics and query_lower in self.info.lyrics.lower())
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.info.id,
            "source": self.info.source,
            "title": self.info.title,
            "display_title": self.display_title,
            "artist": self.credits.artist,
            "display_artist": self.display_artist,
            "album_artist": self.credits.album_artist,
            "track_number": self.info.track_number,
            "disc_number": self.info.disc_number,
            "duration": self.audio.duration_seconds,
            "duration_formatted": self.duration_formatted,
            "quality": self.audio.quality,
            "is_explicit": self.audio.is_explicit,
            "genres": self.genres,
            "release_date": self.release_date,
            "popularity_score": self.popularity_score,
            "play_count": self.play_count,
            "is_favorite": self.is_favorite,
            "download_status": self.status,
            "covers": self.covers.model_dump() if self.covers.has_images else None,
        }
