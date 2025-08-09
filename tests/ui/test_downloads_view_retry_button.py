"""Tests for Retry button behavior in downloads table actions.

Copyright (c) 2025 ripstream and contributors. All rights reserved.
Licensed under the MIT license. See LICENSE file in the project root for details.
"""

from __future__ import annotations

from typing import cast

import pytest
from PyQt6.QtWidgets import QPushButton

from ripstream.models.enums import DownloadStatus
from ripstream.ui.downloads_view import DownloadsTableWidget


def _find_button(widget, text: str) -> QPushButton | None:
    for child in widget.children():
        if isinstance(child, QPushButton) and cast("QPushButton", child).text() == text:
            return cast("QPushButton", child)
    return None


@pytest.fixture
def table() -> DownloadsTableWidget:
    return DownloadsTableWidget()


def test_retry_button_present_and_enabled_for_failed(
    table: DownloadsTableWidget,
) -> None:
    download = {
        "download_id": "dl1",
        "title": "T",
        "artist": "A",
        "album": "Al",
        "type": "Track",
        "media_type": "TRACK",
        "source": "QOBUZ",
        "source_id": "track1",
        "status": DownloadStatus.FAILED,
        "progress": 0,
    }
    table.add_download_item(download)

    actions = table.cellWidget(0, 7)
    assert actions is not None
    retry_btn = _find_button(actions, "Retry")
    assert retry_btn is not None
    assert retry_btn.isEnabled() is True


def test_retry_button_disabled_for_non_failed(table: DownloadsTableWidget) -> None:
    download = {
        "download_id": "dl2",
        "title": "T",
        "artist": "A",
        "album": "Al",
        "type": "Track",
        "media_type": "TRACK",
        "source": "QOBUZ",
        "source_id": "track2",
        "status": DownloadStatus.DOWNLOADING,
        "progress": 50,
    }
    table.add_download_item(download)

    actions = table.cellWidget(0, 7)
    assert actions is not None
    retry_btn = _find_button(actions, "Retry")
    assert retry_btn is not None
    assert retry_btn.isEnabled() is False


def test_retry_button_enables_on_status_update(table: DownloadsTableWidget) -> None:
    download = {
        "download_id": "dl3",
        "title": "T",
        "artist": "A",
        "album": "Al",
        "type": "Track",
        "media_type": "TRACK",
        "source": "QOBUZ",
        "source_id": "track3",
        "status": DownloadStatus.DOWNLOADING,
        "progress": 10,
    }
    table.add_download_item(download)

    # Update to failed
    table.update_download_progress("dl3", 10, DownloadStatus.FAILED)

    actions = table.cellWidget(0, 7)
    assert actions is not None
    retry_btn = _find_button(actions, "Retry")
    assert retry_btn is not None
    assert retry_btn.isEnabled() is True
