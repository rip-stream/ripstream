# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Playlist model for track collections."""

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
TrackRef = ForwardRef("Track")


class PlaylistInfo(MediaInfo):
    """Basic playlist information from streaming sources."""

    name: str = Field(..., description="Playlist name")
    description: str | None = Field(None, description="Playlist description")

    # Ownership and visibility
    owner: str | None = Field(None, description="Playlist owner/creator")
    owner_id: str | None = Field(None, description="Owner's user ID")
    is_public: bool = Field(default=True, description="Whether playlist is public")
    is_collaborative: bool = Field(
        default=False, description="Whether playlist allows collaboration"
    )

    # Content information
    total_tracks: int = Field(default=0, description="Total number of tracks")
    total_duration_seconds: float | None = Field(
        None, description="Total playlist duration"
    )

    # Metadata
    tags: list[str] = Field(default_factory=list, description="Playlist tags")
    genres: list[str] = Field(
        default_factory=list, description="Dominant genres in playlist"
    )

    @field_validator("total_tracks")
    @classmethod
    def validate_total_tracks(cls, v: int) -> int:
        """Validate track count is non-negative."""
        if v < 0:
            msg = "Track count must be non-negative"
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

    def add_tag(self, tag: str) -> None:
        """Add a tag to the playlist."""
        if tag not in self.tags:
            self.tags.append(tag)

    def add_genre(self, genre: str) -> None:
        """Add a genre to the playlist."""
        if genre not in self.genres:
            self.genres.append(genre)


class PlaylistTrack(MetadataContainer):
    """A track within a playlist with position and metadata."""

    track_id: str = Field(..., description="Track ID")
    position: int = Field(..., description="Position in playlist (1-based)")
    album_id: str | None = Field(None, description="Album ID for the track, if known")
    added_at: str | None = Field(None, description="When track was added to playlist")
    added_by: str | None = Field(None, description="Who added the track")

    # Override metadata for playlist context
    custom_title: str | None = Field(
        None, description="Custom title for this playlist context"
    )
    custom_artist: str | None = Field(
        None, description="Custom artist for this playlist context"
    )
    notes: str | None = Field(
        None, description="User notes about this track in playlist"
    )

    @field_validator("position")
    @classmethod
    def validate_position(cls, v: int) -> int:
        """Validate position is positive."""
        if v < 1:
            msg = "Position must be positive"
            raise ValueError(msg)
        return v

    @property
    def display_title(self) -> str | None:
        """Get the display title (custom if available)."""
        return self.custom_title

    @property
    def display_artist(self) -> str | None:
        """Get the display artist (custom if available)."""
        return self.custom_artist


class PlaylistStats(MetadataContainer):
    """Statistical information about a playlist."""

    total_plays: int | None = Field(None, description="Total play count")
    followers: int | None = Field(None, description="Number of followers")
    likes: int | None = Field(None, description="Number of likes")
    shares: int | None = Field(None, description="Number of shares")
    last_played_at: str | None = Field(
        None, description="When playlist was last played"
    )
    last_modified_at: str | None = Field(
        None, description="When playlist was last modified"
    )

    def update_play_stats(self) -> None:
        """Update play statistics."""
        if self.total_plays is None:
            self.total_plays = 0
        self.total_plays += 1
        # last_played_at would be set to current time


class Playlist(DownloadableMedia, SearchableMedia):
    """Complete playlist model with track collections and metadata."""

    info: PlaylistInfo = Field(..., description="Basic playlist information")
    covers: Covers = Field(default_factory=Covers, description="Playlist cover images")
    stats: PlaylistStats = Field(
        default_factory=PlaylistStats, description="Playlist statistics"
    )

    # Track collection
    tracks: list[PlaylistTrack] = Field(
        default_factory=list, description="Tracks in playlist"
    )

    # Organization and preferences
    is_favorite: bool = Field(default=False, description="Whether marked as favorite")
    all_tracks_downloaded: bool = Field(
        default=False, description="Whether all tracks are downloaded"
    )
    download_folder: str | None = Field(None, description="Custom download folder path")

    # Playlist behavior
    shuffle_enabled: bool = Field(
        default=False, description="Whether shuffle is enabled"
    )
    repeat_mode: str = Field(default="none", description="Repeat mode: none, one, all")

    @classmethod
    def from_source_data(
        cls,
        source: StreamingSource,
        playlist_id: str,
        data: dict[str, Any],
        **kwargs: object,
    ) -> "Playlist":
        """Create a Playlist from streaming source data."""
        # Extract basic info
        info = PlaylistInfo(
            id=playlist_id,
            source=source,
            name=data.get("name", "Untitled Playlist"),
            description=data.get("description"),
            owner=data.get("owner"),
            owner_id=data.get("owner_id"),
            is_public=data.get("is_public", True),
            is_collaborative=data.get("is_collaborative", False),
            total_tracks=data.get("total_tracks", 0),
            total_duration_seconds=data.get("total_duration"),
            tags=data.get("tags", []),
            genres=data.get("genres", []),
            url=data.get("url"),
        )

        # Extract covers
        covers = Covers()
        if "covers" in data or "images" in data:
            data.get("covers") or data.get("images", [])
            # Implementation would parse cover data based on source format

        # Extract stats
        stats = PlaylistStats(
            total_plays=data.get("total_plays"),
            followers=data.get("followers"),
            likes=data.get("likes"),
            shares=data.get("shares"),
            last_played_at=data.get("last_played_at"),
            last_modified_at=data.get("last_modified_at"),
        )

        # Extract tracks
        tracks = []
        if "tracks" in data:
            for i, track_data in enumerate(data["tracks"], 1):
                playlist_track = PlaylistTrack(
                    track_id=track_data.get("id", ""),
                    position=track_data.get("position", i),
                    album_id=track_data.get("album_id"),
                    added_at=track_data.get("added_at"),
                    added_by=track_data.get("added_by"),
                    custom_title=track_data.get("custom_title"),
                    custom_artist=track_data.get("custom_artist"),
                    notes=track_data.get("notes"),
                )
                tracks.append(playlist_track)

        playlist = cls(info=info, covers=covers, stats=stats, tracks=tracks, **kwargs)

        # Add raw metadata
        playlist.stats.add_raw_metadata("source_data", data)

        return playlist

    @property
    def name(self) -> str:
        """Get the playlist name."""
        return self.info.name

    @property
    def duration_formatted(self) -> str | None:
        """Get formatted total duration."""
        return self.info.duration_formatted

    @property
    def track_count(self) -> int:
        """Get the number of tracks in the playlist."""
        return len(self.tracks)

    @property
    def is_empty(self) -> bool:
        """Check if the playlist is empty."""
        return len(self.tracks) == 0

    def add_track(
        self,
        track_id: str,
        position: int | None = None,
        added_by: str | None = None,
        **kwargs: object,
    ) -> PlaylistTrack:
        """Add a track to the playlist."""
        if position is None:
            position = len(self.tracks) + 1
        else:
            # Adjust positions of existing tracks
            for track in self.tracks:
                if track.position >= position:
                    track.position += 1

        playlist_track = PlaylistTrack(
            track_id=track_id, position=position, added_by=added_by, **kwargs
        )

        # Insert at correct position
        self.tracks.insert(position - 1, playlist_track)
        self.info.total_tracks = len(self.tracks)

        return playlist_track

    def remove_track(self, track_id: str) -> bool:
        """Remove a track from the playlist."""
        # Find the track to remove first
        track_to_remove = None
        for track in self.tracks:
            if track.track_id == track_id:
                track_to_remove = track
                break

        if track_to_remove is None:
            return False

        removed_position = track_to_remove.position
        self.tracks.remove(track_to_remove)

        # Adjust positions of remaining tracks
        for remaining_track in self.tracks:
            if remaining_track.position > removed_position:
                remaining_track.position -= 1

        self.info.total_tracks = len(self.tracks)
        return True

    def move_track(self, track_id: str, new_position: int) -> bool:
        """Move a track to a new position in the playlist."""
        # Find the track
        track_to_move = None
        old_index = -1
        for i, track in enumerate(self.tracks):
            if track.track_id == track_id:
                track_to_move = track
                old_index = i
                break

        if track_to_move is None:
            return False

        # Remove from old position
        self.tracks.pop(old_index)

        # Insert at new position
        new_index = new_position - 1
        self.tracks.insert(new_index, track_to_move)

        # Update all positions
        for i, track in enumerate(self.tracks):
            track.position = i + 1

        return True

    def get_track(self, track_id: str) -> PlaylistTrack | None:
        """Get a track by ID."""
        for track in self.tracks:
            if track.track_id == track_id:
                return track
        return None

    def get_track_ids(self) -> list[str]:
        """Get list of all track IDs in order."""
        return [
            track.track_id for track in sorted(self.tracks, key=lambda t: t.position)
        ]

    def shuffle_tracks(self) -> None:
        """Shuffle the track order."""
        import random

        random.shuffle(self.tracks)
        # Update positions
        for i, track in enumerate(self.tracks):
            track.position = i + 1

    def sort_tracks_by_title(self) -> None:
        """Sort tracks alphabetically by title (requires track data)."""
        # This would require access to actual track data
        # For now, just sort by track_id as placeholder
        self.tracks.sort(key=lambda t: t.track_id)
        for i, track in enumerate(self.tracks):
            track.position = i + 1

    def toggle_favorite(self) -> None:
        """Toggle favorite status."""
        self.is_favorite = not self.is_favorite

    def get_download_folder_name(self) -> str:
        """Get a safe folder name for downloading the playlist."""
        if self.download_folder:
            return self.download_folder

        # Create safe folder name
        safe_name = "".join(
            c for c in self.info.name if c.isalnum() or c in (" ", "-", "_")
        ).strip()
        folder_name = safe_name or f"Playlist_{self.info.id}"

        if self.info.owner:
            safe_owner = "".join(
                c for c in self.info.owner if c.isalnum() or c in (" ", "-", "_")
            ).strip()
            folder_name = f"{safe_owner} - {folder_name}"

        return folder_name

    def matches_search(self, query: str) -> bool:
        """Check if the playlist matches a search query."""
        query_lower = query.lower()
        return (
            query_lower in self.info.name.lower()
            or (self.info.description and query_lower in self.info.description.lower())
            or (self.info.owner and query_lower in self.info.owner.lower())
            or any(query_lower in tag.lower() for tag in self.info.tags)
            or any(query_lower in genre.lower() for genre in self.info.genres)
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.info.id,
            "source": self.info.source,
            "name": self.info.name,
            "description": self.info.description,
            "owner": self.info.owner,
            "is_public": self.info.is_public,
            "is_collaborative": self.info.is_collaborative,
            "total_tracks": self.info.total_tracks,
            "track_count": self.track_count,
            "duration": self.info.total_duration_seconds,
            "duration_formatted": self.duration_formatted,
            "tags": self.info.tags,
            "genres": self.info.genres,
            "is_favorite": self.is_favorite,
            "is_empty": self.is_empty,
            "followers": self.stats.followers,
            "likes": self.stats.likes,
            "download_status": self.status,
            "covers": self.covers.model_dump() if self.covers.has_images else None,
            "track_ids": self.get_track_ids(),
        }
