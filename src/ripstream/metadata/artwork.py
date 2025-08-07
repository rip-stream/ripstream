# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Artwork downloading and processing for ripstream."""

import asyncio
import contextlib
import hashlib
import logging
import shutil
from pathlib import Path
from typing import Any

import aiofiles
import aiohttp
from PIL import Image

logger = logging.getLogger(__name__)

# Global set to track temporary artwork directories for cleanup
_artwork_tempdirs: set[str] = set()
# Set to track directories that failed cleanup (for retry)
_failed_cleanup_dirs: set[str] = set()
# Global semaphores to prevent concurrent artwork downloads per album/folder
_artwork_download_semaphores: dict[str, asyncio.Semaphore] = {}
_semaphore_lock: asyncio.Lock | None = None


def _get_semaphore_lock() -> asyncio.Lock:
    """Get or create the semaphore lock for the current event loop."""
    global _semaphore_lock

    try:
        current_loop = asyncio.get_running_loop()
    except RuntimeError:
        current_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(current_loop)

    # Check if we have a lock and if it's bound to the current loop
    if _semaphore_lock is not None:
        try:
            # Check if lock is valid by attempting to acquire it without blocking
            # This is safer than accessing private _get_loop method
            if _semaphore_lock.locked():
                pass  # Lock exists and is accessible
            return _semaphore_lock
        except RuntimeError:
            # Lock is bound to a different loop, create a new one
            logger.debug("Creating new semaphore lock for current event loop")
        else:
            return _semaphore_lock
        _semaphore_lock = None

    if _semaphore_lock is None:
        _semaphore_lock = asyncio.Lock()

    return _semaphore_lock


def remove_artwork_tempdirs():
    """Clean up temporary artwork directories."""
    # Create a copy of the set to avoid concurrent modification during iteration
    tempdirs_to_remove = _artwork_tempdirs.copy()
    logger.debug("Removing artwork temp dirs: %s", tempdirs_to_remove)

    for path in tempdirs_to_remove:
        try:
            # Check if directory exists and is not in use
            if Path(path).exists():
                # Try to remove with better error handling
                shutil.rmtree(path, ignore_errors=False)
                logger.debug("Successfully removed temp dir: %s", path)
        except PermissionError:
            logger.warning("Permission denied removing temp dir: %s", path)
        except OSError as e:
            if e.errno == 32:  # File is being used by another process
                logger.warning("Temp dir in use, will retry later: %s", path)
            else:
                logger.warning("Failed to remove temp dir %s: %s", path, e)
        except FileNotFoundError as e:
            logger.warning("Unexpected error removing temp dir %s: %s", path, e)

    # Move failed directories to retry set and clear main set
    _failed_cleanup_dirs.update(
        tempdirs_to_remove
        - {path for path in tempdirs_to_remove if not Path(path).exists()}
    )
    _artwork_tempdirs.clear()

    # Clean up unused semaphores
    cleanup_artwork_semaphores()


def cleanup_failed_artwork_dirs():
    """Retry cleanup of previously failed artwork directories."""
    if not _failed_cleanup_dirs:
        return

    failed_dirs_copy = _failed_cleanup_dirs.copy()
    logger.debug(
        "Retrying cleanup of %d failed artwork directories", len(failed_dirs_copy)
    )

    for path in failed_dirs_copy:
        try:
            if Path(path).exists():
                shutil.rmtree(path, ignore_errors=False)
                logger.debug("Successfully cleaned up previously failed dir: %s", path)
                _failed_cleanup_dirs.discard(path)
        except (OSError, PermissionError, FileNotFoundError) as e:
            logger.debug("Cleanup retry still failed for %s: %s", path, e)


def add_artwork_tempdir(path: str):
    """Safely add a temporary artwork directory to the cleanup set."""
    _artwork_tempdirs.add(path)


def remove_artwork_tempdir(path: str):
    """Safely remove a temporary artwork directory from the cleanup set."""
    _artwork_tempdirs.discard(path)
    _failed_cleanup_dirs.discard(path)


async def get_artwork_semaphore(folder_path: str) -> asyncio.Semaphore:
    """Get or create a semaphore for artwork downloads in a specific folder."""
    try:
        # Get the current event loop
        current_loop = asyncio.get_running_loop()
    except RuntimeError:
        # No running loop, create one
        current_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(current_loop)

    # Get the lock for the current event loop
    semaphore_lock = _get_semaphore_lock()
    async with semaphore_lock:
        # Check if we have a semaphore for this folder
        if folder_path in _artwork_download_semaphores:
            existing_semaphore = _artwork_download_semaphores[folder_path]
            try:
                # Test if the semaphore is bound to the current loop
                # by checking if we can acquire it (safer than accessing private methods)
                if existing_semaphore.locked():
                    pass  # Semaphore exists and is accessible
            except RuntimeError:
                # Semaphore is bound to a different loop, remove it
                logger.debug(
                    "Removing semaphore bound to different event loop for folder: %s",
                    folder_path,
                )
                del _artwork_download_semaphores[folder_path]
            else:
                # If we get here, the semaphore is valid for the current loop
                return existing_semaphore

        # Create a new semaphore for the current event loop
        _artwork_download_semaphores[folder_path] = asyncio.Semaphore(1)
        return _artwork_download_semaphores[folder_path]


def cleanup_artwork_semaphores():
    """Clean up unused artwork download semaphores."""
    # Remove semaphores for folders that no longer exist
    folders_to_remove = [
        folder_path
        for folder_path in _artwork_download_semaphores
        if not Path(folder_path).exists()
    ]

    for folder_path in folders_to_remove:
        _artwork_download_semaphores.pop(folder_path, None)


def _prepare_saved_artwork(
    folder: str, artwork_urls: dict[str, str]
) -> tuple[str | None, Any | None]:
    """Prepare saved artwork download."""
    largest_url = _get_largest_artwork_url(artwork_urls)
    if not largest_url:
        return None, None

    saved_cover_path = str(Path(folder) / "cover.jpg")
    return saved_cover_path, largest_url


def _prepare_embed_artwork(
    folder: str, artwork_urls: dict[str, str], embed_size: str
) -> tuple[str | None, Any | None]:
    """Prepare embedded artwork download."""
    embed_url = artwork_urls.get(embed_size) or _get_largest_artwork_url(artwork_urls)
    if not embed_url:
        return None, None

    # Create temporary directory for embedded artwork
    embed_dir = str(Path(folder) / "__artwork")
    try:
        Path(embed_dir).mkdir(parents=True, exist_ok=True)
        add_artwork_tempdir(embed_dir)
    except OSError:
        logger.exception("Failed to create artwork directory %s", embed_dir)
        return None, None

    # Use a more consistent hash generation approach using SHA-256 (more secure than MD5)
    url_hash = hashlib.sha256(embed_url.encode("utf-8")).hexdigest()[:16]
    embed_cover_path = str(Path(embed_dir) / f"cover-{url_hash}.jpg")
    return embed_cover_path, embed_url


def _apply_size_restrictions(
    config: dict[str, Any],
    save_artwork: bool,
    saved_cover_path: str | None,
    embed_artwork: bool,
    embed_cover_path: str | None,
) -> None:
    """Apply size restrictions to downloaded artwork."""
    if save_artwork and saved_cover_path:
        max_width = config.get("saved_max_width", 0)
        if max_width > 0:
            downscale_image(saved_cover_path, max_width)

    if embed_artwork and embed_cover_path:
        max_width = config.get("embed_max_width", 0)
        if max_width > 0:
            downscale_image(embed_cover_path, max_width)


def _check_existing_artwork(
    folder: str,
    config: dict[str, Any],
    artwork_urls: dict[str, str],
    save_artwork: bool,
    embed_artwork: bool,
) -> tuple[str | None, str | None, bool, bool]:
    """Check for existing artwork files and return paths and updated flags."""
    embed_cover_path = None
    saved_cover_path = None

    # Check for existing saved artwork
    if save_artwork:
        saved_cover_path = str(Path(folder) / "cover.jpg")
        if Path(saved_cover_path).exists():
            logger.debug("Saved artwork already exists: %s", saved_cover_path)
            save_artwork = False  # Skip download

    # Check for existing embedded artwork
    if embed_artwork:
        embed_size = config.get("embed_size", "large")
        embed_url = artwork_urls.get(embed_size) or _get_largest_artwork_url(
            artwork_urls
        )
        if embed_url:
            embed_dir = str(Path(folder) / "__artwork")
            url_hash = hashlib.sha256(embed_url.encode("utf-8")).hexdigest()[:16]
            embed_cover_path = str(Path(embed_dir) / f"cover-{url_hash}.jpg")

            if Path(embed_cover_path).exists():
                logger.debug("Embedded artwork already exists: %s", embed_cover_path)
                embed_artwork = False  # Skip download

    return embed_cover_path, saved_cover_path, save_artwork, embed_artwork


def _prepare_downloadables(
    session: aiohttp.ClientSession,
    folder: str,
    artwork_urls: dict[str, str],
    config: dict[str, Any],
    save_artwork: bool,
    embed_artwork: bool,
) -> tuple[list, str | None, str | None]:
    """Prepare downloadable tasks and return paths."""
    downloadables = []
    embed_cover_path = None
    saved_cover_path = None

    # Prepare saved artwork
    if save_artwork:
        saved_cover_path, saved_url = _prepare_saved_artwork(folder, artwork_urls)
        if saved_url and saved_cover_path:
            downloadables.append(_download_image(session, saved_url, saved_cover_path))

    # Prepare embedded artwork
    if embed_artwork:
        embed_size = config.get("embed_size", "large")
        embed_cover_path, embed_url = _prepare_embed_artwork(
            folder, artwork_urls, embed_size
        )
        if embed_url and embed_cover_path:
            downloadables.append(_download_image(session, embed_url, embed_cover_path))

    return downloadables, embed_cover_path, saved_cover_path


def _verify_downloaded_files(
    embed_cover_path: str | None, saved_cover_path: str | None
) -> tuple[str | None, str | None]:
    """Verify that downloaded files actually exist."""
    if embed_cover_path and not Path(embed_cover_path).exists():
        logger.error("Embed cover art file was not created: %s", embed_cover_path)
        embed_cover_path = None

    if saved_cover_path and not Path(saved_cover_path).exists():
        logger.error("Saved cover art file was not created: %s", saved_cover_path)
        saved_cover_path = None

    return embed_cover_path, saved_cover_path


async def download_artwork(
    session: aiohttp.ClientSession,
    folder: str,
    artwork_urls: dict[str, str],
    config: dict[str, Any],
    for_playlist: bool = False,
) -> tuple[str | None, str | None]:
    """Download artwork and return paths for embedding and saving.

    Args:
        session: HTTP session for downloading
        folder: Target folder for artwork
        artwork_urls: Dictionary with artwork URLs by size (e.g., {'large': 'url', 'small': 'url'})
        config: Artwork configuration settings
        for_playlist: If True, disable saved hi-res covers

    Returns
    -------
        Tuple of (embed_cover_path, saved_cover_path)
    """
    save_artwork = config.get("save_artwork", False) and not for_playlist
    embed_artwork = config.get("embed_artwork", False)

    if not (save_artwork or embed_artwork) or not artwork_urls:
        return None, None

    # Use semaphore to prevent concurrent downloads to the same folder
    semaphore = await get_artwork_semaphore(folder)

    async with semaphore:
        # Check if artwork already exists before downloading
        embed_cover_path, saved_cover_path, save_artwork, embed_artwork = (
            _check_existing_artwork(
                folder, config, artwork_urls, save_artwork, embed_artwork
            )
        )

        # If both files exist, return early
        if not save_artwork and not embed_artwork:
            return embed_cover_path, saved_cover_path

        # Prepare downloadables
        downloadables, embed_cover_path, saved_cover_path = _prepare_downloadables(
            session, folder, artwork_urls, config, save_artwork, embed_artwork
        )

        if not downloadables:
            return embed_cover_path, saved_cover_path

        try:
            await asyncio.gather(*downloadables)
            # Verify files were actually downloaded
            embed_cover_path, saved_cover_path = _verify_downloaded_files(
                embed_cover_path, saved_cover_path
            )

        except Exception:
            logger.exception("Error downloading artwork")
            # Clean up any partial files
            for path in [embed_cover_path, saved_cover_path]:
                if path and Path(path).exists():
                    with contextlib.suppress(OSError):
                        Path(path).unlink()
            return None, None

        # Apply size restrictions if configured
        _apply_size_restrictions(
            config, save_artwork, saved_cover_path, embed_artwork, embed_cover_path
        )

        return embed_cover_path, saved_cover_path


async def _download_image(session: aiohttp.ClientSession, url: str, file_path: str):
    """Download an image from URL to file path."""
    max_retries = 3
    retry_delay = 1.0

    for attempt in range(max_retries):
        try:
            async with session.get(
                url, timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                response.raise_for_status()

                # Ensure directory exists
                Path(file_path).parent.mkdir(parents=True, exist_ok=True)

                # Use a temporary file to avoid partial writes
                temp_path = f"{file_path}.tmp"
                try:
                    async with aiofiles.open(temp_path, "wb") as f:
                        async for chunk in response.content.iter_chunked(8192):
                            await f.write(chunk)

                    # Move temp file to final location atomically
                    # Handle case where target file already exists
                    if Path(file_path).exists():
                        logger.debug(
                            "Target file already exists, removing temp file: %s",
                            file_path,
                        )
                        Path(temp_path).unlink()
                        return

                    Path(temp_path).rename(file_path)
                    logger.debug("Downloaded artwork: %s -> %s", url, file_path)

                except Exception:
                    # Clean up temp file on error
                    if Path(temp_path).exists():
                        with contextlib.suppress(OSError):
                            Path(temp_path).unlink()
                    raise
                else:
                    return

        except (TimeoutError, aiohttp.ClientError, OSError) as e:
            if attempt < max_retries - 1:
                logger.warning(
                    "Artwork download attempt %d failed, retrying: %s", attempt + 1, e
                )
                await asyncio.sleep(retry_delay * (attempt + 1))
            else:
                logger.exception(
                    "Failed to download artwork from %s after %d attempts",
                    url,
                    max_retries,
                )
                raise
        except Exception:
            logger.exception("Unexpected error downloading artwork from %s", url)
            raise


def _get_largest_artwork_url(artwork_urls: dict[str, str]) -> str | None:
    """Get the largest available artwork URL."""
    # Priority order: original > large > medium > small > thumbnail
    size_priority = ["original", "large", "medium", "small", "thumbnail"]

    for size in size_priority:
        if artwork_urls.get(size):
            return artwork_urls[size]

    # Return any available URL if none match priority
    for url in artwork_urls.values():
        if url:
            return url

    return None


def downscale_image(image_path: str, max_dimension: int):
    """Downscale an image in place given a maximum allowed dimension.

    Args:
        image_path: Path to the image file
        max_dimension: Maximum dimension (width or height) allowed
    """
    try:
        # Open the image
        with Image.open(image_path) as image:
            width, height = image.size

            # Skip if already within limits
            if max_dimension >= max(width, height):
                return

            # Calculate new dimensions while maintaining aspect ratio
            if width > height:
                new_width = max_dimension
                new_height = int(height * (max_dimension / width))
            else:
                new_height = max_dimension
                new_width = int(width * (max_dimension / height))

            # Resize and save
            resized_image = image.resize(
                (new_width, new_height), Image.Resampling.LANCZOS
            )
            resized_image.save(image_path, "JPEG", quality=95)

        logger.debug("Downscaled image %s to %dx%d", image_path, new_width, new_height)

    except Exception:
        logger.exception("Failed to downscale image %s", image_path)


def extract_artwork_urls(covers_data: Any) -> dict[str, str]:
    """Extract artwork URLs from covers data.

    This function handles different cover data formats from various sources.
    """
    if not covers_data:
        return {}

    artwork_urls = {}

    # Handle ripstream Covers model
    if hasattr(covers_data, "__dict__"):
        # Try to extract URLs from covers object attributes
        for size in ["original", "large", "medium", "small", "thumbnail"]:
            url = getattr(covers_data, f"{size}_url", None)
            if url:
                artwork_urls[size] = url

    # Handle dictionary format
    elif isinstance(covers_data, dict):
        # Direct URL mapping
        artwork_urls.update({
            key: value
            for key, value in covers_data.items()
            if isinstance(value, str) and value.startswith(("http://", "https://"))
        })

    return artwork_urls
