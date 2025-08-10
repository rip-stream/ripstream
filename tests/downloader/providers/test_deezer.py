# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Unit tests for DeezerDownloadProvider.

Covers auth, download info building, content type validation, and preview download.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Self
from unittest.mock import AsyncMock, Mock

import pytest

from ripstream.downloader.enums import ContentType
from ripstream.downloader.providers.deezer import DeezerDownloadProvider


@pytest.fixture
def provider(
    mock_download_config,  # type: ignore[reportUnknownParameterType]
    mock_session_manager,  # type: ignore[reportUnknownParameterType]
    mock_progress_tracker,  # type: ignore[reportUnknownParameterType]
) -> DeezerDownloadProvider:
    """Create a DeezerDownloadProvider instance with mocked dependencies."""
    return DeezerDownloadProvider(
        mock_download_config, mock_session_manager, mock_progress_tracker, {}
    )


@pytest.mark.asyncio
async def test_authenticate_initializes_client(
    provider: DeezerDownloadProvider,
) -> None:
    """authenticate returns True and sets authenticated when client is created."""
    ok = await provider.authenticate()
    assert ok is True
    assert provider.is_authenticated is True


@pytest.mark.asyncio
async def test_get_download_info_unsupported_type_raises(
    provider: DeezerDownloadProvider,
) -> None:
    """get_download_info raises ValueError for unsupported types."""
    with pytest.raises(ValueError, match="Unsupported content type"):
        await provider.get_download_info("123", ContentType.ALBUM)


@pytest.mark.asyncio
async def test_get_download_info_track_builds_content(
    provider: DeezerDownloadProvider,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """get_download_info builds a DownloadableContent for track preview."""

    class DummyTrack:
        def as_dict(self) -> dict[str, Any]:
            return {
                "id": 123,
                "title": "Song",
                "artist": {"name": "Artist"},
                "album": {"title": "Album"},
                "preview": "https://example.com/preview.mp3",
            }

    dummy_client = Mock()
    dummy_client.get_track = Mock(return_value=DummyTrack())
    provider.client = dummy_client  # type: ignore[assignment]
    provider._authenticated = True

    # No size info available; session manager get_content_info returns {}
    provider.session_manager.get_content_info = AsyncMock(return_value={})  # type: ignore[attr-defined]

    content = await provider.get_download_info("123", ContentType.TRACK)
    assert content.title == "Song"
    assert content.artist == "Artist"
    assert content.album == "Album"
    assert content.url.endswith(".mp3")
    assert content.content_type == ContentType.TRACK


@pytest.mark.asyncio
async def test_download_content_track_success(
    provider: DeezerDownloadProvider,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """download_content downloads preview bytes and writes a file."""

    # Build content via stubbed client
    class DummyTrack:
        def as_dict(self) -> dict[str, Any]:
            return {
                "id": 42,
                "title": "Preview",
                "artist": {"name": "Tester"},
                "album": {"title": "Album"},
                "preview": "https://example.com/preview.mp3",
            }

    dummy_client = Mock()
    dummy_client.get_track = Mock(return_value=DummyTrack())
    provider.client = dummy_client  # type: ignore[assignment]
    provider._authenticated = True

    # Mock session manager to return an object with .get that yields dummy data
    class DummyResp:
        def __init__(self, data: bytes) -> None:
            self._data = data

        async def read(self) -> bytes:
            return self._data

        async def __aenter__(self) -> Self:
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:  # type: ignore[override]
            return None

    class DummySession:
        def __init__(self, data: bytes) -> None:
            self._data = data

        def get(self, url: str):  # type: ignore[override]
            return DummyResp(self._data)

    provider.session_manager.get_session = AsyncMock(  # type: ignore[attr-defined]
        return_value=DummySession(b"0123456789")
    )
    provider.session_manager.get_content_info = AsyncMock(  # type: ignore[attr-defined]
        return_value={}
    )

    result = await provider.download_content(
        "42", ContentType.TRACK, download_directory=str(tmp_path)
    )

    assert result.success is True
    assert result.download_results
    assert result.download_results[0].success is True
    file_path = Path(result.download_results[0].file_path)
    assert file_path.exists()
    assert file_path.stat().st_size == 10


@pytest.mark.asyncio
async def test_download_content_unsupported_type_raises(
    provider: DeezerDownloadProvider,
) -> None:
    """download_content raises ValueError early for unsupported types."""
    with pytest.raises(ValueError, match="Unsupported content type"):
        await provider.download_content("1", ContentType.ALBUM)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("content_type", "should_raise"),
    [
        (ContentType.TRACK, False),
        (ContentType.ALBUM, True),
        (ContentType.PLAYLIST, True),
        (ContentType.ARTIST, True),
    ],
)
async def test_supported_content_types_validation(
    provider: DeezerDownloadProvider, content_type: ContentType, should_raise: bool
) -> None:
    """Parametrized check for content type validation path."""
    if should_raise:
        with pytest.raises(ValueError, match="Unsupported content type"):
            await provider.get_download_info("x", content_type)
    else:
        # Stub client and session for TRACK path
        class DummyTrack:
            def as_dict(self) -> dict[str, Any]:
                return {
                    "id": 7,
                    "title": "T",
                    "artist": {"name": "A"},
                    "album": {"title": "B"},
                    "preview": "https://example.com/p.mp3",
                }

        provider.client = Mock(get_track=Mock(return_value=DummyTrack()))  # type: ignore[assignment]
        provider._authenticated = True
        provider.session_manager.get_content_info = AsyncMock(return_value={})  # type: ignore[attr-defined]
        content = await provider.get_download_info("7", content_type)
        assert content.content_type == ContentType.TRACK
