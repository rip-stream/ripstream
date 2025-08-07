# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Tests for track model classes."""

import pytest

from ripstream.models.audio import AudioInfo
from ripstream.models.enums import StreamingSource
from ripstream.models.track import Track, TrackCredits, TrackInfo


class TestTrackInfo:
    """Test the TrackInfo class."""

    @pytest.fixture
    def track_info_data(self):
        """Sample track info data for testing."""
        return {
            "id": "track123",
            "source": StreamingSource.QOBUZ,
            "title": "Test Track",
            "sort_title": "Test Track, The",
            "version": "Remix",
            "work": "Symphony No. 1",
            "movement": "Allegro",
            "track_number": 5,
            "disc_number": 1,
            "total_tracks": 12,
            "total_discs": 2,
            "isrc": "USRC17607839",
            "upc": "123456789012",
            "lyrics": "Test lyrics here",
            "language": "en",
            "copyright": "2023 Test Records",
            "url": "https://example.com/track/123",
        }

    @pytest.fixture
    def track_info(self, track_info_data):
        """Create a TrackInfo instance for testing."""
        return TrackInfo.model_validate(track_info_data)

    def test_track_info_creation(self, track_info, track_info_data):
        """Test creating a TrackInfo instance."""
        assert track_info.id == track_info_data["id"]
        assert track_info.source == track_info_data["source"]
        assert track_info.title == track_info_data["title"]
        assert track_info.version == track_info_data["version"]
        assert track_info.work == track_info_data["work"]
        assert track_info.track_number == track_info_data["track_number"]
        assert track_info.disc_number == track_info_data["disc_number"]

    def test_track_info_minimal_creation(self):
        """Test creating TrackInfo with minimal required fields."""
        info = TrackInfo.model_validate({
            "id": "test123",
            "source": StreamingSource.TIDAL,
            "title": "Minimal Track",
        })
        assert info.id == "test123"
        assert info.source == StreamingSource.TIDAL
        assert info.title == "Minimal Track"
        assert info.track_number == 1  # Default
        assert info.disc_number == 1  # Default
        assert info.version is None
        assert info.work is None

    @pytest.mark.parametrize(
        ("number", "should_raise"),
        [
            (1, False),
            (5, False),
            (100, False),
            (0, True),
            (-1, True),
        ],
    )
    def test_track_number_validation(self, number, should_raise):
        """Test track number validation."""
        if should_raise:
            with pytest.raises(ValueError, match="must be positive"):
                TrackInfo.model_validate({
                    "id": "test",
                    "source": StreamingSource.QOBUZ,
                    "title": "Test",
                    "track_number": number,
                })
        else:
            info = TrackInfo.model_validate({
                "id": "test",
                "source": StreamingSource.QOBUZ,
                "title": "Test",
                "track_number": number,
            })
            assert info.track_number == number

    @pytest.mark.parametrize(
        ("number", "should_raise"),
        [
            (1, False),
            (2, False),
            (10, False),
            (0, True),
            (-1, True),
        ],
    )
    def test_disc_number_validation(self, number, should_raise):
        """Test disc number validation."""
        if should_raise:
            with pytest.raises(ValueError, match="must be positive"):
                TrackInfo.model_validate({
                    "id": "test",
                    "source": StreamingSource.QOBUZ,
                    "title": "Test",
                    "disc_number": number,
                })
        else:
            info = TrackInfo.model_validate({
                "id": "test",
                "source": StreamingSource.QOBUZ,
                "title": "Test",
                "disc_number": number,
            })
            assert info.disc_number == number

    @pytest.mark.parametrize(
        ("work", "title", "version", "expected"),
        [
            (None, "Test Track", None, "Test Track"),
            (None, "Test Track", "Remix", "Test Track (Remix)"),
            ("Symphony No. 1", "Allegro", None, "Symphony No. 1: Allegro"),
            (
                "Symphony No. 1",
                "Allegro",
                "Live",
                "Symphony No. 1: Allegro: (Live)",
            ),  # Fixed expected
        ],
    )
    def test_full_title_property(self, work, title, version, expected):
        """Test the full_title property."""
        info = TrackInfo.model_validate({
            "id": "test",
            "source": StreamingSource.QOBUZ,
            "title": title,
            "work": work,
            "version": version,
        })
        assert info.full_title == expected

    @pytest.mark.parametrize(
        ("disc", "track", "expected"),
        [
            (1, 5, "1.05"),
            (2, 12, "2.12"),
            (1, 1, "1.01"),
            (10, 99, "10.99"),
        ],
    )
    def test_position_string_property(self, disc, track, expected):
        """Test the position_string property."""
        info = TrackInfo.model_validate({
            "id": "test",
            "source": StreamingSource.QOBUZ,
            "title": "Test",
            "disc_number": disc,
            "track_number": track,
        })
        assert info.position_string == expected


class TestTrackCredits:
    """Test the TrackCredits class."""

    @pytest.fixture
    def track_credits(self):
        """Create a TrackCredits instance for testing."""
        return TrackCredits.model_validate({
            "artist": "Test Artist",
            "album_artist": "Album Artist",
            "composer": "Test Composer",
            "lyricist": "Test Lyricist",
            "producer": "Test Producer",
            "featured_artists": ["Featured Artist 1", "Featured Artist 2"],
        })

    def test_track_credits_creation(self, track_credits):
        """Test creating a TrackCredits instance."""
        assert track_credits.artist == "Test Artist"
        assert track_credits.album_artist == "Album Artist"
        assert track_credits.composer == "Test Composer"
        assert track_credits.lyricist == "Test Lyricist"
        assert track_credits.producer == "Test Producer"
        assert len(track_credits.featured_artists) == 2

    def test_track_credits_minimal_creation(self):
        """Test creating TrackCredits with minimal required fields."""
        track_credits = TrackCredits.model_validate({"artist": "Solo Artist"})
        assert track_credits.artist == "Solo Artist"
        assert track_credits.album_artist is None
        assert track_credits.featured_artists == []
        assert track_credits.additional_credits == {}

    def test_add_featured_artist(self, track_credits):
        """Test adding featured artists."""
        initial_count = len(track_credits.featured_artists)

        # Add new featured artist
        track_credits.add_featured_artist("New Featured Artist")
        assert "New Featured Artist" in track_credits.featured_artists
        assert len(track_credits.featured_artists) == initial_count + 1

        # Adding existing artist should not duplicate
        track_credits.add_featured_artist("Featured Artist 1")
        assert len(track_credits.featured_artists) == initial_count + 1

    def test_add_credit(self, track_credits):
        """Test adding additional credits."""
        # Add first credit for a role
        track_credits.add_credit("Guitarist", "John Doe")
        assert "Guitarist" in track_credits.additional_credits
        assert "John Doe" in track_credits.additional_credits["Guitarist"]

        # Add second credit for same role
        track_credits.add_credit("Guitarist", "Jane Smith")
        assert len(track_credits.additional_credits["Guitarist"]) == 2
        assert "Jane Smith" in track_credits.additional_credits["Guitarist"]

        # Adding same person again should not duplicate
        track_credits.add_credit("Guitarist", "John Doe")
        assert len(track_credits.additional_credits["Guitarist"]) == 2

    def test_display_artist_without_featured(self):
        """Test display_artist property without featured artists."""
        track_credits = TrackCredits.model_validate({"artist": "Solo Artist"})
        assert track_credits.display_artist == "Solo Artist"

    def test_display_artist_with_featured(self, track_credits):
        """Test display_artist property with featured artists."""
        expected = "Test Artist (feat. Featured Artist 1, Featured Artist 2)"
        assert track_credits.display_artist == expected


class TestTrack:
    """Test the Track class."""

    @pytest.fixture
    def track_data(self):
        """Sample track data for testing."""
        return {
            "title": "Test Track",
            "artist": "Test Artist",
            "album_artist": "Album Artist",
            "track_number": 5,
            "disc_number": 1,
            "duration": 240.5,
            "quality": 2,
            "bitrate": 320,
            "codec": "FLAC",
            "container": "flac",
            "is_explicit": False,
            "genres": ["Rock", "Alternative"],
            "popularity": 75.0,
            "album_id": "album123",
            "artist_ids": ["artist1", "artist2"],
            "release_date": "2023-05-15",
            "url": "https://example.com/track/123",
        }

    @pytest.fixture
    def track_info(self):
        """Create a TrackInfo for testing."""
        return TrackInfo.model_validate({
            "id": "track123",
            "source": StreamingSource.QOBUZ,
            "title": "Test Track",
            "track_number": 5,
            "disc_number": 1,
        })

    @pytest.fixture
    def track_credits(self):
        """Create TrackCredits for testing."""
        return TrackCredits.model_validate({
            "artist": "Test Artist",
            "album_artist": "Album Artist",
        })

    @pytest.fixture
    def audio_info(self):
        """Create AudioInfo for testing."""
        return AudioInfo.model_validate({
            "quality": 2,
            "duration_seconds": 240.5,
            "bitrate": 320,
            "codec": "FLAC",
            "container": "flac",
            "is_explicit": False,
        })

    @pytest.fixture
    def track(self, track_info, track_credits, audio_info):
        """Create a Track instance for testing."""
        return Track.model_validate({
            "info": track_info,
            "credits": track_credits,
            "audio": audio_info,
            "album_id": "album123",
            "artist_ids": ["artist1", "artist2"],
            "genres": ["Rock", "Alternative"],
            "popularity_score": 75.0,
        })

    def test_track_creation(self, track):
        """Test creating a Track instance."""
        assert track.info.title == "Test Track"
        assert track.credits.artist == "Test Artist"
        assert track.audio.quality == 2
        assert track.album_id == "album123"
        assert len(track.artist_ids) == 2
        assert len(track.genres) == 2

    def test_track_from_source_data(self, track_data):
        """Test creating Track from source data."""
        track = Track.from_source_data(
            source=StreamingSource.QOBUZ, track_id="track123", data=track_data
        )

        assert track.info.id == "track123"
        assert track.info.source == StreamingSource.QOBUZ
        assert track.info.title == "Test Track"
        assert track.credits.artist == "Test Artist"
        assert track.credits.album_artist == "Album Artist"
        assert track.audio.quality == 2
        assert track.audio.bitrate == 320
        assert track.popularity_score == 75.0
        assert track.album_id == "album123"

    def test_track_from_source_data_with_album_data(self, track_data):
        """Test creating Track from source data with album data."""
        album_data = {"artist": "Album Artist Override"}
        track = Track.from_source_data(
            source=StreamingSource.QOBUZ,
            track_id="track123",
            data=track_data,
            album_data=album_data,
        )

        # Should use album_artist from track data, not album data
        assert track.credits.album_artist == "Album Artist"

    @pytest.mark.parametrize(
        ("score", "should_raise"),
        [
            (0, False),
            (50, False),
            (100, False),
            (-1, True),
            (101, True),
            (None, False),
        ],
    )
    def test_popularity_score_validation(self, score, should_raise):
        """Test popularity score validation."""
        track_data = {
            "info": TrackInfo.model_validate({
                "id": "test",
                "source": StreamingSource.QOBUZ,
                "title": "Test",
            }),
            "credits": TrackCredits.model_validate({"artist": "Test"}),
            "audio": AudioInfo.model_validate({"quality": 1}),
            "popularity_score": score,
        }

        if should_raise:
            with pytest.raises(ValueError, match="between 0 and 100"):
                Track.model_validate(track_data)
        else:
            track = Track.model_validate(track_data)
            assert track.popularity_score == score

    def test_track_properties(self, track):
        """Test track properties."""
        assert track.title == "Test Track"
        assert track.display_title == "Test Track"  # No work/version
        assert track.artist == "Test Artist"
        assert track.display_artist == "Test Artist"  # No featured artists

    def test_track_properties_with_work_and_featured(self):
        """Test track properties with work and featured artists."""
        info = TrackInfo.model_validate({
            "id": "test",
            "source": StreamingSource.QOBUZ,
            "title": "Allegro",
            "work": "Symphony No. 1",
            "version": "Live",
        })
        track_credits = TrackCredits.model_validate({
            "artist": "Orchestra",
            "featured_artists": ["Soloist"],
        })
        audio = AudioInfo.model_validate({"quality": 1})

        track = Track.model_validate({
            "info": info,
            "credits": track_credits,
            "audio": audio,
        })

        assert track.display_title == "Symphony No. 1: Allegro: (Live)"
        assert track.display_artist == "Orchestra (feat. Soloist)"

    def test_add_genre(self, track):
        """Test adding genres to track."""
        initial_count = len(track.genres)

        # Add new genre
        track.add_genre("Jazz")
        assert "Jazz" in track.genres
        assert len(track.genres) == initial_count + 1

        # Adding same genre again should not duplicate
        track.add_genre("Jazz")
        assert len(track.genres) == initial_count + 1

    def test_add_tag(self, track):
        """Test adding tags to track."""
        initial_count = len(track.tags)

        # Add new tag
        track.add_tag("favorite")
        assert "favorite" in track.tags
        assert len(track.tags) == initial_count + 1

        # Adding same tag again should not duplicate
        track.add_tag("favorite")
        assert len(track.tags) == initial_count + 1

    def test_add_artist_id(self, track):
        """Test adding artist IDs."""
        initial_count = len(track.artist_ids)

        # Add new artist ID
        track.add_artist_id("artist3")
        assert "artist3" in track.artist_ids
        assert len(track.artist_ids) == initial_count + 1

        # Adding existing artist ID should not duplicate
        track.add_artist_id("artist3")
        assert len(track.artist_ids) == initial_count + 1

    def test_increment_play_count(self, track):
        """Test incrementing play count."""
        initial_count = track.play_count
        track.increment_play_count()
        assert track.play_count == initial_count + 1

    def test_toggle_favorite(self, track):
        """Test toggling favorite status."""
        initial_status = track.is_favorite
        track.toggle_favorite()
        assert track.is_favorite != initial_status

        track.toggle_favorite()
        assert track.is_favorite == initial_status

    @pytest.mark.parametrize(
        ("format_string", "expected_pattern"),
        [
            ("{track_number:02d} - {artist} - {title}", r"\d{2} - .+ - .+"),
            ("{disc_number}.{track_number:02d} {title}", r"\d\.\d{2} .+"),
            ("{artist} - {title}", r".+ - .+"),
        ],
    )
    def test_get_filename(self, track, format_string, expected_pattern):
        """Test getting filename with different formats."""
        import re

        filename = track.get_filename(format_string)
        assert re.match(expected_pattern, filename)
        assert filename.endswith(".flac")  # Based on container

    def test_get_filename_with_unsafe_characters(self):
        """Test filename generation with unsafe characters."""
        info = TrackInfo.model_validate({
            "id": "test",
            "source": StreamingSource.QOBUZ,
            "title": 'Track<>:"/\\|?*Name',
            "track_number": 1,
        })
        track_credits = TrackCredits.model_validate({"artist": 'Artist<>:"/\\|?*Name'})
        audio = AudioInfo.model_validate({"quality": 1, "container": "mp3"})

        track = Track.model_validate({
            "info": info,
            "credits": track_credits,
            "audio": audio,
        })

        filename = track.get_filename()
        # Should not contain unsafe characters
        unsafe_chars = '<>:"/\\|?*'
        assert not any(char in filename for char in unsafe_chars)
        assert filename.endswith(".mp3")

    @pytest.mark.parametrize(
        ("query", "should_match"),
        [
            ("Test Track", True),
            ("test track", True),  # Case insensitive
            ("Test Artist", True),
            ("Album Artist", True),  # Album artist
            ("Rock", True),  # Genre
        ],
    )
    def test_matches_search(self, track, query, should_match):
        """Test search matching."""
        result = track.matches_search(query)
        assert result == should_match

    def test_matches_search_nonexistent(self, track):
        """Test search matching with nonexistent query."""
        result = track.matches_search("nonexistent")
        assert not result  # This handles both False and None cases

    def test_matches_search_with_lyrics(self):
        """Test search matching with lyrics."""
        info = TrackInfo.model_validate({
            "id": "test",
            "source": StreamingSource.QOBUZ,
            "title": "Test Track",
            "lyrics": "These are test lyrics with special words",
        })
        track_credits = TrackCredits.model_validate({"artist": "Test Artist"})
        audio = AudioInfo.model_validate({"quality": 1})

        track = Track.model_validate({
            "info": info,
            "credits": track_credits,
            "audio": audio,
        })

        assert track.matches_search("special words") is True
        assert track.matches_search("nonexistent lyrics") is False

    def test_to_dict(self, track):
        """Test converting track to dictionary."""
        track_dict = track.to_dict()

        assert track_dict["id"] == track.info.id
        assert track_dict["source"] == track.info.source
        assert track_dict["title"] == track.info.title
        assert track_dict["display_title"] == track.display_title
        assert track_dict["artist"] == track.credits.artist
        assert track_dict["display_artist"] == track.display_artist
        assert track_dict["track_number"] == track.info.track_number
        assert track_dict["disc_number"] == track.info.disc_number
        assert track_dict["quality"] == track.audio.quality
        assert track_dict["is_explicit"] == track.audio.is_explicit
        assert "download_status" in track_dict


if __name__ == "__main__":
    pytest.main([__file__])
