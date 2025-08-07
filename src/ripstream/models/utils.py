# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Utility functions for model operations."""

import re
from pathlib import Path
from typing import Any

from ripstream.models.album import Album
from ripstream.models.artist import Artist
from ripstream.models.enums import AudioQuality, StreamingSource
from ripstream.models.playlist import Playlist
from ripstream.models.track import Track


def sanitize_filename(filename: str, max_length: int = 255) -> str:
    """Sanitize a filename for filesystem compatibility."""
    # Remove or replace invalid characters
    invalid_chars = r'[<>:"/\\|?*]'
    sanitized = re.sub(invalid_chars, "_", filename)

    # Remove control characters
    sanitized = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", sanitized)

    # Remove leading/trailing dots and spaces
    sanitized = sanitized.strip(". ")

    # Truncate if too long
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length].rstrip(". ")

    # Ensure not empty
    return sanitized or "untitled"


def format_duration(seconds: float | None) -> str:
    """Format duration in seconds to HH:MM:SS or MM:SS format."""
    if seconds is None:
        return "00:00"

    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)

    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def parse_duration(duration_str: str) -> float | None:
    """Parse duration string (HH:MM:SS or MM:SS) to seconds."""
    if not duration_str:
        return None

    try:
        parts = duration_str.split(":")
        if len(parts) == 2:  # MM:SS
            minutes, seconds = map(int, parts)
            return minutes * 60 + seconds
        if len(parts) == 3:  # HH:MM:SS
            hours, minutes, seconds = map(int, parts)
            return hours * 3600 + minutes * 60 + seconds
    except ValueError:
        return None
    else:
        return None


def format_file_size(size_bytes: int | None) -> str:
    """Format file size in bytes to human-readable format."""
    if size_bytes is None:
        return "Unknown"

    size = float(size_bytes)
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def get_quality_description(quality: AudioQuality) -> str:
    """Get human-readable description of audio quality."""
    descriptions = {
        AudioQuality.LOW: "Low Quality (~128 kbps)",
        AudioQuality.HIGH: "High Quality (~320 kbps)",
        AudioQuality.LOSSLESS: "CD Quality (16-bit/44.1kHz)",
        AudioQuality.HI_RES: "Hi-Res (24-bit/96kHz+)",
    }
    return descriptions.get(quality, "Unknown Quality")


def create_download_path(
    base_path: str | Path,
    artist: str,
    album: str | None = None,
    track: str | None = None,
    source: StreamingSource | None = None,
    create_dirs: bool = True,
) -> Path:
    """Create a structured download path."""
    path = Path(base_path)

    # Add source subdirectory if specified
    if source:
        path = path / source.value.capitalize()

    # Add artist directory
    safe_artist = sanitize_filename(artist)
    path = path / safe_artist

    # Add album directory if specified
    if album:
        safe_album = sanitize_filename(album)
        path = path / safe_album

    # Create directories if requested
    if create_dirs:
        path.mkdir(parents=True, exist_ok=True)

    # Add track filename if specified
    if track:
        safe_track = sanitize_filename(track)
        path = path / safe_track

    return path


def extract_year_from_date(date_str: str | None) -> int | None:
    """Extract year from date string (YYYY-MM-DD format)."""
    if not date_str:
        return None

    try:
        return int(date_str.split("-")[0])
    except (ValueError, IndexError):
        return None


def normalize_genre(genre: str) -> str:
    """Normalize genre string for consistency."""
    # Convert to title case and remove extra spaces
    normalized = " ".join(word.capitalize() for word in genre.strip().split())

    # Handle common variations
    replacements = {
        "Rnb": "R&B",
        "Hiphop": "Hip-Hop",
        "Hip Hop": "Hip-Hop",
        "Edm": "EDM",
        "Dnb": "Drum & Bass",
        "Drum And Bass": "Drum & Bass",
    }

    return replacements.get(normalized, normalized)


def merge_artist_names(artists: list[str], separator: str = ", ") -> str:
    """Merge multiple artist names with proper formatting."""
    if not artists:
        return "Unknown Artist"

    # Remove duplicates while preserving order
    unique_artists = []
    seen = set()
    for artist in artists:
        if artist.lower() not in seen:
            unique_artists.append(artist)
            seen.add(artist.lower())

    if len(unique_artists) == 1:
        return unique_artists[0]
    if len(unique_artists) == 2:
        return f"{unique_artists[0]} & {unique_artists[1]}"
    return separator.join(unique_artists)


def calculate_album_stats(tracks: list[Track]) -> dict[str, Any]:
    """Calculate statistics for an album from its tracks."""
    if not tracks:
        return {
            "total_duration": 0,
            "total_tracks": 0,
            "total_discs": 1,
            "average_quality": AudioQuality.LOW,
            "genres": [],
            "is_explicit": False,
        }

    total_duration = sum(track.audio.duration_seconds or 0 for track in tracks)

    total_discs = max(track.info.disc_number for track in tracks)

    # Calculate average quality
    qualities = [track.audio.quality for track in tracks]
    # Handle both enum and integer values
    quality_values = []
    for q in qualities:
        if isinstance(q, AudioQuality):
            quality_values.append(q.value)
        else:
            quality_values.append(int(q))

    avg_quality_value = sum(quality_values) / len(quality_values)
    # Round to nearest valid enum value and clamp to valid range
    rounded_quality = max(0, min(3, round(avg_quality_value)))
    avg_quality = AudioQuality(rounded_quality)

    # Collect all genres
    all_genres = []
    for track in tracks:
        all_genres.extend(track.genres)

    # Get unique genres, normalized and sorted
    unique_genres = sorted({normalize_genre(genre) for genre in all_genres})

    # Check if any track is explicit
    is_explicit = any(track.audio.is_explicit for track in tracks)

    return {
        "total_duration": total_duration,
        "total_tracks": len(tracks),
        "total_discs": total_discs,
        "average_quality": avg_quality,
        "genres": unique_genres,
        "is_explicit": is_explicit,
    }


def calculate_playlist_stats(tracks: list[Track]) -> dict[str, Any]:
    """Calculate statistics for a playlist from its tracks."""
    if not tracks:
        return {
            "total_duration": 0,
            "total_tracks": 0,
            "unique_artists": [],
            "unique_albums": [],
            "genres": [],
            "average_quality": AudioQuality.LOW,
        }

    total_duration = sum(track.audio.duration_seconds or 0 for track in tracks)

    # Collect unique artists and albums
    unique_artists = sorted({track.credits.artist for track in tracks})
    unique_albums = sorted({track.album_id for track in tracks if track.album_id})

    # Collect all genres
    all_genres = []
    for track in tracks:
        all_genres.extend(track.genres)

    unique_genres = sorted({normalize_genre(genre) for genre in all_genres})

    # Calculate average quality
    qualities = [track.audio.quality for track in tracks]
    # Handle both enum and integer values
    quality_values = []
    for q in qualities:
        if isinstance(q, AudioQuality):
            quality_values.append(q.value)
        else:
            quality_values.append(int(q))

    avg_quality_value = sum(quality_values) / len(quality_values)
    # Round to nearest valid enum value and clamp to valid range
    rounded_quality = max(0, min(3, round(avg_quality_value)))
    avg_quality = AudioQuality(rounded_quality)

    return {
        "total_duration": total_duration,
        "total_tracks": len(tracks),
        "unique_artists": unique_artists,
        "unique_albums": unique_albums,
        "genres": unique_genres,
        "average_quality": avg_quality,
    }


def search_models(
    models: list[Artist | Album | Track | Playlist],
    query: str,
    limit: int | None = None,
) -> list[Artist | Album | Track | Playlist]:
    """Search through a list of models using their search methods."""
    if not query.strip():
        return models[:limit] if limit else models

    # Filter models that match the search query
    matching_models = [
        model
        for model in models
        if hasattr(model, "matches_search") and model.matches_search(query)
    ]

    # Sort by relevance (placeholder - could be enhanced with scoring)
    # For now, just return the matches
    return matching_models[:limit] if limit else matching_models


def group_tracks_by_album(tracks: list[Track]) -> dict[str | None, list[Track]]:
    """Group tracks by their album ID."""
    albums: dict[str | None, list[Track]] = {}

    for track in tracks:
        album_id = track.album_id
        if album_id not in albums:
            albums[album_id] = []
        albums[album_id].append(track)

    # Sort tracks within each album by disc and track number
    for album_tracks in albums.values():
        album_tracks.sort(key=lambda t: (t.info.disc_number, t.info.track_number))

    return albums


def group_albums_by_artist(albums: list[Album]) -> dict[str, list[Album]]:
    """Group albums by their primary artist."""
    artists: dict[str, list[Album]] = {}

    for album in albums:
        artist_name = album.credits.display_artist
        if artist_name not in artists:
            artists[artist_name] = []
        artists[artist_name].append(album)

    # Sort albums within each artist by release year
    for artist_albums in artists.values():
        artist_albums.sort(key=lambda a: a.info.release_year or 0)

    return artists


def validate_model_relationships(
    artists: list[Artist], albums: list[Album], tracks: list[Track]
) -> dict[str, list[str]]:
    """Validate relationships between models and return any issues."""
    issues = []

    # Create lookup sets for efficient checking
    artist_ids = {artist.info.id for artist in artists}
    album_ids = {album.info.id for album in albums}
    track_ids = {track.info.id for track in tracks}

    # Check artist -> album relationships
    for artist in artists:
        issues.extend(
            f"Artist {artist.info.id} references missing album {album_id}"
            for album_id in artist.album_ids
            if album_id not in album_ids
        )

    # Check album -> track relationships
    for album in albums:
        issues.extend(
            f"Album {album.info.id} references missing track {track_id}"
            for track_id in album.track_ids
            if track_id not in track_ids
        )

    # Check track -> album relationships
    for track in tracks:
        if track.album_id and track.album_id not in album_ids:
            issues.append(
                f"Track {track.info.id} references missing album {track.album_id}"
            )

        issues.extend(
            f"Track {track.info.id} references missing artist {artist_id}"
            for artist_id in track.artist_ids
            if artist_id not in artist_ids
        )

    return {"relationship_issues": issues}
