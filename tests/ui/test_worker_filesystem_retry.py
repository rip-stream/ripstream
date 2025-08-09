"""Tests for worker-level filesystem-based retry behavior.

Copyright (c) 2025 ripstream and contributors. All rights reserved.
Licensed under the MIT license. See LICENSE file in the project root for details.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast
from unittest.mock import Mock, patch

import pytest


def _make_mock_config(tmp_path) -> Any:
    config = Mock()
    # Downloads settings
    config.downloads.folder = tmp_path
    config.downloads.max_connections = 1
    config.downloads.verify_ssl = True
    config.downloads.requests_per_minute = 60
    config.downloads.max_retries = 2
    config.downloads.retry_delay = 0.01
    config.downloads.chunk_size = 8192
    # Service config
    service_cfg = Mock()
    service_cfg.get_decoded_credentials.return_value = {}
    config.get_service_config.return_value = service_cfg
    return config


@pytest.fixture
def worker(tmp_path):
    from ripstream.ui.download_worker import DownloadWorker

    mock_config = _make_mock_config(str(tmp_path))
    w = DownloadWorker(mock_config)
    # Initialize environment to avoid None components
    w.setup_download_environment()
    return w


def _download_info() -> dict[str, Any]:
    from ripstream.downloader.enums import ContentType
    from ripstream.models.enums import StreamingSource

    return {
        "item_id": "id1",
        "title": "T",
        "artist": "A",
        "album": "Al",
        "source": "qobuz",
        "content_type": ContentType.TRACK,
        "streaming_source": StreamingSource.QOBUZ,
    }


@dataclass(slots=True)
class _Result:
    success: bool
    file_path: str | None = None
    error_message: str | None = None


@dataclass(slots=True)
class _ProviderResult:
    download_results: list[_Result]


def test_worker_marks_failure_when_file_missing(worker, tmp_path) -> None:
    """If provider reports success but file is missing, worker should retry then emit failure."""
    from ripstream.ui.download_worker import DownloadWorker

    info = _download_info()

    missing_path = str(tmp_path / "missing.flac")
    first_result = _ProviderResult([_Result(True, missing_path)])
    second_result = _ProviderResult([_Result(True, missing_path)])
    final_result = _ProviderResult([_Result(True, missing_path)])

    sequence = [first_result, second_result, final_result]

    with patch.object(DownloadWorker, "_execute_download", side_effect=sequence):
        emitted: dict[str, Any] = {}

        def _capture(download_id: str, success: bool, message: str) -> None:
            emitted["success"] = success
            emitted["message"] = message

        worker.download_completed.connect(_capture)
        worker._handle_download_result(first_result, info, "dbid1")

        assert emitted
        assert emitted["success"] is False
        assert "failed" in cast("str", emitted["message"]).lower()


def test_worker_succeeds_after_retry_when_file_appears(worker, tmp_path) -> None:
    """Worker should succeed if a later retry returns a valid existing file."""
    from ripstream.ui.download_worker import DownloadWorker

    info = _download_info()

    missing_path = str(tmp_path / "missing.flac")
    valid_path = str(tmp_path / "ok.flac")
    first = _ProviderResult([_Result(True, missing_path)])
    second = _ProviderResult([_Result(True, missing_path)])

    (tmp_path / "ok.flac").write_text("x")
    third = _ProviderResult([_Result(True, valid_path)])

    with patch.object(
        DownloadWorker, "_execute_download", side_effect=[first, second, third]
    ):
        emitted: dict[str, Any] = {}

        def _capture(download_id: str, success: bool, message: str) -> None:
            emitted["success"] = success
            emitted["message"] = message

        worker.download_completed.connect(_capture)
        worker._handle_download_result(first, info, "dbid2")

        assert emitted
        assert emitted["success"] is True
        assert "success" in cast("str", emitted["message"]).lower()
