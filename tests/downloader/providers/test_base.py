# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Tests for base download provider classes."""

from collections.abc import Callable
from typing import Any
from unittest.mock import Mock
from uuid import uuid4

import pytest

from ripstream.downloader.config import DownloaderConfig
from ripstream.downloader.enums import ContentType
from ripstream.downloader.progress import ProgressTracker
from ripstream.downloader.providers.base import (
    BaseDownloadProvider,
    DownloadProviderResult,
)
from ripstream.downloader.session import SessionManager
from ripstream.models.enums import StreamingSource


class MockDownloadProvider(BaseDownloadProvider):
    """Mock download provider for testing BaseDownloadProvider functionality."""

    def __init__(
        self,
        config: DownloaderConfig,
        session_manager: SessionManager,
        progress_tracker: ProgressTracker,
        credentials: dict[str, Any] | None = None,
        should_fail_auth: bool = False,
        should_fail_download: bool = False,
    ):
        super().__init__(config, session_manager, progress_tracker, credentials)
        self._should_fail_auth = should_fail_auth
        self._should_fail_download = should_fail_download
        self._download_calls: list[tuple[str, ContentType]] = []

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
        if self._should_fail_auth:
            return False
        self._authenticated = True
        return True

    async def get_download_info(
        self, content_id: str, content_type: ContentType
    ) -> Any:
        if not self._authenticated:
            msg = "Not authenticated"
            raise RuntimeError(msg)
        return {"id": content_id, "type": content_type, "title": "Test Content"}

    async def download_content(
        self,
        content_id: str,
        content_type: ContentType,
        download_directory: str | None = None,
        progress_callback: Callable[[int], None] | None = None,
    ) -> DownloadProviderResult:
        self._download_calls.append((content_id, content_type))

        if self._should_fail_download:
            return self._create_download_result(
                success=False,
                error_message="Mock download failed",
                metadata={"content_id": content_id, "content_type": content_type.value},
            )

        # Simulate progress updates
        if progress_callback:
            for i in range(0, 101, 25):
                progress_callback(i)

        return self._create_download_result(
            success=True,
            download_results=[],
            metadata={"content_id": content_id, "content_type": content_type.value},
        )

    async def cleanup(self) -> None:
        self._authenticated = False

    def get_download_calls(self) -> list[tuple[str, ContentType]]:
        return self._download_calls.copy()


class TestDownloadProviderResult:
    """Test cases for DownloadProviderResult."""

    @pytest.mark.parametrize(
        ("success", "download_results", "error_message", "metadata"),
        [
            (True, [], None, {}),
            (False, [], "Test error", {"key": "value"}),
            (
                True,
                [{"download_id": str(uuid4()), "success": True}],
                None,
                {"count": 1},
            ),
        ],
    )
    def test_create_download_provider_result(
        self,
        success: bool,
        download_results: list[dict[str, Any]],
        error_message: str | None,
        metadata: dict[str, Any],
    ) -> None:
        """Test creating DownloadProviderResult with various parameters."""
        # Convert dict results to DownloadResult objects
        from uuid import uuid4

        from ripstream.downloader.base import DownloadResult

        download_result_objects = []
        for result_dict in download_results:
            # Use the original download_id if provided, otherwise generate a new one
            download_id = result_dict.get("download_id")
            if download_id:
                from uuid import UUID

                download_id = UUID(download_id)
            else:
                download_id = uuid4()

            download_result = DownloadResult(
                download_id=download_id,
                success=result_dict["success"],
                file_path=result_dict.get("file_path"),
                file_size=result_dict.get("file_size"),
                checksum=result_dict.get("checksum"),
                duration_seconds=result_dict.get("download_time"),
                error_message=result_dict.get("error_message"),
                metadata=result_dict.get("metadata", {}),
            )
            download_result_objects.append(download_result)

        result = DownloadProviderResult(
            success=success,
            download_results=download_result_objects,
            error_message=error_message,
            metadata=metadata,
        )

        assert result.success == success
        # The download_results are converted to DownloadResult objects, so we need to check the structure
        if download_results:
            assert len(result.download_results) == len(download_results)
            for i, expected in enumerate(download_results):
                actual = result.download_results[i]
                assert str(actual.download_id) == expected["download_id"]
                assert actual.success == expected["success"]
        else:
            assert result.download_results == []
        assert result.error_message == error_message
        assert result.metadata == metadata

    def test_download_provider_result_defaults(self) -> None:
        """Test DownloadProviderResult with default values."""
        result = DownloadProviderResult(success=True)

        assert result.success is True
        assert result.download_results == []
        assert result.error_message is None
        assert result.metadata == {}

    def test_download_provider_result_validation(self) -> None:
        """Test DownloadProviderResult field validation."""
        # Test that required fields are enforced
        with pytest.raises(ValueError, match=r".*success.*"):
            DownloadProviderResult()  # Missing required 'success' field


class TestBaseDownloadProvider:
    """Test cases for BaseDownloadProvider."""

    async def test_initialization(
        self,
        mock_download_config: DownloaderConfig,
        mock_session_manager: SessionManager,
        mock_progress_tracker: ProgressTracker,
        sample_credentials: dict[str, Any],
    ) -> None:
        """Test provider initialization."""
        provider = MockDownloadProvider(
            mock_download_config,
            mock_session_manager,
            mock_progress_tracker,
            sample_credentials,
        )

        assert provider.config == mock_download_config
        assert provider.session_manager == mock_session_manager
        assert provider.progress_tracker == mock_progress_tracker
        assert provider.credentials == sample_credentials
        assert provider._authenticated is False

    async def test_initialization_without_credentials(
        self,
        mock_download_config: DownloaderConfig,
        mock_session_manager: SessionManager,
        mock_progress_tracker: ProgressTracker,
    ) -> None:
        """Test provider initialization without credentials."""
        provider = MockDownloadProvider(
            mock_download_config,
            mock_session_manager,
            mock_progress_tracker,
        )

        assert provider.credentials == {}

    @pytest.mark.parametrize(
        ("content_type", "expected"),
        [
            (ContentType.TRACK, True),
            (ContentType.ALBUM, True),
            (ContentType.PLAYLIST, True),
            (ContentType.ARTIST, True),
            (ContentType.UNKNOWN, False),
        ],
    )
    def test_can_download(
        self,
        mock_base_provider: BaseDownloadProvider,
        content_type: ContentType,
        expected: bool,
    ) -> None:
        """Test content type support checking."""
        assert mock_base_provider.can_download(content_type) == expected

    def test_is_authenticated_property(
        self,
        mock_base_provider: BaseDownloadProvider,
    ) -> None:
        """Test authentication status property."""
        assert mock_base_provider.is_authenticated is False

        # Simulate authentication
        mock_base_provider._authenticated = True
        assert mock_base_provider.is_authenticated is True

    @pytest.mark.parametrize(
        ("content_id", "content_type"),
        [
            ("track_123", ContentType.TRACK),
        ],
    )
    async def test_download_track_method(
        self,
        mock_base_provider: BaseDownloadProvider,
        content_id: str,
        content_type: ContentType,
    ) -> None:
        """Test download_track convenience method."""
        result = await mock_base_provider.download_track(content_id)

        assert isinstance(result, DownloadProviderResult)
        assert result.success is True
        assert result.metadata["content_id"] == content_id
        assert result.metadata["content_type"] == content_type.value

    @pytest.mark.parametrize(
        ("content_id", "content_type"),
        [
            ("album_123", ContentType.ALBUM),
            ("album_456", ContentType.ALBUM),
        ],
    )
    async def test_download_album_method(
        self,
        mock_base_provider: BaseDownloadProvider,
        content_id: str,
        content_type: ContentType,
    ) -> None:
        """Test download_album convenience method."""
        result = await mock_base_provider.download_album(content_id)

        assert isinstance(result, DownloadProviderResult)
        assert result.success is True
        assert result.metadata["content_id"] == content_id
        assert result.metadata["content_type"] == content_type.value

    @pytest.mark.parametrize(
        ("content_id", "content_type"),
        [
            ("playlist_123", ContentType.PLAYLIST),
            ("playlist_456", ContentType.PLAYLIST),
        ],
    )
    async def test_download_playlist_method(
        self,
        mock_base_provider: BaseDownloadProvider,
        content_id: str,
        content_type: ContentType,
    ) -> None:
        """Test download_playlist convenience method."""
        result = await mock_base_provider.download_playlist(content_id)

        assert isinstance(result, DownloadProviderResult)
        assert result.success is True
        assert result.metadata["content_id"] == content_id
        assert result.metadata["content_type"] == content_type.value

    @pytest.mark.parametrize(
        ("artist_id", "content_type"),
        [
            ("artist_123", ContentType.ARTIST),
            ("artist_456", ContentType.ARTIST),
        ],
    )
    async def test_download_artist_discography_method(
        self,
        mock_base_provider: BaseDownloadProvider,
        artist_id: str,
        content_type: ContentType,
    ) -> None:
        """Test download_artist_discography convenience method."""
        result = await mock_base_provider.download_artist_discography(artist_id)

        assert isinstance(result, DownloadProviderResult)
        assert result.success is True
        assert result.metadata["content_id"] == artist_id
        assert result.metadata["content_type"] == content_type.value

    @pytest.mark.parametrize(
        ("content_id", "content_type", "download_directory", "progress_callback"),
        [
            ("track_123", ContentType.TRACK, "/tmp/downloads", None),
            ("album_456", ContentType.ALBUM, None, Mock()),
            ("playlist_789", ContentType.PLAYLIST, "/custom/path", Mock()),
        ],
    )
    async def test_download_content_with_parameters(
        self,
        mock_base_provider: BaseDownloadProvider,
        content_id: str,
        content_type: ContentType,
        download_directory: str | None,
        progress_callback: Callable[[int], None] | None,
    ) -> None:
        """Test download_content with various parameters."""
        result = await mock_base_provider.download_content(
            content_id,
            content_type,
            download_directory,
            progress_callback,
        )

        assert isinstance(result, DownloadProviderResult)
        assert result.success is True
        assert result.metadata["content_id"] == content_id
        assert result.metadata["content_type"] == content_type.value

    async def test_download_content_with_progress_callback(
        self,
        mock_download_config: DownloaderConfig,
        mock_session_manager: SessionManager,
        mock_progress_tracker: ProgressTracker,
    ) -> None:
        """Test download_content with progress callback."""
        provider = MockDownloadProvider(
            mock_download_config,
            mock_session_manager,
            mock_progress_tracker,
        )

        progress_calls: list[int] = []

        def progress_callback(progress: int) -> None:
            progress_calls.append(progress)

        result = await provider.download_content(
            "test_track",
            ContentType.TRACK,
            progress_callback=progress_callback,
        )

        assert result.success is True
        assert len(progress_calls) > 0
        assert all(0 <= progress <= 100 for progress in progress_calls)

    async def test_download_content_failure(
        self,
        mock_download_config: DownloaderConfig,
        mock_session_manager: SessionManager,
        mock_progress_tracker: ProgressTracker,
    ) -> None:
        """Test download_content when download fails."""
        provider = MockDownloadProvider(
            mock_download_config,
            mock_session_manager,
            mock_progress_tracker,
            should_fail_download=True,
        )

        result = await provider.download_content("test_track", ContentType.TRACK)

        assert result.success is False
        assert result.error_message == "Mock download failed"

    async def test_get_download_info_requires_authentication(
        self,
        mock_download_config: DownloaderConfig,
        mock_session_manager: SessionManager,
        mock_progress_tracker: ProgressTracker,
    ) -> None:
        """Test that get_download_info requires authentication."""
        provider = MockDownloadProvider(
            mock_download_config,
            mock_session_manager,
            mock_progress_tracker,
        )

        with pytest.raises(RuntimeError, match="Not authenticated"):
            await provider.get_download_info("test_track", ContentType.TRACK)

    async def test_authenticate_success(
        self,
        mock_download_config: DownloaderConfig,
        mock_session_manager: SessionManager,
        mock_progress_tracker: ProgressTracker,
    ) -> None:
        """Test successful authentication."""
        provider = MockDownloadProvider(
            mock_download_config,
            mock_session_manager,
            mock_progress_tracker,
        )

        result = await provider.authenticate()

        assert result is True
        assert provider.is_authenticated is True

    async def test_authenticate_failure(
        self,
        mock_download_config: DownloaderConfig,
        mock_session_manager: SessionManager,
        mock_progress_tracker: ProgressTracker,
    ) -> None:
        """Test failed authentication."""
        provider = MockDownloadProvider(
            mock_download_config,
            mock_session_manager,
            mock_progress_tracker,
            should_fail_auth=True,
        )

        result = await provider.authenticate()

        assert result is False
        assert provider.is_authenticated is False

    def test_create_download_result_helper(
        self,
        mock_base_provider: BaseDownloadProvider,
    ) -> None:
        """Test the _create_download_result helper method."""
        test_uuid = str(uuid4())
        result = mock_base_provider._create_download_result(
            success=True,
            download_results=[{"download_id": test_uuid, "success": True}],
            error_message=None,
            metadata={"key": "value"},
        )

        assert isinstance(result, DownloadProviderResult)
        assert result.success is True
        # The download_results are converted to DownloadResult objects
        assert len(result.download_results) == 1
        actual = result.download_results[0]
        assert str(actual.download_id) == test_uuid
        assert actual.success is True
        assert result.error_message is None
        assert result.metadata == {"key": "value"}

    def test_create_download_result_with_defaults(
        self,
        mock_base_provider: BaseDownloadProvider,
    ) -> None:
        """Test _create_download_result with default values."""
        result = mock_base_provider._create_download_result(success=False)

        assert isinstance(result, DownloadProviderResult)
        assert result.success is False
        assert result.download_results == []
        assert result.error_message is None
        assert result.metadata == {}

    async def test_cleanup_method(
        self,
        mock_base_provider: BaseDownloadProvider,
    ) -> None:
        """Test cleanup method."""
        # Set authenticated to True first
        mock_base_provider._authenticated = True
        assert mock_base_provider.is_authenticated is True

        await mock_base_provider.cleanup()

        # The mock implementation sets authenticated to False
        assert mock_base_provider.is_authenticated is False

    @pytest.mark.parametrize(
        ("property_name", "expected_type"),
        [
            ("service_name", str),
            ("streaming_source", StreamingSource),
            ("supported_content_types", list),
        ],
    )
    def test_abstract_properties(
        self,
        property_name: str,
        expected_type: type,
        mock_base_provider: BaseDownloadProvider,
    ) -> None:
        """Test that abstract properties return correct types."""
        value = getattr(mock_base_provider, property_name)
        assert isinstance(value, expected_type)

    def test_abstract_methods_exist(
        self,
        mock_base_provider: BaseDownloadProvider,
    ) -> None:
        """Test that all abstract methods are implemented."""
        required_methods = [
            "authenticate",
            "get_download_info",
            "download_content",
            "cleanup",
        ]

        for method_name in required_methods:
            assert hasattr(mock_base_provider, method_name)
            method = getattr(mock_base_provider, method_name)
            assert callable(method)
