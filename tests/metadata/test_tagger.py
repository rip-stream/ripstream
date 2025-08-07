# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Tests for metadata tagging functionality."""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ripstream.metadata.tagger import Container, tag_file


class TestContainer:
    """Test Container enum functionality."""

    def test_flac_container(self):
        """Test FLAC container functionality."""
        container = Container.FLAC

        # Test tag pairs generation
        metadata = {
            "title": "Test Song",
            "artist": "Test Artist",
            "album": "Test Album",
            "tracknumber": 1,
            "year": 2023,
        }

        tags = container.get_tag_pairs(metadata)

        # Check that we get the expected FLAC tags
        tag_dict = dict(tags)
        assert tag_dict["TITLE"] == "Test Song"
        assert tag_dict["ARTIST"] == "Test Artist"
        assert tag_dict["ALBUM"] == "Test Album"
        assert tag_dict["TRACKNUMBER"] == "01"  # Should be zero-padded
        assert tag_dict["YEAR"] == "2023"

    def test_mp3_container(self):
        """Test MP3 container functionality."""
        container = Container.MP3

        metadata = {
            "title": "Test Song",
            "artist": "Test Artist",
            "tracknumber": 1,
            "tracktotal": 10,
        }

        tags = container.get_tag_pairs(metadata)

        # Check that we get ID3 tag objects
        assert len(tags) > 0
        for tag_name, tag_obj in tags:
            if tag_name == "TRCK":  # Track number tag
                assert hasattr(tag_obj, "text")

    def test_mp4_container(self):
        """Test MP4/AAC container functionality."""
        container = Container.AAC

        metadata = {
            "title": "Test Song",
            "artist": "Test Artist",
            "tracknumber": 1,
            "tracktotal": 10,
        }

        tags = container.get_tag_pairs(metadata)

        # Check that we get MP4 tags
        tag_dict = dict(tags)
        assert tag_dict["\xa9nam"] == "Test Song"  # Title
        assert tag_dict["\xa9ART"] == "Test Artist"  # Artist
        assert tag_dict["trkn"] == [(1, 10)]  # Track number/total


class TestTagFile:
    """Test tag_file function."""

    @pytest.mark.asyncio
    async def test_tag_file_nonexistent(self):
        """Test tagging a non-existent file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            fake_file = Path(temp_dir) / "nonexistent.flac"

            metadata = {"title": "Test"}

            # Should not raise an exception, just log an error
            await tag_file(str(fake_file), metadata)

    @pytest.mark.asyncio
    async def test_tag_file_unsupported_format(self):
        """Test tagging an unsupported file format."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.txt"
            test_file.write_text("test content")

            metadata = {"title": "Test"}

            # Should not raise an exception, just log an error
            await tag_file(str(test_file), metadata)

    @pytest.mark.asyncio
    @patch("ripstream.metadata.tagger.FLAC")
    @patch("ripstream.metadata.tagger.aiofiles.open")
    async def test_tag_flac_file(self, mock_aiofiles_open, mock_flac):
        """Test tagging a FLAC file with metadata and artwork."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test files
            audio_file = Path(temp_dir) / "test.flac"
            cover_file = Path(temp_dir) / "cover.jpg"

            audio_file.write_bytes(b"fake flac data")
            cover_file.write_bytes(b"fake jpg data")

            # Mock FLAC object
            mock_audio = MagicMock()
            mock_flac.return_value = mock_audio

            # Mock aiofiles for cover reading
            mock_file = AsyncMock()
            mock_file.read.return_value = b"fake jpg data"
            mock_aiofiles_open.return_value.__aenter__.return_value = mock_file

            metadata = {
                "title": "Test Song",
                "artist": "Test Artist",
                "album": "Test Album",
                "tracknumber": 1,
            }

            await tag_file(str(audio_file), metadata, str(cover_file))

            # Verify FLAC was called with the file path
            mock_flac.assert_called_once_with(str(audio_file))

            # Verify tags were set
            assert mock_audio.__setitem__.called

            # Verify cover was added
            assert mock_audio.add_picture.called

            # Verify file was saved
            assert mock_audio.save.called

    @pytest.mark.asyncio
    @patch("ripstream.metadata.tagger.ID3")
    @patch("ripstream.metadata.tagger.aiofiles.open")
    async def test_tag_mp3_file(self, mock_aiofiles_open, mock_id3):
        """Test tagging an MP3 file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            audio_file = Path(temp_dir) / "test.mp3"
            cover_file = Path(temp_dir) / "cover.jpg"

            audio_file.write_bytes(b"fake mp3 data")
            cover_file.write_bytes(b"fake jpg data")

            # Mock ID3 object
            mock_audio = MagicMock()
            mock_id3.return_value = mock_audio

            # Mock aiofiles for cover reading
            mock_file = AsyncMock()
            mock_file.read.return_value = b"fake jpg data"
            mock_aiofiles_open.return_value.__aenter__.return_value = mock_file

            metadata = {
                "title": "Test Song",
                "artist": "Test Artist",
            }

            await tag_file(str(audio_file), metadata, str(cover_file))

            # Verify ID3 was called
            mock_id3.assert_called_once_with(str(audio_file))

            # Verify cover was added
            assert mock_audio.add.called

            # Verify file was saved with correct parameters
            mock_audio.save.assert_called_once_with(str(audio_file), "v2_version=3")


if __name__ == "__main__":
    pytest.main([__file__])
