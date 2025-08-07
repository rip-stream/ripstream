# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Integration utilities for connecting existing models with download tracking."""

import logging
from typing import Any

from ripstream.models.album import Album
from ripstream.models.artist import Artist
from ripstream.models.download_service import get_download_service
from ripstream.models.enums import MediaType
from ripstream.models.playlist import Playlist
from ripstream.models.track import Track

logger = logging.getLogger(__name__)


class DownloadIntegration:
    """Utilities for integrating existing models with download tracking."""

    def __init__(self) -> None:
        """Initialize the download integration."""
        self.download_service = get_download_service()

    def create_artist_download_session(
        self, artist: Artist, download_config: dict[str, Any] | None = None
    ) -> str:
        """Create a download session for all albums from an artist.

        Args:
            artist: Artist model to download
            download_config: Optional download configuration

        Returns
        -------
            Download session ID
        """
        session = self.download_service.create_download_session(
            session_type=MediaType.ARTIST,
            source=artist.info.source,
            source_id=artist.info.id,
            title=f"Download all albums by {artist.name}",
            description=f"Downloading complete discography for {artist.name}",
            source_url=artist.info.url,
            download_config=download_config,
        )

        logger.info(
            "Created artist download session for %s: %s", artist.name, session.id
        )
        return session.id

    def create_album_download_session(
        self, album: Album, download_config: dict[str, Any] | None = None
    ) -> str:
        """Create a download session for an album.

        Args:
            album: Album model to download
            download_config: Optional download configuration

        Returns
        -------
            Download session ID
        """
        session = self.download_service.create_download_session(
            session_type=MediaType.ALBUM,
            source=album.info.source,
            source_id=album.info.id,
            title=f"Download album: {album.title}",
            description=f"Downloading album '{album.title}' by {album.artist}",
            source_url=album.info.url,
            download_config=download_config,
        )

        logger.info(
            "Created album download session for %s: %s", album.title, session.id
        )
        return session.id

    def create_playlist_download_session(
        self, playlist: Playlist, download_config: dict[str, Any] | None = None
    ) -> str:
        """Create a download session for a playlist.

        Args:
            playlist: Playlist model to download
            download_config: Optional download configuration

        Returns
        -------
            Download session ID
        """
        session = self.download_service.create_download_session(
            session_type=MediaType.PLAYLIST,
            source=playlist.info.source,
            source_id=playlist.info.id,
            title=f"Download playlist: {playlist.name}",
            description=f"Downloading playlist '{playlist.name}' ({playlist.track_count} tracks)",
            source_url=playlist.info.url,
            download_config=download_config,
        )

        logger.info(
            "Created playlist download session for %s: %s", playlist.name, session.id
        )
        return session.id

    def add_album_tracks_to_session(
        self, session_id: str, album: Album, tracks: list[Track]
    ) -> list[str]:
        """Add all tracks from an album to a download session.

        Args:
            session_id: Download session ID
            album: Album containing the tracks
            tracks: List of track models to add

        Returns
        -------
            List of download record IDs
        """
        download_ids = []

        for track in tracks:
            # Skip if already downloaded
            if self.download_service.is_already_downloaded(
                track.info.source, track.info.id, MediaType.TRACK
            ):
                logger.info("Skipping already downloaded track: %s", track.title)
                continue

            record = self.download_service.add_download_to_session(
                session_id=session_id,
                media_type=MediaType.TRACK,
                source=track.info.source,
                source_id=track.info.id,
                title=track.title,
                artist=track.artist,
                album=album.title,
                album_artist=track.credits.album_artist,
                track_number=track.info.track_number,
                disc_number=track.info.disc_number,
                duration_seconds=track.audio.duration_seconds,
                quality=track.audio.quality,
                file_format=track.audio.container,
                source_url=track.info.url,
            )

            download_ids.append(record.id)

        logger.info("Added %d tracks to session %s", len(download_ids), session_id)
        return download_ids

    def add_playlist_tracks_to_session(
        self, session_id: str, playlist: Playlist, tracks: list[Track]
    ) -> list[str]:
        """Add all tracks from a playlist to a download session.

        Args:
            session_id: Download session ID
            playlist: Playlist containing the tracks
            tracks: List of track models to add

        Returns
        -------
            List of download record IDs
        """
        download_ids = []

        for i, track in enumerate(tracks):
            # Skip if already downloaded
            if self.download_service.is_already_downloaded(
                track.info.source, track.info.id, MediaType.TRACK
            ):
                logger.info("Skipping already downloaded track: %s", track.title)
                continue

            # Get playlist track info if available
            playlist_track = None
            if i < len(playlist.tracks):
                playlist_track = playlist.tracks[i]

            record = self.download_service.add_download_to_session(
                session_id=session_id,
                media_type=MediaType.TRACK,
                source=track.info.source,
                source_id=track.info.id,
                title=(playlist_track.display_title if playlist_track else None)
                or track.title,
                artist=(playlist_track.display_artist if playlist_track else None)
                or track.artist,
                album=track.album_id,  # May be None for playlist tracks
                track_number=playlist_track.position if playlist_track else i + 1,
                duration_seconds=track.audio.duration_seconds,
                quality=track.audio.quality,
                file_format=track.audio.container,
                source_url=track.info.url,
                extra_metadata={
                    "playlist_position": playlist_track.position
                    if playlist_track
                    else i + 1,
                    "added_to_playlist_at": playlist_track.added_at
                    if playlist_track
                    else None,
                    "playlist_notes": playlist_track.notes if playlist_track else None,
                },
            )

            download_ids.append(record.id)

        logger.info(
            "Added %d tracks from playlist to session %s", len(download_ids), session_id
        )
        return download_ids

    def create_standalone_track_download(self, track: Track) -> str:
        """Create a standalone download for a single track.

        Args:
            track: Track model to download

        Returns
        -------
            Download record ID
        """
        # Check if already downloaded
        if self.download_service.is_already_downloaded(
            track.info.source, track.info.id, MediaType.TRACK
        ):
            logger.info("Track already downloaded: %s", track.title)
            msg = f"Track '{track.title}' has already been downloaded"
            raise ValueError(msg)

        record = self.download_service.create_standalone_download(
            media_type=MediaType.TRACK,
            source=track.info.source,
            source_id=track.info.id,
            title=track.title,
            artist=track.artist,
            album=track.album_id,
            album_artist=track.credits.album_artist,
            track_number=track.info.track_number,
            disc_number=track.info.disc_number,
            duration_seconds=track.audio.duration_seconds,
            quality=track.audio.quality,
            file_format=track.audio.container,
            source_url=track.info.url,
        )

        logger.info("Created standalone download for track: %s", track.title)
        return record.id

    def get_download_status_for_model(
        self, model: Artist | Album | Track | Playlist
    ) -> dict[str, Any]:
        """Get download status information for a model.

        Args:
            model: Model to check download status for

        Returns
        -------
            Dictionary with download status information
        """
        if isinstance(model, Track):
            media_type = MediaType.TRACK
        elif isinstance(model, Album):
            media_type = MediaType.ALBUM
        elif isinstance(model, Artist):
            media_type = MediaType.ARTIST
        elif isinstance(model, Playlist):
            media_type = MediaType.PLAYLIST
        else:
            return {"error": "Unsupported model type"}

        is_downloaded = self.download_service.is_already_downloaded(
            model.info.source, model.info.id, media_type
        )

        # Get active downloads
        active_downloads = self.download_service.get_active_downloads()
        active_download = None
        for download in active_downloads:
            if (
                download.source == model.info.source
                and download.source_id == model.info.id
                and download.media_type == media_type
            ):
                active_download = download
                break

        # Get recent sessions
        sessions = self.download_service.get_download_sessions(
            limit=10, include_completed=True
        )
        related_sessions = [
            session
            for session in sessions
            if (
                session.source == model.info.source
                and session.source_id == model.info.id
                and session.session_type == media_type
            )
        ]

        return {
            "is_downloaded": is_downloaded,
            "active_download": {
                "id": active_download.id,
                "status": active_download.status,
                "progress": active_download.progress_percentage,
                "started_at": active_download.started_at,
                "error_message": active_download.error_message,
            }
            if active_download
            else None,
            "recent_sessions": [
                {
                    "id": session.id,
                    "status": session.status,
                    "progress": session.progress_percentage,
                    "total_items": session.total_items,
                    "completed_items": session.completed_items,
                    "created_at": session.created_at,
                    "completed_at": session.completed_at,
                }
                for session in related_sessions[:3]  # Last 3 sessions
            ],
        }

    def check_duplicate_before_download(
        self, models: list[Artist | Album | Track | Playlist]
    ) -> dict[str, list[Any]]:
        """Check for duplicates before starting downloads.

        Args:
            models: List of models to check

        Returns
        -------
            Dictionary with 'new' and 'duplicates' lists
        """
        new_models = []
        duplicates = []

        for model in models:
            if isinstance(model, Track):
                media_type = MediaType.TRACK
            elif isinstance(model, Album):
                media_type = MediaType.ALBUM
            elif isinstance(model, Artist):
                media_type = MediaType.ARTIST
            elif isinstance(model, Playlist):
                media_type = MediaType.PLAYLIST
            else:
                continue

            is_downloaded = self.download_service.is_already_downloaded(
                model.info.source, model.info.id, media_type
            )

            if is_downloaded:
                duplicates.append(model)
            else:
                new_models.append(model)

        return {
            "new": new_models,
            "duplicates": duplicates,
        }


# Global integration instance
_download_integration: DownloadIntegration | None = None


def get_download_integration() -> DownloadIntegration:
    """Get the global download integration instance.

    Returns
    -------
        DownloadIntegration instance
    """
    global _download_integration
    if _download_integration is None:
        _download_integration = DownloadIntegration()
    return _download_integration
