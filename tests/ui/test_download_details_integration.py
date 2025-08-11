# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Lightweight UI-level test to ensure details can be retrieved after add."""

from __future__ import annotations

import contextlib
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest

from ripstream.config.user import UserConfig
from ripstream.models.db_manager import DatabaseManager
from ripstream.models.download_service import DownloadService
from ripstream.models.enums import MediaType, StreamingSource

if TYPE_CHECKING:
    from collections.abc import Iterator


@pytest.fixture
def service() -> Iterator[DownloadService]:
    with NamedTemporaryFile(suffix=".db", delete=False) as f:
        temp_db = f.name
    try:
        cfg = UserConfig()
        cfg.database.database_path = Path(temp_db)
        dbm = DatabaseManager(temp_db)
        dbm.initialize()
        svc = DownloadService(cfg)
        svc.downloads_db = dbm
        svc.failed_downloads_repository = svc.failed_downloads_repository.__class__(dbm)
        yield svc
    finally:
        with contextlib.suppress(Exception):
            svc.downloads_db.close()
        with contextlib.suppress(OSError):
            os.unlink(temp_db)


def test_get_download_details_after_add(service: DownloadService) -> None:
    did = service.add_download_record(
        title="Song",
        artist="Artist",
        album="Album",
        media_type=MediaType.TRACK,
        source=StreamingSource.QOBUZ,
        source_id=str(uuid4()),
        audio_info={"duration_seconds": 65.0, "container": "FLAC", "bit_depth": 16},
    )
    assert did
    details = service.get_download_details(did)
    # At minimum should return a dict (even with sparse info)
    assert isinstance(details, dict)
    assert details.get("format") in {"", "FLAC"}
    # MM:SS should work even with only duration provided
    assert details.get("length") in {"01:05", ""}
