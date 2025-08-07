# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Unit tests for models/__init__.py module."""

from unittest.mock import Mock, patch

import pytest

from ripstream.models import (
    create_album_from_source,
    create_artist_from_source,
    create_playlist_from_source,
    create_track_from_source,
)
from ripstream.models.album import Album
from ripstream.models.artist import Artist
from ripstream.models.enums import StreamingSource
from ripstream.models.factories import (
    DeezerModelFactory,
    ModelFactory,
    QobuzModelFactory,
    SoundCloudModelFactory,
    TidalModelFactory,
)
from ripstream.models.playlist import Playlist
from ripstream.models.track import Track


class TestCreateFromSourceFunctions:
    """Test the create_*_from_source convenience functions."""

    @pytest.fixture
    def mock_artist_data(self):
        """Mock artist data for testing."""
        return {
            "name": "Test Artist",
            "biography": "Test biography",
            "genres": ["Rock", "Pop"],
            "country": "US",
            "formed_year": 2000,
        }

    @pytest.fixture
    def mock_album_data(self):
        """Mock album data for testing."""
        return {
            "title": "Test Album",
            "artist": "Test Artist",
            "release_date": "2023-01-01",
            "total_tracks": 10,
            "genres": ["Rock"],
        }

    @pytest.fixture
    def mock_track_data(self):
        """Mock track data for testing."""
        return {
            "title": "Test Track",
            "artist": "Test Artist",
            "duration": 180,
            "track_number": 1,
            "disc_number": 1,
        }

    @pytest.fixture
    def mock_playlist_data(self):
        """Mock playlist data for testing."""
        return {
            "title": "Test Playlist",
            "description": "Test description",
            "total_tracks": 20,
            "is_public": True,
        }

    @pytest.mark.parametrize(
        ("source", "expected_factory"),
        [
            (StreamingSource.QOBUZ, QobuzModelFactory),
            (StreamingSource.TIDAL, TidalModelFactory),
            (StreamingSource.DEEZER, DeezerModelFactory),
            (StreamingSource.SOUNDCLOUD, SoundCloudModelFactory),
        ],
    )
    def test_create_artist_from_source_with_specific_factory(
        self, source, expected_factory, mock_artist_data
    ):
        """Test create_artist_from_source uses correct factory when available."""
        with patch.object(expected_factory, "create_artist") as mock_create:
            mock_artist = Mock(spec=Artist)
            mock_create.return_value = mock_artist

            result = create_artist_from_source(source, "test_id", mock_artist_data)

            mock_create.assert_called_once_with("test_id", mock_artist_data)
            assert result == mock_artist

    def test_create_artist_from_source_fallback_to_model_factory(
        self, mock_artist_data
    ):
        """Test create_artist_from_source falls back to ModelFactory when no specific factory."""
        # Create a mock source that doesn't have a specific factory
        mock_source = Mock()

        with patch("ripstream.models.get_factory_for_source") as mock_get_factory:
            mock_factory = Mock()
            mock_factory.create_artist = Mock(return_value=Mock(spec=Artist))
            mock_get_factory.return_value = mock_factory

            # Test when factory doesn't have create_artist method
            delattr(mock_factory, "create_artist")

            with patch.object(ModelFactory, "create_artist") as mock_model_create:
                mock_artist = Mock(spec=Artist)
                mock_model_create.return_value = mock_artist

                result = create_artist_from_source(
                    mock_source,  # type: ignore[invalid-argument-type]
                    "test_id",
                    mock_artist_data,
                )

                mock_model_create.assert_called_once_with(
                    mock_source, "test_id", mock_artist_data
                )
                assert result == mock_artist

    @pytest.mark.parametrize(
        ("source", "expected_factory"),
        [
            (StreamingSource.QOBUZ, QobuzModelFactory),
            (StreamingSource.TIDAL, TidalModelFactory),
            (StreamingSource.DEEZER, DeezerModelFactory),
            # Note: SoundCloudModelFactory doesn't have create_album method
        ],
    )
    def test_create_album_from_source_with_specific_factory(
        self, source, expected_factory, mock_album_data
    ):
        """Test create_album_from_source uses correct factory when available."""
        with patch.object(expected_factory, "create_album") as mock_create:
            mock_album = Mock(spec=Album)
            mock_create.return_value = mock_album

            result = create_album_from_source(source, "test_id", mock_album_data)

            mock_create.assert_called_once_with("test_id", mock_album_data)
            assert result == mock_album

    def test_create_album_from_source_fallback_to_model_factory(self, mock_album_data):
        """Test create_album_from_source falls back to ModelFactory when no specific factory."""
        mock_source = Mock()

        with patch("ripstream.models.get_factory_for_source") as mock_get_factory:
            mock_factory = Mock()
            mock_get_factory.return_value = mock_factory

            # Test when factory doesn't have create_album method
            if hasattr(mock_factory, "create_album"):
                delattr(mock_factory, "create_album")

            with patch.object(ModelFactory, "create_album") as mock_model_create:
                mock_album = Mock(spec=Album)
                mock_model_create.return_value = mock_album

                result = create_album_from_source(
                    mock_source,  # type: ignore[invalid-argument-type]
                    "test_id",
                    mock_album_data,
                )

                mock_model_create.assert_called_once_with(
                    mock_source, "test_id", mock_album_data
                )
                assert result == mock_album

    @pytest.mark.parametrize(
        ("source", "expected_factory"),
        [
            (StreamingSource.QOBUZ, QobuzModelFactory),
            (StreamingSource.TIDAL, TidalModelFactory),
            (StreamingSource.DEEZER, DeezerModelFactory),
            (StreamingSource.SOUNDCLOUD, SoundCloudModelFactory),
        ],
    )
    def test_create_track_from_source_with_specific_factory(
        self, source, expected_factory, mock_track_data
    ):
        """Test create_track_from_source uses correct factory when available."""
        with patch.object(expected_factory, "create_track") as mock_create:
            mock_track = Mock(spec=Track)
            mock_create.return_value = mock_track

            album_data = {"title": "Test Album"}
            result = create_track_from_source(
                source, "test_id", mock_track_data, album_data, extra_param="test"
            )

            mock_create.assert_called_once_with(
                "test_id", mock_track_data, album_data, extra_param="test"
            )
            assert result == mock_track

    def test_create_track_from_source_fallback_to_model_factory(self, mock_track_data):
        """Test create_track_from_source falls back to ModelFactory when no specific factory."""
        mock_source = Mock()

        with patch("ripstream.models.get_factory_for_source") as mock_get_factory:
            mock_factory = Mock()
            mock_get_factory.return_value = mock_factory

            # Test when factory doesn't have create_track method
            if hasattr(mock_factory, "create_track"):
                delattr(mock_factory, "create_track")

            with patch.object(ModelFactory, "create_track") as mock_model_create:
                mock_track = Mock(spec=Track)
                mock_model_create.return_value = mock_track

                album_data = {"title": "Test Album"}
                result = create_track_from_source(
                    mock_source,  # type: ignore[invalid-argument-type]
                    "test_id",
                    mock_track_data,
                    album_data,
                    extra_param="test",
                )

                mock_model_create.assert_called_once_with(
                    mock_source,
                    "test_id",
                    mock_track_data,
                    album_data,
                    extra_param="test",
                )
                assert result == mock_track

    @pytest.mark.parametrize(
        ("source", "expected_factory"),
        [
            (StreamingSource.QOBUZ, QobuzModelFactory),
            (StreamingSource.TIDAL, TidalModelFactory),
            (StreamingSource.DEEZER, DeezerModelFactory),
            (StreamingSource.SOUNDCLOUD, SoundCloudModelFactory),
        ],
    )
    def test_create_playlist_from_source_with_specific_factory(
        self, source, expected_factory, mock_playlist_data
    ):
        """Test create_playlist_from_source uses correct factory when available."""
        with patch.object(expected_factory, "create_playlist") as mock_create:
            mock_playlist = Mock(spec=Playlist)
            mock_create.return_value = mock_playlist

            result = create_playlist_from_source(source, "test_id", mock_playlist_data)

            mock_create.assert_called_once_with("test_id", mock_playlist_data)
            assert result == mock_playlist

    def test_create_playlist_from_source_fallback_to_model_factory(
        self, mock_playlist_data
    ):
        """Test create_playlist_from_source falls back to ModelFactory when no specific factory."""
        mock_source = Mock()

        with patch("ripstream.models.get_factory_for_source") as mock_get_factory:
            mock_factory = Mock()
            mock_get_factory.return_value = mock_factory

            # Test when factory doesn't have create_playlist method
            if hasattr(mock_factory, "create_playlist"):
                delattr(mock_factory, "create_playlist")

            with patch.object(ModelFactory, "create_playlist") as mock_model_create:
                mock_playlist = Mock(spec=Playlist)
                mock_model_create.return_value = mock_playlist

                result = create_playlist_from_source(
                    mock_source,  # type: ignore[invalid-argument-type]
                    "test_id",
                    mock_playlist_data,
                )

                mock_model_create.assert_called_once_with(
                    mock_source, "test_id", mock_playlist_data
                )
                assert result == mock_playlist

    def test_create_functions_with_kwargs(
        self, mock_artist_data, mock_album_data, mock_track_data, mock_playlist_data
    ):
        """Test that all create functions properly pass through kwargs."""
        test_kwargs = {"extra_param": "test_value", "another_param": 123}

        # Test artist creation with kwargs
        with patch.object(QobuzModelFactory, "create_artist") as mock_create:
            mock_create.return_value = Mock(spec=Artist)
            create_artist_from_source(
                StreamingSource.QOBUZ, "test_id", mock_artist_data, **test_kwargs
            )
            mock_create.assert_called_once_with(
                "test_id", mock_artist_data, **test_kwargs
            )

        # Test album creation with kwargs
        with patch.object(QobuzModelFactory, "create_album") as mock_create:
            mock_create.return_value = Mock(spec=Album)
            create_album_from_source(
                StreamingSource.QOBUZ, "test_id", mock_album_data, **test_kwargs
            )
            mock_create.assert_called_once_with(
                "test_id", mock_album_data, **test_kwargs
            )

        # Test track creation with kwargs
        with patch.object(QobuzModelFactory, "create_track") as mock_create:
            mock_create.return_value = Mock(spec=Track)
            create_track_from_source(
                StreamingSource.QOBUZ, "test_id", mock_track_data, None, **test_kwargs
            )
            mock_create.assert_called_once_with(
                "test_id", mock_track_data, None, **test_kwargs
            )

        # Test playlist creation with kwargs
        with patch.object(QobuzModelFactory, "create_playlist") as mock_create:
            mock_create.return_value = Mock(spec=Playlist)
            create_playlist_from_source(
                StreamingSource.QOBUZ, "test_id", mock_playlist_data, **test_kwargs
            )
            mock_create.assert_called_once_with(
                "test_id", mock_playlist_data, **test_kwargs
            )


class TestModuleImports:
    """Test that all expected imports are available in the module."""

    def test_all_exports_available(self):
        """Test that all items in __all__ are importable."""
        from ripstream.models import __all__

        # Test a sample of key exports to ensure they're available
        key_exports = [
            "Album",
            "Artist",
            "Track",
            "Playlist",
            "AudioQuality",
            "StreamingSource",
            "CoverSize",
            "ModelFactory",
            "QobuzModelFactory",
            "create_artist_from_source",
            "create_album_from_source",
            "sanitize_filename",
            "format_duration",
        ]

        for export_name in key_exports:
            assert export_name in __all__, f"{export_name} not in __all__"

    def test_convenience_functions_in_all(self):
        """Test that convenience functions are properly added to __all__."""
        from ripstream.models import __all__

        convenience_functions = [
            "create_album_from_source",
            "create_artist_from_source",
            "create_playlist_from_source",
            "create_track_from_source",
        ]

        for func_name in convenience_functions:
            assert func_name in __all__, f"{func_name} not in __all__"
