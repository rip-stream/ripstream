# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Unit tests for models/factories.py module."""

from unittest.mock import Mock, patch

import pytest

from ripstream.models.album import Album
from ripstream.models.artist import Artist
from ripstream.models.enums import StreamingSource
from ripstream.models.factories import (
    DeezerModelFactory,
    ModelFactory,
    QobuzModelFactory,
    SoundCloudModelFactory,
    TidalModelFactory,
    get_factory_for_source,
)
from ripstream.models.playlist import Playlist
from ripstream.models.track import Track


class TestModelFactory:
    """Test the base ModelFactory class."""

    @pytest.fixture
    def sample_data(self):
        """Sample data for testing."""
        return {"name": "Test Item", "description": "Test description", "id": "test_id"}

    def test_create_artist(self, sample_data):
        """Test ModelFactory.create_artist method."""
        with patch.object(Artist, "from_source_data") as mock_from_source:
            mock_artist = Mock(spec=Artist)
            mock_from_source.return_value = mock_artist

            result = ModelFactory.create_artist(
                StreamingSource.QOBUZ, "test_id", sample_data, extra_param="test"
            )

            mock_from_source.assert_called_once_with(
                StreamingSource.QOBUZ, "test_id", sample_data, extra_param="test"
            )
            assert result == mock_artist

    def test_create_album(self, sample_data):
        """Test ModelFactory.create_album method."""
        with patch.object(Album, "from_source_data") as mock_from_source:
            mock_album = Mock(spec=Album)
            mock_from_source.return_value = mock_album

            result = ModelFactory.create_album(
                StreamingSource.TIDAL, "test_id", sample_data, extra_param="test"
            )

            mock_from_source.assert_called_once_with(
                StreamingSource.TIDAL, "test_id", sample_data, extra_param="test"
            )
            assert result == mock_album

    def test_create_track(self, sample_data):
        """Test ModelFactory.create_track method."""
        with patch.object(Track, "from_source_data") as mock_from_source:
            mock_track = Mock(spec=Track)
            mock_from_source.return_value = mock_track

            album_data = {"title": "Test Album"}
            result = ModelFactory.create_track(
                StreamingSource.DEEZER,
                "test_id",
                sample_data,
                album_data,
                extra_param="test",
            )

            mock_from_source.assert_called_once_with(
                StreamingSource.DEEZER,
                "test_id",
                sample_data,
                album_data,
                extra_param="test",
            )
            assert result == mock_track

    def test_create_playlist(self, sample_data):
        """Test ModelFactory.create_playlist method."""
        with patch.object(Playlist, "from_source_data") as mock_from_source:
            mock_playlist = Mock(spec=Playlist)
            mock_from_source.return_value = mock_playlist

            result = ModelFactory.create_playlist(
                StreamingSource.SOUNDCLOUD, "test_id", sample_data, extra_param="test"
            )

            mock_from_source.assert_called_once_with(
                StreamingSource.SOUNDCLOUD, "test_id", sample_data, extra_param="test"
            )
            assert result == mock_playlist


class TestQobuzModelFactory:
    """Test the QobuzModelFactory class."""

    @pytest.fixture
    def qobuz_artist_data(self):
        """Sample Qobuz artist data."""
        return {
            "name": "Test Artist",
            "biography": {"content": "Artist biography"},
            "genres": {"items": [{"name": "Rock"}, {"name": "Pop"}]},
            "information": {
                "formed": 2000,
                "country": "US",
                "website": "https://example.com",
            },
            "image": {"large": "https://example.com/large.jpg"},
            "albums_count": 5,
        }

    @pytest.fixture
    def qobuz_album_data(self):
        """Sample Qobuz album data."""
        return {
            "title": "Test Album",
            "artist": {"name": "Test Artist"},
            "release_date_original": "2023-01-15",
            "label": {"name": "Test Label", "catalog_number": "TL001"},
            "tracks_count": 12,
            "duration": 3600,
            "genres": {"items": [{"name": "Rock"}]},
            "image": {"large": "https://example.com/album.jpg"},
            "popularity": 85,
        }

    @pytest.fixture
    def qobuz_track_data(self):
        """Sample Qobuz track data."""
        return {
            "title": "Test Track",
            "performer": {"name": "Test Artist"},
            "composer": {"name": "Test Composer"},
            "track_number": 3,
            "media_number": 1,
            "duration": 240,
            "isrc": "USRC17607839",
            "maximum_bit_depth": 24,
            "maximum_sampling_rate": 96000,
            "parental_warning": True,
            "work": "Test Work",
            "version": "Remastered",
        }

    @pytest.fixture
    def qobuz_playlist_data(self):
        """Sample Qobuz playlist data."""
        return {
            "name": "Test Playlist",
            "description": "Test playlist description",
            "tracks_count": 25,
            "duration": 5400,
            "public": False,
            "image": {"large": "https://example.com/playlist.jpg"},
        }

    def test_create_artist_full_data(self, qobuz_artist_data):
        """Test QobuzModelFactory.create_artist with full data."""
        with patch.object(ModelFactory, "create_artist") as mock_create:
            mock_artist = Mock(spec=Artist)
            mock_create.return_value = mock_artist

            result = QobuzModelFactory.create_artist("test_id", qobuz_artist_data)

            # Verify the transformed data structure
            call_args = mock_create.call_args
            assert call_args[0][0] == StreamingSource.QOBUZ
            assert call_args[0][1] == "test_id"

            transformed_data = call_args[0][2]
            assert transformed_data["name"] == "Test Artist"
            assert transformed_data["biography"] == "Artist biography"
            assert transformed_data["genres"] == ["Rock", "Pop"]
            assert transformed_data["formed_year"] == 2000
            assert transformed_data["country"] == "US"
            assert transformed_data["website"] == "https://example.com"
            assert transformed_data["stats"]["total_albums"] == 5

            assert result == mock_artist

    def test_create_artist_minimal_data(self):
        """Test QobuzModelFactory.create_artist with minimal data."""
        minimal_data = {"name": "Minimal Artist"}

        with patch.object(ModelFactory, "create_artist") as mock_create:
            mock_artist = Mock(spec=Artist)
            mock_create.return_value = mock_artist

            QobuzModelFactory.create_artist("test_id", minimal_data)

            call_args = mock_create.call_args
            transformed_data = call_args[0][2]
            assert transformed_data["name"] == "Minimal Artist"
            assert transformed_data["biography"] is None
            assert transformed_data["genres"] == []
            assert transformed_data["stats"]["total_albums"] == 0

    def test_create_artist_invalid_nested_data(self):
        """Test QobuzModelFactory.create_artist handles invalid nested data gracefully."""
        invalid_data = {
            "name": "Test Artist",
            "biography": "not_a_dict",  # Should be dict
            "genres": "not_a_dict",  # Should be dict with items
            "information": "not_a_dict",  # Should be dict
        }

        with patch.object(ModelFactory, "create_artist") as mock_create:
            mock_artist = Mock(spec=Artist)
            mock_create.return_value = mock_artist

            # This should not raise an exception, but handle gracefully
            QobuzModelFactory.create_artist("test_id", invalid_data)

            call_args = mock_create.call_args
            transformed_data = call_args[0][2]
            assert transformed_data["biography"] is None
            assert (
                transformed_data["genres"] == []
            )  # Should be empty when genres is not a dict
            assert transformed_data["formed_year"] is None

    def test_create_album_full_data(self, qobuz_album_data):
        """Test QobuzModelFactory.create_album with full data."""
        with patch.object(ModelFactory, "create_album") as mock_create:
            mock_album = Mock(spec=Album)
            mock_create.return_value = mock_album

            QobuzModelFactory.create_album("test_id", qobuz_album_data)

            call_args = mock_create.call_args
            transformed_data = call_args[0][2]
            assert transformed_data["title"] == "Test Album"
            assert transformed_data["artist"] == "Test Artist"
            assert transformed_data["release_date"] == "2023-01-15"
            assert transformed_data["release_year"] == 2023
            assert transformed_data["label"] == "Test Label"
            assert transformed_data["catalog_number"] == "TL001"
            assert transformed_data["total_tracks"] == 12
            assert transformed_data["genres"] == ["Rock"]

    def test_create_album_invalid_release_date(self):
        """Test QobuzModelFactory.create_album handles invalid release date."""
        data = {"title": "Test Album", "release_date_original": "invalid-date"}

        with patch.object(ModelFactory, "create_album") as mock_create:
            mock_album = Mock(spec=Album)
            mock_create.return_value = mock_album

            QobuzModelFactory.create_album("test_id", data)

            call_args = mock_create.call_args
            transformed_data = call_args[0][2]
            assert transformed_data["release_year"] is None

    def test_create_track_full_data(self, qobuz_track_data):
        """Test QobuzModelFactory.create_track with full data."""
        with patch.object(ModelFactory, "create_track") as mock_create:
            mock_track = Mock(spec=Track)
            mock_create.return_value = mock_track

            album_data = {"title": "Test Album"}
            QobuzModelFactory.create_track("test_id", qobuz_track_data, album_data)

            call_args = mock_create.call_args
            transformed_data = call_args[0][2]
            assert transformed_data["title"] == "Test Track"
            assert transformed_data["artist"] == "Test Artist"
            assert transformed_data["composer"] == "Test Composer"
            assert transformed_data["track_number"] == 3
            assert transformed_data["disc_number"] == 1
            assert transformed_data["duration"] == 240
            assert transformed_data["bit_depth"] == 24
            assert transformed_data["sampling_rate"] == 96000
            assert transformed_data["is_explicit"] is True

    def test_create_playlist_full_data(self, qobuz_playlist_data):
        """Test QobuzModelFactory.create_playlist with full data."""
        with patch.object(ModelFactory, "create_playlist") as mock_create:
            mock_playlist = Mock(spec=Playlist)
            mock_create.return_value = mock_playlist

            QobuzModelFactory.create_playlist("test_id", qobuz_playlist_data)

            call_args = mock_create.call_args
            transformed_data = call_args[0][2]
            assert transformed_data["title"] == "Test Playlist"
            assert transformed_data["description"] == "Test playlist description"
            assert transformed_data["total_tracks"] == 25
            assert transformed_data["is_public"] is False


class TestTidalModelFactory:
    """Test the TidalModelFactory class."""

    @pytest.fixture
    def tidal_artist_data(self):
        """Sample Tidal artist data."""
        return {
            "name": "Tidal Artist",
            "bio": "Artist biography",
            "picture": "https://example.com/artist.jpg",
            "popularity": 75,
        }

    @pytest.fixture
    def tidal_track_data(self):
        """Sample Tidal track data."""
        return {
            "title": "Tidal Track",
            "artists": [{"name": "Artist 1"}, {"name": "Artist 2"}],
            "trackNumber": 5,
            "volumeNumber": 2,
            "duration": 300,
            "isrc": "USTD12345678",
            "audioQuality": "HI_RES",
            "explicit": True,
            "version": "Deluxe Edition",
            "lyrics": "Song lyrics here",
        }

    def test_create_artist(self, tidal_artist_data):
        """Test TidalModelFactory.create_artist."""
        with patch.object(ModelFactory, "create_artist") as mock_create:
            mock_artist = Mock(spec=Artist)
            mock_create.return_value = mock_artist

            TidalModelFactory.create_artist("test_id", tidal_artist_data)

            call_args = mock_create.call_args
            transformed_data = call_args[0][2]
            assert transformed_data["name"] == "Tidal Artist"
            assert transformed_data["biography"] == "Artist biography"
            assert transformed_data["stats"]["popularity_score"] == 75

    def test_create_track_with_quality_mapping(self, tidal_track_data):
        """Test TidalModelFactory.create_track with quality mapping."""
        with patch.object(ModelFactory, "create_track") as mock_create:
            mock_track = Mock(spec=Track)
            mock_create.return_value = mock_track

            TidalModelFactory.create_track("test_id", tidal_track_data)

            call_args = mock_create.call_args
            transformed_data = call_args[0][2]
            assert transformed_data["title"] == "Tidal Track"
            assert transformed_data["artist"] == "Artist 1, Artist 2"
            assert transformed_data["quality"] == 3  # HI_RES maps to 3
            assert transformed_data["track_number"] == 5
            assert transformed_data["disc_number"] == 2

    @pytest.mark.parametrize(
        ("audio_quality", "expected_quality"),
        [
            ("LOW", 0),
            ("HIGH", 1),
            ("LOSSLESS", 2),
            ("HI_RES", 3),
            ("UNKNOWN", 0),
            (None, 0),
        ],
    )
    def test_create_track_quality_mapping(self, audio_quality, expected_quality):
        """Test TidalModelFactory track quality mapping."""
        track_data = {
            "title": "Test Track",
            "audioQuality": audio_quality,
            "artists": [],
        }

        with patch.object(ModelFactory, "create_track") as mock_create:
            mock_track = Mock(spec=Track)
            mock_create.return_value = mock_track

            TidalModelFactory.create_track("test_id", track_data)

            call_args = mock_create.call_args
            transformed_data = call_args[0][2]
            assert transformed_data["quality"] == expected_quality

    def test_create_track_invalid_artists_data(self):
        """Test TidalModelFactory.create_track handles invalid artists data."""
        track_data = {
            "title": "Test Track",
            "artists": "not_a_list",  # Should be list
        }

        with patch.object(ModelFactory, "create_track") as mock_create:
            mock_track = Mock(spec=Track)
            mock_create.return_value = mock_track

            TidalModelFactory.create_track("test_id", track_data)

            call_args = mock_create.call_args
            transformed_data = call_args[0][2]
            assert transformed_data["artist"] == "Unknown Artist"


class TestDeezerModelFactory:
    """Test the DeezerModelFactory class."""

    @pytest.fixture
    def deezer_album_data(self):
        """Sample Deezer album data."""
        return {
            "title": "Deezer Album",
            "artist": {"name": "Deezer Artist"},
            "release_date": "2023-06-15",
            "nb_tracks": 15,
            "duration": 4200,
            "explicit_lyrics": True,
            "cover_xl": "https://example.com/cover.jpg",
            "genres": {"data": [{"name": "Electronic"}, {"name": "Dance"}]},
        }

    def test_create_album_with_genres(self, deezer_album_data):
        """Test DeezerModelFactory.create_album with genres."""
        with patch.object(ModelFactory, "create_album") as mock_create:
            mock_album = Mock(spec=Album)
            mock_create.return_value = mock_album

            DeezerModelFactory.create_album("test_id", deezer_album_data)

            call_args = mock_create.call_args
            transformed_data = call_args[0][2]
            assert transformed_data["genres"] == ["Electronic", "Dance"]
            assert transformed_data["is_explicit"] is True

    def test_create_album_invalid_genres_data(self):
        """Test DeezerModelFactory.create_album handles invalid genres data."""
        album_data = {
            "title": "Test Album",
            "genres": "not_a_dict",  # Should be dict
        }

        with patch.object(ModelFactory, "create_album") as mock_create:
            mock_album = Mock(spec=Album)
            mock_create.return_value = mock_album

            DeezerModelFactory.create_album("test_id", album_data)

            call_args = mock_create.call_args
            transformed_data = call_args[0][2]
            assert transformed_data["genres"] == []

    def test_create_track_with_defaults(self):
        """Test DeezerModelFactory.create_track with default values."""
        track_data = {
            "title": "Deezer Track",
            "artist": {"name": "Deezer Artist"},
            "track_position": 7,
            "disk_number": 2,
        }

        with patch.object(ModelFactory, "create_track") as mock_create:
            mock_track = Mock(spec=Track)
            mock_create.return_value = mock_track

            DeezerModelFactory.create_track("test_id", track_data)

            call_args = mock_create.call_args
            transformed_data = call_args[0][2]
            assert transformed_data["quality"] == 1  # Default for Deezer
            assert transformed_data["bit_depth"] == 16
            assert transformed_data["sampling_rate"] == 44100


class TestSoundCloudModelFactory:
    """Test the SoundCloudModelFactory class."""

    @pytest.fixture
    def soundcloud_track_data(self):
        """Sample SoundCloud track data."""
        return {
            "title": "SoundCloud Track",
            "user": {"username": "SoundCloud User"},
            "duration": 180000,  # milliseconds
            "genre": "Hip Hop",
            "artwork_url": "https://example.com/artwork.jpg",
            "publisher_metadata": {"explicit": True},
        }

    def test_create_track_duration_conversion(self, soundcloud_track_data):
        """Test SoundCloudModelFactory.create_track converts duration from ms to seconds."""
        with patch.object(ModelFactory, "create_track") as mock_create:
            mock_track = Mock(spec=Track)
            mock_create.return_value = mock_track

            SoundCloudModelFactory.create_track("test_id", soundcloud_track_data)

            call_args = mock_create.call_args
            transformed_data = call_args[0][2]
            assert transformed_data["duration"] == 180.0  # Converted from 180000ms
            assert transformed_data["genres"] == ["Hip Hop"]
            assert transformed_data["is_explicit"] is True

    def test_create_track_invalid_duration(self):
        """Test SoundCloudModelFactory.create_track handles invalid duration."""
        track_data = {"title": "Test Track", "duration": "not_a_number"}

        with patch.object(ModelFactory, "create_track") as mock_create:
            mock_track = Mock(spec=Track)
            mock_create.return_value = mock_track

            SoundCloudModelFactory.create_track("test_id", track_data)

            call_args = mock_create.call_args
            transformed_data = call_args[0][2]
            assert transformed_data["duration"] == 0

    def test_create_playlist_sharing_mapping(self):
        """Test SoundCloudModelFactory.create_playlist sharing to public mapping."""
        playlist_data = {"title": "Test Playlist", "sharing": "public"}

        with patch.object(ModelFactory, "create_playlist") as mock_create:
            mock_playlist = Mock(spec=Playlist)
            mock_create.return_value = mock_playlist

            SoundCloudModelFactory.create_playlist("test_id", playlist_data)

            call_args = mock_create.call_args
            transformed_data = call_args[0][2]
            assert transformed_data["is_public"] is True

    def test_create_playlist_no_sharing_defaults_to_public(self):
        """Test SoundCloudModelFactory.create_playlist defaults to public when no sharing."""
        playlist_data = {"title": "Test Playlist"}

        with patch.object(ModelFactory, "create_playlist") as mock_create:
            mock_playlist = Mock(spec=Playlist)
            mock_create.return_value = mock_playlist

            SoundCloudModelFactory.create_playlist("test_id", playlist_data)

            call_args = mock_create.call_args
            transformed_data = call_args[0][2]
            assert transformed_data["is_public"] is True


class TestGetFactoryForSource:
    """Test the get_factory_for_source function."""

    @pytest.mark.parametrize(
        ("source", "expected_factory"),
        [
            (StreamingSource.QOBUZ, QobuzModelFactory),
            (StreamingSource.TIDAL, TidalModelFactory),
            (StreamingSource.DEEZER, DeezerModelFactory),
            (StreamingSource.SOUNDCLOUD, SoundCloudModelFactory),
        ],
    )
    def test_get_factory_for_known_sources(self, source, expected_factory):
        """Test get_factory_for_source returns correct factory for known sources."""
        result = get_factory_for_source(source)
        assert result == expected_factory

    def test_get_factory_for_unknown_source(self):
        """Test get_factory_for_source returns ModelFactory for unknown sources."""
        # Create a mock unknown source
        unknown_source = Mock()
        result = get_factory_for_source(unknown_source)  # type: ignore[invalid-argument-type]
        assert result == ModelFactory

    def test_get_factory_for_none(self):
        """Test get_factory_for_source handles None gracefully."""
        # Use type: ignore to handle the intentional type mismatch for testing
        result = get_factory_for_source(None)  # type: ignore
        assert result == ModelFactory


class TestFactoryIntegration:
    """Integration tests for factory classes."""

    def test_all_factories_implement_protocol_methods(self):
        """Test that all factory classes have the required methods."""
        # Different factories support different methods
        factory_methods = {
            QobuzModelFactory: [
                "create_artist",
                "create_album",
                "create_track",
                "create_playlist",
            ],
            TidalModelFactory: [
                "create_artist",
                "create_album",
                "create_track",
                "create_playlist",
            ],
            DeezerModelFactory: [
                "create_artist",
                "create_album",
                "create_track",
                "create_playlist",
            ],
            SoundCloudModelFactory: [
                "create_artist",
                "create_track",
                "create_playlist",
            ],  # No create_album
        }

        for factory, required_methods in factory_methods.items():
            for method_name in required_methods:
                assert hasattr(factory, method_name), (
                    f"{factory.__name__} missing {method_name}"
                )
                method = getattr(factory, method_name)
                assert callable(method), (
                    f"{factory.__name__}.{method_name} is not callable"
                )

    def test_factory_methods_are_static(self):
        """Test that factory methods are static methods."""
        factories = [
            ModelFactory,
            QobuzModelFactory,
            TidalModelFactory,
            DeezerModelFactory,
            SoundCloudModelFactory,
        ]

        for factory in factories:
            # Test that we can call methods without instantiating the class
            if hasattr(factory, "create_artist"):
                assert callable(factory.create_artist)
