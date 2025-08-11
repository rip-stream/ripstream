# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Service layer for downloads and favorites database operations."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Iterable

from sqlalchemy import and_, desc, func, select
from sqlalchemy.exc import SQLAlchemyError

from ripstream.config.user import UserConfig
from ripstream.models.database import (
    DownloadAudioInfo,
    DownloadHistory,
    DownloadRecord,
    DownloadSession,
    FavoriteArtist,
)
from ripstream.models.db_manager import get_downloads_db
from ripstream.models.enums import DownloadStatus, MediaType, StreamingSource


class FavoritesService:
    """High-level operations for managing favorite artists."""

    def __init__(self) -> None:
        self.db = get_downloads_db()

    def add_favorite_artist(
        self,
        *,
        source: StreamingSource,
        artist_id: str,
        name: str,
        artist_url: str | None,
        photo_url: str | None,
    ) -> bool:
        """Insert a favorite artist if not already present.

        Returns True if inserted or existed, False if a DB error occurred.
        """
        try:
            with self.db.get_session() as session:
                # Upsert-like behavior: check existence first
                existing = session.scalar(
                    select(FavoriteArtist).where(
                        FavoriteArtist.source == source,
                        FavoriteArtist.source_artist_id == artist_id,
                    )
                )
                if existing:
                    # Update any changed fields for freshness
                    changed = False
                    if name and existing.name != name:
                        existing.name = name
                        changed = True
                    if artist_url and existing.artist_url != artist_url:
                        existing.artist_url = artist_url
                        changed = True
                    if photo_url and existing.photo_url != photo_url:
                        existing.photo_url = photo_url
                        changed = True
                    if changed:
                        session.add(existing)
                    session.commit()
                    return True

                fav = FavoriteArtist(
                    source=source,
                    source_artist_id=artist_id,
                    name=name,
                    artist_url=artist_url,
                    photo_url=photo_url,
                )
                session.add(fav)
                session.commit()
                return True
        except SQLAlchemyError:
            return False

    def list_favorites(self) -> list[dict[str, Any]]:
        """Return all favorite artists as dictionaries sorted by name."""
        try:
            with self.db.get_session() as session:
                rows: Iterable[FavoriteArtist] = session.scalars(
                    select(FavoriteArtist).order_by(FavoriteArtist.name.asc())
                )
                return [
                    {
                        "id": fav.id,
                        "source": fav.source,
                        "artist_id": fav.source_artist_id,
                        "name": fav.name,
                        "artist_url": fav.artist_url,
                        "photo_url": fav.photo_url,
                    }
                    for fav in rows
                ]
        except SQLAlchemyError:
            return []

    def is_favorite(self, source: StreamingSource, artist_id: str) -> bool:
        """Check if an artist is already in favorites."""
        try:
            with self.db.get_session() as session:
                existing = session.scalar(
                    select(FavoriteArtist).where(
                        FavoriteArtist.source == source,
                        FavoriteArtist.source_artist_id == artist_id,
                    )
                )
                return existing is not None
        except SQLAlchemyError:
            return False

    def remove_favorite(self, source: StreamingSource, artist_id: str) -> bool:
        """Remove a favorite artist by source and artist id."""
        try:
            with self.db.get_session() as session:
                fav = session.scalar(
                    select(FavoriteArtist).where(
                        FavoriteArtist.source == source,
                        FavoriteArtist.source_artist_id == artist_id,
                    )
                )
                if not fav:
                    return True
                session.delete(fav)
                session.commit()
                return True
        except SQLAlchemyError:
            return False

    def remove_favorite_by_id(self, favorite_id: str) -> bool:
        """Remove a favorite artist by its internal ID."""
        try:
            with self.db.get_session() as session:
                fav = session.get(FavoriteArtist, favorite_id)
                if not fav:
                    return True
                session.delete(fav)
                session.commit()
                return True
        except SQLAlchemyError:
            return False


logger = logging.getLogger(__name__)


class FailedDownloadsRepository:
    """Repository for managing failed downloads."""

    def __init__(self, downloads_db) -> None:
        """Initialize the repository."""
        self.downloads_db = downloads_db

    def get_all(
        self,
        limit: int = 100,
        source: StreamingSource | None = None,
        can_retry_only: bool = False,
    ) -> list[DownloadRecord]:
        """Get all failed downloads.

        Args:
            limit: Maximum number of records to return
            source: Optional source filter
            can_retry_only: Only return downloads that can be retried

        Returns
        -------
            List of failed download records
        """
        with self.downloads_db.get_session() as db_session:
            query = db_session.query(DownloadRecord).filter(
                DownloadRecord.status == DownloadStatus.FAILED
            )

            if source:
                query = query.filter(DownloadRecord.source == source)

            if can_retry_only:
                query = query.filter(DownloadRecord.retry_count < 3)

            return query.order_by(desc(DownloadRecord.updated_at)).limit(limit).all()

    def get_by_session(
        self, session_id: str, can_retry_only: bool = False
    ) -> list[DownloadRecord]:
        """Get failed downloads for a specific session.

        Args:
            session_id: ID of the download session
            can_retry_only: Only return downloads that can be retried

        Returns
        -------
            List of failed download records for the session
        """
        with self.downloads_db.get_session() as db_session:
            query = db_session.query(DownloadRecord).filter(
                and_(
                    DownloadRecord.status == DownloadStatus.FAILED,
                    DownloadRecord.session_id == session_id,
                )
            )

            if can_retry_only:
                query = query.filter(DownloadRecord.retry_count < 3)

            return query.order_by(DownloadRecord.created_at).all()

    def get_by_source(
        self, source: StreamingSource, limit: int = 100, can_retry_only: bool = False
    ) -> list[DownloadRecord]:
        """Get failed downloads for a specific source.

        Args:
            source: Streaming source to filter by
            limit: Maximum number of records to return
            can_retry_only: Only return downloads that can be retried

        Returns
        -------
            List of failed download records for the source
        """
        with self.downloads_db.get_session() as db_session:
            query = db_session.query(DownloadRecord).filter(
                and_(
                    DownloadRecord.status == DownloadStatus.FAILED,
                    DownloadRecord.source == source,
                )
            )

            if can_retry_only:
                query = query.filter(DownloadRecord.retry_count < 3)

            return query.order_by(desc(DownloadRecord.updated_at)).limit(limit).all()

    def get_by_error_pattern(
        self, error_pattern: str, limit: int = 100, can_retry_only: bool = False
    ) -> list[DownloadRecord]:
        """Get failed downloads by error message pattern.

        Args:
            error_pattern: Pattern to search in error messages
            limit: Maximum number of records to return
            can_retry_only: Only return downloads that can be retried

        Returns
        -------
            List of failed download records matching the error pattern
        """
        with self.downloads_db.get_session() as db_session:
            query = db_session.query(DownloadRecord).filter(
                and_(
                    DownloadRecord.status == DownloadStatus.FAILED,
                    DownloadRecord.error_message.like(f"%{error_pattern}%"),
                )
            )

            if can_retry_only:
                query = query.filter(DownloadRecord.retry_count < 3)

            return query.order_by(desc(DownloadRecord.updated_at)).limit(limit).all()

    def count_all(self, source: StreamingSource | None = None) -> int:
        """Count total failed downloads.

        Args:
            source: Optional source filter

        Returns
        -------
            Total count of failed downloads
        """
        with self.downloads_db.get_session() as db_session:
            query = db_session.query(DownloadRecord).filter(
                DownloadRecord.status == DownloadStatus.FAILED
            )

            if source:
                query = query.filter(DownloadRecord.source == source)

            return query.count()

    def count_retryable(self, source: StreamingSource | None = None) -> int:
        """Count failed downloads that can be retried.

        Args:
            source: Optional source filter

        Returns
        -------
            Count of failed downloads that can be retried
        """
        with self.downloads_db.get_session() as db_session:
            query = db_session.query(DownloadRecord).filter(
                and_(
                    DownloadRecord.status == DownloadStatus.FAILED,
                    DownloadRecord.retry_count < 3,
                )
            )

            if source:
                query = query.filter(DownloadRecord.source == source)

            return query.count()

    def get_stats(self) -> dict[str, Any]:
        """Get statistics about failed downloads.

        Returns
        -------
            Dictionary with failed download statistics
        """
        with self.downloads_db.get_session() as db_session:
            # Total failed downloads
            total_failed = (
                db_session.query(DownloadRecord)
                .filter(DownloadRecord.status == DownloadStatus.FAILED)
                .count()
            )

            # Failed downloads by source
            failed_by_source = (
                db_session.query(
                    DownloadRecord.source,
                    func.count(DownloadRecord.id).label("count"),
                )
                .filter(DownloadRecord.status == DownloadStatus.FAILED)
                .group_by(DownloadRecord.source)
                .all()
            )

            # Failed downloads by retry count
            failed_by_retry = (
                db_session.query(
                    DownloadRecord.retry_count,
                    func.count(DownloadRecord.id).label("count"),
                )
                .filter(DownloadRecord.status == DownloadStatus.FAILED)
                .group_by(DownloadRecord.retry_count)
                .all()
            )

            # Can retry vs cannot retry
            can_retry = (
                db_session.query(DownloadRecord)
                .filter(
                    and_(
                        DownloadRecord.status == DownloadStatus.FAILED,
                        DownloadRecord.retry_count < 3,
                    )
                )
                .count()
            )

            cannot_retry = (
                db_session.query(DownloadRecord)
                .filter(
                    and_(
                        DownloadRecord.status == DownloadStatus.FAILED,
                        DownloadRecord.retry_count >= 3,
                    )
                )
                .count()
            )

            return {
                "total_failed": total_failed,
                "can_retry": can_retry,
                "cannot_retry": cannot_retry,
                "by_source": dict(failed_by_source),
                "by_retry_count": dict(failed_by_retry),
            }


class DownloadService:
    """Service for managing download records and history."""

    def __init__(self, config: UserConfig | None = None) -> None:
        """Initialize the download service.

        Args:
            config: User configuration, defaults to new instance
        """
        self.config = config or UserConfig()
        self.downloads_db = get_downloads_db()
        self.failed_downloads_repository = FailedDownloadsRepository(self.downloads_db)

    @property
    def failed_downloads(self) -> FailedDownloadsRepository:
        """Get the failed downloads repository."""
        return self.failed_downloads_repository

    # UI-focused methods (from download_history_service.py)
    def get_recent_downloads(self, limit: int | None = None) -> list[dict[str, Any]]:
        """Get recent download records from the database.

        Args:
            limit: Maximum number of records to return, uses config default if None

        Returns
        -------
            List of download records as dictionaries
        """
        if limit is None:
            limit = self.config.database.history_limit

        try:
            with self.downloads_db.get_session() as session:
                # Query recent downloads ordered by creation date
                stmt = (
                    select(DownloadRecord)
                    .order_by(desc(DownloadRecord.created_at))
                    .limit(limit)
                )

                records = session.execute(stmt).scalars().all()

                return [self._record_to_dict(record) for record in records]

        except Exception:
            logger.exception("Failed to fetch recent downloads")
            return []

    def get_download_by_id(self, download_id: str) -> dict[str, Any] | None:
        """Get a specific download record by ID.

        Args:
            download_id: The download record ID

        Returns
        -------
            Download record as dictionary or None if not found
        """
        try:
            with self.downloads_db.get_session() as session:
                stmt = select(DownloadRecord).where(DownloadRecord.id == download_id)
                record = session.execute(stmt).scalar_one_or_none()

                return self._record_to_dict(record) if record else None

        except Exception:
            logger.exception("Failed to fetch download by ID %s", download_id)
            return None

    def add_download_record(
        self,
        title: str,
        artist: str,
        album: str | None = None,
        media_type: MediaType = MediaType.TRACK,
        source: StreamingSource = StreamingSource.QOBUZ,
        source_id: str = "",
        source_url: str | None = None,
        session_id: str | None = None,
        album_id: str | None = None,
        audio_info: dict[str, Any] | None = None,
    ) -> str | None:
        """Add a new download record to the database.

        Args:
            title: Track/album title
            artist: Artist name
            album: Album name (optional)
            media_type: Type of media being downloaded
            source: Streaming source
            source_id: Source-specific ID
            source_url: Source URL (optional)
            session_id: Associated session ID (optional)

        Returns
        -------
            The created download record ID or None if failed
        """
        try:
            with self.downloads_db.get_session() as session:
                record = DownloadRecord(
                    title=title,
                    artist=artist,
                    album=album,
                    media_type=media_type,
                    source=source,
                    source_id=source_id,
                    source_url=source_url,
                    session_id=session_id,
                    status=DownloadStatus.PENDING,
                    progress_percentage=0.0,
                    album_id=album_id,
                )

                session.add(record)
                session.commit()

                # If audio_info provided, persist linked technicals
                if audio_info and isinstance(audio_info, dict):
                    ai = DownloadAudioInfo(
                        download_id=record.id,
                        quality=audio_info.get("quality"),
                        bit_depth=audio_info.get("bit_depth"),
                        sampling_rate=audio_info.get("sampling_rate"),
                        bitrate=audio_info.get("bitrate"),
                        codec=audio_info.get("codec"),
                        container=audio_info.get("container"),
                        duration_seconds=audio_info.get("duration_seconds"),
                        file_size_bytes=audio_info.get("file_size_bytes"),
                        is_lossless=audio_info.get("is_lossless"),
                        is_explicit=bool(audio_info.get("is_explicit", False)),
                        channels=audio_info.get("channels"),
                    )
                    session.add(ai)
                    session.commit()

                logger.info("Added download record: %s - %s", artist, title)
                return record.id

        except Exception:
            logger.exception("Failed to add download record")
            return None

    def update_download_status(
        self, download_id: str, status: DownloadStatus, progress: float = 0.0
    ) -> bool:
        """Update the status of a download record.

        Args:
            download_id: The download record ID
            status: New status
            progress: Progress percentage (0-100)

        Returns
        -------
            True if update was successful, False otherwise
        """
        try:
            with self.downloads_db.get_session() as session:
                stmt = select(DownloadRecord).where(DownloadRecord.id == download_id)
                record = session.execute(stmt).scalar_one_or_none()

                if not record:
                    logger.warning("Download record not found: %s", download_id)
                    return False

                record.status = status
                record.progress_percentage = max(0.0, min(100.0, progress))
                record.updated_at = datetime.now(UTC)

                if status == DownloadStatus.DOWNLOADING and not record.started_at:
                    record.started_at = datetime.now(UTC)
                elif status == DownloadStatus.COMPLETED:
                    record.completed_at = datetime.now(UTC)

                session.commit()
                logger.debug("Updated download status: %s -> %s", download_id, status)
                return True

        except Exception:
            logger.exception("Failed to update download status")
            return False

    def mark_download_completed(
        self, download_id: str, file_path: str, file_size_bytes: int | None = None
    ) -> bool:
        """Mark a download as completed.

        Args:
            download_id: The download record ID
            file_path: Path to the downloaded file
            file_size_bytes: File size in bytes (optional)

        Returns
        -------
            True if update was successful, False otherwise
        """
        try:
            with self.downloads_db.get_session() as session:
                stmt = select(DownloadRecord).where(DownloadRecord.id == download_id)
                record = session.execute(stmt).scalar_one_or_none()

                if not record:
                    logger.warning("Download record not found: %s", download_id)
                    return False

                record.mark_completed(file_path, file_size_bytes)
                session.commit()

                logger.info("Marked download completed: %s", download_id)
                return True

        except Exception:
            logger.exception("Failed to mark download completed")
            return False

    def mark_download_failed(self, download_id: str, error_message: str) -> bool:
        """Mark a download as failed.

        Args:
            download_id: The download record ID
            error_message: Error message describing the failure

        Returns
        -------
            True if update was successful, False otherwise
        """
        try:
            with self.downloads_db.get_session() as session:
                stmt = select(DownloadRecord).where(DownloadRecord.id == download_id)
                record = session.execute(stmt).scalar_one_or_none()

                if not record:
                    logger.warning("Download record not found: %s", download_id)
                    return False

                record.mark_failed(error_message)
                session.commit()

                logger.warning(
                    "Marked download failed: %s - %s", download_id, error_message
                )
                return True

        except Exception:
            logger.exception("Failed to mark download failed")
            return False

    def retry_download(self, download_id: str) -> bool:
        """Retry a failed download.

        Args:
            download_id: The download record ID

        Returns
        -------
            True if retry was successful, False otherwise
        """
        try:
            with self.downloads_db.get_session() as session:
                stmt = select(DownloadRecord).where(DownloadRecord.id == download_id)
                record = session.execute(stmt).scalar_one_or_none()

                if not record:
                    logger.warning("Download record not found: %s", download_id)
                    return False

                if not record.can_retry:
                    logger.warning("Download cannot be retried: %s", download_id)
                    return False

                record.reset_for_retry()
                session.commit()

                logger.info("Reset download for retry: %s", download_id)
                return True

        except Exception:
            logger.exception("Failed to retry download")
            return False

    def remove_download(self, download_id: str) -> bool:
        """Remove a download record from the database.

        Args:
            download_id: The download record ID

        Returns
        -------
            True if removal was successful, False otherwise
        """
        try:
            with self.downloads_db.get_session() as session:
                stmt = select(DownloadRecord).where(DownloadRecord.id == download_id)
                record = session.execute(stmt).scalar_one_or_none()

                if not record:
                    logger.warning("Download record not found: %s", download_id)
                    return False

                session.delete(record)
                session.commit()

                logger.info("Removed download record: %s", download_id)
                return True

        except Exception:
            logger.exception("Failed to remove download")
            return False

    def clear_completed_downloads(self) -> int:
        """Remove all completed downloads from the database.

        Returns
        -------
            Number of records removed
        """
        try:
            with self.downloads_db.get_session() as session:
                stmt = select(DownloadRecord).where(
                    DownloadRecord.status == DownloadStatus.COMPLETED
                )
                records = session.execute(stmt).scalars().all()

                count = len(records)
                for record in records:
                    session.delete(record)

                session.commit()
                logger.info("Cleared %d completed downloads", count)
                return count

        except Exception:
            logger.exception("Failed to clear completed downloads")
            return 0

    def clear_all_downloads(self) -> int:
        """Remove all download records from the database.

        Returns
        -------
            Number of records removed
        """
        try:
            with self.downloads_db.get_session() as session:
                stmt = select(DownloadRecord)
                records = session.execute(stmt).scalars().all()

                count = len(records)
                for record in records:
                    session.delete(record)

                session.commit()
                logger.info("Cleared all %d downloads", count)
                return count

        except Exception:
            logger.exception("Failed to clear all downloads")
            return 0

    def get_download_statistics(self) -> dict[str, int]:
        """Get download statistics.

        Returns
        -------
            Dictionary with statistics counts
        """
        try:
            with self.downloads_db.get_session() as session:
                total_stmt = select(DownloadRecord)
                total_records = session.execute(total_stmt).scalars().all()

                completed = sum(
                    1 for r in total_records if r.status == DownloadStatus.COMPLETED
                )
                failed = sum(
                    1 for r in total_records if r.status == DownloadStatus.FAILED
                )
                pending = sum(
                    1
                    for r in total_records
                    if r.status in (DownloadStatus.PENDING, DownloadStatus.DOWNLOADING)
                )

                return {
                    "total": len(total_records),
                    "completed": completed,
                    "failed": failed,
                    "pending": pending,
                }

        except Exception:
            logger.exception("Failed to get download statistics")
            return {"total": 0, "completed": 0, "failed": 0, "pending": 0}

    def get_downloaded_albums(self) -> set[tuple[str, str]]:
        """Get set of downloaded albums as (album_id, source) tuples.

        Returns
        -------
            Set of (album_id, source) tuples for completed downloads
        """
        try:
            with self.downloads_db.get_session() as session:
                stmt = select(DownloadRecord).where(
                    and_(
                        DownloadRecord.status == DownloadStatus.COMPLETED,
                        DownloadRecord.album_id.is_not(None),
                    )
                )
                records = session.execute(stmt).scalars().all()

                downloaded_albums = set()
                for record in records:
                    if record.album_id:
                        downloaded_albums.add((record.album_id, record.source.value))

                return downloaded_albums

        except Exception:
            logger.exception("Failed to get downloaded albums")
            return set()

    def get_download_details(self, download_id: str) -> dict[str, Any] | None:
        """Return a detailed dictionary of file and audio technicals for Info dialogs.

        Includes: filename, format, length (MM:SS), bitrate text, file size text,
        sample rate Hz, bits per sample, channels label, album title, track count.
        """
        try:
            with self.downloads_db.get_session() as session:
                stmt = select(DownloadRecord).where(DownloadRecord.id == download_id)
                record = session.execute(stmt).scalar_one_or_none()
                if not record:
                    return None

                ai = getattr(record, "audio_info", None)
                # Compute human-friendly fields
                file_path = record.file_path or ""
                container = (ai.container if ai else None) or (
                    (file_path.rsplit(".", 1)[-1]).upper() if "." in file_path else None
                )
                # Duration in seconds to MM:SS
                duration = (
                    ai.duration_seconds if ai else None
                ) or record.duration_seconds
                length_text = ""
                if isinstance(duration, (int, float)) and duration is not None:
                    minutes = int(duration // 60)
                    seconds = int(duration % 60)
                    length_text = f"{minutes:02d}:{seconds:02d}"
                # Bitrate kbps text
                bitrate_kbps = ai.bitrate if ai else None
                bitrate_text = f"{bitrate_kbps} kbps" if bitrate_kbps else ""
                # File size MB
                file_size_bytes = ai.file_size_bytes if ai else record.file_size_bytes
                file_size_text = ""
                if isinstance(file_size_bytes, int) and file_size_bytes > 0:
                    file_size_text = f"{(file_size_bytes / (1024 * 1024)):.1f} MB"
                # Sample rate Hz
                sampling_rate = ai.sampling_rate if ai else None
                sample_rate_text = f"{int(sampling_rate)} Hz" if sampling_rate else ""
                # Bit depth
                bit_depth = ai.bit_depth if ai else None
                # Channels label
                channels = ai.channels if ai else None
                channels_text = ""
                if channels == 1:
                    channels_text = "Mono"
                elif channels == 2:
                    channels_text = "Stereo"
                elif isinstance(channels, int) and channels > 2:
                    channels_text = f"{channels} ch"

                return {
                    "filename": file_path,
                    "format": container or "",
                    "length": length_text,
                    "bitrate": bitrate_text,
                    "file_size": file_size_text,
                    "sample_rate": sample_rate_text,
                    "bits_per_sample": bit_depth,
                    "channels": channels_text,
                    "album": record.album or "",
                    "total_tracks": 1,
                }
        except Exception:
            logger.exception("Failed to build download details for %s", download_id)
            return None

    def _record_to_dict(self, record: DownloadRecord) -> dict[str, Any]:
        """Convert a DownloadRecord to a dictionary for UI consumption.

        Args:
            record: The download record

        Returns
        -------
            Dictionary representation of the record
        """
        return {
            "download_id": record.id,
            "title": record.title,
            "artist": record.artist,
            "album": record.album or "Unknown",
            "type": record.media_type.value.title(),
            "status": record.status,
            "progress": int(record.progress_percentage),
            "started_at": record.started_at,
            "completed_at": record.completed_at,
            "source": record.source.value,
            "source_id": record.source_id,
            "error_message": record.error_message,
            "retry_count": record.retry_count,
            "album_id": record.album_id,
        }

    # Original comprehensive methods (keeping existing functionality)
    def create_download_session(
        self,
        session_type: MediaType,
        source: StreamingSource,
        source_id: str,
        title: str,
        description: str | None = None,
        source_url: str | None = None,
        download_config: dict[str, Any] | None = None,
    ) -> DownloadSession:
        """Create a new download session.

        Args:
            session_type: Type of media being downloaded (artist, album, playlist)
            source: Streaming source
            source_id: ID from the streaming service
            title: Display title for the session
            description: Optional description
            source_url: Optional source URL
            download_config: Optional download configuration

        Returns
        -------
            Created DownloadSession
        """
        session = DownloadSession(
            session_type=session_type,
            source=source,
            source_id=source_id,
            title=title,
            description=description,
            source_url=source_url,
            download_config=download_config,
        )

        with self.downloads_db.get_session() as db_session:
            db_session.add(session)
            db_session.commit()
            db_session.refresh(session)

        logger.info("Created download session: %s (%s)", session.title, session.id)
        return session

    def add_download_to_session(
        self,
        session_id: str,
        media_type: MediaType,
        source: StreamingSource,
        source_id: str,
        title: str,
        artist: str,
        album: str | None = None,
        **kwargs: Any,
    ) -> DownloadRecord:
        """Add a download record to a session.

        Args:
            session_id: ID of the download session
            media_type: Type of media (track, album)
            source: Streaming source
            source_id: ID from streaming service
            title: Media title
            artist: Artist name
            album: Album name (optional)
            **kwargs: Additional metadata

        Returns
        -------
            Created DownloadRecord
        """
        record = DownloadRecord(
            session_id=session_id,
            media_type=media_type,
            source=source,
            source_id=source_id,
            title=title,
            artist=artist,
            album=album,
            **kwargs,
        )

        with self.downloads_db.get_session() as db_session:
            db_session.add(record)

            # Update session total count
            session = db_session.get(DownloadSession, session_id)
            if session:
                session.total_items += 1
                session.updated_at = datetime.now(UTC)

            db_session.commit()
            db_session.refresh(record)

        return record

    def create_standalone_download(
        self,
        media_type: MediaType,
        source: StreamingSource,
        source_id: str,
        title: str,
        artist: str,
        album: str | None = None,
        **kwargs: Any,
    ) -> DownloadRecord:
        """Create a standalone download record (not part of a session).

        Args:
            media_type: Type of media
            source: Streaming source
            source_id: ID from streaming service
            title: Media title
            artist: Artist name
            album: Album name (optional)
            **kwargs: Additional metadata

        Returns
        -------
            Created DownloadRecord
        """
        record = DownloadRecord(
            media_type=media_type,
            source=source,
            source_id=source_id,
            title=title,
            artist=artist,
            album=album,
            **kwargs,
        )

        with self.downloads_db.get_session() as db_session:
            db_session.add(record)
            db_session.commit()
            db_session.refresh(record)
            # Get the ID before the session closes

        # Reattach the record to a new session to avoid DetachedInstanceError
        with self.downloads_db.get_session() as db_session:
            return db_session.merge(record)

    def is_already_downloaded(
        self, source: StreamingSource, source_id: str, media_type: MediaType
    ) -> bool:
        """Check if media has already been downloaded.

        Args:
            source: Streaming source
            source_id: ID from streaming service
            media_type: Type of media

        Returns
        -------
            True if already downloaded, False otherwise
        """
        with self.downloads_db.get_session() as db_session:
            # Check download history
            history_exists = (
                db_session.query(DownloadHistory)
                .filter(
                    and_(
                        DownloadHistory.source == source,
                        DownloadHistory.source_id == source_id,
                        DownloadHistory.media_type == media_type,
                        DownloadHistory.file_exists == True,  # noqa: E712
                    )
                )
                .first()
                is not None
            )

            if history_exists:
                return True

            # Check active downloads
            active_download = (
                db_session.query(DownloadRecord)
                .filter(
                    and_(
                        DownloadRecord.source == source,
                        DownloadRecord.source_id == source_id,
                        DownloadRecord.media_type == media_type,
                        DownloadRecord.status == DownloadStatus.COMPLETED,
                    )
                )
                .first()
            )

            return active_download is not None

    def mark_download_started(self, download_id: str) -> None:
        """Mark a download as started.

        Args:
            download_id: ID of the download record
        """
        with self.downloads_db.get_session() as db_session:
            record = db_session.get(DownloadRecord, download_id)
            if record:
                record.mark_started()

                # Update session if applicable
                if record.session_id:
                    session = db_session.get(DownloadSession, record.session_id)
                    if session and session.status == DownloadStatus.PENDING:
                        session.status = DownloadStatus.DOWNLOADING
                        session.started_at = datetime.now(UTC)

                db_session.commit()

    def update_download_progress(self, download_id: str, progress: float) -> None:
        """Update download progress.

        Args:
            download_id: ID of the download record
            progress: Progress percentage (0-100)
        """
        with self.downloads_db.get_session() as db_session:
            record = db_session.get(DownloadRecord, download_id)
            if record:
                record.update_progress(progress)
                db_session.commit()

    def get_active_downloads(self) -> list[DownloadRecord]:
        """Get all active (pending/downloading) downloads.

        Returns
        -------
            List of active download records
        """
        with self.downloads_db.get_session() as db_session:
            return (
                db_session.query(DownloadRecord)
                .filter(
                    DownloadRecord.status.in_([
                        DownloadStatus.PENDING,
                        DownloadStatus.DOWNLOADING,
                    ])
                )
                .order_by(DownloadRecord.created_at)
                .all()
            )

    def get_download_sessions(
        self, limit: int = 50, include_completed: bool = True
    ) -> list[DownloadSession]:
        """Get recent download sessions.

        Args:
            limit: Maximum number of sessions to return
            include_completed: Whether to include completed sessions

        Returns
        -------
            List of download sessions
        """
        with self.downloads_db.get_session() as db_session:
            query = db_session.query(DownloadSession)

            if not include_completed:
                query = query.filter(DownloadSession.status != DownloadStatus.COMPLETED)

            return query.order_by(desc(DownloadSession.created_at)).limit(limit).all()

    def get_download_history(
        self, limit: int = 100, source: StreamingSource | None = None
    ) -> list[DownloadHistory]:
        """Get download history.

        Args:
            limit: Maximum number of records to return
            source: Optional source filter

        Returns
        -------
            List of download history records
        """
        with self.downloads_db.get_session() as db_session:
            query = db_session.query(DownloadHistory)

            if source:
                query = query.filter(DownloadHistory.source == source)

            return (
                query.order_by(desc(DownloadHistory.downloaded_at)).limit(limit).all()
            )

    def retry_failed_download(self, download_id: str) -> DownloadRecord | None:
        """Retry a failed download by resetting its status.

        Args:
            download_id: ID of the failed download

        Returns
        -------
            Updated download record if successful, None if not found or cannot retry
        """
        with self.downloads_db.get_session() as db_session:
            record = db_session.get(DownloadRecord, download_id)
            if not record or record.status != DownloadStatus.FAILED:
                return None

            if record.retry_count >= 3:
                logger.warning("Download %s has exceeded retry limit", download_id)
                return None

            # Reset the download for retry
            record.status = DownloadStatus.PENDING
            record.error_message = None
            record.started_at = None
            record.completed_at = None
            record.progress_percentage = 0.0
            record.updated_at = datetime.now(UTC)

            db_session.commit()
            logger.info("Reset download %s for retry", download_id)
            return record

    def retry_failed_downloads(
        self,
        download_ids: list[str] | None = None,
        session_id: str | None = None,
        source: StreamingSource | None = None,
    ) -> list[DownloadRecord]:
        """Retry multiple failed downloads.

        Args:
            download_ids: List of specific download IDs to retry (if None, retry all)
            session_id: Retry failed downloads from specific session
            source: Retry failed downloads from specific source

        Returns
        -------
            List of successfully reset download records
        """
        with self.downloads_db.get_session() as db_session:
            query = db_session.query(DownloadRecord).filter(
                DownloadRecord.status == DownloadStatus.FAILED
            )

            if download_ids:
                query = query.filter(DownloadRecord.id.in_(download_ids))
            elif session_id:
                query = query.filter(DownloadRecord.session_id == session_id)
            elif source:
                query = query.filter(DownloadRecord.source == source)

            # Only retry downloads that haven't exceeded retry limit
            query = query.filter(DownloadRecord.retry_count < 3)
            failed_downloads = query.all()

            retried_downloads = []
            for record in failed_downloads:
                # Reset the download for retry
                record.status = DownloadStatus.PENDING
                record.error_message = None
                record.started_at = None
                record.completed_at = None
                record.progress_percentage = 0.0
                record.updated_at = datetime.now(UTC)
                retried_downloads.append(record)

            db_session.commit()
            logger.info("Reset %d downloads for retry", len(retried_downloads))

            # Reattach records to a new session to avoid DetachedInstanceError
            with self.downloads_db.get_session() as new_session:
                return [new_session.merge(record) for record in retried_downloads]

    def cleanup_old_records(self, days_old: int = 30) -> int:
        """Clean up old completed download records.

        Args:
            days_old: Remove records older than this many days

        Returns
        -------
            Number of records removed
        """
        from datetime import timedelta

        cutoff_date = datetime.now(UTC) - timedelta(days=days_old)

        with self.downloads_db.get_session() as db_session:
            # Only remove completed downloads that are also in history
            completed_records = (
                db_session.query(DownloadRecord)
                .filter(
                    and_(
                        DownloadRecord.status == DownloadStatus.COMPLETED,
                        DownloadRecord.completed_at < cutoff_date,
                    )
                )
                .all()
            )

            removed_count = 0
            for record in completed_records:
                # Check if it exists in history
                history_exists = (
                    db_session.query(DownloadHistory)
                    .filter(
                        and_(
                            DownloadHistory.source == record.source,
                            DownloadHistory.source_id == record.source_id,
                            DownloadHistory.media_type == record.media_type,
                        )
                    )
                    .first()
                    is not None
                )

                if history_exists:
                    db_session.delete(record)
                    removed_count += 1

            db_session.commit()

        logger.info("Cleaned up %d old download records", removed_count)
        return removed_count


# Global service instance
_download_service: DownloadService | None = None


def get_download_service() -> DownloadService:
    """Get the global download service instance.

    Returns
    -------
        DownloadService instance
    """
    global _download_service
    if _download_service is None:
        _download_service = DownloadService()
    return _download_service
