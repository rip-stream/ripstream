# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Factory classes for creating models from streaming source data."""

import contextlib
from typing import Any, Protocol

from ripstream.models.album import Album
from ripstream.models.artist import Artist
from ripstream.models.enums import StreamingSource
from ripstream.models.playlist import Playlist
from ripstream.models.track import Track


class FactoryProtocol(Protocol):
    """Protocol defining the interface for factory classes."""

    @staticmethod
    def create_artist(artist_id: str, data: dict[str, Any], **kwargs: object) -> Artist:
        """Create an Artist model from source data."""
        ...

    @staticmethod
    def create_album(album_id: str, data: dict[str, Any], **kwargs: object) -> Album:
        """Create an Album model from source data."""
        ...

    @staticmethod
    def create_track(
        track_id: str,
        data: dict[str, Any],
        album_data: dict[str, Any] | None = None,
        **kwargs: object,
    ) -> Track:
        """Create a Track model from source data."""
        ...

    @staticmethod
    def create_playlist(
        playlist_id: str, data: dict[str, Any], **kwargs: object
    ) -> Playlist:
        """Create a Playlist model from source data."""
        ...


class ModelFactory:
    """Factory class for creating models from source data."""

    @staticmethod
    def create_artist(
        source: StreamingSource, artist_id: str, data: dict[str, Any], **kwargs: object
    ) -> Artist:
        """Create an Artist model from source data."""
        return Artist.from_source_data(source, artist_id, data, **kwargs)

    @staticmethod
    def create_album(
        source: StreamingSource, album_id: str, data: dict[str, Any], **kwargs: object
    ) -> Album:
        """Create an Album model from source data."""
        return Album.from_source_data(source, album_id, data, **kwargs)

    @staticmethod
    def create_track(
        source: StreamingSource,
        track_id: str,
        data: dict[str, Any],
        album_data: dict[str, Any] | None = None,
        **kwargs: object,
    ) -> Track:
        """Create a Track model from source data."""
        return Track.from_source_data(source, track_id, data, album_data, **kwargs)

    @staticmethod
    def create_playlist(
        source: StreamingSource,
        playlist_id: str,
        data: dict[str, Any],
        **kwargs: object,
    ) -> Playlist:
        """Create a Playlist model from source data."""
        return Playlist.from_source_data(source, playlist_id, data, **kwargs)


class QobuzModelFactory:
    """Factory for creating models from Qobuz API data."""

    @staticmethod
    def create_artist(artist_id: str, data: dict[str, Any], **kwargs: object) -> Artist:
        """Create an Artist from Qobuz data."""
        # Transform Qobuz-specific data structure
        transformed_data = {
            "name": data.get("name", "Unknown Artist"),
            "biography": data.get("biography", {}).get("content")
            if isinstance(data.get("biography"), dict)
            else None,
            "genres": [
                genre.get("name")
                for genre in (
                    data.get("genres", {}).get("items", [])
                    if isinstance(data.get("genres"), dict)
                    else []
                )
                if isinstance(genre, dict)
            ],
            "formed_year": data.get("information", {}).get("formed")
            if isinstance(data.get("information"), dict)
            else None,
            "country": data.get("information", {}).get("country")
            if isinstance(data.get("information"), dict)
            else None,
            "website": data.get("information", {}).get("website")
            if isinstance(data.get("information"), dict)
            else None,
            "covers": data.get("image", {}),
            "stats": {
                "total_albums": data.get("albums_count", 0),
            },
        }
        return ModelFactory.create_artist(
            StreamingSource.QOBUZ, artist_id, transformed_data, **kwargs
        )

    @staticmethod
    def create_album(album_id: str, data: dict[str, Any], **kwargs: object) -> Album:
        """Create an Album from Qobuz data."""
        release_date = data.get("release_date_original", "")
        release_year = None
        if release_date and isinstance(release_date, str):
            with contextlib.suppress(ValueError, IndexError):
                release_year = int(release_date.split("-")[0])

        transformed_data = {
            "title": data.get("title", "Unknown Album"),
            "artist": data.get("artist", {}).get("name", "Unknown Artist")
            if isinstance(data.get("artist"), dict)
            else "Unknown Artist",
            "release_date": release_date,
            "release_year": release_year,
            "label": data.get("label", {}).get("name")
            if isinstance(data.get("label"), dict)
            else None,
            "catalog_number": data.get("label", {}).get("catalog_number")
            if isinstance(data.get("label"), dict)
            else None,
            "total_tracks": data.get("tracks_count", 0),
            "total_duration": data.get("duration"),
            "genres": [
                genre.get("name")
                for genre in data.get("genres", {}).get("items", [])
                if isinstance(genre, dict)
            ],
            "covers": data.get("image", {}),
            "popularity": data.get("popularity"),
        }
        return ModelFactory.create_album(
            StreamingSource.QOBUZ, album_id, transformed_data, **kwargs
        )

    @staticmethod
    def create_track(
        track_id: str,
        data: dict[str, Any],
        album_data: dict[str, Any] | None = None,
        **kwargs: object,
    ) -> Track:
        """Create a Track from Qobuz data."""
        transformed_data = {
            "title": data.get("title", "Unknown Track"),
            "artist": data.get("performer", {}).get("name", "Unknown Artist")
            if isinstance(data.get("performer"), dict)
            else "Unknown Artist",
            "composer": data.get("composer", {}).get("name")
            if isinstance(data.get("composer"), dict)
            else None,
            "track_number": data.get("track_number", 1),
            "disc_number": data.get("media_number", 1),
            "duration": data.get("duration"),
            "isrc": data.get("isrc"),
            "quality": data.get("maximum_bit_depth", 16),
            "bit_depth": data.get("maximum_bit_depth"),
            "sampling_rate": data.get("maximum_sampling_rate"),
            "is_explicit": data.get("parental_warning", False),
            "work": data.get("work"),
            "version": data.get("version"),
        }
        return ModelFactory.create_track(
            StreamingSource.QOBUZ, track_id, transformed_data, album_data, **kwargs
        )

    @staticmethod
    def create_playlist(
        playlist_id: str, data: dict[str, Any], **kwargs: object
    ) -> Playlist:
        """Create a Playlist from Qobuz data."""
        transformed_data = {
            "title": data.get("name", "Unknown Playlist"),
            "description": data.get("description"),
            "total_tracks": data.get("tracks_count", 0),
            "total_duration": data.get("duration"),
            "is_public": data.get("public", True),
            "covers": data.get("image", {}),
        }
        return ModelFactory.create_playlist(
            StreamingSource.QOBUZ, playlist_id, transformed_data, **kwargs
        )


class TidalModelFactory:
    """Factory for creating models from Tidal API data."""

    @staticmethod
    def create_artist(artist_id: str, data: dict[str, Any], **kwargs: object) -> Artist:
        """Create an Artist from Tidal data."""
        transformed_data = {
            "name": data.get("name", "Unknown Artist"),
            "biography": data.get("bio"),
            "covers": data.get("picture"),
            "stats": {
                "popularity_score": data.get("popularity"),
            },
        }
        return ModelFactory.create_artist(
            StreamingSource.TIDAL, artist_id, transformed_data, **kwargs
        )

    @staticmethod
    def create_album(album_id: str, data: dict[str, Any], **kwargs: object) -> Album:
        """Create an Album from Tidal data."""
        transformed_data = {
            "title": data.get("title", "Unknown Album"),
            "artist": data.get("artist", {}).get("name", "Unknown Artist")
            if isinstance(data.get("artist"), dict)
            else "Unknown Artist",
            "release_date": data.get("releaseDate"),
            "total_tracks": data.get("numberOfTracks", 0),
            "total_duration": data.get("duration"),
            "is_explicit": data.get("explicit", False),
            "covers": data.get("cover"),
            "popularity": data.get("popularity"),
        }
        return ModelFactory.create_album(
            StreamingSource.TIDAL, album_id, transformed_data, **kwargs
        )

    @staticmethod
    def create_track(
        track_id: str,
        data: dict[str, Any],
        album_data: dict[str, Any] | None = None,
        **kwargs: object,
    ) -> Track:
        """Create a Track from Tidal data."""
        # Map Tidal quality to our enum
        quality_map = {
            "LOW": 0,
            "HIGH": 1,
            "LOSSLESS": 2,
            "HI_RES": 3,
        }

        audio_quality = data.get("audioQuality")
        quality = quality_map.get(audio_quality, 0) if audio_quality else 0

        artists_list = data.get("artists", [])
        artist_names = []
        if isinstance(artists_list, list):
            artist_names.extend(
                artist["name"]
                for artist in artists_list
                if isinstance(artist, dict) and "name" in artist
            )

        transformed_data = {
            "title": data.get("title", "Unknown Track"),
            "artist": ", ".join(artist_names) if artist_names else "Unknown Artist",
            "track_number": data.get("trackNumber", 1),
            "disc_number": data.get("volumeNumber", 1),
            "duration": data.get("duration"),
            "isrc": data.get("isrc"),
            "quality": quality,
            "is_explicit": data.get("explicit", False),
            "version": data.get("version"),
            "lyrics": data.get("lyrics"),
        }
        return ModelFactory.create_track(
            StreamingSource.TIDAL, track_id, transformed_data, album_data, **kwargs
        )

    @staticmethod
    def create_playlist(
        playlist_id: str, data: dict[str, Any], **kwargs: object
    ) -> Playlist:
        """Create a Playlist from Tidal data."""
        transformed_data = {
            "title": data.get("title", "Unknown Playlist"),
            "description": data.get("description"),
            "total_tracks": data.get("numberOfTracks", 0),
            "total_duration": data.get("duration"),
            "is_public": data.get("publicPlaylist", True),
            "covers": data.get("image"),
        }
        return ModelFactory.create_playlist(
            StreamingSource.TIDAL, playlist_id, transformed_data, **kwargs
        )


class DeezerModelFactory:
    """Factory for creating models from Deezer API data."""

    @staticmethod
    def create_artist(artist_id: str, data: dict[str, Any], **kwargs: object) -> Artist:
        """Create an Artist from Deezer data."""
        transformed_data = {
            "name": data.get("name", "Unknown Artist"),
            "covers": {"url": data.get("picture_xl")},
            "stats": {
                "total_albums": data.get("nb_album", 0),
                "followers": data.get("nb_fan"),
            },
        }
        return ModelFactory.create_artist(
            StreamingSource.DEEZER, artist_id, transformed_data, **kwargs
        )

    @staticmethod
    def create_album(album_id: str, data: dict[str, Any], **kwargs: object) -> Album:
        """Create an Album from Deezer data."""
        genres_data = data.get("genres", {})
        genres = []
        if isinstance(genres_data, dict) and "data" in genres_data:
            genres = [
                genre.get("name")
                for genre in genres_data["data"]
                if isinstance(genre, dict)
            ]

        transformed_data = {
            "title": data.get("title", "Unknown Album"),
            "artist": data.get("artist", {}).get("name", "Unknown Artist")
            if isinstance(data.get("artist"), dict)
            else "Unknown Artist",
            "release_date": data.get("release_date"),
            "total_tracks": data.get("nb_tracks", 0),
            "total_duration": data.get("duration"),
            "is_explicit": data.get("explicit_lyrics", False),
            "covers": {"url": data.get("cover_xl")},
            "genres": genres,
        }
        return ModelFactory.create_album(
            StreamingSource.DEEZER, album_id, transformed_data, **kwargs
        )

    @staticmethod
    def create_track(
        track_id: str,
        data: dict[str, Any],
        album_data: dict[str, Any] | None = None,
        **kwargs: object,
    ) -> Track:
        """Create a Track from Deezer data."""
        transformed_data = {
            "title": data.get("title", "Unknown Track"),
            "artist": data.get("artist", {}).get("name", "Unknown Artist")
            if isinstance(data.get("artist"), dict)
            else "Unknown Artist",
            "track_number": data.get("track_position", 1),
            "disc_number": data.get("disk_number", 1),
            "duration": data.get("duration"),
            "isrc": data.get("isrc"),
            "quality": 1,  # Deezer is typically 320kbps
            "bit_depth": 16,
            "sampling_rate": 44100,
            "is_explicit": data.get("explicit_lyrics", False),
        }
        return ModelFactory.create_track(
            StreamingSource.DEEZER, track_id, transformed_data, album_data, **kwargs
        )

    @staticmethod
    def create_playlist(
        playlist_id: str, data: dict[str, Any], **kwargs: object
    ) -> Playlist:
        """Create a Playlist from Deezer data."""
        transformed_data = {
            "title": data.get("title", "Unknown Playlist"),
            "description": data.get("description"),
            "total_tracks": data.get("nb_tracks", 0),
            "total_duration": data.get("duration"),
            "is_public": data.get("public", True),
            "covers": {"url": data.get("picture_xl")},
        }
        return ModelFactory.create_playlist(
            StreamingSource.DEEZER, playlist_id, transformed_data, **kwargs
        )


class SoundCloudModelFactory:
    """Factory for creating models from SoundCloud API data."""

    @staticmethod
    def create_artist(artist_id: str, data: dict[str, Any], **kwargs: object) -> Artist:
        """Create an Artist from SoundCloud data."""
        transformed_data = {
            "name": data.get("username", "Unknown Artist"),
            "biography": data.get("description"),
            "website": data.get("website"),
            "covers": {"url": data.get("avatar_url")},
            "stats": {
                "followers": data.get("followers_count"),
                "total_tracks": data.get("track_count"),
            },
        }
        return ModelFactory.create_artist(
            StreamingSource.SOUNDCLOUD, artist_id, transformed_data, **kwargs
        )

    @staticmethod
    def create_track(
        track_id: str,
        data: dict[str, Any],
        album_data: dict[str, Any] | None = None,
        **kwargs: object,
    ) -> Track:
        """Create a Track from SoundCloud data."""
        duration_ms = data.get("duration", 0)
        duration_seconds = (
            duration_ms / 1000 if isinstance(duration_ms, (int, float)) else 0
        )

        user_data = data.get("user", {})
        artist_name = (
            user_data.get("username", "Unknown Artist")
            if isinstance(user_data, dict)
            else "Unknown Artist"
        )

        publisher_metadata = data.get("publisher_metadata", {})
        is_explicit = False
        if isinstance(publisher_metadata, dict):
            is_explicit = publisher_metadata.get("explicit", False)

        genre = data.get("genre")
        genres = [genre] if genre else []

        transformed_data = {
            "title": data.get("title", "Unknown Track"),
            "artist": artist_name,
            "duration": duration_seconds,
            "quality": 0,  # SoundCloud is typically lower quality
            "is_explicit": is_explicit,
            "genres": genres,
            "covers": {"url": data.get("artwork_url")},
        }
        return ModelFactory.create_track(
            StreamingSource.SOUNDCLOUD, track_id, transformed_data, album_data, **kwargs
        )

    @staticmethod
    def create_playlist(
        playlist_id: str, data: dict[str, Any], **kwargs: object
    ) -> Playlist:
        """Create a Playlist from SoundCloud data."""
        transformed_data = {
            "title": data.get("title", "Unknown Playlist"),
            "description": data.get("description"),
            "total_tracks": data.get("track_count", 0),
            "total_duration": data.get("duration"),
            "is_public": data.get("sharing") == "public"
            if data.get("sharing")
            else True,
            "covers": {"url": data.get("artwork_url")},
        }
        return ModelFactory.create_playlist(
            StreamingSource.SOUNDCLOUD, playlist_id, transformed_data, **kwargs
        )


# Type alias for factory classes
FactoryType = (
    type[QobuzModelFactory]
    | type[TidalModelFactory]
    | type[DeezerModelFactory]
    | type[SoundCloudModelFactory]
    | type[ModelFactory]
)


def get_factory_for_source(source: StreamingSource) -> FactoryType:
    """Get the appropriate factory class for a streaming source."""
    factories = {
        StreamingSource.QOBUZ: QobuzModelFactory,
        StreamingSource.TIDAL: TidalModelFactory,
        StreamingSource.DEEZER: DeezerModelFactory,
        StreamingSource.SOUNDCLOUD: SoundCloudModelFactory,
    }
    return factories.get(source, ModelFactory)
