# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Unit tests for src/ripstream/models/playlist.py module."""

import pytest

from ripstream.models.enums import StreamingSource
from ripstream.models.playlist import Playlist, PlaylistInfo, PlaylistTrack


@pytest.fixture
def sample_playlist_info() -> PlaylistInfo:
    """Create a sample PlaylistInfo for testing."""
    return PlaylistInfo(
        id="playlist1",
        source=StreamingSource.SPOTIFY,
        name="Test Playlist",
        description="A test playlist",
        owner="test_user",
        owner_id="user123",
        is_public=True,
        is_collaborative=False,
        total_tracks=3,
        total_duration_seconds=600.0,
        tags=["rock", "pop"],
        genres=["Rock", "Pop"],
    )


@pytest.fixture
def sample_playlist_tracks() -> list[PlaylistTrack]:
    """Create sample PlaylistTrack objects for testing."""
    return [
        PlaylistTrack(
            track_id="track1",
            position=1,
            added_at="2023-01-01T00:00:00Z",
            added_by="user123",
        ),
        PlaylistTrack(
            track_id="track2",
            position=2,
            added_at="2023-01-02T00:00:00Z",
            added_by="user123",
        ),
        PlaylistTrack(
            track_id="track3",
            position=3,
            added_at="2023-01-03T00:00:00Z",
            added_by="user123",
        ),
    ]


@pytest.fixture
def sample_playlist(
    sample_playlist_info: PlaylistInfo, sample_playlist_tracks: list[PlaylistTrack]
) -> Playlist:
    """Create a sample Playlist for testing."""
    return Playlist(info=sample_playlist_info, tracks=sample_playlist_tracks)


class TestPlaylistInfo:
    """Test cases for PlaylistInfo model."""

    def test_playlist_info_creation(self, sample_playlist_info: PlaylistInfo) -> None:
        """Test creating a PlaylistInfo instance."""
        assert sample_playlist_info.name == "Test Playlist"
        assert sample_playlist_info.total_tracks == 3
        assert sample_playlist_info.is_public is True

    def test_validate_total_tracks_negative(self) -> None:
        """Test that negative track count raises ValueError."""
        with pytest.raises(ValueError, match="Track count must be non-negative"):
            PlaylistInfo(
                id="playlist1",
                source=StreamingSource.SPOTIFY,
                name="Test Playlist",
                total_tracks=-1,
            )

    def test_duration_formatted_with_hours(self) -> None:
        """Test duration formatting with hours."""
        info = PlaylistInfo(
            id="playlist1",
            source=StreamingSource.SPOTIFY,
            name="Test Playlist",
            total_duration_seconds=3665.0,  # 1 hour, 1 minute, 5 seconds
        )
        assert info.duration_formatted == "01:01:05"

    def test_duration_formatted_without_hours(self) -> None:
        """Test duration formatting without hours."""
        info = PlaylistInfo(
            id="playlist1",
            source=StreamingSource.SPOTIFY,
            name="Test Playlist",
            total_duration_seconds=125.0,  # 2 minutes, 5 seconds
        )
        assert info.duration_formatted == "02:05"

    def test_duration_formatted_none(self) -> None:
        """Test duration formatting when duration is None."""
        info = PlaylistInfo(
            id="playlist1",
            source=StreamingSource.SPOTIFY,
            name="Test Playlist",
            total_duration_seconds=None,
        )
        assert info.duration_formatted is None

    def test_add_tag(self) -> None:
        """Test adding tags to playlist."""
        info = PlaylistInfo(
            id="playlist1",
            source=StreamingSource.SPOTIFY,
            name="Test Playlist",
        )
        info.add_tag("rock")
        info.add_tag("pop")
        info.add_tag("rock")  # Duplicate should not be added

        assert info.tags == ["rock", "pop"]

    def test_add_genre(self) -> None:
        """Test adding genres to playlist."""
        info = PlaylistInfo(
            id="playlist1",
            source=StreamingSource.SPOTIFY,
            name="Test Playlist",
        )
        info.add_genre("Rock")
        info.add_genre("Pop")
        info.add_genre("Rock")  # Duplicate should not be added

        assert info.genres == ["Rock", "Pop"]


class TestPlaylistTrack:
    """Test cases for PlaylistTrack model."""

    def test_playlist_track_creation(self) -> None:
        """Test creating a PlaylistTrack instance."""
        track = PlaylistTrack(
            track_id="track1",
            position=1,
            added_at="2023-01-01T00:00:00Z",
            added_by="user123",
            custom_title="Custom Title",
            custom_artist="Custom Artist",
            notes="Test notes",
        )

        assert track.track_id == "track1"
        assert track.position == 1
        assert track.custom_title == "Custom Title"
        assert track.custom_artist == "Custom Artist"
        assert track.notes == "Test notes"

    def test_validate_position_negative(self) -> None:
        """Test that negative position raises ValueError."""
        with pytest.raises(ValueError, match="Position must be positive"):
            PlaylistTrack(track_id="track1", position=0)

    def test_display_properties(self) -> None:
        """Test display title and artist properties."""
        track = PlaylistTrack(
            track_id="track1",
            position=1,
            custom_title="Custom Title",
            custom_artist="Custom Artist",
        )

        assert track.display_title == "Custom Title"
        assert track.display_artist == "Custom Artist"


class TestPlaylist:
    """Test cases for Playlist model."""

    def test_playlist_creation(self, sample_playlist: Playlist) -> None:
        """Test creating a Playlist instance."""
        assert sample_playlist.name == "Test Playlist"
        assert sample_playlist.track_count == 3
        assert sample_playlist.is_empty is False

    def test_empty_playlist(self) -> None:
        """Test empty playlist properties."""
        info = PlaylistInfo(
            id="playlist1",
            source=StreamingSource.SPOTIFY,
            name="Empty Playlist",
        )
        playlist = Playlist(info=info)

        assert playlist.track_count == 0
        assert playlist.is_empty is True

    def test_add_track_to_end(self, sample_playlist: Playlist) -> None:
        """Test adding a track to the end of the playlist."""
        initial_count = sample_playlist.track_count

        new_track = sample_playlist.add_track("track4", added_by="user456")

        assert sample_playlist.track_count == initial_count + 1
        assert new_track.track_id == "track4"
        assert new_track.position == 4
        assert new_track.added_by == "user456"
        assert sample_playlist.info.total_tracks == 4

    def test_add_track_at_position(self, sample_playlist: Playlist) -> None:
        """Test adding a track at a specific position."""
        initial_count = sample_playlist.track_count

        new_track = sample_playlist.add_track(
            "track_new", position=2, added_by="user456"
        )

        assert sample_playlist.track_count == initial_count + 1
        assert new_track.position == 2

        # Check that existing tracks have updated positions
        track_positions = [track.position for track in sample_playlist.tracks]
        assert sorted(track_positions) == [1, 2, 3, 4]

        # Verify the new track is at the correct position in the list
        assert sample_playlist.tracks[1].track_id == "track_new"

    def test_remove_track_success(self, sample_playlist: Playlist) -> None:
        """Test successfully removing a track from the playlist."""
        initial_count = sample_playlist.track_count

        # Remove the middle track
        result = sample_playlist.remove_track("track2")

        assert result is True
        assert sample_playlist.track_count == initial_count - 1
        assert sample_playlist.info.total_tracks == 2

        # Check that positions are adjusted correctly
        remaining_track_ids = [track.track_id for track in sample_playlist.tracks]
        assert remaining_track_ids == ["track1", "track3"]

        # Check that positions are sequential
        positions = [track.position for track in sample_playlist.tracks]
        assert positions == [1, 2]

    def test_remove_track_not_found(self, sample_playlist: Playlist) -> None:
        """Test removing a track that doesn't exist."""
        initial_count = sample_playlist.track_count

        result = sample_playlist.remove_track("nonexistent_track")

        assert result is False
        assert sample_playlist.track_count == initial_count
        assert sample_playlist.info.total_tracks == 3

    def test_remove_track_first_position(self, sample_playlist: Playlist) -> None:
        """Test removing the first track and position adjustment."""
        result = sample_playlist.remove_track("track1")

        assert result is True
        assert sample_playlist.track_count == 2

        # Check that remaining tracks have correct positions
        remaining_tracks = sample_playlist.tracks
        assert remaining_tracks[0].track_id == "track2"
        assert remaining_tracks[0].position == 1
        assert remaining_tracks[1].track_id == "track3"
        assert remaining_tracks[1].position == 2

    def test_remove_track_last_position(self, sample_playlist: Playlist) -> None:
        """Test removing the last track."""
        result = sample_playlist.remove_track("track3")

        assert result is True
        assert sample_playlist.track_count == 2

        # Check that remaining tracks maintain their positions
        remaining_tracks = sample_playlist.tracks
        assert remaining_tracks[0].track_id == "track1"
        assert remaining_tracks[0].position == 1
        assert remaining_tracks[1].track_id == "track2"
        assert remaining_tracks[1].position == 2

    def test_move_track_success(self, sample_playlist: Playlist) -> None:
        """Test successfully moving a track to a new position."""
        result = sample_playlist.move_track("track1", 3)

        assert result is True

        # Check new order
        track_ids = [track.track_id for track in sample_playlist.tracks]
        assert track_ids == ["track2", "track3", "track1"]

        # Check positions are updated correctly
        positions = [track.position for track in sample_playlist.tracks]
        assert positions == [1, 2, 3]

    def test_move_track_not_found(self, sample_playlist: Playlist) -> None:
        """Test moving a track that doesn't exist."""
        result = sample_playlist.move_track("nonexistent_track", 2)

        assert result is False

        # Check that nothing changed
        track_ids = [track.track_id for track in sample_playlist.tracks]
        assert track_ids == ["track1", "track2", "track3"]

    def test_get_track_success(self, sample_playlist: Playlist) -> None:
        """Test getting a track by ID."""
        track = sample_playlist.get_track("track2")

        assert track is not None
        assert track.track_id == "track2"
        assert track.position == 2

    def test_get_track_not_found(self, sample_playlist: Playlist) -> None:
        """Test getting a track that doesn't exist."""
        track = sample_playlist.get_track("nonexistent_track")

        assert track is None

    def test_get_track_ids(self, sample_playlist: Playlist) -> None:
        """Test getting all track IDs in order."""
        track_ids = sample_playlist.get_track_ids()

        assert track_ids == ["track1", "track2", "track3"]

    def test_shuffle_tracks(self, sample_playlist: Playlist) -> None:
        """Test shuffling tracks."""
        original_track_ids = sample_playlist.get_track_ids()

        sample_playlist.shuffle_tracks()

        # Check that all tracks are still present
        shuffled_track_ids = sample_playlist.get_track_ids()
        assert set(shuffled_track_ids) == set(original_track_ids)

        # Check that positions are sequential
        positions = [track.position for track in sample_playlist.tracks]
        assert sorted(positions) == [1, 2, 3]

    def test_sort_tracks_by_title(self, sample_playlist: Playlist) -> None:
        """Test sorting tracks by title (using track_id as placeholder)."""
        sample_playlist.sort_tracks_by_title()

        # Check that tracks are sorted by track_id
        track_ids = [track.track_id for track in sample_playlist.tracks]
        assert track_ids == sorted(["track1", "track2", "track3"])

        # Check that positions are updated
        positions = [track.position for track in sample_playlist.tracks]
        assert positions == [1, 2, 3]

    def test_toggle_favorite(self, sample_playlist: Playlist) -> None:
        """Test toggling favorite status."""
        initial_favorite = sample_playlist.is_favorite

        sample_playlist.toggle_favorite()
        assert sample_playlist.is_favorite != initial_favorite

        sample_playlist.toggle_favorite()
        assert sample_playlist.is_favorite == initial_favorite

    def test_matches_search(self, sample_playlist: Playlist) -> None:
        """Test search matching functionality."""
        # Test matching playlist name
        assert sample_playlist.matches_search("Test") is True
        assert sample_playlist.matches_search("test") is True

        # Test matching description
        assert sample_playlist.matches_search("test playlist") is True

        # Test matching owner
        assert sample_playlist.matches_search("test_user") is True

        # Test matching tags
        assert sample_playlist.matches_search("rock") is True

        # Test matching genres
        assert sample_playlist.matches_search("Pop") is True

        # Test non-matching query
        assert sample_playlist.matches_search("nonexistent") is False

    def test_get_download_folder_name_custom(self, sample_playlist: Playlist) -> None:
        """Test getting download folder name with custom folder."""
        sample_playlist.download_folder = "Custom Folder"

        result = sample_playlist.get_download_folder_name()
        assert result == "Custom Folder"

    def test_get_download_folder_name_generated(
        self, sample_playlist: Playlist
    ) -> None:
        """Test getting generated download folder name."""
        result = sample_playlist.get_download_folder_name()
        expected = "test_user - Test Playlist"
        assert result == expected

    def test_get_download_folder_name_no_owner(self) -> None:
        """Test getting download folder name without owner."""
        info = PlaylistInfo(
            id="playlist1",
            source=StreamingSource.SPOTIFY,
            name="Test Playlist",
            owner=None,
        )
        playlist = Playlist(info=info)

        result = playlist.get_download_folder_name()
        assert result == "Test Playlist"

    def test_get_download_folder_name_unsafe_characters(self) -> None:
        """Test getting download folder name with unsafe characters."""
        info = PlaylistInfo(
            id="playlist1",
            source=StreamingSource.SPOTIFY,
            name="Test<>Playlist|Name",
            owner="User/Name",
        )
        playlist = Playlist(info=info)

        result = playlist.get_download_folder_name()
        assert result == "UserName - TestPlaylistName"

    def test_to_dict(self, sample_playlist: Playlist) -> None:
        """Test converting playlist to dictionary."""
        result = sample_playlist.to_dict()

        expected_keys = {
            "id",
            "source",
            "name",
            "description",
            "owner",
            "is_public",
            "is_collaborative",
            "total_tracks",
            "track_count",
            "duration",
            "duration_formatted",
            "tags",
            "genres",
            "is_favorite",
            "is_empty",
            "followers",
            "likes",
            "download_status",
            "covers",
            "track_ids",
        }

        assert set(result.keys()) == expected_keys
        assert result["name"] == "Test Playlist"
        assert result["track_count"] == 3
        assert result["track_ids"] == ["track1", "track2", "track3"]

    def test_from_source_data(self) -> None:
        """Test creating playlist from source data."""
        source_data = {
            "name": "Source Playlist",
            "description": "From source",
            "owner": "source_user",
            "owner_id": "source123",
            "is_public": False,
            "is_collaborative": True,
            "total_tracks": 2,
            "total_duration": 300.0,
            "tags": ["electronic"],
            "genres": ["Electronic"],
            "url": "https://example.com/playlist",
            "tracks": [
                {
                    "id": "source_track1",
                    "position": 1,
                    "added_at": "2023-01-01T00:00:00Z",
                    "added_by": "source_user",
                },
                {
                    "id": "source_track2",
                    "position": 2,
                    "added_at": "2023-01-02T00:00:00Z",
                    "added_by": "source_user",
                },
            ],
        }

        playlist = Playlist.from_source_data(
            source=StreamingSource.SPOTIFY,
            playlist_id="source_playlist1",
            data=source_data,
        )

        assert playlist.info.name == "Source Playlist"
        assert playlist.info.description == "From source"
        assert playlist.info.is_public is False
        assert playlist.info.is_collaborative is True
        assert playlist.track_count == 2
        assert len(playlist.tracks) == 2
        assert playlist.tracks[0].track_id == "source_track1"
        assert playlist.tracks[1].track_id == "source_track2"

        # Check that raw metadata was added to the playlist stats
        assert "source_data" in playlist.stats.raw_metadata
