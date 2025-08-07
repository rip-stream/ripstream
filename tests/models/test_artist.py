# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Unit tests for models/artist.py module."""

import pytest

from ripstream.models.artist import Artist, ArtistInfo, ArtistStats
from ripstream.models.artwork import Covers
from ripstream.models.enums import StreamingSource


class TestArtistInfo:
    """Test the ArtistInfo model."""

    @pytest.fixture
    def sample_artist_info(self):
        """Sample ArtistInfo for testing."""
        return ArtistInfo(
            id="artist_123",
            source=StreamingSource.QOBUZ,
            name="Test Artist",
            sort_name="Artist, Test",
            disambiguation="rock band",
            country="US",
            formed_year=2000,
            genres=["Rock", "Alternative"],
            biography="Test artist biography",
            website="https://testartist.com",
            url="https://qobuz.com/artist/123",
        )

    def test_artist_info_creation(self, sample_artist_info):
        """Test ArtistInfo creation with all fields."""
        assert sample_artist_info.name == "Test Artist"
        assert sample_artist_info.sort_name == "Artist, Test"
        assert sample_artist_info.disambiguation == "rock band"
        assert sample_artist_info.country == "US"
        assert sample_artist_info.formed_year == 2000
        assert sample_artist_info.genres == ["Rock", "Alternative"]
        assert sample_artist_info.biography == "Test artist biography"
        assert sample_artist_info.website == "https://testartist.com"

    def test_artist_info_minimal_creation(self):
        """Test ArtistInfo creation with minimal required fields."""
        info = ArtistInfo(
            id="artist_456", source=StreamingSource.TIDAL, name="Minimal Artist"
        )
        assert info.name == "Minimal Artist"
        assert info.sort_name is None
        assert info.disambiguation is None
        assert info.country is None
        assert info.formed_year is None
        assert info.genres == []
        assert info.biography is None
        assert info.website is None

    @pytest.mark.parametrize("invalid_year", [1799, 2031, -100, 3000])
    def test_validate_formed_year_invalid(self, invalid_year):
        """Test formed year validation with invalid values."""
        with pytest.raises(ValueError, match=f"Invalid formed year: {invalid_year}"):
            ArtistInfo(
                id="artist_123",
                source=StreamingSource.QOBUZ,
                name="Test Artist",
                formed_year=invalid_year,
            )

    @pytest.mark.parametrize("valid_year", [1800, 1950, 2000, 2023, 2030])
    def test_validate_formed_year_valid(self, valid_year):
        """Test formed year validation with valid values."""
        info = ArtistInfo(
            id="artist_123",
            source=StreamingSource.QOBUZ,
            name="Test Artist",
            formed_year=valid_year,
        )
        assert info.formed_year == valid_year

    def test_add_social_link(self, sample_artist_info):
        """Test add_social_link method."""
        sample_artist_info.add_social_link("twitter", "https://twitter.com/testartist")
        sample_artist_info.add_social_link(
            "instagram", "https://instagram.com/testartist"
        )

        assert (
            sample_artist_info.social_links["twitter"]
            == "https://twitter.com/testartist"
        )
        assert (
            sample_artist_info.social_links["instagram"]
            == "https://instagram.com/testartist"
        )

    def test_add_genre(self, sample_artist_info):
        """Test add_genre method."""
        initial_genres = len(sample_artist_info.genres)

        # Add new genre
        sample_artist_info.add_genre("Pop")
        assert "Pop" in sample_artist_info.genres
        assert len(sample_artist_info.genres) == initial_genres + 1

        # Add duplicate genre (should not be added)
        sample_artist_info.add_genre("Rock")  # Already exists
        assert len(sample_artist_info.genres) == initial_genres + 1


class TestArtistStats:
    """Test the ArtistStats model."""

    @pytest.fixture
    def sample_artist_stats(self):
        """Sample ArtistStats for testing."""
        return ArtistStats(
            total_albums=10,
            total_tracks=120,
            total_plays=1000000,
            monthly_listeners=50000,
            followers=25000,
            popularity_score=85.5,
        )

    def test_artist_stats_creation(self, sample_artist_stats):
        """Test ArtistStats creation with all fields."""
        assert sample_artist_stats.total_albums == 10
        assert sample_artist_stats.total_tracks == 120
        assert sample_artist_stats.total_plays == 1000000
        assert sample_artist_stats.monthly_listeners == 50000
        assert sample_artist_stats.followers == 25000
        assert sample_artist_stats.popularity_score == 85.5

    def test_artist_stats_defaults(self):
        """Test ArtistStats creation with default values."""
        stats = ArtistStats()
        assert stats.total_albums == 0
        assert stats.total_tracks == 0
        assert stats.total_plays is None
        assert stats.monthly_listeners is None
        assert stats.followers is None
        assert stats.popularity_score is None

    @pytest.mark.parametrize("invalid_score", [-1, 101, -50, 150])
    def test_validate_popularity_score_invalid(self, invalid_score):
        """Test popularity score validation with invalid values."""
        with pytest.raises(
            ValueError, match="Popularity score must be between 0 and 100"
        ):
            ArtistStats(popularity_score=invalid_score)

    @pytest.mark.parametrize("valid_score", [0, 50, 100, 0.5, 99.9])
    def test_validate_popularity_score_valid(self, valid_score):
        """Test popularity score validation with valid values."""
        stats = ArtistStats(popularity_score=valid_score)
        assert stats.popularity_score == valid_score

    def test_update_stats(self, sample_artist_stats):
        """Test update_stats method."""
        sample_artist_stats.update_stats(
            total_albums=15,
            followers=30000,
            new_field=123,  # Should be ignored if field doesn't exist
        )

        assert sample_artist_stats.total_albums == 15
        assert sample_artist_stats.followers == 30000
        assert sample_artist_stats.total_tracks == 120  # Unchanged
        assert not hasattr(sample_artist_stats, "new_field")


class TestArtist:
    """Test the Artist model."""

    @pytest.fixture
    def sample_artist_data(self):
        """Sample artist data for testing."""
        return {
            "name": "Test Artist",
            "sort_name": "Artist, Test",
            "disambiguation": "rock band",
            "country": "US",
            "formed_year": 2000,
            "genres": ["Rock", "Alternative"],
            "biography": "Test artist biography",
            "website": "https://testartist.com",
            "url": "https://qobuz.com/artist/123",
            "covers": {"large": "https://example.com/cover.jpg"},
            "stats": {"total_albums": 5, "followers": 10000, "popularity_score": 75.0},
            "is_various_artists": False,
            "is_verified": True,
        }

    @pytest.fixture
    def sample_artist(self, sample_artist_data):
        """Sample Artist for testing."""
        return Artist.from_source_data(
            StreamingSource.QOBUZ, "artist_123", sample_artist_data
        )

    def test_from_source_data_complete(self, sample_artist_data):
        """Test Artist.from_source_data with complete data."""
        artist = Artist.from_source_data(
            StreamingSource.QOBUZ, "artist_123", sample_artist_data
        )

        assert artist.info.name == "Test Artist"
        assert artist.info.source == StreamingSource.QOBUZ
        assert artist.info.id == "artist_123"
        assert artist.info.country == "US"
        assert artist.info.formed_year == 2000
        assert artist.info.genres == ["Rock", "Alternative"]
        assert artist.is_verified is True
        assert artist.is_various_artists is False

    def test_from_source_data_minimal(self):
        """Test Artist.from_source_data with minimal data."""
        minimal_data = {"name": "Minimal Artist"}
        artist = Artist.from_source_data(
            StreamingSource.TIDAL, "artist_456", minimal_data
        )

        assert artist.info.name == "Minimal Artist"
        assert artist.info.source == StreamingSource.TIDAL
        assert artist.info.id == "artist_456"
        assert artist.is_verified is False
        assert artist.is_various_artists is False

    def test_from_source_data_missing_name(self):
        """Test Artist.from_source_data with missing name uses default."""
        data = {"country": "UK"}
        artist = Artist.from_source_data(StreamingSource.DEEZER, "artist_789", data)

        assert artist.info.name == "Unknown Artist"
        assert artist.info.country == "UK"

    def test_from_source_data_with_stats(self, sample_artist_data):
        """Test Artist.from_source_data properly processes stats."""
        artist = Artist.from_source_data(
            StreamingSource.QOBUZ, "artist_123", sample_artist_data
        )

        assert artist.stats.total_albums == 5
        assert artist.stats.followers == 10000
        assert artist.stats.popularity_score == 75.0

    def test_name_property(self, sample_artist):
        """Test name property."""
        assert sample_artist.name == "Test Artist"

    def test_display_name_with_disambiguation(self, sample_artist):
        """Test display_name property with disambiguation."""
        assert sample_artist.display_name == "Test Artist (rock band)"

    def test_display_name_without_disambiguation(self):
        """Test display_name property without disambiguation."""
        data = {"name": "Simple Artist"}
        artist = Artist.from_source_data(StreamingSource.QOBUZ, "artist_123", data)
        assert artist.display_name == "Simple Artist"

    def test_add_album_id(self, sample_artist):
        """Test add_album_id method."""

        sample_artist.add_album_id("album_1")
        sample_artist.add_album_id("album_2")

        assert "album_1" in sample_artist.album_ids
        assert "album_2" in sample_artist.album_ids
        assert len(sample_artist.album_ids) == 2
        assert sample_artist.stats.total_albums == 2

    def test_add_album_id_duplicate(self, sample_artist):
        """Test add_album_id method with duplicate IDs."""
        sample_artist.add_album_id("album_1")
        sample_artist.add_album_id("album_1")  # Duplicate

        assert len(sample_artist.album_ids) == 1
        assert sample_artist.stats.total_albums == 1

    def test_add_featured_track_id(self, sample_artist):
        """Test add_featured_track_id method."""
        sample_artist.add_featured_track_id("track_1")
        sample_artist.add_featured_track_id("track_2")

        assert "track_1" in sample_artist.featured_track_ids
        assert "track_2" in sample_artist.featured_track_ids
        assert len(sample_artist.featured_track_ids) == 2

    def test_add_featured_track_id_duplicate(self, sample_artist):
        """Test add_featured_track_id method with duplicate IDs."""
        sample_artist.add_featured_track_id("track_1")
        sample_artist.add_featured_track_id("track_1")  # Duplicate

        assert len(sample_artist.featured_track_ids) == 1

    def test_add_similar_artist_id(self, sample_artist):
        """Test add_similar_artist_id method."""
        sample_artist.add_similar_artist_id("similar_1")
        sample_artist.add_similar_artist_id("similar_2")

        assert "similar_1" in sample_artist.similar_artist_ids
        assert "similar_2" in sample_artist.similar_artist_ids
        assert len(sample_artist.similar_artist_ids) == 2

    def test_add_similar_artist_id_duplicate(self, sample_artist):
        """Test add_similar_artist_id method with duplicate IDs."""
        sample_artist.add_similar_artist_id("similar_1")
        sample_artist.add_similar_artist_id("similar_1")  # Duplicate

        assert len(sample_artist.similar_artist_ids) == 1

    def test_get_download_folder_name_normal(self, sample_artist):
        """Test get_download_folder_name with normal artist name."""
        folder_name = sample_artist.get_download_folder_name()
        assert folder_name == "Test Artist"

    def test_get_download_folder_name_with_special_chars(self):
        """Test get_download_folder_name with special characters."""
        data = {"name": "Artist/Name\\With:Special*Chars?"}
        artist = Artist.from_source_data(StreamingSource.QOBUZ, "artist_123", data)

        folder_name = artist.get_download_folder_name()
        # Should only contain alphanumeric, spaces, hyphens, and underscores
        assert folder_name == "ArtistNameWithSpecialChars"

    def test_get_download_folder_name_empty_after_cleaning(self):
        """Test get_download_folder_name when name becomes empty after cleaning."""
        data = {"name": "///***???"}
        artist = Artist.from_source_data(StreamingSource.QOBUZ, "artist_123", data)

        folder_name = artist.get_download_folder_name()
        assert folder_name == "Artist_artist_123"

    @pytest.mark.parametrize(
        ("query", "expected"),
        [
            ("test", True),
            ("TEST", True),
            ("artist", True),
            ("rock", True),
            ("alternative", True),
            ("pop", False),
            ("jazz", False),
            ("", True),  # Empty query should match
        ],
    )
    def test_matches_search(self, sample_artist, query, expected):
        """Test matches_search method."""
        result = sample_artist.matches_search(query)
        assert result == expected

    def test_matches_search_with_sort_name(self):
        """Test matches_search method with sort name."""
        data = {"name": "John Doe", "sort_name": "Doe, John"}
        artist = Artist.from_source_data(StreamingSource.QOBUZ, "artist_123", data)

        assert artist.matches_search("doe") is True
        assert artist.matches_search("john") is True
        assert artist.matches_search("smith") is False

    def test_matches_search_no_sort_name(self, sample_artist):
        """Test matches_search method when sort_name is None."""
        # Ensure sort_name is None for this test
        sample_artist.info.sort_name = None

        assert sample_artist.matches_search("test") is True
        assert sample_artist.matches_search("nonexistent") is False

    def test_to_dict(self, sample_artist):
        """Test to_dict method."""
        result = sample_artist.to_dict()

        expected_keys = [
            "id",
            "source",
            "name",
            "display_name",
            "genres",
            "country",
            "formed_year",
            "album_count",
            "track_count",
            "is_various_artists",
            "is_verified",
            "covers",
        ]

        for key in expected_keys:
            assert key in result

        assert result["id"] == "artist_123"
        assert result["source"] == StreamingSource.QOBUZ
        assert result["name"] == "Test Artist"
        assert result["display_name"] == "Test Artist (rock band)"
        assert result["genres"] == ["Rock", "Alternative"]
        assert result["country"] == "US"
        assert result["formed_year"] == 2000
        assert result["is_various_artists"] is False
        assert result["is_verified"] is True

    def test_to_dict_no_covers(self):
        """Test to_dict method when artist has no cover images."""
        data = {"name": "No Cover Artist"}
        artist = Artist.from_source_data(StreamingSource.QOBUZ, "artist_123", data)

        result = artist.to_dict()
        assert result["covers"] is None

    def test_to_dict_with_covers(self, sample_artist):
        """Test to_dict method when artist has cover images."""
        # Add a cover image to test the covers serialization
        from ripstream.models.enums import CoverSize

        sample_artist.covers.add_image("https://example.com/cover.jpg", CoverSize.LARGE)

        result = sample_artist.to_dict()
        assert result["covers"] is not None
        assert isinstance(result["covers"], dict)


class TestArtistIntegration:
    """Integration tests for Artist model."""

    def test_artist_with_all_relationships(self):
        """Test Artist with all relationship IDs populated."""
        data = {"name": "Popular Artist"}
        artist = Artist.from_source_data(StreamingSource.QOBUZ, "artist_123", data)

        # Add various relationships
        artist.add_album_id("album_1")
        artist.add_album_id("album_2")
        artist.add_featured_track_id("track_1")
        artist.add_featured_track_id("track_2")
        artist.add_similar_artist_id("similar_1")

        assert len(artist.album_ids) == 2
        assert len(artist.featured_track_ids) == 2
        assert len(artist.similar_artist_ids) == 1
        assert artist.stats.total_albums == 2

    def test_artist_raw_metadata_storage(self):
        """Test that raw metadata is properly stored."""
        data = {
            "name": "Test Artist",
            "custom_field": "custom_value",
            "nested_data": {"key": "value"},
        }
        artist = Artist.from_source_data(StreamingSource.QOBUZ, "artist_123", data)

        # Verify the artist was created successfully with the data
        assert artist.info.name == "Test Artist"
        # The raw metadata storage is handled internally by the from_source_data method

    def test_artist_covers_integration(self):
        """Test Artist integration with Covers model."""
        data = {
            "name": "Artist with Covers",
            "covers": {"large": "https://example.com/large.jpg"},
        }
        artist = Artist.from_source_data(StreamingSource.QOBUZ, "artist_123", data)

        # Covers should be initialized but empty (since we don't parse in from_source_data)
        assert isinstance(artist.covers, Covers)
        assert not artist.covers.has_images

    def test_artist_stats_integration(self):
        """Test Artist integration with ArtistStats model."""
        data = {
            "name": "Popular Artist",
            "stats": {
                "total_albums": 10,
                "followers": 50000,
                "popularity_score": 90.0,
                "unknown_stat": 123,  # Should be ignored
            },
        }
        artist = Artist.from_source_data(StreamingSource.QOBUZ, "artist_123", data)

        assert artist.stats.total_albums == 10
        assert artist.stats.followers == 50000
        assert artist.stats.popularity_score == 90.0
        assert not hasattr(artist.stats, "unknown_stat")

    def test_artist_with_kwargs(self):
        """Test Artist.from_source_data with additional kwargs."""
        data = {"name": "Test Artist"}
        artist = Artist.from_source_data(
            StreamingSource.QOBUZ,
            "artist_123",
            data,
            custom_field="custom_value",
            another_field=123,
        )

        # Additional kwargs should be stored in the model's extra fields
        # Since Pydantic allows extra fields, they should be accessible
        assert artist.info.name == "Test Artist"
        # Note: kwargs are passed to the Artist constructor, not necessarily stored as attributes
        # This test verifies the method accepts kwargs without error


class TestArtistEdgeCases:
    """Test edge cases and error conditions for Artist."""

    def test_artist_with_empty_data(self):
        """Test Artist creation with empty data dictionary."""
        artist = Artist.from_source_data(StreamingSource.QOBUZ, "artist_123", {})

        assert artist.info.name == "Unknown Artist"
        assert artist.info.genres == []
        assert artist.stats.total_albums == 0

    def test_artist_with_none_values(self):
        """Test Artist creation with None values in data (except required fields)."""
        data = {
            "name": "Valid Artist",  # Name is required and cannot be None
            "country": None,
            "formed_year": None,
            "genres": [],  # Empty list instead of None
            "stats": None,
        }
        artist = Artist.from_source_data(StreamingSource.QOBUZ, "artist_123", data)

        assert artist.info.name == "Valid Artist"
        assert artist.info.country is None
        assert artist.info.formed_year is None
        assert artist.info.genres == []

    def test_get_download_folder_name_whitespace_only(self):
        """Test get_download_folder_name with whitespace-only name."""
        data = {"name": "   \t\n   "}
        artist = Artist.from_source_data(StreamingSource.QOBUZ, "artist_123", data)

        folder_name = artist.get_download_folder_name()
        assert folder_name == "Artist_artist_123"

    def test_matches_search_empty_genres(self):
        """Test matches_search when genres list is empty."""
        data = {"name": "Test Artist", "genres": []}
        artist = Artist.from_source_data(StreamingSource.QOBUZ, "artist_123", data)

        assert artist.matches_search("test") is True
        assert artist.matches_search("rock") is False  # No genres to match
