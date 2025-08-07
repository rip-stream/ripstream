# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Shared fixtures for download provider tests."""

import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest

from ripstream.downloader.config import DownloadBehaviorSettings, DownloaderConfig
from ripstream.downloader.enums import ContentType
from ripstream.downloader.progress import ProgressTracker
from ripstream.downloader.providers.base import (
    BaseDownloadProvider,
    DownloadProviderResult,
)
from ripstream.downloader.session import SessionManager
from ripstream.models.enums import StreamingSource


@pytest.fixture
def mock_download_config() -> DownloaderConfig:
    """Create a mock download configuration."""
    settings = DownloadBehaviorSettings(
        timeout_seconds=30,
        chunk_size=8192,
        max_retries=3,
    )
    return DownloaderConfig(
        download_directory=Path("/tmp/test_downloads"),
        max_concurrent_downloads=3,
        default_behavior=settings,
    )


@pytest.fixture
def mock_session_manager() -> SessionManager:
    """Create a mock session manager."""
    session_manager = Mock(spec=SessionManager)
    session_manager.get_session = AsyncMock()
    session_manager.cleanup = AsyncMock()
    return session_manager


@pytest.fixture
def mock_progress_tracker() -> ProgressTracker:
    """Create a mock progress tracker."""
    progress_tracker = Mock(spec=ProgressTracker)
    progress_tracker.start_tracking = Mock()
    progress_tracker.update_progress = Mock()
    progress_tracker.stop_tracking = Mock()
    progress_tracker.get_progress = Mock(return_value=50)
    return progress_tracker


@pytest.fixture
def sample_credentials() -> dict[str, Any]:
    """Sample credentials for testing."""
    return {
        "username": "test_user",
        "password": "test_password",
        "api_key": "test_api_key",
    }


@pytest.fixture
def sample_download_result() -> dict[str, Any]:
    """Sample download result for testing."""
    return {
        "download_id": "download_123",
        "success": True,
        "file_path": "/tmp/test_file.mp3",
        "file_size": 1024,
        "download_time": 5.0,
        "checksum": "abc123",
    }


@pytest.fixture
def sample_downloadable_content() -> dict[str, Any]:
    """Sample downloadable content for testing."""
    return {
        "content_id": "test_content_123",
        "content_type": ContentType.TRACK,
        "source": "qobuz",
        "title": "Test Track",
        "artist": "Test Artist",
        "album": "Test Album",
        "url": "https://example.com/track/123",
        "file_name": "test_track",
        "file_extension": "mp3",
        "expected_size": 1024,
    }


@pytest.fixture
def mock_qobuz_downloader() -> Mock:
    """Create a mock QobuzDownloader."""
    downloader = Mock()
    downloader.authenticate = AsyncMock(return_value=True)
    downloader.get_download_info = AsyncMock()
    downloader.download = AsyncMock()
    downloader.download_album = AsyncMock()
    downloader.download_playlist = AsyncMock()
    downloader.download_artist_discography = AsyncMock()
    downloader.cleanup = AsyncMock()
    return downloader


@pytest.fixture
def temp_download_directory() -> Path:
    """Create a temporary download directory."""
    return Path(tempfile.mkdtemp())
    # Cleanup is handled by pytest's tmp_path fixture


@pytest.fixture
def mock_progress_callback() -> Callable[[int], None]:
    """Create a mock progress callback function."""
    return Mock(spec=Callable[[int], None])


@pytest.fixture
def sample_content_ids() -> list[str]:
    """Sample content IDs for testing."""
    return [
        "track_123",
        "album_456",
        "playlist_789",
        "artist_101",
    ]


@pytest.fixture
def sample_content_types() -> list[ContentType]:
    """Sample content types for testing."""
    return [
        ContentType.TRACK,
        ContentType.ALBUM,
        ContentType.PLAYLIST,
        ContentType.ARTIST,
    ]


@pytest.fixture
def sample_streaming_sources() -> list[StreamingSource]:
    """Sample streaming sources for testing."""
    return [
        StreamingSource.QOBUZ,
        StreamingSource.TIDAL,
        StreamingSource.DEEZER,
        StreamingSource.YOUTUBE,
    ]


@pytest.fixture
def mock_base_provider(
    mock_download_config: DownloaderConfig,
    mock_session_manager: SessionManager,
    mock_progress_tracker: ProgressTracker,
    sample_credentials: dict[str, Any],
) -> BaseDownloadProvider:
    """Create a mock base download provider."""

    class MockDownloadProvider(BaseDownloadProvider):
        """Mock download provider for testing."""

        @property
        def service_name(self) -> str:
            return "mock"

        @property
        def streaming_source(self) -> StreamingSource:
            return StreamingSource.QOBUZ

        @property
        def supported_content_types(self) -> list[ContentType]:
            return [
                ContentType.TRACK,
                ContentType.ALBUM,
                ContentType.PLAYLIST,
                ContentType.ARTIST,
            ]

        async def authenticate(self) -> bool:
            return True

        async def get_download_info(
            self, content_id: str, content_type: ContentType
        ) -> Any:
            return {"id": content_id, "type": content_type}

        async def download_content(
            self,
            content_id: str,
            content_type: ContentType,
            download_directory: str | None = None,
            progress_callback: Callable[[int], None] | None = None,
        ) -> DownloadProviderResult:
            return self._create_download_result(
                success=True,
                download_results=[],
                metadata={"content_id": content_id, "content_type": content_type.value},
            )

        async def cleanup(self) -> None:
            self._authenticated = False

    return MockDownloadProvider(
        mock_download_config,
        mock_session_manager,
        mock_progress_tracker,
        sample_credentials,
    )


@pytest.fixture
def sample_urls() -> list[str]:
    """Sample URLs for testing."""
    return [
        "https://open.qobuz.com/album/123",
        "https://open.qobuz.com/track/456",
        "https://open.qobuz.com/playlist/789",
        "https://open.qobuz.com/artist/101",
    ]


@pytest.fixture
def sample_metadata_result() -> dict[str, Any]:
    """Sample metadata result for testing."""
    return {
        "content_type": "album",
        "service": "Qobuz",
        "data": {
            "id": "album_123",
            "title": "Test Album",
            "artist": "Test Artist",
        },
    }


@pytest.fixture
def mock_url_parser() -> Mock:
    """Create a mock URL parser."""
    parser = Mock()
    parser.parse_url = Mock()
    return parser


@pytest.fixture
def mock_metadata_provider() -> Mock:
    """Create a mock metadata provider."""
    provider = Mock()
    provider.fetch_metadata = AsyncMock()
    return provider
