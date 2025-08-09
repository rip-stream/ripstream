# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Qobuz downloader implementation."""

import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast
from uuid import uuid4

import aiofiles

from ripstream.downloader.base import (
    BaseDownloader,
    DownloadableContent,
    DownloadResult,
)
from ripstream.downloader.config import DownloaderConfig
from ripstream.downloader.enums import ContentType
from ripstream.downloader.exceptions import (
    AuthenticationError,
    ContentNotFoundError,
    DownloadError,
)
from ripstream.downloader.progress import ProgressTracker
from ripstream.downloader.qobuz.client import QobuzClient
from ripstream.downloader.qobuz.models import (
    QobuzCredentials,
    QobuzTrackResponse,
)
from ripstream.downloader.session import SessionManager
from ripstream.models.album import Album
from ripstream.models.artist import Artist
from ripstream.models.artwork import Covers
from ripstream.models.enums import AudioQuality, StreamingSource
from ripstream.models.playlist import Playlist
from ripstream.models.track import Track
from ripstream.ui.config_manager import ConfigManager

logger = logging.getLogger(__name__)


class QobuzDownloader(BaseDownloader):
    """Qobuz music downloader."""

    def __init__(
        self,
        config: DownloaderConfig,
        session_manager: SessionManager,
        progress_tracker: ProgressTracker,
    ) -> None:
        super().__init__(config, session_manager, progress_tracker)
        self.client = QobuzClient(session_manager, self._update_qobuz_config)
        self._authenticated = False

    def _update_qobuz_config(self, app_id: str, secrets: list[str]) -> None:
        """Update Qobuz config with retrieved app_id and secrets."""
        try:
            logger.info(
                "Saving retrieved Qobuz app_id: %s and %d secrets to config",
                app_id,
                len(secrets),
            )

            # Create config manager and load current config
            config_manager = ConfigManager()
            config = config_manager.get_config()

            # Update the Qobuz config with retrieved secrets
            config.qobuz.app_id = app_id
            config.qobuz.secrets = secrets

            # Save the updated config
            config_manager.save_config()
            logger.info("Successfully saved Qobuz secrets to config")

        except Exception:
            logger.exception("Failed to save Qobuz secrets to config")

    @property
    def source_name(self) -> str:
        """Get the name of the download source."""
        return "qobuz"

    @property
    def supported_content_types(self) -> list[ContentType]:
        """Get list of supported content types."""
        return [
            ContentType.TRACK,
            ContentType.ALBUM,
            ContentType.PLAYLIST,
        ]

    async def authenticate(self, credentials: dict[str, Any]) -> bool:
        """Authenticate with Qobuz."""
        try:
            qobuz_creds = QobuzCredentials(
                email_or_userid=credentials.get("email_or_userid", ""),
                password_or_token=credentials.get("password_or_token", ""),
                app_id=credentials.get("app_id"),
                secrets=credentials.get("secrets", []),
                use_auth_token=credentials.get("use_auth_token", False),
            )

            self._authenticated = await self.client.authenticate(qobuz_creds)
        except Exception:
            logger.exception("Qobuz authentication failed")
            self._authenticated = False
            return False
        else:
            return self._authenticated

    async def get_download_info(self, content_id: str) -> DownloadableContent:
        """Get download information for content."""
        if not self._authenticated:
            msg = "Not authenticated with Qobuz"
            raise AuthenticationError(msg)

        # Determine content type from ID format
        content_type = self._determine_content_type(content_id)

        if content_type == ContentType.TRACK:
            return await self._get_track_download_info(content_id)
        if content_type == ContentType.ALBUM:
            return await self._get_album_download_info(content_id)
        if content_type == ContentType.PLAYLIST:
            return await self._get_playlist_download_info(content_id)
        msg = f"Unsupported content type for download: {content_type}"
        raise DownloadError(msg)

    async def get_track_metadata(self, track_id: str) -> Track:
        """Get track metadata."""
        if not self._authenticated:
            msg = "Not authenticated with Qobuz"
            raise AuthenticationError(msg)

        qobuz_track = await self.client.get_track_info(track_id)

        # Convert Qobuz track response to our Track model
        track_data = {
            "title": qobuz_track.title,
            "artist": qobuz_track.artist_name,
            "album": qobuz_track.album_title,
            "album_artist": qobuz_track.album_artist,
            "track_number": qobuz_track.track_number,
            "disc_number": qobuz_track.disc_number,
            "duration": qobuz_track.duration,
            "isrc": qobuz_track.isrc,
            "copyright": qobuz_track.copyright,
            "is_explicit": qobuz_track.parental_warning,
            "quality": self._map_qobuz_quality(qobuz_track),
            "bit_depth": qobuz_track.maximum_bit_depth,
            "sampling_rate": int(qobuz_track.maximum_sampling_rate)
            if qobuz_track.maximum_sampling_rate
            else None,
            "is_lossless": qobuz_track.maximum_bit_depth is not None
            and qobuz_track.maximum_bit_depth > 16,
            "version": qobuz_track.version,
            "composer": qobuz_track.composer.get("name")
            if qobuz_track.composer
            else None,
        }

        return Track.from_source_data(
            source=StreamingSource.QOBUZ,
            track_id=track_id,
            data=track_data,
        )

    async def get_album_metadata(self, album_id: str) -> Album:
        """Get album metadata."""
        if not self._authenticated:
            msg = "Not authenticated with Qobuz"
            raise AuthenticationError(msg)

        qobuz_album = await self.client.get_album_info(album_id)

        # Create covers object from Qobuz response
        covers = Covers.from_qobuz_response(qobuz_album)

        # Convert Qobuz album response to our Album model
        album_data = {
            "title": qobuz_album.title,
            "artist": qobuz_album.artist_name,
            "release_date": qobuz_album.release_date_original,
            "release_year": self._extract_year_from_date(
                qobuz_album.release_date_original
            ),
            "label": qobuz_album.label_name,
            "total_tracks": qobuz_album.tracks_count,
            "total_duration": qobuz_album.duration,
            "genres": qobuz_album.genres_list
            or ([qobuz_album.genre_name] if qobuz_album.genre_name else []),
            "description": qobuz_album.description,
            "copyright": qobuz_album.copyright,
            "barcode": qobuz_album.upc,
            "version": qobuz_album.version,
            "covers": covers,
            "booklets": qobuz_album.get_booklets(),
            "hires": qobuz_album.hires,
            "is_explicit": qobuz_album.parental_warning,
        }

        # Extract track IDs if available
        track_ids = []
        if qobuz_album.tracks and "items" in qobuz_album.tracks:
            track_ids = [str(track["id"]) for track in qobuz_album.tracks["items"]]

        return Album.from_source_data(
            source=StreamingSource.QOBUZ,
            album_id=album_id,
            data={**album_data, "track_ids": track_ids},
        )

    async def get_playlist_metadata(self, playlist_id: str) -> Playlist:
        """Get playlist metadata."""
        if not self._authenticated:
            msg = "Not authenticated with Qobuz"
            raise AuthenticationError(msg)

        qobuz_playlist = await self.client.get_playlist_info(playlist_id)

        # Convert Qobuz playlist response to our Playlist model
        playlist_data = {
            "name": qobuz_playlist.name,
            "description": qobuz_playlist.description,
            "owner": qobuz_playlist.owner_name,
            "owner_id": str(qobuz_playlist.owner.get("id", "")),
            "total_tracks": qobuz_playlist.tracks_count,
            "total_duration": qobuz_playlist.duration,
            "is_public": qobuz_playlist.is_public,
            "is_collaborative": qobuz_playlist.is_collaborative,
        }

        # Extract tracks with position information
        tracks = []
        if qobuz_playlist.tracks and "items" in qobuz_playlist.tracks:
            for i, track_data in enumerate(qobuz_playlist.tracks["items"], 1):
                tracks.append({
                    "id": str(track_data["id"]),
                    "position": i,
                    "added_at": None,  # Qobuz doesn't provide this
                    "added_by": None,  # Qobuz doesn't provide this
                })

        return Playlist.from_source_data(
            source=StreamingSource.QOBUZ,
            playlist_id=playlist_id,
            data={**playlist_data, "tracks": tracks},
        )

    async def get_artist_metadata(self, artist_id: str) -> Artist:
        """Get artist metadata."""
        if not self._authenticated:
            msg = "Not authenticated with Qobuz"
            raise AuthenticationError(msg)

        qobuz_artist = await self.client.get_artist_info(artist_id)

        # Create covers object from Qobuz response
        covers = Covers.from_qobuz_response(qobuz_artist)

        # Convert Qobuz artist response to our Artist model
        artist_data = {
            "name": qobuz_artist.name,
            "biography": qobuz_artist.biography.get("content")
            if qobuz_artist.biography
            else None,
            "covers": covers,
        }

        # Extract album IDs and raw album items if available
        album_ids: list[str] = []
        albums_items: list[dict] = []
        if qobuz_artist.albums and "items" in qobuz_artist.albums:
            albums_items = qobuz_artist.albums["items"] or []
            album_ids = [
                str(album.get("id"))
                for album in albums_items
                if album.get("id") is not None
            ]

        return Artist.from_source_data(
            source=StreamingSource.QOBUZ,
            artist_id=artist_id,
            data={**artist_data, "album_ids": album_ids, "albums_items": albums_items},
        )

    async def search(
        self, query: str, content_type: ContentType = ContentType.TRACK, limit: int = 50
    ) -> list[Track | Album | Artist]:
        """Search for content."""
        if not self._authenticated:
            msg = "Not authenticated with Qobuz"
            raise AuthenticationError(msg)

        # Map content type to Qobuz search type
        search_type_map = {
            ContentType.TRACK: "track",
            ContentType.ALBUM: "album",
            ContentType.PLAYLIST: "playlist",
        }

        search_type = search_type_map.get(content_type)
        if not search_type:
            msg = f"Unsupported search content type: {content_type}"
            raise ValueError(msg)

        search_result = await self.client.search(query, search_type, limit)

        results = []
        if content_type == ContentType.TRACK and search_result.tracks:
            items = search_result.tracks.get("items", [])
            for item in items:
                track = await self.get_track_metadata(str(item["id"]))
                results.append(track)
        elif content_type == ContentType.ALBUM and search_result.albums:
            items = search_result.albums.get("items", [])
            for item in items:
                album = await self.get_album_metadata(str(item["id"]))
                results.append(album)
        # Note: Artist search not currently supported as a ContentType
        # Artists can be found through album/track metadata

        return results

    async def _download_content(
        self,
        content: DownloadableContent,
        file_path: str,
        progress_callback: Callable[[int], None] | None = None,
    ) -> None:
        """Download content to file."""
        if not self._authenticated:
            msg = "Not authenticated with Qobuz"
            raise AuthenticationError(msg)

        # Get download session
        session = await self.session_manager.get_session("qobuz")

        try:
            # Stream download with progress tracking
            async with session.get(content.url) as response:
                response.raise_for_status()

                # Get content length for progress tracking
                content_length = response.headers.get("Content-Length")
                total_size = int(content_length) if content_length else None
                logger.info(
                    "Download started: total_size=%s, url=%s", total_size, content.url
                )

                # Update progress tracker with actual total size from HTTP headers
                # This is crucial for percentage calculations!
                if (
                    total_size
                    and hasattr(self, "progress_tracker")
                    and self.progress_tracker
                ):
                    # We need to find the current download_id to update the progress tracker
                    # Since we don't have direct access to download_id here, we'll update all active downloads
                    all_progress = self.progress_tracker.get_all_progress()
                    for download_id, progress in all_progress.items():
                        if progress.is_active and progress.total_bytes is None:
                            logger.info(
                                "Setting total_size=%d for download_id=%s",
                                total_size,
                                download_id,
                            )
                            self.progress_tracker.set_total_size(
                                download_id, total_size
                            )
                            break

                downloaded = 0
                chunk_size = 8192

                async with aiofiles.open(file_path, "wb") as f:
                    async for chunk in response.content.iter_chunked(chunk_size):
                        await f.write(chunk)
                        downloaded += len(chunk)

                        # Call progress callback if provided
                        if progress_callback is not None:
                            try:
                                progress_callback(downloaded)
                            except Exception:
                                logger.exception("Error in progress callback")

        except Exception as e:
            msg = f"Failed to download content: {e}"
            raise DownloadError(msg) from e

    async def _get_track_download_info(self, track_id: str) -> DownloadableContent:
        """Get download info for a specific track."""
        # Get track metadata
        qobuz_track = await self.client.get_track_info(track_id)

        # Get download info with highest quality
        download_info = await self.client.get_download_info(track_id, quality=4)

        # Determine file extension based on quality
        file_extension = "flac" if download_info.format_id > 5 else "mp3"

        # Create track filename using user's template
        track_filename = self._format_track_filename(qobuz_track, file_extension)

        return DownloadableContent(
            content_id=track_id,
            content_type=ContentType.TRACK,
            source=self.source_name,
            title=qobuz_track.title,
            artist=qobuz_track.artist_name,
            album=qobuz_track.album_title,
            url=download_info.url,
            file_name=track_filename,
            file_extension=file_extension,
            expected_size=None,  # Qobuz doesn't provide size in advance
            checksum=None,  # Qobuz doesn't provide checksums
            quality=str(download_info.format_id),
            format=file_extension.upper(),
            bitrate=self._get_bitrate_for_quality(download_info.format_id),
            metadata={
                "album_id": qobuz_track.album.get("id") if qobuz_track.album else None,
                "audio_info": {
                    "container": file_extension.upper(),
                    "bit_depth": 24 if download_info.format_id > 5 else 16,
                    "sampling_rate": 44100,  # Default, could be enhanced with actual track info
                },
            },
        )

    def _format_folder_name(self, qobuz_album, audio_info: dict | None = None) -> str:
        """Format folder name using the user's folder_format template."""
        # Get folder format from source settings, fallback to default
        source_settings = self.config.source_settings.get("default", {})
        folder_format = source_settings.get(
            "folder_format",
            "{albumartist} - {title} ({year}) [{container}] [{bit_depth}B-{sampling_rate}kHz]",
        )

        # Extract year from release date
        year = ""
        if qobuz_album.release_date_original:
            year = self._extract_year_from_date(qobuz_album.release_date_original)

        # Prepare template variables
        template_vars = {
            "albumartist": self._sanitize_filename(qobuz_album.artist_name),
            "artist": self._sanitize_filename(qobuz_album.artist_name),
            "title": self._sanitize_filename(qobuz_album.title),
            "year": year or "",
            "container": audio_info.get("container", "FLAC") if audio_info else "FLAC",
            "bit_depth": str(audio_info.get("bit_depth", 24)) if audio_info else "24",
            "sampling_rate": str(audio_info.get("sampling_rate", 44100) // 1000)
            if audio_info
            else "44.1",
        }

        try:
            # Format the folder name using the template
            folder_name = folder_format.format(**template_vars)
            return self._sanitize_filename(folder_name)
        except (KeyError, ValueError) as e:
            # Fallback to simple format if template formatting fails
            logger.warning(
                "Failed to format folder name with template '%s': %s", folder_format, e
            )
            safe_title = self._sanitize_filename(qobuz_album.title)
            safe_artist = self._sanitize_filename(qobuz_album.artist_name)
            fallback_name = f"{safe_artist} - {safe_title}"
            if year:
                fallback_name += f" ({year})"
            return fallback_name

    def _format_track_filename(self, qobuz_track, file_extension: str) -> str:  # noqa: ARG002
        """Format track filename using the user's track_format template."""
        # Get track format from source settings, fallback to default
        source_settings = self.config.source_settings.get("default", {})
        track_format = source_settings.get(
            "track_format", "{tracknumber:02}. {artist} - {title}{explicit}"
        )

        # Prepare template variables
        template_vars = {
            "tracknumber": qobuz_track.track_number,
            "artist": self._sanitize_filename(qobuz_track.artist_name),
            "title": self._sanitize_filename(qobuz_track.title),
            "albumartist": self._sanitize_filename(qobuz_track.album_artist),
            "album": self._sanitize_filename(qobuz_track.album_title),
            "explicit": " (Explicit)"
            if getattr(qobuz_track, "parental_warning", False)
            else "",
            "disc": qobuz_track.disc_number,
            "discnumber": qobuz_track.disc_number,
        }

        try:
            # Format the track filename using the template
            filename = track_format.format(**template_vars)
            return self._sanitize_filename(filename)
        except (KeyError, ValueError) as e:
            # Fallback to simple format if template formatting fails
            logger.warning(
                "Failed to format track filename with template '%s': %s",
                track_format,
                e,
            )
            safe_title = self._sanitize_filename(qobuz_track.title)
            safe_artist = self._sanitize_filename(qobuz_track.artist_name)
            return f"{qobuz_track.track_number:02d} - {safe_artist} - {safe_title}"

    async def _get_album_download_info(self, album_id: str) -> DownloadableContent:
        """Get download info for an album (returns metadata for bulk download)."""
        qobuz_album = await self.client.get_album_info(album_id)

        # Use the user's folder format template
        folder_name = self._format_folder_name(qobuz_album)

        return DownloadableContent(
            content_id=album_id,
            content_type=ContentType.ALBUM,
            source=self.source_name,
            title=qobuz_album.title,
            artist=qobuz_album.artist_name,
            album=qobuz_album.title,
            url="",  # Albums don't have direct URLs
            file_name=folder_name,
            file_extension="",  # Albums are folders
            expected_size=None,
            checksum=None,
            quality="album",
            format="ALBUM",
            bitrate=None,
            metadata={
                "track_count": qobuz_album.tracks_count,
                "total_duration": qobuz_album.duration,
                "track_ids": [
                    str(track["id"]) for track in qobuz_album.tracks.get("items", [])
                ]
                if qobuz_album.tracks
                else [],
            },
        )

    async def _get_playlist_download_info(
        self, playlist_id: str
    ) -> DownloadableContent:
        """Get download info for a playlist (returns metadata for bulk download)."""
        qobuz_playlist = await self.client.get_playlist_info(playlist_id)

        # Create safe filename for playlist folder
        safe_name = self._sanitize_filename(qobuz_playlist.name)
        safe_owner = self._sanitize_filename(qobuz_playlist.owner_name)
        folder_name = f"{safe_owner} - {safe_name}"

        return DownloadableContent(
            content_id=playlist_id,
            content_type=ContentType.PLAYLIST,
            source=self.source_name,
            title=qobuz_playlist.name,
            artist=qobuz_playlist.owner_name,
            album="",
            url="",  # Playlists don't have direct URLs
            file_name=folder_name,
            file_extension="",  # Playlists are folders
            expected_size=None,
            checksum=None,
            quality="playlist",
            format="PLAYLIST",
            bitrate=None,
            metadata={
                "track_count": qobuz_playlist.tracks_count,
                "total_duration": qobuz_playlist.duration,
                "track_ids": [
                    str(track["id"]) for track in qobuz_playlist.tracks.get("items", [])
                ]
                if qobuz_playlist.tracks
                else [],
            },
        )

    async def download_track_with_album_folder(
        self, track_id: str, download_directory: str | None = None
    ) -> DownloadResult:
        """Download a single track with proper album folder structure."""
        # Get track download info
        track_info = await self._get_track_download_info(track_id)

        # Get album info for folder creation if available
        album_folder = ""
        if track_info.metadata and track_info.metadata.get("album_id"):
            try:
                album_id = track_info.metadata["album_id"]
                qobuz_album = await self.client.get_album_info(album_id)
                audio_info = track_info.metadata.get("audio_info", {})
                album_folder = self._format_folder_name(qobuz_album, audio_info)
            except (KeyError, ValueError, AttributeError) as e:
                logger.warning("Failed to get album info for track %s: %s", track_id, e)
                # Fallback to simple folder name
                album_folder = f"{track_info.artist} - {track_info.album}"

        # Determine download path
        if download_directory:
            base_path = Path(download_directory)
        else:
            base_path = Path(self.config.download_directory)

        # Create album folder if we have one
        track_path = base_path / album_folder if album_folder else base_path

        # Ensure directory exists
        track_path.mkdir(parents=True, exist_ok=True)

        # Download the track to the album folder
        return await self.download(track_info, str(track_path))

    async def download_album(
        self,
        album_id: str,
        download_directory: str | None = None,
        download_artwork: bool = True,
        download_booklets: bool = True,
    ) -> list[DownloadResult]:
        """Download all tracks in an album, plus artwork and booklets."""
        if not self._authenticated:
            msg = "Not authenticated with Qobuz"
            raise AuthenticationError(msg)

        # Get album metadata
        album = await self.get_album_metadata(album_id)

        # Create album folder
        album_folder = album.get_download_folder_name()
        if download_directory:
            album_path = Path(download_directory) / album_folder
        else:
            album_path = Path(self.config.download_directory) / album_folder

        album_path.mkdir(parents=True, exist_ok=True)

        all_results = []

        # Prefetch artwork first so tracks can embed without racing
        if download_artwork and hasattr(album, "covers"):
            try:
                from ripstream.metadata.artwork import (
                    build_artwork_config,
                )
                from ripstream.metadata.artwork import (
                    download_artwork as prefetch_download_artwork,
                )

                # Build artwork config from source settings
                source_settings = self.config.source_settings.get("default", {})
                artwork_config = build_artwork_config(source_settings)

                # Session for artwork
                session = await self.session_manager.get_session("qobuz")

                # Extract URLs and download to album folder
                album_info_for_art = await self.client.get_album_info(album_id)
                artwork_urls = self._extract_artwork_urls(album_info_for_art)
                # Only prefetch if we have URLs
                if artwork_urls:
                    await prefetch_download_artwork(
                        session,
                        str(album_path),
                        artwork_urls,
                        artwork_config,
                    )
            except Exception:
                logger.exception("Failed to prefetch artwork for album %s", album_id)

        # Download tracks
        track_results = await self.download_multiple(
            [
                await self._get_track_download_info(track_id)
                for track_id in album.track_ids
            ],
            str(album_path),
        )
        all_results.extend(track_results)

        # Download booklets if requested and available
        if download_booklets:
            try:
                booklet_results = await self.download_booklets(
                    album_id, str(album_path)
                )
                all_results.extend(booklet_results)
            except Exception:
                logger.exception("Failed to download booklets for album %s", album_id)

        return all_results

    async def download_playlist(
        self, playlist_id: str, download_directory: str | None = None
    ) -> list[DownloadResult]:
        """Download all tracks in a playlist."""
        if not self._authenticated:
            msg = "Not authenticated with Qobuz"
            raise AuthenticationError(msg)

        # Get playlist metadata
        playlist = await self.get_playlist_metadata(playlist_id)

        # Create playlist folder
        playlist_folder = playlist.get_download_folder_name()
        if download_directory:
            playlist_path = Path(download_directory) / playlist_folder
        else:
            playlist_path = Path(self.config.download_directory) / playlist_folder

        playlist_path.mkdir(parents=True, exist_ok=True)

        # Get track IDs from playlist
        track_ids = playlist.get_track_ids()

        # Download all tracks
        return await self.download_multiple(
            [await self._get_track_download_info(track_id) for track_id in track_ids],
            str(playlist_path),
        )

    async def download_artist_discography(
        self, artist_id: str, download_directory: str | None = None
    ) -> list[DownloadResult]:
        """Download an artist's complete discography."""
        if not self._authenticated:
            msg = "Not authenticated with Qobuz"
            raise AuthenticationError(msg)

        # Search for artist's albums
        search_results = await self.search(
            f"artist_id:{artist_id}", ContentType.ALBUM, limit=100
        )
        artist_albums = cast("list[Album]", search_results)

        if not artist_albums:
            # Fallback: get artist info and search by name
            # This would require implementing get_artist_metadata method
            msg = f"No albums found for artist {artist_id}"
            raise ContentNotFoundError(msg)

        # Create artist folder
        artist_name = (
            artist_albums[0].artist if artist_albums else f"Artist_{artist_id}"
        )
        safe_artist_name = self._sanitize_filename(artist_name)

        if download_directory:
            artist_path = Path(download_directory) / safe_artist_name
        else:
            artist_path = Path(self.config.download_directory) / safe_artist_name

        artist_path.mkdir(parents=True, exist_ok=True)

        # Download all albums
        all_results = []
        for album in artist_albums:
            album_results = await self.download_album(album.info.id, str(artist_path))
            all_results.extend(album_results)

        return all_results

    async def download_artwork(
        self, album_id: str, download_directory: str, covers: Covers
    ) -> list[DownloadResult]:
        """Download album artwork in different sizes."""
        if not self._authenticated:
            msg = "Not authenticated with Qobuz"
            raise AuthenticationError(msg)

        if not covers.has_images:
            return []

        results = []
        download_path = Path(download_directory)
        download_path.mkdir(parents=True, exist_ok=True)

        # Download each available cover size
        for image in covers.images:
            try:
                # Determine file extension from URL or default to jpg
                file_extension = "jpg"
                if image.format:
                    file_extension = image.format.lower()
                elif "." in image.url:
                    file_extension = image.url.split(".")[-1].split("?")[0]

                # Create filename based on size
                filename = image.get_filename("cover")
                _ = download_path / filename

                # Handle both enum and string values for size
                size_value = (
                    image.size.value
                    if hasattr(image.size, "value")
                    else str(image.size)
                )

                # Create downloadable content
                downloadable = DownloadableContent(
                    content_id=f"{album_id}_artwork_{size_value}",
                    content_type=ContentType.TRACK,  # Using TRACK as base type
                    source=self.source_name,
                    title=f"Cover Art ({size_value})",
                    artist="",
                    album="",
                    url=image.url,
                    file_name=filename.rsplit(".", 1)[0],
                    file_extension=file_extension,
                    expected_size=image.file_size_bytes,
                    checksum=None,
                    quality="artwork",
                    format="IMAGE",
                    bitrate=None,
                )

                # Download the artwork
                result = await self.download(downloadable, str(download_path))
                results.append(result)

                # Update image with local path if successful
                if result.success and result.file_path:
                    image.local_path = result.file_path

            except Exception as exc:
                logger.exception("Failed to download artwork %s", image.url)
                # Create failed result
                results.append(
                    DownloadResult(
                        download_id=uuid4(),
                        success=False,
                        file_path=None,
                        file_size=None,
                        checksum=None,
                        duration_seconds=0.0,
                        average_speed_bps=None,
                        error_message=str(exc),
                        retry_count=0,
                        metadata={"artwork_url": image.url},
                    )
                )

        return results

    async def download_booklets(
        self, album_id: str, download_directory: str
    ) -> list[DownloadResult]:
        """Download album booklets and additional materials."""
        if not self._authenticated:
            msg = "Not authenticated with Qobuz"
            raise AuthenticationError(msg)

        # Get album info to access booklets
        qobuz_album = await self.client.get_album_info(album_id)
        booklets = qobuz_album.get_booklets()

        if not booklets:
            return []

        results = []
        download_path = Path(download_directory)
        download_path.mkdir(parents=True, exist_ok=True)

        for booklet in booklets:
            try:
                # Create safe filename
                filename = self._sanitize_filename(booklet["name"])
                if not filename.lower().endswith(".pdf"):
                    filename += ".pdf"

                # Create downloadable content
                downloadable = DownloadableContent(
                    content_id=f"{album_id}_booklet_{hash(booklet['url'])}",
                    content_type=ContentType.TRACK,  # Using TRACK as base type
                    source=self.source_name,
                    title=booklet.get("description", "Album Booklet"),
                    artist="",
                    album="",
                    url=booklet["url"],
                    file_name=filename.rsplit(".", 1)[0],
                    file_extension="pdf",
                    expected_size=None,
                    checksum=None,
                    quality="booklet",
                    format="PDF",
                    bitrate=None,
                )

                # Download the booklet
                result = await self.download(downloadable, str(download_path))
                results.append(result)

            except Exception as exc:
                logger.exception("Failed to download booklet %s", booklet["url"])
                # Create failed result
                results.append(
                    DownloadResult(
                        download_id=uuid4(),
                        success=False,
                        file_path=None,
                        file_size=None,
                        checksum=None,
                        duration_seconds=0.0,
                        average_speed_bps=None,
                        error_message=str(exc),
                        retry_count=0,
                        metadata={"booklet_url": booklet["url"]},
                    )
                )

        return results

    def _determine_content_type(self, content_id: str) -> ContentType:
        """Determine content type from ID format."""
        # This is a simple heuristic - in practice you might need more sophisticated logic
        # or additional API calls to determine the type
        if len(content_id) <= 10 and content_id.isdigit():
            return ContentType.TRACK
        # For now, assume longer IDs are albums
        return ContentType.ALBUM

    def _map_qobuz_quality(self, qobuz_track: QobuzTrackResponse) -> int:
        """Map Qobuz quality info to our quality scale."""
        if qobuz_track.maximum_bit_depth and qobuz_track.maximum_bit_depth >= 24:
            return AudioQuality.HI_RES
        if qobuz_track.maximum_bit_depth and qobuz_track.maximum_bit_depth >= 16:
            return AudioQuality.LOSSLESS
        return AudioQuality.HIGH

    def _extract_year_from_date(self, date_string: str | None) -> int | None:
        """Extract year from date string."""
        if not date_string:
            return None
        try:
            # Assume format is YYYY-MM-DD or similar
            return int(date_string.split("-")[0])
        except (ValueError, IndexError):
            return None

    def _get_bitrate_for_quality(self, format_id: int) -> int | None:
        """Get bitrate for Qobuz format ID."""
        bitrate_map = {
            5: 320,  # MP3 320
            6: 1411,  # FLAC 16/44.1
            7: 2304,  # FLAC 24/96 (approximate)
            27: 4608,  # FLAC 24/192 (approximate)
        }
        return bitrate_map.get(format_id)

    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for filesystem compatibility."""
        # Remove or replace invalid characters
        invalid_chars = '<>:"/\\|?*'
        safe_name = filename
        for char in invalid_chars:
            safe_name = safe_name.replace(char, "_")

        # Limit length
        if len(safe_name) > 100:
            safe_name = safe_name[:100]

        return safe_name.strip()

    async def _postprocess_downloaded_file(
        self, content: DownloadableContent, file_path: str
    ) -> None:
        """Post-process downloaded audio file with metadata and artwork embedding."""
        # Only process audio files, skip artwork and booklets
        if content.content_type != ContentType.TRACK:
            return

        # Skip if file doesn't exist or isn't an audio file
        if not Path(file_path).exists():
            logger.warning(
                "Downloaded file not found for post-processing: %s", file_path
            )
            return

        file_ext = Path(file_path).suffix.lower()
        if file_ext not in [".flac", ".mp3", ".m4a", ".mp4", ".aac"]:
            logger.debug("Skipping post-processing for non-audio file: %s", file_path)
            return

        try:
            # Get source settings for metadata and artwork configuration
            source_settings = self.config.source_settings.get("default", {})

            # Check if metadata embedding is enabled
            embed_metadata = source_settings.get("embed_metadata", True)
            embed_artwork = source_settings.get("embed_artwork", True)

            if not (embed_metadata or embed_artwork):
                logger.debug(
                    "Metadata and artwork embedding disabled, skipping post-processing"
                )
                return

            # Get track metadata for embedding
            track_metadata = await self._get_track_metadata_for_embedding(
                content.content_id
            )

            # Download and prepare artwork if embedding is enabled
            cover_path = None
            if embed_artwork:
                cover_path = await self._prepare_artwork_for_embedding(
                    content.content_id, file_path, source_settings
                )

            # Embed metadata and artwork
            if embed_metadata and track_metadata:
                from ripstream.metadata import tag_file

                await tag_file(file_path, track_metadata, cover_path)
                logger.info(
                    "Successfully embedded metadata and artwork for: %s", file_path
                )
            elif embed_artwork and cover_path:
                # If only artwork embedding is enabled
                from ripstream.metadata import tag_file

                await tag_file(file_path, {}, cover_path)
                logger.info("Successfully embedded artwork for: %s", file_path)

        except Exception:
            logger.exception("Failed to post-process file %s", file_path)
            # Don't raise the exception - post-processing failure shouldn't fail the download

    async def _get_track_metadata_for_embedding(
        self, track_id: str
    ) -> dict[str, Any] | None:
        """Get track metadata formatted for embedding."""
        try:
            # Get track info from Qobuz
            qobuz_track = await self.client.get_track_info(track_id)

            # Convert to metadata dictionary for tagging
            metadata = {
                "title": qobuz_track.title,
                "artist": qobuz_track.artist_name,
                "album": qobuz_track.album_title,
                "albumartist": qobuz_track.album_artist,
                "tracknumber": qobuz_track.track_number,
                "discnumber": qobuz_track.disc_number,
                "year": self._extract_year_from_date(
                    qobuz_track.album.get("release_date_original")
                )
                if qobuz_track.album
                else None,
                "genre": qobuz_track.album.get("genre", {}).get("name")
                if qobuz_track.album
                else None,
                "isrc": qobuz_track.isrc,
                "copyright": qobuz_track.copyright,
                "composer": qobuz_track.composer.get("name")
                if qobuz_track.composer
                else None,
            }

            # Get album info for additional metadata
            if qobuz_track.album and qobuz_track.album.get("id"):
                try:
                    album_info = await self.client.get_album_info(
                        str(qobuz_track.album["id"])
                    )
                    metadata.update({
                        "tracktotal": album_info.tracks_count,
                        "disctotal": getattr(album_info, "disc_total", 1),
                        "date": album_info.release_date_original,
                        "label": album_info.label_name,
                    })
                except (AuthenticationError, ContentNotFoundError, DownloadError):
                    logger.debug("Could not get album info for additional metadata")

            # Remove None values
            return {k: v for k, v in metadata.items() if v is not None}

        except Exception:
            logger.exception("Failed to get track metadata for %s", track_id)
            return None

    def _extract_artwork_urls(self, album_info) -> dict[str, str]:
        """Extract artwork URLs from album info."""
        artwork_urls = {}
        if hasattr(album_info.image, "get"):
            # Handle dictionary format
            for size in ["large", "small", "thumbnail"]:
                if size in album_info.image:
                    artwork_urls[size] = album_info.image[size]

            # Add original size if available
            if "large" in album_info.image:
                artwork_urls["original"] = "org".join(
                    album_info.image["large"].rsplit("600", 1)
                )
        return artwork_urls

    def _find_fallback_artwork(self, file_path: str) -> str | None:
        """Find fallback artwork files in the directory."""
        folder_path = Path(file_path).parent
        fallback_files = [
            folder_path / "cover.jpg",
            folder_path / "cover.jpeg",
            folder_path / "cover.png",
            folder_path / "folder.jpg",
            folder_path / "folder.jpeg",
            folder_path / "folder.png",
        ]

        for fallback_file in fallback_files:
            if fallback_file.exists():
                logger.info("Using fallback cover art: %s", fallback_file)
                return str(fallback_file)

        logger.warning("No fallback cover art found in directory: %s", folder_path)
        return None

    async def _prepare_artwork_for_embedding(
        self, track_id: str, file_path: str, source_settings: dict[str, Any]
    ) -> str | None:
        """Download and prepare artwork for embedding."""
        try:
            # Get track info to access album artwork
            qobuz_track = await self.client.get_track_info(track_id)

            if not qobuz_track.album or not qobuz_track.album.get("id"):
                logger.debug("No album info available for artwork")
                return None

            # Get album info with artwork
            album_info = await self.client.get_album_info(str(qobuz_track.album["id"]))

            if not hasattr(album_info, "image") or not album_info.image:
                logger.debug("No artwork available for album")
                return None

            # Extract artwork URLs
            artwork_urls = self._extract_artwork_urls(album_info)
            if not artwork_urls:
                logger.debug("No artwork URLs found")
                return None

            # Download artwork using our artwork module
            from ripstream.metadata.artwork import download_artwork

            # Get session for downloading
            session = await self.session_manager.get_session("qobuz")

            # Prepare artwork config
            artwork_config = {
                "embed_artwork": True,
                "save_artwork": source_settings.get("save_artwork", False),
                "embed_size": source_settings.get("artwork_size", "large"),
                "embed_max_width": source_settings.get("artwork_max_width", 0),
                "saved_max_width": source_settings.get("saved_artwork_max_width", 0),
            }

            # Download artwork
            folder = str(Path(file_path).parent)
            logger.debug(
                "Downloading artwork for track %s to folder %s with URLs: %s",
                track_id,
                folder,
                artwork_urls,
            )
            embed_cover_path, _ = await download_artwork(
                session, folder, artwork_urls, artwork_config
            )
            logger.debug(
                "Artwork download result: embed_cover_path=%s", embed_cover_path
            )

            # Verify the artwork file was actually downloaded
            if embed_cover_path and Path(embed_cover_path).exists():
                logger.debug("Successfully downloaded artwork to: %s", embed_cover_path)
                return embed_cover_path
            logger.warning(
                "Artwork download failed or file not found: %s", embed_cover_path
            )

            # Fallback: Look for existing cover art files in the album directory
            return self._find_fallback_artwork(file_path)

        except Exception:
            logger.exception("Failed to prepare artwork for %s", track_id)
            return None

    async def cleanup(self) -> None:
        """Cleanup resources."""
        await super().cleanup()
        await self.client.close()
        self._authenticated = False

        # Clean up any temporary artwork directories with error handling
        try:
            from ripstream.metadata.artwork import (
                cleanup_failed_artwork_dirs,
                remove_artwork_tempdirs,
            )

            # First try to cleanup any previously failed directories
            cleanup_failed_artwork_dirs()

            # Then cleanup current directories
            remove_artwork_tempdirs()
        except (ImportError, OSError, RuntimeError) as e:
            logger.warning("Failed to cleanup artwork temp directories: %s", e)
