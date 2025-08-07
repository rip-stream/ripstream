# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Tests for artwork downloading functionality."""

import tempfile
from unittest.mock import MagicMock, patch

import pytest

from ripstream.metadata.artwork import (
    download_artwork,
    downscale_image,
    extract_artwork_urls,
    remove_artwork_tempdirs,
)


class TestArtworkDownload:
    """Test artwork downloading functionality."""

    @pytest.mark.asyncio
    async def test_download_artwork_disabled(self):
        """Test when both save and embed artwork are disabled."""
        mock_session = MagicMock()
        folder = "/test/folder"
        artwork_urls = {"large": "http://example.com/large.jpg"}
        config = {"save_artwork": False, "embed_artwork": False}

        embed_path, saved_path = await download_artwork(
            mock_session, folder, artwork_urls, config
        )

        assert embed_path is None
        assert saved_path is None

    @pytest.mark.asyncio
    async def test_download_artwork_no_urls(self):
        """Test when no artwork URLs are provided."""
        mock_session = MagicMock()
        folder = "/test/folder"
        artwork_urls = {}
        config = {"save_artwork": True, "embed_artwork": True}

        embed_path, saved_path = await download_artwork(
            mock_session, folder, artwork_urls, config
        )

        assert embed_path is None
        assert saved_path is None

    @pytest.mark.asyncio
    @patch("ripstream.metadata.artwork._download_image")
    async def test_download_artwork_success(self, mock_download):
        """Test successful artwork download."""
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_session = MagicMock()
            artwork_urls = {
                "large": "http://example.com/large.jpg",
                "small": "http://example.com/small.jpg",
            }
            config = {
                "save_artwork": True,
                "embed_artwork": True,
                "embed_size": "large",
                "embed_max_width": 0,
                "saved_max_width": 0,
            }

            # Mock successful downloads and create the actual files
            async def mock_download_side_effect(session, url, file_path):
                # Create the directory if it doesn't exist
                import asyncio
                from pathlib import Path

                Path(file_path).parent.mkdir(parents=True, exist_ok=True)
                # Create the actual file
                Path(file_path).touch()
                # Make it properly async by awaiting something trivial
                await asyncio.sleep(0)

            mock_download.side_effect = mock_download_side_effect

            embed_path, saved_path = await download_artwork(
                mock_session, temp_dir, artwork_urls, config
            )

            # Verify paths are set
            assert embed_path is not None
            assert saved_path is not None
            assert saved_path.endswith("cover.jpg")
            assert "__artwork" in embed_path

            # Verify downloads were called
            assert mock_download.call_count == 2

    @pytest.mark.asyncio
    @patch("ripstream.metadata.artwork._download_image")
    async def test_download_artwork_failure(self, mock_download):
        """Test artwork download failure."""
        mock_session = MagicMock()
        folder = "/test/folder"
        artwork_urls = {"large": "http://example.com/large.jpg"}
        config = {"save_artwork": True, "embed_artwork": False}

        # Mock download failure
        mock_download.side_effect = Exception("Download failed")

        embed_path, saved_path = await download_artwork(
            mock_session, folder, artwork_urls, config
        )

        assert embed_path is None
        assert saved_path is None


class TestImageProcessing:
    """Test image processing functionality."""

    @patch("ripstream.metadata.artwork.Image")
    def test_downscale_image_no_resize_needed(self, mock_image):
        """Test downscaling when image is already small enough."""
        # Mock image that's already small
        mock_img = MagicMock()
        mock_img.size = (500, 400)  # Smaller than max dimension
        mock_image.open.return_value.__enter__.return_value = mock_img

        downscale_image("/fake/path.jpg", 600)

        # Should not call resize since image is already small enough
        mock_img.resize.assert_not_called()

    @patch("ripstream.metadata.artwork.Image")
    def test_downscale_image_resize_needed(self, mock_image):
        """Test downscaling when image needs to be resized."""
        # Mock large image
        mock_img = MagicMock()
        mock_img.size = (1200, 800)  # Larger than max dimension
        mock_resized = MagicMock()
        mock_img.resize.return_value = mock_resized
        mock_image.open.return_value.__enter__.return_value = mock_img

        downscale_image("/fake/path.jpg", 600)

        # Should call resize with correct dimensions (maintaining aspect ratio)
        mock_img.resize.assert_called_once()
        call_args = mock_img.resize.call_args[0]
        new_width, new_height = call_args[0]
        assert new_width == 600  # Width should be max dimension
        assert new_height == 400  # Height should maintain aspect ratio

        # Should save the resized image
        mock_resized.save.assert_called_once_with("/fake/path.jpg", "JPEG", quality=95)

    @patch("ripstream.metadata.artwork.Image")
    def test_downscale_image_error_handling(self, mock_image):
        """Test error handling in image downscaling."""
        mock_image.open.side_effect = Exception("Image error")

        # Should not raise exception, just log error
        downscale_image("/fake/path.jpg", 600)


class TestArtworkUtils:
    """Test artwork utility functions."""

    def test_extract_artwork_urls_empty(self):
        """Test extracting URLs from empty data."""
        assert extract_artwork_urls(None) == {}
        assert extract_artwork_urls({}) == {}

    def test_extract_artwork_urls_dict(self):
        """Test extracting URLs from dictionary format."""
        covers_data = {
            "large": "http://example.com/large.jpg",
            "small": "http://example.com/small.jpg",
            "invalid": "not_a_url",
        }

        urls = extract_artwork_urls(covers_data)

        assert urls["large"] == "http://example.com/large.jpg"
        assert urls["small"] == "http://example.com/small.jpg"
        assert "invalid" not in urls  # Non-URL values should be filtered

    def test_extract_artwork_urls_object(self):
        """Test extracting URLs from object with attributes."""
        mock_covers = MagicMock()
        mock_covers.large_url = "http://example.com/large.jpg"
        mock_covers.small_url = "http://example.com/small.jpg"
        mock_covers.original_url = None

        urls = extract_artwork_urls(mock_covers)

        assert urls["large"] == "http://example.com/large.jpg"
        assert urls["small"] == "http://example.com/small.jpg"
        assert "original" not in urls  # None values should be filtered

    @patch("ripstream.metadata.artwork.shutil.rmtree")
    @patch("ripstream.metadata.artwork.Path")
    def test_remove_artwork_tempdirs(self, mock_path, mock_rmtree):
        """Test cleanup of temporary artwork directories."""
        # Add some fake temp dirs
        from ripstream.metadata.artwork import _artwork_tempdirs

        # Clear any existing entries first
        _artwork_tempdirs.clear()

        _artwork_tempdirs.add("/tmp/artwork1")
        _artwork_tempdirs.add("/tmp/artwork2")

        # Mock Path.exists() to return True so directories are considered existing
        mock_path_instance = MagicMock()
        mock_path_instance.exists.return_value = True
        mock_path.return_value = mock_path_instance

        remove_artwork_tempdirs()

        # Should call rmtree for each directory that exists
        assert mock_rmtree.call_count == 2

        # Should clear the set
        assert len(_artwork_tempdirs) == 0

    @patch("ripstream.metadata.artwork.shutil.rmtree")
    def test_remove_artwork_tempdirs_file_not_found(self, mock_rmtree):
        """Test cleanup when directories don't exist."""
        from ripstream.metadata.artwork import _artwork_tempdirs

        _artwork_tempdirs.add("/tmp/nonexistent")

        # Mock FileNotFoundError
        mock_rmtree.side_effect = FileNotFoundError()

        # Should not raise exception
        remove_artwork_tempdirs()

        # Should still clear the set
        assert len(_artwork_tempdirs) == 0


if __name__ == "__main__":
    pytest.main([__file__])
