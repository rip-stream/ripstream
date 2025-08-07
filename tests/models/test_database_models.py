# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Tests for database models and download service."""

import tempfile
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import and_

from ripstream.models.database import (
    DownloadHistory,
    DownloadRecord,
    DownloadSession,
)
from ripstream.models.db_manager import DatabaseManager
from ripstream.models.download_service import DownloadService
from ripstream.models.enums import DownloadStatus, MediaType, StreamingSource


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)

    db_manager = DatabaseManager(db_path)
    db_manager.initialize()

    yield db_manager

    db_manager.close()
    db_path.unlink(missing_ok=True)


@pytest.fixture
def download_service(temp_db):
    """Create a download service with temporary database."""
    # Mock the database managers
    import ripstream.models.db_manager as db_manager_module

    original_downloads_db = db_manager_module._downloads_db

    db_manager_module._downloads_db = temp_db

    service = DownloadService()

    yield service

    # Restore original state
    db_manager_module._downloads_db = original_downloads_db


class TestDownloadSession:
    """Test DownloadSession model."""

    def test_create_download_session(self, temp_db):
        """Test creating a download session."""
        session = DownloadSession(
            session_type=MediaType.ARTIST,
            source=StreamingSource.QOBUZ,
            source_id="123456",
            title="Test Artist",
            description="Downloading all albums from Test Artist",
        )

        with temp_db.get_session() as db_session:
            db_session.add(session)
            db_session.commit()
            db_session.refresh(session)

        assert session.id is not None
        assert session.session_type == MediaType.ARTIST
        assert session.source == StreamingSource.QOBUZ
        assert session.title == "Test Artist"
        assert session.status == DownloadStatus.PENDING
        assert session.total_items == 0
        assert session.progress_percentage == 0.0
        assert session.is_active is True

    def test_update_progress(self, temp_db):
        """Test updating session progress."""
        session = DownloadSession(
            session_type=MediaType.ALBUM,
            source=StreamingSource.QOBUZ,
            source_id="789",
            title="Test Album",
            total_items=3,
        )

        with temp_db.get_session() as db_session:
            # Add session first
            db_session.add(session)
            db_session.commit()
            db_session.refresh(session)

            # Now create records with the proper session_id
            records = [
                DownloadRecord(
                    session_id=session.id,
                    media_type=MediaType.TRACK,
                    source=StreamingSource.QOBUZ,
                    source_id=f"track_{i}",
                    title=f"Track {i}",
                    artist="Test Artist",
                    album="Test Album",
                    status=DownloadStatus.COMPLETED
                    if i < 2
                    else DownloadStatus.PENDING,
                    progress_percentage=100.0 if i < 2 else 0.0,
                )
                for i in range(3)
            ]

            db_session.add_all(records)
            db_session.commit()

            # Refresh the session to load the relationship
            db_session.refresh(session, attribute_names=["downloads"])

            # Update progress within the session context
            session.update_progress()

            # Commit the changes
            db_session.commit()

            # Refresh again to get the updated values
            db_session.refresh(session)

            # Test the properties while session is still open
            assert session.completed_items == 2
            assert session.progress_percentage == (2 / 3) * 100.0


class TestDownloadRecord:
    """Test DownloadRecord model."""

    def test_create_download_record(self, temp_db):
        """Test creating a download record."""
        record = DownloadRecord(
            media_type=MediaType.TRACK,
            source=StreamingSource.QOBUZ,
            source_id="track_123",
            title="Test Track",
            artist="Test Artist",
            album="Test Album",
            track_number=1,
        )

        with temp_db.get_session() as db_session:
            db_session.add(record)
            db_session.commit()
            db_session.refresh(record)

        assert record.id is not None
        assert record.media_type == MediaType.TRACK
        assert record.source == StreamingSource.QOBUZ
        assert record.source_id == "track_123"
        assert record.title == "Test Track"
        assert record.status == DownloadStatus.PENDING
        assert record.progress_percentage == 0.0
        assert record.is_active is True

    def test_download_lifecycle(self, temp_db):
        """Test complete download lifecycle."""
        record = DownloadRecord(
            media_type=MediaType.TRACK,
            source=StreamingSource.QOBUZ,
            source_id="lifecycle_track",
            title="Lifecycle Track",
            artist="Test Artist",
        )

        with temp_db.get_session() as db_session:
            db_session.add(record)
            db_session.commit()
            db_session.refresh(record)

        # Start download
        record.mark_started()
        assert record.status == DownloadStatus.DOWNLOADING
        assert record.started_at is not None

        # Update progress
        record.update_progress(50.0)
        assert record.progress_percentage == 50.0

        # Complete download
        record.mark_completed("/path/to/file.flac", 1234567)
        assert record.status == DownloadStatus.COMPLETED
        assert record.progress_percentage == 100.0
        assert record.file_path == "/path/to/file.flac"
        assert record.file_size_bytes == 1234567
        assert record.completed_at is not None

    def test_download_failure(self, temp_db):
        """Test download failure handling."""
        record = DownloadRecord(
            media_type=MediaType.TRACK,
            source=StreamingSource.QOBUZ,
            source_id="failed_track",
            title="Failed Track",
            artist="Test Artist",
        )

        with temp_db.get_session() as db_session:
            db_session.add(record)
            db_session.commit()
            db_session.refresh(record)

        # Mark as failed
        record.mark_failed("Connection timeout")
        assert record.status == DownloadStatus.FAILED
        assert record.error_message == "Connection timeout"
        assert record.retry_count == 1
        assert record.can_retry is True

        # Retry
        record.reset_for_retry()
        assert record.status == DownloadStatus.PENDING
        assert record.error_message is None
        assert record.progress_percentage == 0.0


class TestDownloadHistory:
    """Test DownloadHistory model."""

    def test_create_from_download_record(self, temp_db):
        """Test creating history from download record."""
        record = DownloadRecord(
            media_type=MediaType.TRACK,
            source=StreamingSource.QOBUZ,
            source_id="history_track",
            title="History Track",
            artist="Test Artist",
            album="Test Album",
        )
        record.mark_completed("/path/to/file.flac", 1234567)

        history = DownloadHistory.from_download_record(record)

        assert history.source == StreamingSource.QOBUZ
        assert history.source_id == "history_track"
        assert history.media_type == MediaType.TRACK
        assert history.title == "History Track"
        assert history.artist == "Test Artist"
        assert history.album == "Test Album"
        assert history.file_path == "/path/to/file.flac"
        assert history.file_size_bytes == 1234567

    def test_verify_file_exists(self, temp_db):
        """Test file existence verification."""
        history = DownloadHistory(
            source=StreamingSource.QOBUZ,
            source_id="verify_track",
            media_type=MediaType.TRACK,
            title="Verify Track",
            artist="Test Artist",
            file_path="/nonexistent/file.flac",
            downloaded_at=datetime.now(UTC),
        )

        # Should return False for non-existent file
        assert history.verify_file_exists() is False


class TestDownloadService:
    """Test DownloadService functionality."""

    def test_create_download_session(self, download_service):
        """Test creating a download session."""
        session = download_service.create_download_session(
            session_type=MediaType.ALBUM,
            source=StreamingSource.QOBUZ,
            source_id="album456",
            title="Test Album",
        )

        assert session.id is not None
        assert session.session_type == MediaType.ALBUM
        assert session.source == StreamingSource.QOBUZ
        assert session.title == "Test Album"

    def test_add_download_to_session(self, download_service):
        """Test adding downloads to a session."""
        session = download_service.create_download_session(
            session_type=MediaType.ALBUM,
            source=StreamingSource.QOBUZ,
            source_id="album456",
            title="Test Album",
        )

        # Use unique source_id to avoid constraint violation
        unique_id = f"track001_{uuid4().hex[:8]}"
        record = download_service.add_download_to_session(
            session_id=session.id,
            media_type=MediaType.TRACK,
            source=StreamingSource.QOBUZ,
            source_id=unique_id,
            title="Track 1",
            artist="Test Artist",
            album="Test Album",
            track_number=1,
        )

        assert record.session_id == session.id
        assert record.title == "Track 1"
        assert record.track_number == 1

    def test_is_already_downloaded(self, download_service):
        """Test duplicate detection."""
        # Create a completed download with unique source_id
        unique_id = f"duplicate_test_{uuid4().hex[:8]}"
        record = download_service.create_standalone_download(
            media_type=MediaType.TRACK,
            source=StreamingSource.QOBUZ,
            source_id=unique_id,
            title="Duplicate Track",
            artist="Test Artist",
        )

        download_service.mark_download_completed(
            record.id, "/path/to/file.flac", 1234567
        )

        # Check if it's detected as already downloaded
        is_downloaded = download_service.is_already_downloaded(
            StreamingSource.QOBUZ, unique_id, MediaType.TRACK
        )

        assert is_downloaded is True

        # Check different track
        is_downloaded_other = download_service.is_already_downloaded(
            StreamingSource.QOBUZ, "different_track", MediaType.TRACK
        )

        assert is_downloaded_other is False

    def test_download_lifecycle_through_service(self, download_service):
        """Test complete download lifecycle through service."""
        # Create download with unique source_id
        unique_id = f"lifecycle_test_{uuid4().hex[:8]}"
        record = download_service.create_standalone_download(
            media_type=MediaType.TRACK,
            source=StreamingSource.QOBUZ,
            source_id=unique_id,
            title="Lifecycle Track",
            artist="Test Artist",
        )

        # Start download
        download_service.mark_download_started(record.id)

        # Update progress
        download_service.update_download_progress(record.id, 25.0)
        download_service.update_download_progress(record.id, 75.0)

        # Complete download
        download_service.mark_download_completed(
            record.id, "/path/to/completed.flac", 2345678
        )

        # Manually create history entry since it's not automatic
        with download_service.downloads_db.get_session() as session:
            # Get the completed record
            completed_record = (
                session.query(DownloadRecord)
                .filter(DownloadRecord.id == record.id)
                .first()
            )

            # Create history entry
            history_entry = DownloadHistory.from_download_record(completed_record)
            session.add(history_entry)
            session.commit()

        # Verify history was created - check that our record is in the history
        history = download_service.get_download_history(limit=10)
        assert len(history) >= 1

        # Find our record in the history
        our_record = None
        for hist_record in history:
            if hist_record.source_id == unique_id:
                our_record = hist_record
                break

        assert our_record is not None
        assert our_record.file_path == "/path/to/completed.flac"

    def test_download_session_failed_downloads(self, temp_db):
        """Test session failed downloads functionality."""
        session = DownloadSession(
            session_type=MediaType.ALBUM,
            source=StreamingSource.QOBUZ,
            source_id="failed_album",
            title="Failed Album",
            total_items=3,
        )

        with temp_db.get_session() as db_session:
            # Add session first
            db_session.add(session)
            db_session.commit()
            db_session.refresh(session)

            # Add some failed downloads with the session ID
            records = [
                DownloadRecord(
                    session_id=session.id,
                    media_type=MediaType.TRACK,
                    source=StreamingSource.QOBUZ,
                    source_id=f"failed_track_{i}",
                    title=f"Failed Track {i}",
                    artist="Test Artist",
                    album="Failed Album",
                    status=DownloadStatus.FAILED,
                    error_message=f"Error {i}",
                    retry_count=1,
                )
                for i in range(3)
            ]

            db_session.add_all(records)
            db_session.commit()

            # Update session counts manually since they're not updated automatically
            session.failed_items = 3
            session.total_items = 3
            db_session.commit()

            # Refresh the session object to get updated counts
            db_session.refresh(session)

            # Test the properties while session is still open
            assert session.has_failed_downloads is True

            # Query failed downloads directly to verify they exist
            failed_records = (
                db_session.query(DownloadRecord)
                .filter(
                    and_(
                        DownloadRecord.session_id == session.id,
                        DownloadRecord.status == DownloadStatus.FAILED,
                    )
                )
                .all()
            )
            assert len(failed_records) == 3

            # Load the downloads relationship explicitly
            db_session.refresh(session, attribute_names=["downloads"])
            assert len(session.failed_downloads) == 3
            assert len(session.can_retry_downloads) == 3

            # Retry failed downloads
            retried = session.retry_failed_downloads()
            assert len(retried) == 3

            for record in retried:
                assert record.status == DownloadStatus.PENDING
                assert record.error_message is None

    def test_remove_download(self, download_service):
        """Test removing a download record."""
        # Create a download record
        record = download_service.create_standalone_download(
            media_type=MediaType.TRACK,
            source=StreamingSource.QOBUZ,
            source_id=f"remove_test_{uuid4().hex[:8]}",
            title="Track to Remove",
            artist="Test Artist",
        )

        # Verify the record exists
        retrieved_record = download_service.get_download_by_id(record.id)
        assert retrieved_record is not None
        assert retrieved_record["download_id"] == record.id

        # Remove the download
        success = download_service.remove_download(record.id)
        assert success is True

        # Verify the record no longer exists
        retrieved_record = download_service.get_download_by_id(record.id)
        assert retrieved_record is None

    def test_remove_nonexistent_download(self, download_service):
        """Test removing a download that doesn't exist."""
        # Try to remove a non-existent download
        success = download_service.remove_download("nonexistent_id")
        assert success is False


class TestFailedDownloads:
    """Test failed download functionality."""

    def test_download_record_failed_properties(self, temp_db):
        """Test DownloadRecord properties for failed downloads."""
        record = DownloadRecord(
            media_type=MediaType.TRACK,
            source=StreamingSource.QOBUZ,
            source_id="failed_track",
            title="Failed Track",
            artist="Test Artist",
            status=DownloadStatus.FAILED,
            error_message="Connection timeout",
            retry_count=2,
        )

        with temp_db.get_session() as db_session:
            db_session.add(record)
            db_session.commit()
            db_session.refresh(record)

        assert record.is_failed is True
        assert record.can_retry is True
        assert record.has_exceeded_retry_limit is False
        assert "Failed (retry 2/3)" in record.display_status

    def test_download_record_reset_for_retry(self, temp_db):
        """Test resetting failed download for retry."""
        record = DownloadRecord(
            media_type=MediaType.TRACK,
            source=StreamingSource.QOBUZ,
            source_id="retry_track",
            title="Retry Track",
            artist="Test Artist",
            status=DownloadStatus.FAILED,
            error_message="Connection timeout",
            retry_count=1,
        )

        with temp_db.get_session() as db_session:
            db_session.add(record)
            db_session.commit()
            db_session.refresh(record)

        # Reset for retry
        record.reset_for_retry()

        assert record.status == DownloadStatus.PENDING
        assert record.error_message is None
        assert record.progress_percentage == 0.0
        assert record.started_at is None
        assert record.completed_at is None

    def test_failed_downloads_repository(self, temp_db):
        """Test failed downloads repository functionality."""
        # Create some failed downloads
        records = [
            DownloadRecord(
                media_type=MediaType.TRACK,
                source=StreamingSource.QOBUZ,
                source_id=f"repo_failed_track_{i}",
                title=f"Repo Failed Track {i}",
                artist="Test Artist",
                status=DownloadStatus.FAILED,
                error_message=f"Repository error {i}",
                retry_count=1,
            )
            for i in range(3)
        ]

        with temp_db.get_session() as db_session:
            db_session.add_all(records)
            db_session.commit()

            # Test repository queries
            failed_records = (
                db_session.query(DownloadRecord)
                .filter(DownloadRecord.status == DownloadStatus.FAILED)
                .all()
            )

            assert len(failed_records) == 3

            retryable_records = [r for r in failed_records if r.can_retry]
            assert len(retryable_records) == 3

    def test_download_service_failed_downloads(self, download_service):
        """Test DownloadService failed download functionality."""
        # Create some failed downloads with unique source_ids
        failed_records = []
        for i in range(3):
            unique_id = f"failed_track_{i}_{uuid4().hex[:8]}"
            record = download_service.create_standalone_download(
                media_type=MediaType.TRACK,
                source=StreamingSource.QOBUZ,
                source_id=unique_id,
                title=f"Failed Track {i}",
                artist="Test Artist",
            )

            # Mark as failed
            download_service.mark_download_failed(record.id, f"Error {i}")
            failed_records.append(record)

        # Get failed downloads using the repository
        failed_downloads = download_service.failed_downloads.get_all()
        assert len(failed_downloads) >= 3

        # Test retry functionality
        for record in failed_records:
            if record.can_retry:
                download_service.retry_download(record.id)
                # Verify status was reset
                updated_record = download_service.get_download_by_id(record.id)
                assert updated_record is not None
                assert updated_record["status"] == "PENDING"
