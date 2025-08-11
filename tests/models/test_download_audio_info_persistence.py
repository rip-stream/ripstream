# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Tests for persistence and formatting of DownloadAudioInfo and details."""

from __future__ import annotations

import contextlib
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest

from ripstream.config.user import UserConfig
from ripstream.models.database import DownloadAudioInfo
from ripstream.models.db_manager import DatabaseManager
from ripstream.models.download_service import DownloadService
from ripstream.models.enums import MediaType, StreamingSource

if TYPE_CHECKING:
    from collections.abc import Iterator


@pytest.fixture
def temp_db_path() -> Iterator[str]:
    with NamedTemporaryFile(suffix=".db", delete=False) as f:
        pass
    try:
        yield f.name
    finally:
        with contextlib.suppress(OSError):
            os.unlink(f.name)


@pytest.fixture
def download_service(temp_db_path: str) -> Iterator[DownloadService]:
    cfg = UserConfig()
    cfg.database.database_path = Path(temp_db_path)

    dbm = DatabaseManager(temp_db_path)
    dbm.initialize()

    svc = DownloadService(cfg)
    svc.downloads_db = dbm
    svc.failed_downloads_repository = svc.failed_downloads_repository.__class__(dbm)
    yield svc
    dbm.close()


@pytest.mark.parametrize(
    "audio_info",
    [
        {
            "quality": 3,
            "bit_depth": 24,
            "sampling_rate": 96000,
            "bitrate": 1760,
            "codec": "FLAC",
            "container": "FLAC",
            "duration_seconds": 224.0,
            "file_size_bytes": 32_400_000,
            "is_lossless": True,
            "is_explicit": False,
            "channels": 2,
        },
        {
            # minimal sparse info should still persist
            "bit_depth": None,
            "sampling_rate": 48000,
            "duration_seconds": 180.0,
            "is_lossless": False,
        },
    ],
)
def test_add_download_record_persists_audio_info(
    download_service: DownloadService, audio_info: dict
) -> None:
    unique_id = str(uuid4())
    download_id = download_service.add_download_record(
        title="Track",
        artist="Artist",
        album="Album",
        media_type=MediaType.TRACK,
        source=StreamingSource.QOBUZ,
        source_id=unique_id,
        audio_info=audio_info,
    )
    assert download_id

    # Verify audio info row exists and mirrors inputs
    with download_service.downloads_db.get_session() as s:
        ai = (
            s.query(DownloadAudioInfo)
            .filter(DownloadAudioInfo.download_id == download_id)
            .first()
        )
        assert ai is not None
        for key, val in audio_info.items():
            # Only check fields that exist on the model
            if hasattr(ai, key):
                assert getattr(ai, key) == val


def test_get_download_details_formats_human_values(
    download_service: DownloadService,
) -> None:
    # Create record with audio info attached
    src_id = str(uuid4())
    download_id = download_service.add_download_record(
        title="Kenny Chesney - Come Here, Go Away",
        artist="Kenny Chesney",
        album="Born",
        media_type=MediaType.TRACK,
        source=StreamingSource.QOBUZ,
        source_id=src_id,
        audio_info={
            "bit_depth": 24,
            "sampling_rate": 48000,
            "bitrate": 1761,
            "container": "FLAC",
            "duration_seconds": 199.0,
            "file_size_bytes": 34_000_000,
            "channels": 2,
            "is_lossless": True,
        },
    )
    assert download_id

    # Set a plausible final filename on the record
    file_path = "/Volumes/plex/music/Kenny Chesney - Born (2024) [FLAC] [24B-44kHz]/12. Kenny Chesney - Come Here, Go Away.flac"
    with download_service.downloads_db.get_session() as s:
        from ripstream.models.database import DownloadRecord

        rec = s.get(DownloadRecord, download_id)
        rec.file_path = file_path
        s.commit()

    details = download_service.get_download_details(download_id)
    assert details is not None
    assert details["filename"] == file_path
    assert details["format"] == "FLAC"
    # MM:SS formatting
    assert details["length"] == "03:19"
    assert details["bitrate"].endswith("kbps")
    assert details["file_size"].endswith("MB")
    assert details["sample_rate"].endswith("Hz")
    assert details["bits_per_sample"] == 24
    assert details["channels"] == "Stereo"
    assert details["album"] == "Born"
    assert details["total_tracks"] == 1
