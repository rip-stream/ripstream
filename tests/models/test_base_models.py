# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Tests for base model classes."""

from datetime import UTC, datetime
from uuid import UUID

import pytest

from ripstream.models.base import (
    DownloadableMedia,
    MediaInfo,
    MetadataContainer,
    MetadataValue,
    RipStreamBaseModel,
    SearchableMedia,
)
from ripstream.models.enums import DownloadStatus, StreamingSource


class TestRipStreamBaseModel:
    """Test the RipStreamBaseModel base class."""

    def test_ripstream_base_model_creation(self):
        """Test creating a RipStreamBaseModel instance."""
        model = RipStreamBaseModel()
        assert model is not None

    def test_ripstream_base_model_config(self):
        """Test that RipStreamBaseModel has the correct model configuration."""
        model = RipStreamBaseModel()
        assert hasattr(model, "model_config")
        assert isinstance(model.model_config, dict)


class TestMediaInfo:
    """Test the MediaInfo class."""

    @pytest.fixture
    def media_info(self):
        """Create a basic MediaInfo instance."""
        return MediaInfo(
            id="test_id",
            source=StreamingSource.QOBUZ,
            url="https://example.com/test",
        )

    def test_media_info_creation(self, media_info):
        """Test creating a MediaInfo instance."""
        assert media_info.id == "test_id"
        assert media_info.source == StreamingSource.QOBUZ
        assert media_info.url == "https://example.com/test"
        assert isinstance(media_info.created_at, datetime)
        assert isinstance(media_info.updated_at, datetime)

    def test_media_info_defaults(self):
        """Test MediaInfo with default values."""
        media_info = MediaInfo(
            id="test_id",
            source=StreamingSource.QOBUZ,
            url=None,
        )
        assert media_info.url is None
        assert isinstance(media_info.created_at, datetime)
        assert isinstance(media_info.updated_at, datetime)

    def test_media_info_update_timestamp(self, media_info):
        """Test updating the timestamp."""
        original_updated_at = media_info.updated_at

        # Wait a moment to ensure time difference
        import time

        time.sleep(0.001)

        media_info.update_timestamp()

        assert media_info.updated_at > original_updated_at

    def test_media_info_timestamps_utc(self, media_info):
        """Test that timestamps are in UTC."""
        assert media_info.created_at.tzinfo == UTC
        assert media_info.updated_at.tzinfo == UTC


class TestDownloadableMedia:
    """Test the DownloadableMedia class."""

    @pytest.fixture
    def downloadable_media(self):
        """Create a basic DownloadableMedia instance."""
        return DownloadableMedia()

    def test_downloadable_media_creation(self, downloadable_media):
        """Test creating a DownloadableMedia instance."""
        assert isinstance(downloadable_media.download_id, UUID)
        assert downloadable_media.status == DownloadStatus.PENDING
        assert downloadable_media.download_path is None
        assert downloadable_media.error_message is None
        assert downloadable_media.download_started_at is None
        assert downloadable_media.download_completed_at is None
        assert downloadable_media.retry_count == 0

    def test_downloadable_media_mark_downloading(self, downloadable_media):
        """Test marking media as downloading."""
        downloadable_media.mark_downloading()

        assert downloadable_media.status == DownloadStatus.DOWNLOADING
        assert downloadable_media.download_started_at is not None
        assert downloadable_media.error_message is None
        assert downloadable_media.download_started_at.tzinfo == UTC

    def test_downloadable_media_mark_completed(self, downloadable_media):
        """Test marking media as completed."""
        download_path = "/path/to/file.mp3"
        downloadable_media.mark_completed(download_path)

        assert downloadable_media.status == DownloadStatus.COMPLETED
        assert downloadable_media.download_path == download_path
        assert downloadable_media.download_completed_at is not None
        assert downloadable_media.error_message is None
        assert downloadable_media.download_completed_at.tzinfo == UTC

    def test_downloadable_media_mark_failed(self, downloadable_media):
        """Test marking media as failed."""
        error_message = "Network error"
        original_retry_count = downloadable_media.retry_count

        downloadable_media.mark_failed(error_message)

        assert downloadable_media.status == DownloadStatus.FAILED
        assert downloadable_media.error_message == error_message
        assert downloadable_media.retry_count == original_retry_count + 1

    def test_downloadable_media_mark_skipped(self, downloadable_media):
        """Test marking media as skipped."""
        reason = "File already exists"
        downloadable_media.mark_skipped(reason)

        assert downloadable_media.status == DownloadStatus.SKIPPED
        assert downloadable_media.error_message == reason

    def test_downloadable_media_is_downloaded_property(self, downloadable_media):
        """Test the is_downloaded property."""
        assert downloadable_media.is_downloaded is False

        downloadable_media.status = DownloadStatus.COMPLETED
        assert downloadable_media.is_downloaded is True

        downloadable_media.status = DownloadStatus.FAILED
        assert downloadable_media.is_downloaded is False

    def test_downloadable_media_can_retry_property(self, downloadable_media):
        """Test the can_retry property."""
        # Initially not failed, so can't retry
        assert downloadable_media.can_retry is False

        # Mark as failed, should be able to retry
        downloadable_media.mark_failed("Error")
        assert downloadable_media.can_retry is True

        # After 3 retries, should not be able to retry
        downloadable_media.retry_count = 3
        assert downloadable_media.can_retry is False

        # If not failed, should not be able to retry
        downloadable_media.status = DownloadStatus.PENDING
        assert downloadable_media.can_retry is False

    def test_downloadable_media_multiple_failures(self, downloadable_media):
        """Test multiple failure scenarios."""
        # First failure
        downloadable_media.mark_failed("Error 1")
        assert downloadable_media.retry_count == 1
        assert downloadable_media.can_retry is True

        # Second failure
        downloadable_media.mark_failed("Error 2")
        assert downloadable_media.retry_count == 2
        assert downloadable_media.can_retry is True

        # Third failure
        downloadable_media.mark_failed("Error 3")
        assert downloadable_media.retry_count == 3
        assert downloadable_media.can_retry is False

    def test_downloadable_media_status_transitions(self, downloadable_media):
        """Test various status transitions."""
        # Start with pending
        assert downloadable_media.status == DownloadStatus.PENDING

        # Mark as downloading
        downloadable_media.mark_downloading()
        assert downloadable_media.status == DownloadStatus.DOWNLOADING

        # Mark as completed
        downloadable_media.mark_completed("/path/to/file.mp3")
        assert downloadable_media.status == DownloadStatus.COMPLETED

        # Reset and test failure
        downloadable_media.status = DownloadStatus.PENDING
        downloadable_media.mark_failed("Error")
        assert downloadable_media.status == DownloadStatus.FAILED


class TestSearchableMedia:
    """Test the SearchableMedia class."""

    @pytest.fixture
    def searchable_media(self):
        """Create a basic SearchableMedia instance."""
        return SearchableMedia()

    def test_searchable_media_creation(self, searchable_media):
        """Test creating a SearchableMedia instance."""
        assert searchable_media.search_query is None
        assert searchable_media.search_rank is None
        assert searchable_media.relevance_score is None

    def test_searchable_media_set_search_info(self, searchable_media):
        """Test setting search information."""
        query = "test query"
        rank = 5
        score = 0.85

        searchable_media.set_search_info(query, rank, score)

        assert searchable_media.search_query == query
        assert searchable_media.search_rank == rank
        assert searchable_media.relevance_score == score

    def test_searchable_media_set_search_info_no_score(self, searchable_media):
        """Test setting search information without score."""
        query = "test query"
        rank = 3

        searchable_media.set_search_info(query, rank)

        assert searchable_media.search_query == query
        assert searchable_media.search_rank == rank
        assert searchable_media.relevance_score is None

    def test_searchable_media_update_search_info(self, searchable_media):
        """Test updating search information."""
        # Set initial search info
        searchable_media.set_search_info("initial query", 1, 0.5)

        # Update with new info
        searchable_media.set_search_info("updated query", 2, 0.8)

        assert searchable_media.search_query == "updated query"
        assert searchable_media.search_rank == 2
        assert searchable_media.relevance_score == 0.8


class TestMetadataContainer:
    """Test the MetadataContainer class."""

    @pytest.fixture
    def metadata_container(self):
        """Create a basic MetadataContainer instance."""
        return MetadataContainer()

    def test_metadata_container_creation(self, metadata_container):
        """Test creating a MetadataContainer instance."""
        assert metadata_container.raw_metadata == {}
        assert metadata_container.custom_metadata == {}

    def test_metadata_container_add_raw_metadata(self, metadata_container):
        """Test adding raw metadata."""
        metadata_container.add_raw_metadata("title", "Test Title")
        metadata_container.add_raw_metadata("artist", "Test Artist")
        metadata_container.add_raw_metadata("year", 2023)
        metadata_container.add_raw_metadata("genres", ["rock", "pop"])

        assert metadata_container.raw_metadata["title"] == "Test Title"
        assert metadata_container.raw_metadata["artist"] == "Test Artist"
        assert metadata_container.raw_metadata["year"] == 2023
        assert metadata_container.raw_metadata["genres"] == ["rock", "pop"]

    def test_metadata_container_add_custom_metadata(self, metadata_container):
        """Test adding custom metadata."""
        metadata_container.add_custom_metadata("rating", 5)
        metadata_container.add_custom_metadata("notes", "Great album")
        metadata_container.add_custom_metadata("tags", ["favorite", "rock"])

        assert metadata_container.custom_metadata["rating"] == 5
        assert metadata_container.custom_metadata["notes"] == "Great album"
        assert metadata_container.custom_metadata["tags"] == ["favorite", "rock"]

    def test_metadata_container_get_metadata_custom_first(self, metadata_container):
        """Test getting metadata with custom taking precedence."""
        metadata_container.add_raw_metadata("title", "Raw Title")
        metadata_container.add_custom_metadata("title", "Custom Title")

        result = metadata_container.get_metadata("title")
        assert result == "Custom Title"

    def test_metadata_container_get_metadata_raw_fallback(self, metadata_container):
        """Test getting metadata with raw fallback."""
        metadata_container.add_raw_metadata("artist", "Raw Artist")

        result = metadata_container.get_metadata("artist")
        assert result == "Raw Artist"

    def test_metadata_container_get_metadata_default(self, metadata_container):
        """Test getting metadata with default value."""
        result = metadata_container.get_metadata("unknown", "default_value")
        assert result == "default_value"

    def test_metadata_container_get_metadata_none_default(self, metadata_container):
        """Test getting metadata with None default."""
        result = metadata_container.get_metadata("unknown")
        assert result is None

    def test_metadata_container_overwrite_metadata(self, metadata_container):
        """Test overwriting existing metadata."""
        metadata_container.add_raw_metadata("title", "Original Title")
        metadata_container.add_raw_metadata("title", "Updated Title")

        assert metadata_container.raw_metadata["title"] == "Updated Title"

    def test_metadata_container_complex_metadata_types(self, metadata_container):
        """Test complex metadata types."""
        complex_metadata = {
            "nested": {"key": "value"},
            "list": [1, 2, 3],
            "boolean": True,
            "none": None,
        }

        for key, value in complex_metadata.items():
            metadata_container.add_raw_metadata(key, value)

        for key, expected_value in complex_metadata.items():
            result = metadata_container.get_metadata(key)
            assert result == expected_value

    def test_metadata_container_empty_strings(self, metadata_container):
        """Test handling empty strings."""
        metadata_container.add_raw_metadata("empty", "")
        metadata_container.add_custom_metadata("custom_empty", "")

        assert metadata_container.get_metadata("empty") == ""
        assert metadata_container.get_metadata("custom_empty") == ""

    def test_metadata_container_zero_values(self, metadata_container):
        """Test handling zero values."""
        metadata_container.add_raw_metadata("zero_int", 0)
        metadata_container.add_raw_metadata("zero_float", 0.0)

        assert metadata_container.get_metadata("zero_int") == 0
        assert metadata_container.get_metadata("zero_float") == 0.0


class TestMetadataValue:
    """Test the MetadataValue type alias."""

    def test_metadata_value_types(self):
        """Test that MetadataValue includes all expected types."""
        # This test ensures the type alias is correctly defined
        from typing import get_args

        # Get the actual types from the union
        metadata_types = get_args(MetadataValue)

        # Check that all expected types are included
        expected_types = {str, int, float, bool, list, dict, type(None)}

        # Convert to sets for easier comparison
        actual_types = set(metadata_types)
        expected_types_set = expected_types

        # Check that all expected types are present
        for expected_type in expected_types_set:
            if expected_type in (list, dict):
                # These are generic types, so we check for their presence differently
                assert any(
                    hasattr(t, "__origin__") and t.__origin__ == expected_type
                    for t in actual_types
                )
            else:
                assert expected_type in actual_types


class TestModelIntegration:
    """Test integration between different model classes."""

    def test_media_info_with_downloadable_media(self):
        """Test combining MediaInfo with DownloadableMedia."""

        class TestMedia(MediaInfo, DownloadableMedia):
            pass

        media = TestMedia(
            id="test_id",
            source=StreamingSource.QOBUZ,
            url=None,
        )

        # Test MediaInfo functionality
        assert media.id == "test_id"
        assert media.source == StreamingSource.QOBUZ

        # Test DownloadableMedia functionality
        assert media.status == DownloadStatus.PENDING
        media.mark_downloading()
        assert media.status == DownloadStatus.DOWNLOADING

    def test_media_info_with_searchable_media(self):
        """Test combining MediaInfo with SearchableMedia."""

        class TestMedia(MediaInfo, SearchableMedia):
            pass

        media = TestMedia(
            id="test_id",
            source=StreamingSource.QOBUZ,
            url=None,
        )

        # Test MediaInfo functionality
        assert media.id == "test_id"

        # Test SearchableMedia functionality
        media.set_search_info("test query", 1, 0.8)
        assert media.search_query == "test query"
        assert media.search_rank == 1
        assert media.relevance_score == 0.8

    def test_metadata_container_with_other_classes(self):
        """Test combining MetadataContainer with other classes."""

        class TestMedia(MediaInfo, MetadataContainer):
            pass

        media = TestMedia(
            id="test_id",
            source=StreamingSource.QOBUZ,
        )

        # Test MediaInfo functionality
        assert media.id == "test_id"

        # Test MetadataContainer functionality
        media.add_raw_metadata("title", "Test Title")
        media.add_custom_metadata("rating", 5)

        assert media.get_metadata("title") == "Test Title"
        assert media.get_metadata("rating") == 5

    def test_complex_inheritance_chain(self):
        """Test a complex inheritance chain with all base classes."""

        class TestMedia(
            MediaInfo, DownloadableMedia, SearchableMedia, MetadataContainer
        ):
            pass

        media = TestMedia(
            id="test_id",
            source=StreamingSource.QOBUZ,
        )

        # Test all functionalities
        assert media.id == "test_id"
        assert media.status == DownloadStatus.PENDING
        assert media.search_query is None
        assert media.raw_metadata == {}

        # Test interactions
        media.mark_downloading()
        media.set_search_info("query", 1, 0.9)
        media.add_raw_metadata("title", "Test")

        assert media.status == DownloadStatus.DOWNLOADING
        assert media.search_query == "query"
        assert media.get_metadata("title") == "Test"
