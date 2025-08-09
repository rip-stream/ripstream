# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Tests for active album status signal emission from DownloadsHistoryView."""

from __future__ import annotations

import pytest

from ripstream.models.enums import DownloadStatus
from ripstream.ui.downloads_view import DownloadsHistoryView


class TestDownloadsActiveSignal:
    @pytest.fixture
    def view(self, qapp, mock_download_service) -> DownloadsHistoryView:
        v = DownloadsHistoryView()
        # Ensure clean table
        v.downloads_table.clear_all_downloads()
        return v

    def test_emit_active_albums_on_progress(self, view: DownloadsHistoryView):
        captured: list[tuple[set[str], set[str]]] = []

        def _capture(downloading: set[str], pending: set[str]) -> None:
            captured.append((downloading, pending))

        view.active_albums_updated.connect(_capture)

        # Add a download with album_id
        download = {
            "download_id": "d1",
            "title": "T",
            "artist": "A",
            "album": "Al",
            "type": "Track",
            "media_type": "TRACK",
            "source": "QOBUZ",
            "source_id": "s1",
            "album_id": "album_1",
            "status": DownloadStatus.PENDING,
            "progress": 0,
        }

        view.add_download(download)

        # Simulate progress update to downloading
        view.update_download_progress("d1", 10, DownloadStatus.DOWNLOADING)

        assert captured, "Expected active_albums_updated to be emitted"
        downloading, pending = captured[-1]
        assert "album_1" in downloading or "album_1" in pending
