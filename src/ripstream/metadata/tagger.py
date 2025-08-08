# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Audio file tagging with metadata and artwork embedding."""

import logging
from enum import Enum
from pathlib import Path
from typing import Any

import aiofiles
from mutagen import id3
from mutagen.flac import FLAC, Picture
from mutagen.id3 import (
    APIC,  # type: ignore
    ID3,
    ID3NoHeaderError,
)
from mutagen.mp4 import MP4, MP4Cover

logger = logging.getLogger(__name__)

FLAC_MAX_BLOCKSIZE = 16777215  # 16.7 MB

# MP4/M4A tag mappings
MP4_KEYS = (
    "\xa9nam",  # title
    "\xa9ART",  # artist
    "\xa9alb",  # album
    "aART",  # album artist
    "\xa9wrt",  # composer
    "\xa9day",  # year
    "\xa9cmt",  # comment
    "desc",  # description
    "purd",  # purchase date
    "\xa9grp",  # grouping
    "\xa9gen",  # genre
    "\xa9lyr",  # lyrics
    "\xa9too",  # encoder
    "cprt",  # copyright
    "cpil",  # compilation
    "trkn",  # track number
    "disk",  # disc number
    None,  # track total (handled with track number)
    None,  # disc total (handled with disc number)
    None,  # date (same as year)
    "----:com.apple.iTunes:ISRC",  # ISRC
)

# MP3 ID3 tag mappings
MP3_KEYS = (
    id3.TIT2,  # title
    id3.TPE1,  # artist
    id3.TALB,  # album
    id3.TPE2,  # album artist
    id3.TCOM,  # composer
    id3.TYER,  # year
    id3.COMM,  # comment
    id3.TIT1,  # description (content group)
    id3.TIT1,  # purchase date (reuse content group)
    id3.TIT1,  # grouping (content group)
    id3.TCON,  # genre
    id3.USLT,  # lyrics
    id3.TENC,  # encoder
    id3.TCOP,  # copyright
    id3.TCMP,  # compilation
    id3.TRCK,  # track number
    id3.TPOS,  # disc number
    None,  # track total (handled with track number)
    None,  # disc total (handled with disc number)
    None,  # date (same as year)
    id3.TSRC,  # ISRC
)

METADATA_TYPES = (
    "title",
    "artist",
    "album",
    "albumartist",
    "composer",
    "year",
    "comment",
    "description",
    "purchase_date",
    "grouping",
    "genre",
    "lyrics",
    "encoder",
    "copyright",
    "compilation",
    "tracknumber",
    "discnumber",
    "tracktotal",
    "disctotal",
    "date",
    "isrc",
)

# FLAC uses uppercase field names
FLAC_KEY = {v: v.upper() for v in METADATA_TYPES}
MP4_KEY = dict(zip(METADATA_TYPES, MP4_KEYS, strict=False))
MP3_KEY = dict(zip(METADATA_TYPES, MP3_KEYS, strict=False))


class Container(Enum):
    """Audio container formats."""

    FLAC = 1
    AAC = 2
    MP3 = 3

    def get_mutagen_class(self, path: str) -> Any:
        """Get the appropriate mutagen class for this container."""
        if self == Container.FLAC:
            return FLAC(path)
        if self == Container.AAC:
            return MP4(path)
        if self == Container.MP3:
            try:
                return ID3(path)
            except ID3NoHeaderError:
                return ID3()
        return {}

    def get_tag_pairs(self, metadata: dict[str, Any]) -> list[tuple]:
        """Get tag key-value pairs for this container format."""
        if self == Container.FLAC:
            return self._tag_flac(metadata)
        if self == Container.MP3:
            return self._tag_mp3(metadata)
        if self == Container.AAC:
            return self._tag_mp4(metadata)
        return []

    def _tag_flac(self, metadata: dict[str, Any]) -> list[tuple]:
        """Create FLAC tags from metadata."""
        out = []
        for k, v in FLAC_KEY.items():
            tag = metadata.get(k)
            if tag is not None:
                if k in {"tracknumber", "discnumber", "tracktotal", "disctotal"}:
                    tag = f"{int(tag):02}"
                out.append((v, str(tag)))
        return out

    def _tag_mp3(self, metadata: dict[str, Any]) -> list[tuple]:
        """Create MP3 ID3 tags from metadata."""
        out = []
        for k, v in MP3_KEY.items():
            if k == "tracknumber":
                tracktotal = metadata.get("tracktotal", "")
                text = (
                    f"{metadata.get('tracknumber', '')}/{tracktotal}"
                    if tracktotal
                    else str(metadata.get("tracknumber", ""))
                )
            elif k == "discnumber":
                disctotal = metadata.get("disctotal", "")
                text = (
                    f"{metadata.get('discnumber', '')}/{disctotal}"
                    if disctotal
                    else str(metadata.get("discnumber", ""))
                )
            else:
                text = metadata.get(k)

            if text is not None and v is not None:
                out.append((v.__name__, v(encoding=3, text=str(text))))
        return out

    def _tag_mp4(self, metadata: dict[str, Any]) -> list[tuple]:
        """Create MP4/M4A tags from metadata."""
        out = []
        for k, v in MP4_KEY.items():
            if k == "tracknumber":
                tracktotal = metadata.get("tracktotal", 0) or 0
                text = [(metadata.get("tracknumber", 0) or 0, tracktotal)]
            elif k == "discnumber":
                disctotal = metadata.get("disctotal", 0) or 0
                text = [(metadata.get("discnumber", 0) or 0, disctotal)]
            elif k == "isrc" and metadata.get("isrc"):
                # ISRC is a freeform value in MP4
                text = str(metadata["isrc"]).encode("utf-8")
            else:
                text = metadata.get(k)

            if v is not None and text is not None:
                out.append((v, text))
        return out

    def tag_audio(self, audio: Any, tags: list[tuple]) -> None:
        """Apply tags to the audio file object."""
        for k, v in tags:
            audio[k] = v

    async def embed_cover(self, audio: Any, cover_path: str) -> None:
        """Embed cover art into the audio file."""
        if not Path(cover_path).exists():
            logger.warning("Cover art file not found: %s", cover_path)
            return

        # Check if file is accessible and not empty
        try:
            file_size = Path(cover_path).stat().st_size
            if file_size == 0:
                logger.warning("Cover art file is empty: %s", cover_path)
                return
        except OSError as e:
            logger.warning("Cannot access cover art file %s: %s", cover_path, e)
            return

        if self == Container.FLAC:
            # Enforce FLAC blocksize limit using previously computed file_size
            if file_size > FLAC_MAX_BLOCKSIZE:
                logger.error("Cover art too big for FLAC: %d bytes", file_size)
                return

            cover = Picture()
            cover.type = 3  # Cover (front)
            cover.mime = "image/jpeg"
            async with aiofiles.open(cover_path, "rb") as img:
                cover.data = await img.read()
            audio.add_picture(cover)

        elif self == Container.MP3:
            cover = APIC()
            cover.type = 3  # Cover (front)
            cover.mime = "image/jpeg"
            async with aiofiles.open(cover_path, "rb") as img:
                cover.data = await img.read()
            audio.add(cover)

        elif self == Container.AAC:
            async with aiofiles.open(cover_path, "rb") as img:
                cover = MP4Cover(await img.read(), imageformat=MP4Cover.FORMAT_JPEG)
            audio["covr"] = [cover]

    def save_audio(self, audio: Any, path: str) -> None:
        """Save the audio file with embedded tags and artwork."""
        if self == Container.FLAC or self == Container.AAC:
            audio.save()
        elif self == Container.MP3:
            audio.save(path, "v2_version=3")


async def tag_file(
    file_path: str, metadata: dict[str, Any], cover_path: str | None = None
) -> None:
    """Tag an audio file with metadata and optionally embed cover art.

    Args:
        file_path: Path to the audio file
        metadata: Dictionary containing metadata fields
        cover_path: Optional path to cover art image
    """
    if not Path(file_path).exists():
        logger.error("Audio file not found: %s", file_path)
        return

    # Determine container format from file extension
    ext = Path(file_path).suffix.lower()
    if ext == ".flac":
        container = Container.FLAC
    elif ext in (".m4a", ".mp4", ".aac"):
        container = Container.AAC
    elif ext == ".mp3":
        container = Container.MP3
    else:
        logger.error("Unsupported audio format: %s", ext)
        return

    try:
        # Load the audio file
        audio = container.get_mutagen_class(file_path)

        # Apply metadata tags
        tags = container.get_tag_pairs(metadata)
        logger.debug("Tagging %s with %d tags", file_path, len(tags))
        container.tag_audio(audio, tags)

        # Embed cover art if provided
        if cover_path:
            await container.embed_cover(audio, cover_path)
            logger.debug("Embedded cover art from %s", cover_path)

        # Save the file
        container.save_audio(audio, file_path)
        logger.info("Successfully tagged audio file: %s", file_path)

    except Exception:
        logger.exception("Failed to tag audio file %s", file_path)
        raise
