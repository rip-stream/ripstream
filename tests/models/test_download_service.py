# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Tests for the download history service."""

import contextlib
import os
from tempfile import NamedTemporaryFile
from uuid import uuid4

import pytest

from ripstream.config.user import UserConfig
from ripstream.models.db_manager import DatabaseManager
from ripstream.models.download_service import DownloadService
from ripstream.models.enums import DownloadStatus


class TestDownloadService:
    """Test the DownloadService class."""

    @pytest.fixture
    def temp_db_path(self):
        """Create a unique temporary database path for each test."""
        # Create a unique temporary file for each test process
        with NamedTemporaryFile(suffix=".db", delete=False) as temp_file:
            pass
        yield temp_file.name
        # Clean up the file
        with contextlib.suppress(OSError):
            os.unlink(temp_file.name)

    @pytest.fixture
    def service(self, temp_db_path):
        """Create a DownloadService with a unique temporary database."""
        # Create a unique config for this test
        config = UserConfig()
        config.database.database_path = temp_db_path

        # Create a custom database manager for this test
        db_manager = DatabaseManager(temp_db_path)
        db_manager.initialize()

        # Create service with the custom database manager
        service = DownloadService(config)
        # Override the database manager to use our isolated one
        service.downloads_db = db_manager
        service.failed_downloads_repository = (
            service.failed_downloads_repository.__class__(db_manager)
        )

        yield service

        # Clean up - close the database connection
        if hasattr(service, "downloads_db") and service.downloads_db:
            service.downloads_db.close()

    def test_service_initialization(self, service):
        """Test service initialization."""
        assert service is not None
        assert hasattr(service, "downloads_db")
        assert service.downloads_db is not None

    def test_add_download_record(self, service):
        """Test adding a download record."""
        unique_id = str(uuid4())
        download_id = service.add_download_record(
            title="Test Track",
            artist="Test Artist",
            album="Test Album",
            source_id=unique_id,
        )

        assert download_id is not None

        # Verify the record was added
        record = service.get_download_by_id(download_id)
        assert record is not None
        assert record["title"] == "Test Track"
        assert record["artist"] == "Test Artist"
        assert record["album"] == "Test Album"
        # Note: source_id is not included in the _record_to_dict output

    def test_get_recent_downloads(self, service):
        """Test getting recent downloads."""
        # Add some test downloads with unique IDs
        service.add_download_record(
            title="Track 1",
            artist="Artist 1",
            album="Album 1",
            source_id=str(uuid4()),
        )
        service.add_download_record(
            title="Track 2",
            artist="Artist 2",
            album="Album 2",
            source_id=str(uuid4()),
        )

        downloads = service.get_recent_downloads(limit=10)
        assert len(downloads) == 2

    def test_mark_download_completed(self, service):
        """Test marking a download as completed."""
        unique_id = str(uuid4())
        download_id = service.add_download_record(
            title="Test Track",
            artist="Test Artist",
            source_id=unique_id,
        )

        success = service.mark_download_completed(download_id, "/path/to/file.flac")
        assert success is True

        record = service.get_download_by_id(download_id)
        assert record["status"] == DownloadStatus.COMPLETED
        # Note: file_path is not included in the _record_to_dict output
        assert record["completed_at"] is not None

    def test_mark_download_failed(self, service):
        """Test marking a download as failed."""
        unique_id = str(uuid4())
        download_id = service.add_download_record(
            title="Test Track",
            artist="Test Artist",
            source_id=unique_id,
        )

        success = service.mark_download_failed(download_id, "Test error")
        assert success is True

        record = service.get_download_by_id(download_id)
        assert record["status"] == DownloadStatus.FAILED
        assert record["error_message"] == "Test error"

    def test_retry_download(self, service):
        """Test retrying a failed download."""
        unique_id = str(uuid4())
        download_id = service.add_download_record(
            title="Test Track",
            artist="Test Artist",
            source_id=unique_id,
        )

        # Mark as failed first
        service.mark_download_failed(download_id, "Test error")

        # Retry
        success = service.retry_download(download_id)
        assert success is True

        record = service.get_download_by_id(download_id)
        assert record["status"] == DownloadStatus.PENDING
        assert record["error_message"] is None

    def test_update_download_status(self, service):
        """Test updating download status."""
        unique_id = str(uuid4())
        download_id = service.add_download_record(
            title="Test Track",
            artist="Test Artist",
            source_id=unique_id,
        )

        success = service.update_download_status(
            download_id, DownloadStatus.DOWNLOADING
        )
        assert success is True

        record = service.get_download_by_id(download_id)
        assert record["status"] == DownloadStatus.DOWNLOADING

    def test_remove_download(self, service):
        """Test removing a download record."""
        unique_id = str(uuid4())
        download_id = service.add_download_record(
            title="Test Track",
            artist="Test Artist",
            source_id=unique_id,
        )

        success = service.remove_download(download_id)
        assert success is True

        record = service.get_download_by_id(download_id)
        assert record is None

    def test_clear_completed_downloads(self, service):
        """Test clearing completed downloads."""
        # Add some downloads with unique IDs
        download_id1 = service.add_download_record(
            title="Track 1", artist="Artist 1", source_id=str(uuid4())
        )
        download_id2 = service.add_download_record(
            title="Track 2", artist="Artist 2", source_id=str(uuid4())
        )

        # Mark one as completed
        service.mark_download_completed(download_id1, "/path/to/file.flac")

        # Clear completed
        removed_count = service.clear_completed_downloads()
        assert removed_count == 1

        # Verify only completed was removed
        assert service.get_download_by_id(download_id1) is None
        assert service.get_download_by_id(download_id2) is not None

    def test_clear_all_downloads(self, service):
        """Test clearing all downloads."""
        # Add some downloads
        service.add_download_record(
            title="Track 1", artist="Artist 1", source_id=str(uuid4())
        )
        service.add_download_record(
            title="Track 2", artist="Artist 2", source_id=str(uuid4())
        )

        # Clear all
        removed_count = service.clear_all_downloads()
        assert removed_count == 2

        # Verify all were removed
        downloads = service.get_recent_downloads(limit=10)
        assert len(downloads) == 0

    def test_get_download_statistics(self, service):
        """Test getting download statistics."""
        # Add downloads with different statuses and unique IDs
        download_id1 = service.add_download_record(
            title="Track 1", artist="Artist 1", source_id=str(uuid4())
        )
        download_id2 = service.add_download_record(
            title="Track 2", artist="Artist 2", source_id=str(uuid4())
        )
        service.add_download_record(
            title="Track 3", artist="Artist 3", source_id=str(uuid4())
        )

        # Mark one as completed, one as failed
        service.mark_download_completed(download_id1, "/path/to/file.flac")
        service.mark_download_failed(download_id2, "Error")

        stats = service.get_download_statistics()
        assert stats["total"] == 3
        assert stats["completed"] == 1
        assert stats["failed"] == 1
        assert stats["pending"] == 1

    def test_history_limit_respected(self, service):
        """Test that history limit is respected."""
        # Add more records than the limit
        for i in range(15):
            service.add_download_record(
                title=f"Track {i}",
                artist=f"Artist {i}",
                source_id=str(uuid4()),
            )

        # Should only keep the most recent records up to the limit
        downloads = service.get_recent_downloads(limit=10)
        assert len(downloads) <= 10
