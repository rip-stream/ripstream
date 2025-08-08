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
    async def test_download_artwork_disabled(self, tmp_path):
        """Test when both save and embed artwork are disabled."""
        mock_session = MagicMock()
        folder = str(tmp_path)
        artwork_urls = {"large": "http://example.com/large.jpg"}
        config = {"save_artwork": False, "embed_artwork": False}

        embed_path, saved_path = await download_artwork(
            mock_session, folder, artwork_urls, config
        )

        assert embed_path is None
        assert saved_path is None

    @pytest.mark.asyncio
    async def test_download_artwork_no_urls(self, tmp_path):
        """Test when no artwork URLs are provided."""
        mock_session = MagicMock()
        folder = str(tmp_path)
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
    async def test_download_artwork_failure(self, mock_download, tmp_path):
        """Test artwork download failure."""
        mock_session = MagicMock()
        folder = str(tmp_path)
        artwork_urls = {"large": "http://example.com/large.jpg"}
        config = {"save_artwork": True, "embed_artwork": False}

        # Mock download failure
        mock_download.side_effect = Exception("Download failed")

        embed_path, saved_path = await download_artwork(
            mock_session, folder, artwork_urls, config
        )

        assert embed_path is None
        assert saved_path is None

    @pytest.mark.asyncio
    async def test_concurrent_downloads_same_target_do_not_conflict(
        self, monkeypatch, tmp_path
    ):
        """Ensure concurrent downloads to the same file path don't raise and produce a single output."""
        import asyncio

        from ripstream.metadata.artwork import _download_image

        # Use a real _download_image but mock HTTP session and content
        class FakeStream:
            def __init__(self, chunks: list[bytes]):
                self._chunks = chunks

            async def iter_chunked(self, _size: int):
                for c in self._chunks:
                    await asyncio.sleep(0)  # yield control
                    yield c

        class FakeResponse:
            def __init__(self, chunks: list[bytes]):
                self.content = FakeStream(chunks)
                self.headers = {}

            def raise_for_status(self):
                return None

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

        class FakeSession:
            def __init__(self, chunks: list[bytes]):
                self._chunks = chunks

            def get(self, url: str, timeout=None):
                return FakeResponse(self._chunks)

        folder = tmp_path / "album"
        folder.mkdir(parents=True, exist_ok=True)
        target = folder / "cover.jpg"

        chunks = [b"a" * 10, b"b" * 10]
        session = FakeSession(chunks)

        # Run two concurrent downloads to the same destination
        await asyncio.gather(
            _download_image(session, "http://example/1.jpg", str(target)),
            _download_image(session, "http://example/1.jpg", str(target)),
        )

        # Assert file exists and contains expected length
        assert target.exists()
        assert target.stat().st_size in (20,)  # one winner writes full content


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

    def test_remove_artwork_tempdirs(self, tmp_path):
        """Test cleanup of temporary artwork directories without active locks."""
        from ripstream.metadata.artwork import _artwork_tempdirs

        # Prepare real directories
        d1 = tmp_path / "artwork1"
        d2 = tmp_path / "artwork2"
        d1.mkdir(parents=True, exist_ok=True)
        d2.mkdir(parents=True, exist_ok=True)

        # Ensure directories are tracked
        _artwork_tempdirs.clear()
        _artwork_tempdirs.add(str(d1))
        _artwork_tempdirs.add(str(d2))

        # Execute cleanup
        remove_artwork_tempdirs()

        # Directories should be removed and set cleared
        assert not d1.exists()
        assert not d2.exists()
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


class TestArtworkSemaphores:
    """Tests for artwork semaphore scoping per event loop and folder."""

    def test_get_artwork_semaphore_same_loop_same_folder_is_same(self, tmp_path):
        import asyncio
        import shutil

        from ripstream.metadata.artwork import (
            cleanup_artwork_semaphores,
            get_artwork_semaphore,
        )

        folder = tmp_path / "album"
        folder.mkdir(parents=True, exist_ok=True)

        loop = asyncio.new_event_loop()
        try:
            s1 = loop.run_until_complete(get_artwork_semaphore(str(folder)))
            s2 = loop.run_until_complete(get_artwork_semaphore(str(folder)))
            assert s1 is s2
        finally:
            loop.close()

        # Cleanup: remove folder and purge semaphores for non-existent folders
        shutil.rmtree(folder, ignore_errors=True)
        cleanup_artwork_semaphores()

    def test_get_artwork_semaphore_same_loop_different_folders_are_different(
        self, tmp_path
    ):
        import asyncio
        import shutil

        from ripstream.metadata.artwork import (
            cleanup_artwork_semaphores,
            get_artwork_semaphore,
        )

        folder_a = tmp_path / "albumA"
        folder_b = tmp_path / "albumB"
        folder_a.mkdir(parents=True, exist_ok=True)
        folder_b.mkdir(parents=True, exist_ok=True)

        loop = asyncio.new_event_loop()
        try:
            s1 = loop.run_until_complete(get_artwork_semaphore(str(folder_a)))
            s2 = loop.run_until_complete(get_artwork_semaphore(str(folder_b)))
            assert s1 is not s2
        finally:
            loop.close()

        shutil.rmtree(folder_a, ignore_errors=True)
        shutil.rmtree(folder_b, ignore_errors=True)
        cleanup_artwork_semaphores()

    def test_get_artwork_semaphore_different_loops_same_folder_are_different(
        self, tmp_path
    ):
        import asyncio
        import shutil

        from ripstream.metadata.artwork import (
            cleanup_artwork_semaphores,
            get_artwork_semaphore,
        )

        folder = tmp_path / "album"
        folder.mkdir(parents=True, exist_ok=True)

        loop1 = asyncio.new_event_loop()
        loop2 = asyncio.new_event_loop()
        try:
            s1 = loop1.run_until_complete(get_artwork_semaphore(str(folder)))
            s2 = loop2.run_until_complete(get_artwork_semaphore(str(folder)))
            assert s1 is not s2
        finally:
            loop1.close()
            loop2.close()

        shutil.rmtree(folder, ignore_errors=True)
        cleanup_artwork_semaphores()

    def test_cleanup_artwork_semaphores_removes_nonexistent_folders(self, tmp_path):
        import asyncio
        import shutil

        from ripstream.metadata.artwork import (
            _artwork_download_semaphores,
            cleanup_artwork_semaphores,
            get_artwork_semaphore,
        )

        folder = tmp_path / "album"
        folder.mkdir(parents=True, exist_ok=True)

        loop = asyncio.new_event_loop()
        try:
            # Create a semaphore entry
            _ = loop.run_until_complete(get_artwork_semaphore(str(folder)))
        finally:
            loop.close()

        # Ensure an entry exists for this folder
        assert any(str(folder) == key[1] for key in _artwork_download_semaphores)

        # Remove folder and cleanup
        shutil.rmtree(folder, ignore_errors=True)
        cleanup_artwork_semaphores()

        # Ensure entries for the removed folder are gone
        assert not any(str(folder) == key[1] for key in _artwork_download_semaphores)
