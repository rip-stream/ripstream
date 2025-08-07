# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Tests for Qobuz download provider."""

from collections.abc import Callable
from typing import Any
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest

from ripstream.downloader.base import DownloadResult
from ripstream.downloader.config import DownloaderConfig
from ripstream.downloader.enums import ContentType
from ripstream.downloader.progress import ProgressTracker
from ripstream.downloader.providers.qobuz import QobuzDownloadProvider
from ripstream.downloader.qobuz.downloader import QobuzDownloader
from ripstream.downloader.session import SessionManager
from ripstream.models.enums import StreamingSource


class TestQobuzDownloadProvider:
    """Test cases for QobuzDownloadProvider."""

    @pytest.mark.parametrize(
        "credentials",
        [
            {"username": "test", "password": "test"},
            {"api_key": "test_key"},
            {},
            None,
        ],
    )
    def test_initialization(
        self,
        mock_download_config: DownloaderConfig,
        mock_session_manager: SessionManager,
        mock_progress_tracker: ProgressTracker,
        credentials: dict[str, Any] | None,
    ) -> None:
        """Test QobuzDownloadProvider initialization."""
        provider = QobuzDownloadProvider(
            mock_download_config,
            mock_session_manager,
            mock_progress_tracker,
            credentials,
        )

        assert provider.config == mock_download_config
        assert provider.session_manager == mock_session_manager
        assert provider.progress_tracker == mock_progress_tracker
        assert provider.credentials == (credentials or {})
        assert provider._authenticated is False
        assert provider._downloader is None

    def test_service_name_property(
        self,
        mock_download_config: DownloaderConfig,
        mock_session_manager: SessionManager,
        mock_progress_tracker: ProgressTracker,
    ) -> None:
        """Test service_name property."""
        provider = QobuzDownloadProvider(
            mock_download_config,
            mock_session_manager,
            mock_progress_tracker,
        )
        assert provider.service_name == "qobuz"

    def test_streaming_source_property(
        self,
        mock_download_config: DownloaderConfig,
        mock_session_manager: SessionManager,
        mock_progress_tracker: ProgressTracker,
    ) -> None:
        """Test streaming_source property."""
        provider = QobuzDownloadProvider(
            mock_download_config,
            mock_session_manager,
            mock_progress_tracker,
        )
        assert provider.streaming_source == StreamingSource.QOBUZ

    def test_supported_content_types_property(
        self,
        mock_download_config: DownloaderConfig,
        mock_session_manager: SessionManager,
        mock_progress_tracker: ProgressTracker,
    ) -> None:
        """Test supported_content_types property."""
        provider = QobuzDownloadProvider(
            mock_download_config,
            mock_session_manager,
            mock_progress_tracker,
        )
        expected_types = [
            ContentType.TRACK,
            ContentType.ALBUM,
            ContentType.PLAYLIST,
            ContentType.ARTIST,
        ]
        assert provider.supported_content_types == expected_types

    @pytest.mark.parametrize(
        ("auth_result", "expected_authenticated"),
        [
            (True, True),
            (False, False),
        ],
    )
    async def test_authenticate_success(
        self,
        mock_download_config: DownloaderConfig,
        mock_session_manager: SessionManager,
        mock_progress_tracker: ProgressTracker,
        sample_credentials: dict[str, Any],
        auth_result: bool,
        expected_authenticated: bool,
    ) -> None:
        """Test successful authentication."""
        with patch(
            "ripstream.downloader.providers.qobuz.QobuzDownloader"
        ) as mock_downloader_class:
            mock_downloader = Mock(spec=QobuzDownloader)
            mock_downloader.authenticate = AsyncMock(return_value=auth_result)
            mock_downloader_class.return_value = mock_downloader

            provider = QobuzDownloadProvider(
                mock_download_config,
                mock_session_manager,
                mock_progress_tracker,
                sample_credentials,
            )

            result = await provider.authenticate()

            assert result == auth_result
            assert provider._authenticated == expected_authenticated
            assert provider._downloader is not None

    async def test_authenticate_failure_exception(
        self,
        mock_download_config: DownloaderConfig,
        mock_session_manager: SessionManager,
        mock_progress_tracker: ProgressTracker,
        sample_credentials: dict[str, Any],
    ) -> None:
        """Test authentication failure with exception."""
        with patch(
            "ripstream.downloader.providers.qobuz.QobuzDownloader"
        ) as mock_downloader_class:
            mock_downloader = Mock(spec=QobuzDownloader)
            mock_downloader.authenticate = AsyncMock(
                side_effect=Exception("Auth failed")
            )
            mock_downloader_class.return_value = mock_downloader

            provider = QobuzDownloadProvider(
                mock_download_config,
                mock_session_manager,
                mock_progress_tracker,
                sample_credentials,
            )

            result = await provider.authenticate()

            assert result is False
            assert provider._authenticated is False

    async def test_authenticate_reuses_existing_downloader(
        self,
        mock_download_config: DownloaderConfig,
        mock_session_manager: SessionManager,
        mock_progress_tracker: ProgressTracker,
        sample_credentials: dict[str, Any],
    ) -> None:
        """Test that authenticate reuses existing downloader."""
        with patch(
            "ripstream.downloader.providers.qobuz.QobuzDownloader"
        ) as mock_downloader_class:
            mock_downloader = Mock(spec=QobuzDownloader)
            mock_downloader.authenticate = AsyncMock(return_value=True)
            mock_downloader_class.return_value = mock_downloader

            provider = QobuzDownloadProvider(
                mock_download_config,
                mock_session_manager,
                mock_progress_tracker,
                sample_credentials,
            )

            # First authentication
            await provider.authenticate()
            first_downloader = provider._downloader

            # Second authentication
            await provider.authenticate()
            second_downloader = provider._downloader

            # Should reuse the same downloader
            assert first_downloader is second_downloader

    @pytest.mark.parametrize(
        ("content_id", "content_type"),
        [
            ("track_123", ContentType.TRACK),
            ("album_456", ContentType.ALBUM),
            ("playlist_789", ContentType.PLAYLIST),
            ("artist_101", ContentType.ARTIST),
        ],
    )
    async def test_get_download_info_success(
        self,
        mock_download_config: DownloaderConfig,
        mock_session_manager: SessionManager,
        mock_progress_tracker: ProgressTracker,
        sample_credentials: dict[str, Any],
        content_id: str,
        content_type: ContentType,
    ) -> None:
        """Test successful get_download_info."""
        with patch(
            "ripstream.downloader.providers.qobuz.QobuzDownloader"
        ) as mock_downloader_class:
            mock_downloader = Mock(spec=QobuzDownloader)
            mock_downloader.authenticate = AsyncMock(return_value=True)
            mock_downloader.get_download_info = AsyncMock(
                return_value={"id": content_id}
            )
            mock_downloader_class.return_value = mock_downloader

            provider = QobuzDownloadProvider(
                mock_download_config,
                mock_session_manager,
                mock_progress_tracker,
                sample_credentials,
            )

            result = await provider.get_download_info(content_id, content_type)

            assert result == {"id": content_id}
            mock_downloader.get_download_info.assert_called_once_with(content_id)

    async def test_get_download_info_requires_authentication(
        self,
        mock_download_config: DownloaderConfig,
        mock_session_manager: SessionManager,
        mock_progress_tracker: ProgressTracker,
    ) -> None:
        """Test that get_download_info requires authentication."""
        with patch(
            "ripstream.downloader.providers.qobuz.QobuzDownloader"
        ) as mock_downloader_class:
            mock_downloader = Mock(spec=QobuzDownloader)
            mock_downloader.get_download_info = AsyncMock(
                side_effect=Exception("Not authenticated")
            )
            mock_downloader_class.return_value = mock_downloader

            provider = QobuzDownloadProvider(
                mock_download_config,
                mock_session_manager,
                mock_progress_tracker,
            )

            with pytest.raises(Exception, match="Not authenticated"):
                await provider.get_download_info("test_id", ContentType.TRACK)

    async def test_get_download_info_authenticates_if_needed(
        self,
        mock_download_config: DownloaderConfig,
        mock_session_manager: SessionManager,
        mock_progress_tracker: ProgressTracker,
        sample_credentials: dict[str, Any],
    ) -> None:
        """Test that get_download_info authenticates if not authenticated."""
        with patch(
            "ripstream.downloader.providers.qobuz.QobuzDownloader"
        ) as mock_downloader_class:
            mock_downloader = Mock(spec=QobuzDownloader)
            mock_downloader.authenticate = AsyncMock(return_value=True)
            mock_downloader.get_download_info = AsyncMock(return_value={"id": "test"})
            mock_downloader_class.return_value = mock_downloader

            provider = QobuzDownloadProvider(
                mock_download_config,
                mock_session_manager,
                mock_progress_tracker,
                sample_credentials,
            )

            await provider.get_download_info("test_id", ContentType.TRACK)

            # Should have called authenticate
            mock_downloader.authenticate.assert_called_once_with(sample_credentials)

    @pytest.mark.parametrize(
        ("content_type", "expected_method"),
        [
            (ContentType.TRACK, "download"),
            (ContentType.ALBUM, "download_album"),
            (ContentType.PLAYLIST, "download_playlist"),
            (ContentType.ARTIST, "download_artist_discography"),
        ],
    )
    async def test_download_content_success(
        self,
        mock_download_config: DownloaderConfig,
        mock_session_manager: SessionManager,
        mock_progress_tracker: ProgressTracker,
        sample_credentials: dict[str, Any],
        content_type: ContentType,
        expected_method: str,
    ) -> None:
        """Test successful download_content for different content types."""
        with patch(
            "ripstream.downloader.providers.qobuz.QobuzDownloader"
        ) as mock_downloader_class:
            mock_downloader = Mock(spec=QobuzDownloader)
            mock_downloader.authenticate = AsyncMock(return_value=True)

            # Create proper DownloadResult objects
            download_result = DownloadResult(
                download_id=uuid4(),
                success=True,
                file_path="/tmp/test.mp3",
                file_size=1024,
                duration_seconds=1.0,
                average_speed_bps=1024.0,
                metadata={"file": "test.mp3"},
            )

            # Mock get_download_info for track downloads
            mock_downloader.get_download_info = AsyncMock(return_value=Mock())
            mock_downloader.download = AsyncMock(return_value=download_result)
            mock_downloader.download_track_with_album_folder = AsyncMock(
                return_value=download_result
            )
            mock_downloader.download_album = AsyncMock(return_value=[download_result])
            mock_downloader.download_playlist = AsyncMock(
                return_value=[download_result]
            )
            mock_downloader.download_artist_discography = AsyncMock(
                return_value=[download_result]
            )
            mock_downloader_class.return_value = mock_downloader

            provider = QobuzDownloadProvider(
                mock_download_config,
                mock_session_manager,
                mock_progress_tracker,
                sample_credentials,
            )

            result = await provider.download_content("test_id", content_type)

            assert result.success is True
            assert result.metadata["content_type"] == content_type.value
            assert result.metadata["content_id"] == "test_id"

            # Verify the correct method was called
            if content_type == ContentType.TRACK:
                mock_downloader.download_track_with_album_folder.assert_called_once_with(
                    "test_id", None
                )
            elif content_type == ContentType.ALBUM:
                mock_downloader.download_album.assert_called_once()
            elif content_type == ContentType.PLAYLIST:
                mock_downloader.download_playlist.assert_called_once()
            elif content_type == ContentType.ARTIST:
                mock_downloader.download_artist_discography.assert_called_once()

    @pytest.mark.parametrize(
        "unsupported_content_type",
        [
            ContentType.UNKNOWN,
        ],
    )
    async def test_download_content_unsupported_type(
        self,
        mock_download_config: DownloaderConfig,
        mock_session_manager: SessionManager,
        mock_progress_tracker: ProgressTracker,
        sample_credentials: dict[str, Any],
        unsupported_content_type: ContentType,
    ) -> None:
        """Test download_content with unsupported content type."""
        with patch(
            "ripstream.downloader.providers.qobuz.QobuzDownloader"
        ) as mock_downloader_class:
            mock_downloader = Mock(spec=QobuzDownloader)
            mock_downloader.authenticate = AsyncMock(return_value=True)
            mock_downloader_class.return_value = mock_downloader

            provider = QobuzDownloadProvider(
                mock_download_config,
                mock_session_manager,
                mock_progress_tracker,
                sample_credentials,
            )

            with pytest.raises(ValueError, match="Unsupported content type"):
                await provider.download_content("test_id", unsupported_content_type)

    async def test_download_content_failure(
        self,
        mock_download_config: DownloaderConfig,
        mock_session_manager: SessionManager,
        mock_progress_tracker: ProgressTracker,
        sample_credentials: dict[str, Any],
    ) -> None:
        """Test download_content when download fails."""
        with patch(
            "ripstream.downloader.providers.qobuz.QobuzDownloader"
        ) as mock_downloader_class:
            mock_downloader = Mock(spec=QobuzDownloader)
            mock_downloader.authenticate = AsyncMock(return_value=True)
            mock_downloader.download = AsyncMock(
                side_effect=Exception("Download failed")
            )
            mock_downloader.download_track_with_album_folder = AsyncMock(
                side_effect=Exception("Download failed")
            )
            mock_downloader_class.return_value = mock_downloader

            provider = QobuzDownloadProvider(
                mock_download_config,
                mock_session_manager,
                mock_progress_tracker,
                sample_credentials,
            )

            result = await provider.download_content("test_id", ContentType.TRACK)

            assert result.success is False
            assert "Download failed" in result.error_message

    async def test_download_content_authenticates_if_needed(
        self,
        mock_download_config: DownloaderConfig,
        mock_session_manager: SessionManager,
        mock_progress_tracker: ProgressTracker,
        sample_credentials: dict[str, Any],
    ) -> None:
        """Test that download_content authenticates if not authenticated."""
        with patch(
            "ripstream.downloader.providers.qobuz.QobuzDownloader"
        ) as mock_downloader_class:
            mock_downloader = Mock(spec=QobuzDownloader)
            mock_downloader.authenticate = AsyncMock(return_value=True)

            # Create proper DownloadResult object
            download_result = DownloadResult(
                download_id=uuid4(),
                success=True,
                file_path="/tmp/test.mp3",
                file_size=1024,
                duration_seconds=1.0,
                average_speed_bps=1024.0,
                metadata={"file": "test.mp3"},
            )

            mock_downloader.get_download_info = AsyncMock(return_value=Mock())
            mock_downloader.download = AsyncMock(return_value=download_result)
            mock_downloader.download_track_with_album_folder = AsyncMock(
                return_value=download_result
            )
            mock_downloader_class.return_value = mock_downloader

            provider = QobuzDownloadProvider(
                mock_download_config,
                mock_session_manager,
                mock_progress_tracker,
                sample_credentials,
            )

            await provider.download_content("test_id", ContentType.TRACK)

            # Should have called authenticate
            mock_downloader.authenticate.assert_called_once_with(sample_credentials)

    @pytest.mark.parametrize(
        ("download_directory", "progress_callback"),
        [
            ("/tmp/downloads", None),
            (None, Mock(spec=Callable[[int], None])),
            ("/custom/path", Mock(spec=Callable[[int], None])),
        ],
    )
    async def test_download_content_with_parameters(
        self,
        mock_download_config: DownloaderConfig,
        mock_session_manager: SessionManager,
        mock_progress_tracker: ProgressTracker,
        sample_credentials: dict[str, Any],
        download_directory: str | None,
        progress_callback: Callable[[int], None] | None,
    ) -> None:
        """Test download_content with various parameters."""
        with patch(
            "ripstream.downloader.providers.qobuz.QobuzDownloader"
        ) as mock_downloader_class:
            mock_downloader = Mock(spec=QobuzDownloader)
            mock_downloader.authenticate = AsyncMock(return_value=True)

            # Create proper DownloadResult object
            download_result = DownloadResult(
                download_id=uuid4(),
                success=True,
                file_path="/tmp/test.mp3",
                file_size=1024,
                duration_seconds=1.0,
                average_speed_bps=1024.0,
                metadata={"file": "test.mp3"},
            )

            mock_downloader.get_download_info = AsyncMock(return_value=Mock())
            mock_downloader.download = AsyncMock(return_value=download_result)
            mock_downloader.download_track_with_album_folder = AsyncMock(
                return_value=download_result
            )
            mock_downloader_class.return_value = mock_downloader

            provider = QobuzDownloadProvider(
                mock_download_config,
                mock_session_manager,
                mock_progress_tracker,
                sample_credentials,
            )

            result = await provider.download_content(
                "test_id",
                ContentType.TRACK,
                download_directory,
                progress_callback,
            )

            assert result.success is True
            assert result.metadata["content_type"] == "track"
            assert result.metadata["content_id"] == "test_id"

            # Verify download was called with correct parameters
            mock_downloader.download_track_with_album_folder.assert_called_once_with(
                "test_id", download_directory
            )

    async def test_download_artist_discography_success(
        self,
        mock_download_config: DownloaderConfig,
        mock_session_manager: SessionManager,
        mock_progress_tracker: ProgressTracker,
        sample_credentials: dict[str, Any],
    ) -> None:
        """Test successful download_artist_discography."""
        with patch(
            "ripstream.downloader.providers.qobuz.QobuzDownloader"
        ) as mock_downloader_class:
            mock_downloader = Mock(spec=QobuzDownloader)
            mock_downloader.authenticate = AsyncMock(return_value=True)

            # Create proper DownloadResult object
            download_result = DownloadResult(
                download_id=uuid4(),
                success=True,
                file_path="/tmp/artist.mp3",
                file_size=1024,
                duration_seconds=1.0,
                average_speed_bps=1024.0,
                metadata={"file": "artist.mp3"},
            )

            mock_downloader.download_artist_discography = AsyncMock(
                return_value=[download_result]
            )
            mock_downloader_class.return_value = mock_downloader

            provider = QobuzDownloadProvider(
                mock_download_config,
                mock_session_manager,
                mock_progress_tracker,
                sample_credentials,
            )

            result = await provider.download_artist_discography("artist_123")

            assert result.success is True
            assert result.metadata["content_type"] == "artist"
            assert result.metadata["content_id"] == "artist_123"

    async def test_download_artist_discography_failure(
        self,
        mock_download_config: DownloaderConfig,
        mock_session_manager: SessionManager,
        mock_progress_tracker: ProgressTracker,
        sample_credentials: dict[str, Any],
    ) -> None:
        """Test download_artist_discography when download fails."""
        with patch(
            "ripstream.downloader.providers.qobuz.QobuzDownloader"
        ) as mock_downloader_class:
            mock_downloader = Mock(spec=QobuzDownloader)
            mock_downloader.authenticate = AsyncMock(return_value=True)
            mock_downloader.download_artist_discography = AsyncMock(
                side_effect=Exception("Download failed")
            )
            mock_downloader_class.return_value = mock_downloader

            provider = QobuzDownloadProvider(
                mock_download_config,
                mock_session_manager,
                mock_progress_tracker,
                sample_credentials,
            )

            result = await provider.download_artist_discography("artist_123")

            assert result.success is False
            assert "Download failed" in result.error_message

    async def test_cleanup(
        self,
        mock_download_config: DownloaderConfig,
        mock_session_manager: SessionManager,
        mock_progress_tracker: ProgressTracker,
        sample_credentials: dict[str, Any],
    ) -> None:
        """Test cleanup method."""
        with patch(
            "ripstream.downloader.providers.qobuz.QobuzDownloader"
        ) as mock_downloader_class:
            mock_downloader = Mock(spec=QobuzDownloader)
            mock_downloader.authenticate = AsyncMock(return_value=True)
            mock_downloader.cleanup = AsyncMock()
            mock_downloader_class.return_value = mock_downloader

            provider = QobuzDownloadProvider(
                mock_download_config,
                mock_session_manager,
                mock_progress_tracker,
                sample_credentials,
            )

            # Authenticate first to create downloader
            await provider.authenticate()
            assert provider._downloader is not None
            assert provider._authenticated is True

            # Cleanup
            await provider.cleanup()

            # Verify cleanup was called and state was reset
            mock_downloader.cleanup.assert_called_once()
            assert provider._downloader is None
            assert provider._authenticated is False

    async def test_cleanup_without_downloader(
        self,
        mock_download_config: DownloaderConfig,
        mock_session_manager: SessionManager,
        mock_progress_tracker: ProgressTracker,
    ) -> None:
        """Test cleanup when no downloader exists."""
        provider = QobuzDownloadProvider(
            mock_download_config,
            mock_session_manager,
            mock_progress_tracker,
        )

        # Should not raise an exception
        await provider.cleanup()

    def test_validate_downloader_method(
        self,
        mock_download_config: DownloaderConfig,
        mock_session_manager: SessionManager,
        mock_progress_tracker: ProgressTracker,
    ) -> None:
        """Test _validate_downloader method."""
        provider = QobuzDownloadProvider(
            mock_download_config,
            mock_session_manager,
            mock_progress_tracker,
        )

        # Should raise RuntimeError when downloader is None
        with pytest.raises(RuntimeError, match="Downloader not initialized"):
            provider._validate_downloader()

        # Should not raise when downloader exists
        provider._downloader = Mock()
        provider._validate_downloader()  # Should not raise

    @pytest.mark.parametrize(
        ("content_type", "should_raise"),
        [
            (ContentType.TRACK, False),
            (ContentType.ALBUM, False),
            (ContentType.PLAYLIST, False),
            (ContentType.ARTIST, False),
            (ContentType.UNKNOWN, True),
        ],
    )
    def test_validate_content_type_method(
        self,
        mock_download_config: DownloaderConfig,
        mock_session_manager: SessionManager,
        mock_progress_tracker: ProgressTracker,
        content_type: ContentType,
        should_raise: bool,
    ) -> None:
        """Test _validate_content_type method."""
        provider = QobuzDownloadProvider(
            mock_download_config,
            mock_session_manager,
            mock_progress_tracker,
        )

        if should_raise:
            with pytest.raises(ValueError, match="Unsupported content type"):
                provider._validate_content_type(content_type)
        else:
            provider._validate_content_type(content_type)  # Should not raise

    def test_is_authenticated_property(
        self,
        mock_download_config: DownloaderConfig,
        mock_session_manager: SessionManager,
        mock_progress_tracker: ProgressTracker,
    ) -> None:
        """Test is_authenticated property."""
        provider = QobuzDownloadProvider(
            mock_download_config,
            mock_session_manager,
            mock_progress_tracker,
        )

        assert provider.is_authenticated is False

        provider._authenticated = True
        assert provider.is_authenticated is True

    def test_can_download_method(
        self,
        mock_download_config: DownloaderConfig,
        mock_session_manager: SessionManager,
        mock_progress_tracker: ProgressTracker,
    ) -> None:
        """Test can_download method."""
        provider = QobuzDownloadProvider(
            mock_download_config,
            mock_session_manager,
            mock_progress_tracker,
        )

        assert provider.can_download(ContentType.TRACK) is True
        assert provider.can_download(ContentType.ALBUM) is True
        assert provider.can_download(ContentType.PLAYLIST) is True
        assert provider.can_download(ContentType.ARTIST) is True
        assert provider.can_download(ContentType.UNKNOWN) is False
