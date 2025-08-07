# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Unit tests for src/ripstream/models/utils.py module."""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from ripstream.models.album import Album, AlbumCredits, AlbumInfo
from ripstream.models.artist import Artist, ArtistInfo
from ripstream.models.audio import AudioInfo
from ripstream.models.enums import AudioQuality, StreamingSource
from ripstream.models.playlist import Playlist, PlaylistInfo
from ripstream.models.track import Track, TrackCredits, TrackInfo
from ripstream.models.utils import (
    calculate_album_stats,
    calculate_playlist_stats,
    create_download_path,
    extract_year_from_date,
    format_duration,
    format_file_size,
    get_quality_description,
    group_albums_by_artist,
    group_tracks_by_album,
    merge_artist_names,
    normalize_genre,
    parse_duration,
    sanitize_filename,
    search_models,
    validate_model_relationships,
)


class TestSanitizeFilename:
    """Test cases for sanitize_filename function."""

    @pytest.mark.parametrize(
        ("input_filename", "expected"),
        [
            ("My Song.mp3", "My Song.mp3"),
            ('Song<>:"/\\|?*Name', "Song_________Name"),
            ("Song\x00\x1f\x7f\x9fName", "SongName"),
            ("  ...Song Name...  ", "Song Name"),
            ("", "untitled"),
            ('<>:"/\\|?*', "_________"),
        ],
    )
    def test_sanitize_filename_basic_cases(
        self, input_filename: str, expected: str
    ) -> None:
        """Test basic filename sanitization cases."""
        result = sanitize_filename(input_filename)
        assert result == expected

    def test_sanitize_max_length_truncation(self) -> None:
        """Test filename truncation when exceeding max length."""
        long_name = "a" * 300
        result = sanitize_filename(long_name, max_length=255)
        assert len(result) == 255
        assert result == "a" * 255

    def test_sanitize_max_length_with_trailing_dots(self) -> None:
        """Test filename truncation removes trailing dots after truncation."""
        long_name = "a" * 250 + "....."
        result = sanitize_filename(long_name, max_length=255)
        assert len(result) <= 255
        assert not result.endswith(".")

    def test_sanitize_custom_max_length(self) -> None:
        """Test sanitizing with custom max length."""
        result = sanitize_filename("Very Long Filename", max_length=10)
        assert len(result) <= 10
        assert result == "Very Long"


class TestFormatDuration:
    """Test cases for format_duration function."""

    @pytest.mark.parametrize(
        ("seconds", "expected"),
        [
            (None, "00:00"),
            (0.0, "00:00"),
            (45.0, "00:45"),
            (125.0, "02:05"),
            (3665.0, "01:01:05"),
            (65.7, "01:05"),  # Fractional seconds truncated
            (36000.0, "10:00:00"),
        ],
    )
    def test_format_duration_cases(self, seconds: float | None, expected: str) -> None:
        """Test duration formatting for various inputs."""
        result = format_duration(seconds)
        assert result == expected


class TestParseDuration:
    """Test cases for parse_duration function."""

    @pytest.mark.parametrize(
        ("duration_str", "expected"),
        [
            ("", None),
            ("02:30", 150.0),
            ("01:02:30", 3750.0),
            ("invalid", None),
            ("01:02:03:04", None),
            ("ab:cd", None),
            ("00:00", 0.0),
            ("1:5", 65.0),
        ],
    )
    def test_parse_duration_cases(
        self, duration_str: str, expected: float | None
    ) -> None:
        """Test duration parsing for various inputs."""
        result = parse_duration(duration_str)
        assert result == expected


class TestFormatFileSize:
    """Test cases for format_file_size function."""

    @pytest.mark.parametrize(
        ("size_bytes", "expected"),
        [
            (None, "Unknown"),
            (0, "0.0 B"),
            (512, "512.0 B"),
            (1024, "1.0 KB"),
            (1536, "1.5 KB"),
            (1572864, "1.5 MB"),
            (1610612736, "1.5 GB"),
            (1649267441664, "1.5 TB"),
        ],
    )
    def test_format_file_size_cases(
        self, size_bytes: int | None, expected: str
    ) -> None:
        """Test file size formatting for various inputs."""
        result = format_file_size(size_bytes)
        assert result == expected


class TestGetQualityDescription:
    """Test cases for get_quality_description function."""

    @pytest.mark.parametrize(
        ("quality", "expected"),
        [
            (AudioQuality.LOW, "Low Quality (~128 kbps)"),
            (AudioQuality.HIGH, "High Quality (~320 kbps)"),
            (AudioQuality.LOSSLESS, "CD Quality (16-bit/44.1kHz)"),
            (AudioQuality.HI_RES, "Hi-Res (24-bit/96kHz+)"),
        ],
    )
    def test_quality_descriptions(self, quality: AudioQuality, expected: str) -> None:
        """Test quality descriptions for known qualities."""
        result = get_quality_description(quality)
        assert result == expected

    def test_unknown_quality_description(self) -> None:
        """Test description for unknown quality."""

        # Test with a quality value that doesn't exist in the mapping
        from dataclasses import dataclass

        @dataclass(frozen=True)
        class UnknownQuality:
            value: int

        unknown_quality = UnknownQuality(999)
        result = get_quality_description(unknown_quality)  # type: ignore[arg-type]
        assert result == "Unknown Quality"


class TestCreateDownloadPath:
    """Test cases for create_download_path function."""

    def test_create_basic_path(self) -> None:
        """Test creating basic download path."""
        with tempfile.TemporaryDirectory() as temp_dir:
            result = create_download_path(temp_dir, "Artist Name", create_dirs=False)
            expected = Path(temp_dir) / "Artist Name"
            assert result == expected

    def test_create_path_with_album(self) -> None:
        """Test creating path with album."""
        with tempfile.TemporaryDirectory() as temp_dir:
            result = create_download_path(
                temp_dir, "Artist Name", album="Album Name", create_dirs=False
            )
            expected = Path(temp_dir) / "Artist Name" / "Album Name"
            assert result == expected

    def test_create_path_with_track(self) -> None:
        """Test creating path with track."""
        with tempfile.TemporaryDirectory() as temp_dir:
            result = create_download_path(
                temp_dir, "Artist Name", track="Track Name", create_dirs=False
            )
            expected = Path(temp_dir) / "Artist Name" / "Track Name"
            assert result == expected

    def test_create_path_with_source(self) -> None:
        """Test creating path with streaming source."""
        with tempfile.TemporaryDirectory() as temp_dir:
            result = create_download_path(
                temp_dir, "Artist Name", source=StreamingSource.QOBUZ, create_dirs=False
            )
            expected = Path(temp_dir) / "Qobuz" / "Artist Name"
            assert result == expected

    def test_create_path_with_all_components(self) -> None:
        """Test creating path with all components."""
        with tempfile.TemporaryDirectory() as temp_dir:
            result = create_download_path(
                temp_dir,
                "Artist Name",
                album="Album Name",
                track="Track Name",
                source=StreamingSource.TIDAL,
                create_dirs=False,
            )
            expected = (
                Path(temp_dir) / "Tidal" / "Artist Name" / "Album Name" / "Track Name"
            )
            assert result == expected

    def test_create_directories(self) -> None:
        """Test that directories are created when create_dirs=True."""
        with tempfile.TemporaryDirectory() as temp_dir:
            result = create_download_path(
                temp_dir, "Artist Name", album="Album Name", create_dirs=True
            )
            assert result.exists()
            assert result.is_dir()

    def test_sanitize_path_components(self) -> None:
        """Test that path components are sanitized."""
        with tempfile.TemporaryDirectory() as temp_dir:
            result = create_download_path(
                temp_dir, "Artist<>Name", album="Album|Name", create_dirs=False
            )
            expected = Path(temp_dir) / "Artist__Name" / "Album_Name"
            assert result == expected


class TestExtractYearFromDate:
    """Test cases for extract_year_from_date function."""

    @pytest.mark.parametrize(
        ("date_str", "expected"),
        [
            ("2023-05-15", 2023),
            (None, None),
            ("", None),
            ("invalid-date", None),
            ("2023", 2023),
            ("abcd-05-15", None),
        ],
    )
    def test_extract_year_cases(
        self, date_str: str | None, expected: int | None
    ) -> None:
        """Test year extraction for various date formats."""
        result = extract_year_from_date(date_str)
        assert result == expected


class TestNormalizeGenre:
    """Test cases for normalize_genre function."""

    @pytest.mark.parametrize(
        ("input_genre", "expected"),
        [
            ("rock", "Rock"),
            ("progressive rock", "Progressive Rock"),
            ("  electronic   music  ", "Electronic Music"),
            ("rnb", "R&B"),
            ("hiphop", "Hip-Hop"),
            ("hip hop", "Hip-Hop"),
            ("edm", "EDM"),
            ("dnb", "Drum & Bass"),
            ("drum and bass", "Drum & Bass"),
            ("unknown genre", "Unknown Genre"),
        ],
    )
    def test_normalize_genre_cases(self, input_genre: str, expected: str) -> None:
        """Test genre normalization for various inputs."""
        result = normalize_genre(input_genre)
        assert result == expected


class TestMergeArtistNames:
    """Test cases for merge_artist_names function."""

    @pytest.mark.parametrize(
        ("artists", "expected"),
        [
            ([], "Unknown Artist"),
            (["Artist One"], "Artist One"),
            (["Artist One", "Artist Two"], "Artist One & Artist Two"),
            (
                ["Artist One", "Artist Two", "Artist Three"],
                "Artist One, Artist Two, Artist Three",
            ),
            (["Artist One", "artist one", "Artist Two"], "Artist One & Artist Two"),
            (["ARTIST ONE", "Artist One", "artist one"], "ARTIST ONE"),
        ],
    )
    def test_merge_artist_names_cases(self, artists: list[str], expected: str) -> None:
        """Test artist name merging for various inputs."""
        result = merge_artist_names(artists)
        assert result == expected

    def test_merge_custom_separator(self) -> None:
        """Test merging with custom separator."""
        result = merge_artist_names(["Artist One", "Artist Two", "Artist Three"], " | ")
        assert result == "Artist One | Artist Two | Artist Three"


@pytest.fixture
def mock_track() -> Track:
    """Create a mock Track for testing."""
    track_info = TrackInfo(
        id="track1",
        source=StreamingSource.QOBUZ,
        title="Test Track",
        track_number=1,
        disc_number=1,
    )
    track_credits = TrackCredits(artist="Test Artist")
    audio_info = AudioInfo(
        quality=AudioQuality.HIGH,  # Use the enum directly
        duration_seconds=180.0,
        is_explicit=False,
    )

    return Track(
        info=track_info,
        credits=track_credits,
        audio=audio_info,
        album_id="album1",
        artist_ids=["artist1"],
        genres=["Rock", "Pop"],
    )


@pytest.fixture
def mock_tracks(mock_track: Track) -> list[Track]:
    """Create a list of mock tracks for testing."""
    tracks = []
    for i in range(3):
        track_info = TrackInfo(
            id=f"track{i + 1}",
            source=StreamingSource.QOBUZ,
            title=f"Test Track {i + 1}",
            track_number=i + 1,
            disc_number=1,
        )
        track_credits = TrackCredits(artist=f"Test Artist {i + 1}")
        audio_info = AudioInfo(
            quality=AudioQuality.HIGH,  # Use the enum directly
            duration_seconds=180.0 + i * 30,
            is_explicit=i % 2 == 0,
        )

        track = Track(
            info=track_info,
            credits=track_credits,
            audio=audio_info,
            album_id=f"album{(i // 2) + 1}",
            artist_ids=[f"artist{i + 1}"],
            genres=["Rock", "Pop"] if i % 2 == 0 else ["Jazz"],
        )
        tracks.append(track)

    return tracks


class TestCalculateAlbumStats:
    """Test cases for calculate_album_stats function."""

    def test_calculate_empty_tracks(self) -> None:
        """Test calculating stats for empty track list."""
        result = calculate_album_stats([])
        expected = {
            "total_duration": 0,
            "total_tracks": 0,
            "total_discs": 1,
            "average_quality": AudioQuality.LOW,
            "genres": [],
            "is_explicit": False,
        }
        assert result == expected

    def test_calculate_single_track_stats(self, mock_track: Track) -> None:
        """Test calculating stats for single track."""
        result = calculate_album_stats([mock_track])
        expected = {
            "total_duration": 180.0,
            "total_tracks": 1,
            "total_discs": 1,
            "average_quality": AudioQuality.HIGH,
            "genres": ["Pop", "Rock"],  # Sorted alphabetically
            "is_explicit": False,
        }
        assert result == expected

    def test_calculate_multiple_tracks_stats(self, mock_tracks: list[Track]) -> None:
        """Test calculating stats for multiple tracks."""
        result = calculate_album_stats(mock_tracks)
        expected = {
            "total_duration": 630.0,  # 180 + 210 + 240
            "total_tracks": 3,
            "total_discs": 1,
            "average_quality": AudioQuality.HIGH,
            "genres": ["Jazz", "Pop", "Rock"],  # Sorted unique genres
            "is_explicit": True,  # At least one track is explicit
        }
        assert result == expected


class TestCalculatePlaylistStats:
    """Test cases for calculate_playlist_stats function."""

    def test_calculate_empty_playlist_stats(self) -> None:
        """Test calculating stats for empty playlist."""
        result = calculate_playlist_stats([])
        expected = {
            "total_duration": 0,
            "total_tracks": 0,
            "unique_artists": [],
            "unique_albums": [],
            "genres": [],
            "average_quality": AudioQuality.LOW,
        }
        assert result == expected

    def test_calculate_playlist_stats(self, mock_tracks: list[Track]) -> None:
        """Test calculating stats for playlist with tracks."""
        result = calculate_playlist_stats(mock_tracks)
        expected = {
            "total_duration": 630.0,  # 180 + 210 + 240
            "total_tracks": 3,
            "unique_artists": [
                "Test Artist 1",
                "Test Artist 2",
                "Test Artist 3",
            ],  # Sorted alphabetically
            "unique_albums": ["album1", "album2"],  # Sorted alphabetically
            "genres": ["Jazz", "Pop", "Rock"],  # Sorted unique genres
            "average_quality": AudioQuality.HIGH,
        }
        assert result == expected


@pytest.fixture
def mock_album() -> Album:
    """Create a mock Album for testing."""
    album_info = AlbumInfo(
        id="album1",
        source=StreamingSource.QOBUZ,
        title="Test Album",
        release_year=2023,
    )
    album_credits = AlbumCredits(artist="Test Artist")

    return Album(info=album_info, credits=album_credits)


@pytest.fixture
def mock_artist() -> Artist:
    """Create a mock Artist for testing."""
    artist_info = ArtistInfo(
        id="artist1",
        source=StreamingSource.QOBUZ,
        name="Test Artist",
    )

    return Artist(info=artist_info)


@pytest.fixture
def mock_playlist() -> Playlist:
    """Create a mock Playlist for testing."""
    playlist_info = PlaylistInfo(
        id="playlist1",
        source=StreamingSource.QOBUZ,
        name="Test Playlist",
    )

    return Playlist(info=playlist_info)


class TestSearchModels:
    """Test cases for search_models function."""

    def test_search_empty_query(self, mock_track: Track, mock_album: Album) -> None:
        """Test searching with empty query returns all models."""
        models = [mock_track, mock_album]
        result = search_models(models, "")
        assert result == models

    def test_search_with_limit(self, mock_tracks: list[Track]) -> None:
        """Test searching with limit."""
        from typing import cast

        # Cast to the expected union type
        models = cast("list[Artist | Album | Track | Playlist]", mock_tracks)
        result = search_models(models, "", limit=2)
        assert len(result) == 2

    def test_search_matching_models(self, mock_track: Track) -> None:
        """Test searching for matching models."""
        # Use patch to mock the matches_search method on the class
        with patch(
            "ripstream.models.track.Track.matches_search", return_value=True
        ) as mock_method:
            result = search_models([mock_track], "test")
            assert len(result) == 1
            assert result[0] == mock_track
            mock_method.assert_called_once_with("test")

    def test_search_non_matching_models(self, mock_track: Track) -> None:
        """Test searching for non-matching models."""
        with patch(
            "ripstream.models.track.Track.matches_search", return_value=False
        ) as mock_method:
            result = search_models([mock_track], "nonexistent")
            assert len(result) == 0
            mock_method.assert_called_once_with("nonexistent")


class TestGroupTracksByAlbum:
    """Test cases for group_tracks_by_album function."""

    def test_group_empty_tracks(self) -> None:
        """Test grouping empty track list."""
        result = group_tracks_by_album([])
        assert result == {}

    def test_group_tracks_by_album(self, mock_tracks: list[Track]) -> None:
        """Test grouping tracks by album."""
        result = group_tracks_by_album(mock_tracks)

        assert "album1" in result
        assert "album2" in result
        assert len(result["album1"]) == 2  # First two tracks
        assert len(result["album2"]) == 1  # Third track

    def test_group_tracks_sorted_by_position(self) -> None:
        """Test that tracks within albums are sorted by disc and track number."""
        # Create tracks with different disc/track numbers
        track1 = Mock()
        track1.album_id = "album1"
        track1.info.disc_number = 1
        track1.info.track_number = 2

        track2 = Mock()
        track2.album_id = "album1"
        track2.info.disc_number = 1
        track2.info.track_number = 1

        track3 = Mock()
        track3.album_id = "album1"
        track3.info.disc_number = 2
        track3.info.track_number = 1

        tracks = [track1, track2, track3]
        result = group_tracks_by_album(tracks)

        album_tracks = result["album1"]
        assert album_tracks[0] == track2  # Disc 1, Track 1
        assert album_tracks[1] == track1  # Disc 1, Track 2
        assert album_tracks[2] == track3  # Disc 2, Track 1


class TestGroupAlbumsByArtist:
    """Test cases for group_albums_by_artist function."""

    def test_group_empty_albums(self) -> None:
        """Test grouping empty album list."""
        result = group_albums_by_artist([])
        assert result == {}

    def test_group_albums_by_artist(self) -> None:
        """Test grouping albums by artist."""
        album1 = Mock()
        album1.credits.display_artist = "Artist One"
        album1.info.release_year = 2020

        album2 = Mock()
        album2.credits.display_artist = "Artist One"
        album2.info.release_year = 2022

        album3 = Mock()
        album3.credits.display_artist = "Artist Two"
        album3.info.release_year = 2021

        albums = [album1, album2, album3]
        result = group_albums_by_artist(albums)

        assert "Artist One" in result
        assert "Artist Two" in result
        assert len(result["Artist One"]) == 2
        assert len(result["Artist Two"]) == 1

    def test_group_albums_sorted_by_release_year(self) -> None:
        """Test that albums are sorted by release year."""
        album1 = Mock()
        album1.credits.display_artist = "Artist One"
        album1.info.release_year = 2022

        album2 = Mock()
        album2.credits.display_artist = "Artist One"
        album2.info.release_year = 2020

        album3 = Mock()
        album3.credits.display_artist = "Artist One"
        album3.info.release_year = None

        albums = [album1, album2, album3]
        result = group_albums_by_artist(albums)

        artist_albums = result["Artist One"]
        assert artist_albums[0] == album3  # None (treated as 0)
        assert artist_albums[1] == album2  # 2020
        assert artist_albums[2] == album1  # 2022


class TestValidateModelRelationships:
    """Test cases for validate_model_relationships function."""

    def test_validate_empty_models(self) -> None:
        """Test validating empty model lists."""
        result = validate_model_relationships([], [], [])
        assert result == {"relationship_issues": []}

    def test_validate_valid_relationships(self) -> None:
        """Test validating valid model relationships."""
        artist = Mock()
        artist.info.id = "artist1"
        artist.album_ids = ["album1"]

        album = Mock()
        album.info.id = "album1"
        album.track_ids = ["track1"]

        track = Mock()
        track.info.id = "track1"
        track.album_id = "album1"
        track.artist_ids = ["artist1"]

        result = validate_model_relationships([artist], [album], [track])
        assert result == {"relationship_issues": []}

    def test_validate_missing_album_reference(self) -> None:
        """Test validating missing album reference from artist."""
        artist = Mock()
        artist.info.id = "artist1"
        artist.album_ids = ["missing_album"]

        result = validate_model_relationships([artist], [], [])
        issues = result["relationship_issues"]
        assert len(issues) == 1
        assert "Artist artist1 references missing album missing_album" in issues[0]

    def test_validate_missing_track_reference(self) -> None:
        """Test validating missing track reference from album."""
        album = Mock()
        album.info.id = "album1"
        album.track_ids = ["missing_track"]

        result = validate_model_relationships([], [album], [])
        issues = result["relationship_issues"]
        assert len(issues) == 1
        assert "Album album1 references missing track missing_track" in issues[0]

    def test_validate_missing_album_reference_from_track(self) -> None:
        """Test validating missing album reference from track."""
        track = Mock()
        track.info.id = "track1"
        track.album_id = "missing_album"
        track.artist_ids = []

        result = validate_model_relationships([], [], [track])
        issues = result["relationship_issues"]
        assert len(issues) == 1
        assert "Track track1 references missing album missing_album" in issues[0]

    def test_validate_missing_artist_reference_from_track(self) -> None:
        """Test validating missing artist reference from track."""
        track = Mock()
        track.info.id = "track1"
        track.album_id = None
        track.artist_ids = ["missing_artist"]

        result = validate_model_relationships([], [], [track])
        issues = result["relationship_issues"]
        assert len(issues) == 1
        assert "Track track1 references missing artist missing_artist" in issues[0]

    def test_validate_multiple_issues(self) -> None:
        """Test validating multiple relationship issues."""
        artist = Mock()
        artist.info.id = "artist1"
        artist.album_ids = ["missing_album1", "missing_album2"]

        album = Mock()
        album.info.id = "album1"
        album.track_ids = ["missing_track"]

        track = Mock()
        track.info.id = "track1"
        track.album_id = "missing_album3"
        track.artist_ids = ["missing_artist"]

        result = validate_model_relationships([artist], [album], [track])
        issues = result["relationship_issues"]
        assert (
            len(issues) == 5
        )  # 2 missing albums + 1 missing track + 1 missing album + 1 missing artist
