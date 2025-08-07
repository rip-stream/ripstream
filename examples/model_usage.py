#!/usr/bin/env python3
# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.
"""
Example usage of RipStream models.

This example demonstrates how to create and use the various music models
including Artists, Albums, Tracks, and Playlists.
"""

import sys
from pathlib import Path

# Add the src directory to the path so we can import ripstream
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ripstream.models import (
    Album,
    Artist,
    AudioQuality,
    Playlist,
    StreamingSource,
    Track,
    create_album_from_source,
    create_artist_from_source,
    create_track_from_source,
)


def create_sample_artist() -> Artist:
    """Create a sample artist using the factory."""
    sample_data = {
        "name": "The Beatles",
        "country": "United Kingdom",
        "formed_year": 1960,
        "genres": ["Rock", "Pop", "Psychedelic Rock"],
        "biography": "The Beatles were an English rock band formed in Liverpool in 1960.",
        "stats": {
            "total_albums": 13,
            "popularity_score": 95.5,
        },
    }

    return create_artist_from_source(StreamingSource.QOBUZ, "artist_123", sample_data)


def create_sample_album(artist: Artist) -> Album:
    """Create a sample album."""
    sample_data = {
        "title": "Abbey Road",
        "artist": artist.name,
        "release_date": "1969-09-26",
        "release_year": 1969,
        "album_type": "album",
        "label": "Apple Records",
        "total_tracks": 17,
        "total_duration": 2841,  # 47 minutes 21 seconds
        "genres": ["Rock", "Pop"],
        "popularity": 92.3,
    }

    album = create_album_from_source(StreamingSource.QOBUZ, "album_456", sample_data)

    # Add relationship
    artist.add_album_id(album.info.id)

    return album


def create_sample_track(album: Album, artist: Artist) -> Track:
    """Create a sample track."""
    sample_data = {
        "title": "Come Together",
        "artist": artist.name,
        "album_artist": artist.name,
        "track_number": 1,
        "disc_number": 1,
        "duration": 259,  # 4:19
        "quality": AudioQuality.HI_RES,
        "bit_depth": 24,
        "sampling_rate": 96000,
        "isrc": "GBUM71505078",
        "genres": ["Rock"],
    }

    track = create_track_from_source(
        StreamingSource.QOBUZ,
        "track_789",
        sample_data,
        album_data={"artist": album.artist, "title": album.title},
    )

    # Add relationships
    track.album_id = album.info.id
    track.add_artist_id(artist.info.id)
    album.add_track_id(track.info.id)

    return track


def create_sample_playlist() -> Playlist:
    """Create a sample playlist."""
    from ripstream.models.playlist import Playlist, PlaylistInfo, PlaylistStats

    # Create playlist info
    info = PlaylistInfo(
        id="playlist_001",
        source=StreamingSource.QOBUZ,
        name="My Favorite Rock Songs",
        description="A collection of classic rock tracks",
        owner="music_lover",
        is_public=True,
        total_tracks=0,
        tags=["rock", "classics", "favorites"],
    )

    # Create playlist
    return Playlist(info=info, stats=PlaylistStats(), tracks=[])


def demonstrate_model_features() -> None:
    """Demonstrate various model features."""
    # Create sample data
    artist = create_sample_artist()

    album = create_sample_album(artist)

    track = create_sample_track(album, artist)

    playlist = create_sample_playlist()
    playlist.add_track(track.info.id, added_by=playlist.info.owner)

    artist.to_dict()

    album.to_dict()

    track.to_dict()

    track.mark_downloading()
    track.mark_completed("/path/to/downloaded/file.flac")


if __name__ == "__main__":
    try:
        demonstrate_model_features()
    except ImportError:
        pass
    except Exception:
        import traceback

        traceback.print_exc()
