# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Tests for download service."""

from collections.abc import Callable
from typing import Any
from unittest.mock import AsyncMock, Mock, patch

import pytest

from ripstream.core.url_parser import ParsedURL
from ripstream.downloader.config import DownloaderConfig
from ripstream.downloader.enums import ContentType
from ripstream.downloader.progress import ProgressTracker
from ripstream.downloader.providers.base import (
    BaseDownloadProvider,
    DownloadProviderResult,
)
from ripstream.downloader.providers.service import DownloadService
from ripstream.downloader.session import SessionManager
from ripstream.models.enums import StreamingSource
from ripstream.ui.metadata_providers.base import MetadataResult


class MockDownloadProvider(BaseDownloadProvider):
    """Mock download provider for testing DownloadService."""

    def __init__(
        self,
        config: DownloaderConfig,
        session_manager: SessionManager,
        progress_tracker: ProgressTracker,
        credentials: dict[str, Any] | None = None,
        should_fail: bool = False,
    ):
        super().__init__(config, session_manager, progress_tracker, credentials)
        self._should_fail = should_fail

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
        return not self._should_fail

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
        if self._should_fail:
            return self._create_download_result(
                success=False,
                error_message="Mock download failed",
                metadata={"content_id": content_id, "content_type": content_type.value},
            )

        return self._create_download_result(
            success=True,
            download_results=[],
            metadata={"content_id": content_id, "content_type": content_type.value},
        )

    async def cleanup(self) -> None:
        pass


class TestDownloadService:
    """Test cases for DownloadService."""

    def test_initialization(
        self,
        mock_download_config: DownloaderConfig,
        mock_session_manager: SessionManager,
        mock_progress_tracker: ProgressTracker,
    ) -> None:
        """Test DownloadService initialization."""
        service = DownloadService(
            mock_download_config,
            mock_session_manager,
            mock_progress_tracker,
        )

        assert service.config == mock_download_config
        assert service.session_manager == mock_session_manager
        assert service.progress_tracker == mock_progress_tracker
        assert service.url_parser is not None
        assert service._providers == {}

    @pytest.mark.parametrize(
        ("url", "parsed_url_data"),
        [
            (
                "https://open.qobuz.com/album/123",
                {
                    "service": StreamingSource.QOBUZ,
                    "content_type": ContentType.ALBUM,
                    "content_id": "123",
                    "url": "https://open.qobuz.com/album/123",
                    "is_valid": True,
                },
            ),
            (
                "https://open.qobuz.com/track/456",
                {
                    "service": StreamingSource.QOBUZ,
                    "content_type": ContentType.TRACK,
                    "content_id": "456",
                    "url": "https://open.qobuz.com/track/456",
                    "is_valid": True,
                },
            ),
        ],
    )
    async def test_download_from_url_success(
        self,
        mock_download_config: DownloaderConfig,
        mock_session_manager: SessionManager,
        mock_progress_tracker: ProgressTracker,
        url: str,
        parsed_url_data: dict[str, Any],
    ) -> None:
        """Test successful download from URL."""
        with patch(
            "ripstream.downloader.providers.service.DownloadProviderFactory"
        ) as mock_factory:
            mock_provider = Mock(spec=BaseDownloadProvider)
            mock_provider.download_content = AsyncMock(
                return_value=DownloadProviderResult(success=True)
            )
            mock_factory.create_provider.return_value = mock_provider

            service = DownloadService(
                mock_download_config,
                mock_session_manager,
                mock_progress_tracker,
            )

            # Mock the URL parser
            mock_parsed_url = ParsedURL(
                service=parsed_url_data["service"],
                content_type=parsed_url_data["content_type"],
                content_id=parsed_url_data["content_id"],
                url=parsed_url_data["url"],
                metadata={},
            )
            service.url_parser.parse_url = Mock(return_value=mock_parsed_url)  # type: ignore[assignment]

            result = await service.download_from_url(url)

            assert result.success is True
            mock_factory.create_provider.assert_called_once()
            mock_provider.download_content.assert_called_once()

    async def test_download_from_url_invalid_url(
        self,
        mock_download_config: DownloaderConfig,
        mock_session_manager: SessionManager,
        mock_progress_tracker: ProgressTracker,
    ) -> None:
        """Test download from URL with invalid URL."""
        service = DownloadService(
            mock_download_config,
            mock_session_manager,
            mock_progress_tracker,
        )

        # Mock the URL parser to return invalid URL
        mock_parsed_url = ParsedURL(
            service=StreamingSource.UNKNOWN,
            content_type=ContentType.UNKNOWN,
            content_id="",
            url="invalid",
            metadata={},
        )
        service.url_parser.parse_url = Mock(return_value=mock_parsed_url)  # type: ignore[assignment]

        result = await service.download_from_url("invalid_url")

        assert result.success is False
        assert "Invalid URL" in result.error_message

    async def test_download_from_url_exception(
        self,
        mock_download_config: DownloaderConfig,
        mock_session_manager: SessionManager,
        mock_progress_tracker: ProgressTracker,
    ) -> None:
        """Test download from URL when exception occurs."""
        service = DownloadService(
            mock_download_config,
            mock_session_manager,
            mock_progress_tracker,
        )

        # Mock the URL parser to raise exception
        service.url_parser.parse_url = Mock(side_effect=Exception("Parser failed"))  # type: ignore[assignment]

        result = await service.download_from_url("test_url")

        assert result.success is False
        assert "Parser failed" in result.error_message

    @pytest.mark.parametrize(
        "metadata_result_data",
        [
            {
                "content_type": "album",
                "service": "Qobuz",
                "data": {"id": "album_123"},
            },
            {
                "content_type": "track",
                "service": "Qobuz",
                "data": {"id": "track_456"},
            },
        ],
    )
    async def test_download_with_metadata_success(
        self,
        mock_download_config: DownloaderConfig,
        mock_session_manager: SessionManager,
        mock_progress_tracker: ProgressTracker,
        metadata_result_data: dict[str, Any],
    ) -> None:
        """Test successful download with metadata."""
        with patch(
            "ripstream.downloader.providers.service.DownloadProviderFactory"
        ) as mock_factory:
            mock_provider = Mock(spec=BaseDownloadProvider)
            mock_provider.download_content = AsyncMock(
                return_value=DownloadProviderResult(success=True)
            )
            mock_factory.create_provider.return_value = mock_provider

            service = DownloadService(
                mock_download_config,
                mock_session_manager,
                mock_progress_tracker,
            )

            # Create metadata result
            metadata_result = MetadataResult(**metadata_result_data)

            result = await service.download_with_metadata(metadata_result)

            assert result.success is True
            mock_factory.create_provider.assert_called_once()
            mock_provider.download_content.assert_called_once()

    async def test_download_with_metadata_exception(
        self,
        mock_download_config: DownloaderConfig,
        mock_session_manager: SessionManager,
        mock_progress_tracker: ProgressTracker,
    ) -> None:
        """Test download with metadata when exception occurs."""
        service = DownloadService(
            mock_download_config,
            mock_session_manager,
            mock_progress_tracker,
        )

        # Create metadata result that will cause exception
        metadata_result = MetadataResult(
            content_type="album",
            service="Qobuz",
            data={"id": "album_123"},
        )

        # Mock factory to raise exception
        with patch(
            "ripstream.downloader.providers.service.DownloadProviderFactory"
        ) as mock_factory:
            mock_factory.create_provider.side_effect = Exception("Factory failed")

            result = await service.download_with_metadata(metadata_result)

            assert result.success is False
            assert "Factory failed" in result.error_message

    @pytest.mark.parametrize(
        ("service_name", "expected_source"),
        [
            ("qobuz", StreamingSource.QOBUZ),
            ("tidal", StreamingSource.TIDAL),
            ("deezer", StreamingSource.DEEZER),
            ("youtube", StreamingSource.YOUTUBE),
            ("spotify", StreamingSource.SPOTIFY),
            ("unknown", StreamingSource.UNKNOWN),
        ],
    )
    def test_get_streaming_source_from_metadata(
        self,
        mock_download_config: DownloaderConfig,
        mock_session_manager: SessionManager,
        mock_progress_tracker: ProgressTracker,
        service_name: str,
        expected_source: StreamingSource,
    ) -> None:
        """Test getting streaming source from metadata."""
        service = DownloadService(
            mock_download_config,
            mock_session_manager,
            mock_progress_tracker,
        )

        metadata_result = MetadataResult(
            content_type="album",
            service=service_name,
            data={"id": "test"},
        )

        result = service._get_streaming_source_from_metadata(metadata_result)
        assert result == expected_source

    @pytest.mark.parametrize(
        ("content_type", "expected_type"),
        [
            ("artist", ContentType.ARTIST),
            ("album", ContentType.ALBUM),
            ("track", ContentType.TRACK),
            ("playlist", ContentType.PLAYLIST),
            ("unknown", ContentType.UNKNOWN),
        ],
    )
    def test_determine_content_type_from_metadata(
        self,
        mock_download_config: DownloaderConfig,
        mock_session_manager: SessionManager,
        mock_progress_tracker: ProgressTracker,
        content_type: str,
        expected_type: ContentType,
    ) -> None:
        """Test determining content type from metadata."""
        service = DownloadService(
            mock_download_config,
            mock_session_manager,
            mock_progress_tracker,
        )

        metadata_result = MetadataResult(
            content_type=content_type,
            service="Qobuz",
            data={"id": "test"},
        )

        result = service._determine_content_type_from_metadata(metadata_result)
        assert result == expected_type

    @pytest.mark.parametrize(
        ("content_type", "should_raise"),
        [
            ("artist", False),
            ("album", False),
            ("track", False),
            ("playlist", False),
            ("unknown", True),
            ("invalid", True),
        ],
    )
    def test_validate_content_type(
        self,
        mock_download_config: DownloaderConfig,
        mock_session_manager: SessionManager,
        mock_progress_tracker: ProgressTracker,
        content_type: str,
        should_raise: bool,
    ) -> None:
        """Test content type validation."""
        service = DownloadService(
            mock_download_config,
            mock_session_manager,
            mock_progress_tracker,
        )

        if should_raise:
            with pytest.raises(ValueError, match="Unknown content type"):
                service._validate_content_type(content_type)
        else:
            service._validate_content_type(content_type)  # Should not raise

    @pytest.mark.parametrize(
        ("metadata_data", "expected_id"),
        [
            ({"id": "test_123"}, "test_123"),
            ({"id": "track_456"}, "track_456"),
            ({"id": "album_789"}, "album_789"),
            ({}, ""),
        ],
    )
    def test_extract_content_id_from_metadata(
        self,
        mock_download_config: DownloaderConfig,
        mock_session_manager: SessionManager,
        mock_progress_tracker: ProgressTracker,
        metadata_data: dict[str, Any],
        expected_id: str,
    ) -> None:
        """Test extracting content ID from metadata."""
        service = DownloadService(
            mock_download_config,
            mock_session_manager,
            mock_progress_tracker,
        )

        metadata_result = MetadataResult(
            content_type="album",
            service="Qobuz",
            data=metadata_data,
        )

        result = service._extract_content_id_from_metadata(metadata_result)
        assert result == expected_id

    async def test_get_download_info_from_url_success(
        self,
        mock_download_config: DownloaderConfig,
        mock_session_manager: SessionManager,
        mock_progress_tracker: ProgressTracker,
    ) -> None:
        """Test successful get_download_info_from_url."""
        with patch(
            "ripstream.downloader.providers.service.DownloadProviderFactory"
        ) as mock_factory:
            mock_provider = Mock(spec=BaseDownloadProvider)
            mock_provider.get_download_info = AsyncMock(return_value={"info": "test"})
            mock_factory.create_provider.return_value = mock_provider

            service = DownloadService(
                mock_download_config,
                mock_session_manager,
                mock_progress_tracker,
            )

            # Mock the URL parser
            mock_parsed_url = ParsedURL(
                service=StreamingSource.QOBUZ,
                content_type=ContentType.ALBUM,
                content_id="test_id",
                url="test_url",
                metadata={},
            )
            service.url_parser.parse_url = Mock(return_value=mock_parsed_url)  # type: ignore[assignment]

            result = await service.get_download_info_from_url("test_url")

            assert result == {"info": "test"}
            mock_factory.create_provider.assert_called_once()
            mock_provider.get_download_info.assert_called_once()

    async def test_get_download_info_from_url_invalid_url(
        self,
        mock_download_config: DownloaderConfig,
        mock_session_manager: SessionManager,
        mock_progress_tracker: ProgressTracker,
    ) -> None:
        """Test get_download_info_from_url with invalid URL."""
        service = DownloadService(
            mock_download_config,
            mock_session_manager,
            mock_progress_tracker,
        )

        # Mock the URL parser to return invalid URL
        mock_parsed_url = Mock(spec=ParsedURL)
        mock_parsed_url.is_valid = False
        service.url_parser.parse_url = Mock(return_value=mock_parsed_url)  # type: ignore[assignment]

        with pytest.raises(ValueError, match="Invalid URL"):
            await service.get_download_info_from_url("invalid_url")

    async def test_get_download_info_from_url_exception(
        self,
        mock_download_config: DownloaderConfig,
        mock_session_manager: SessionManager,
        mock_progress_tracker: ProgressTracker,
    ) -> None:
        """Test get_download_info_from_url when exception occurs."""
        service = DownloadService(
            mock_download_config,
            mock_session_manager,
            mock_progress_tracker,
        )

        # Mock the URL parser to raise exception
        service.url_parser.parse_url = Mock(side_effect=Exception("Parser failed"))  # type: ignore[assignment]

        with pytest.raises(Exception, match="Parser failed"):
            await service.get_download_info_from_url("test_url")

    async def test_get_or_create_provider_new_provider(
        self,
        mock_download_config: DownloaderConfig,
        mock_session_manager: SessionManager,
        mock_progress_tracker: ProgressTracker,
        sample_credentials: dict[str, Any],
    ) -> None:
        """Test getting or creating a new provider."""
        with patch(
            "ripstream.downloader.providers.service.DownloadProviderFactory"
        ) as mock_factory:
            mock_provider = Mock(spec=BaseDownloadProvider)
            mock_factory.create_provider.return_value = mock_provider

            service = DownloadService(
                mock_download_config,
                mock_session_manager,
                mock_progress_tracker,
            )

            result = await service._get_or_create_provider(
                StreamingSource.QOBUZ, sample_credentials
            )

            assert result == mock_provider
            mock_factory.create_provider.assert_called_once_with(
                StreamingSource.QOBUZ,
                mock_download_config,
                mock_session_manager,
                mock_progress_tracker,
                sample_credentials,
            )

    async def test_get_or_create_provider_existing_provider(
        self,
        mock_download_config: DownloaderConfig,
        mock_session_manager: SessionManager,
        mock_progress_tracker: ProgressTracker,
    ) -> None:
        """Test getting an existing provider."""
        mock_provider = Mock(spec=BaseDownloadProvider)

        service = DownloadService(
            mock_download_config,
            mock_session_manager,
            mock_progress_tracker,
        )
        service._providers[StreamingSource.QOBUZ] = mock_provider

        result = await service._get_or_create_provider(StreamingSource.QOBUZ)

        assert result == mock_provider

    def test_create_error_result(
        self,
        mock_download_config: DownloaderConfig,
        mock_session_manager: SessionManager,
        mock_progress_tracker: ProgressTracker,
    ) -> None:
        """Test creating error result."""
        service = DownloadService(
            mock_download_config,
            mock_session_manager,
            mock_progress_tracker,
        )

        error_message = "Test error"
        metadata = {"key": "value"}

        result = service._create_error_result(error_message, metadata)

        assert isinstance(result, DownloadProviderResult)
        assert result.success is False
        assert result.error_message == error_message
        assert result.metadata == metadata

    async def test_cleanup(
        self,
        mock_download_config: DownloaderConfig,
        mock_session_manager: SessionManager,
        mock_progress_tracker: ProgressTracker,
    ) -> None:
        """Test cleanup method."""
        service = DownloadService(
            mock_download_config,
            mock_session_manager,
            mock_progress_tracker,
        )

        # Add some providers
        mock_provider1 = Mock(spec=BaseDownloadProvider)
        mock_provider1.cleanup = AsyncMock()
        mock_provider2 = Mock(spec=BaseDownloadProvider)
        mock_provider2.cleanup = AsyncMock()

        service._providers[StreamingSource.QOBUZ] = mock_provider1
        service._providers[StreamingSource.TIDAL] = mock_provider2

        await service.cleanup()

        # Verify cleanup was called on all providers
        mock_provider1.cleanup.assert_called_once()
        mock_provider2.cleanup.assert_called_once()
        assert service._providers == {}

    def test_get_supported_services(
        self,
        mock_download_config: DownloaderConfig,
        mock_session_manager: SessionManager,
        mock_progress_tracker: ProgressTracker,
    ) -> None:
        """Test getting supported services."""
        service = DownloadService(
            mock_download_config,
            mock_session_manager,
            mock_progress_tracker,
        )

        with patch(
            "ripstream.downloader.providers.service.DownloadProviderFactory"
        ) as mock_factory:
            mock_factory.get_supported_services.return_value = [StreamingSource.QOBUZ]

            result = service.get_supported_services()

            assert result == [StreamingSource.QOBUZ]
            mock_factory.get_supported_services.assert_called_once()

    def test_is_service_supported(
        self,
        mock_download_config: DownloaderConfig,
        mock_session_manager: SessionManager,
        mock_progress_tracker: ProgressTracker,
    ) -> None:
        """Test checking if service is supported."""
        service = DownloadService(
            mock_download_config,
            mock_session_manager,
            mock_progress_tracker,
        )

        with patch(
            "ripstream.downloader.providers.service.DownloadProviderFactory"
        ) as mock_factory:
            mock_factory.is_service_supported.return_value = True

            result = service.is_service_supported(StreamingSource.QOBUZ)

            assert result is True
            mock_factory.is_service_supported.assert_called_once_with(
                StreamingSource.QOBUZ
            )

    @pytest.mark.parametrize(
        ("url", "expected_valid"),
        [
            ("https://open.qobuz.com/album/123", True),
            ("invalid_url", False),
        ],
    )
    def test_validate_url(
        self,
        mock_download_config: DownloaderConfig,
        mock_session_manager: SessionManager,
        mock_progress_tracker: ProgressTracker,
        url: str,
        expected_valid: bool,
    ) -> None:
        """Test URL validation."""
        service = DownloadService(
            mock_download_config,
            mock_session_manager,
            mock_progress_tracker,
        )

        # Mock the URL parser
        mock_parsed_url = Mock(spec=ParsedURL)
        mock_parsed_url.is_valid = expected_valid
        service.url_parser.parse_url = Mock(return_value=mock_parsed_url)  # type: ignore[assignment]

        if expected_valid:
            service._validate_url(url)  # Should not raise
        else:
            with pytest.raises(ValueError, match="Invalid URL"):
                service._validate_url(url)
