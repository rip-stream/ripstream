# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Unit tests for probe_audio_file utility."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING

import pytest

from ripstream.metadata.tagger import probe_audio_file

if TYPE_CHECKING:
    from collections.abc import Iterator


@pytest.fixture
def temp_dir() -> Iterator[str]:
    with TemporaryDirectory() as d:
        yield d


@pytest.mark.parametrize(
    ("ext", "content", "expect_container"),
    [
        ("flac", b"fLaC" + b"\x00" * 128, "FLAC"),
        ("mp3", b"ID3" + b"\x00" * 128, "MP3"),
        ("m4a", b"\x00" * 256, "MP4/M4A"),  # container inferred as MP4/M4A
        ("aac", b"\xff\xf1" + b"\x00" * 128, "AAC"),
    ],
)
def test_probe_container_and_filesize(
    temp_dir: str, ext: str, content: bytes, expect_container: str
) -> None:
    # Create a minimal dummy file; mutagen may not parse, but size and container must be set
    p = Path(temp_dir) / f"test.{ext}"
    p.write_bytes(content)

    info = probe_audio_file(str(p))

    assert isinstance(info, dict)
    assert info.get("container") == expect_container
    assert info.get("file_size_bytes") == p.stat().st_size


def test_probe_unsupported_container_reports_size(temp_dir: str) -> None:
    p = Path(temp_dir) / "test.wavpack"
    # Write some bytes
    p.write_bytes(b"abc" * 100)
    info = probe_audio_file(str(p))
    assert info.get("container") == "WAVPACK"  # from extension upper
    assert info.get("file_size_bytes") == p.stat().st_size
