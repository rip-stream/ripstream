# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Example usage of the download provider strategy pattern."""

import asyncio
import logging
from pathlib import Path

from ripstream.core.url_parser import URLParser
from ripstream.downloader.config import DownloaderConfig
from ripstream.downloader.progress import ProgressTracker
from ripstream.downloader.providers.service import DownloadService
from ripstream.downloader.session import SessionManager
from ripstream.models.enums import StreamingSource
from ripstream.ui.metadata_providers.factory import MetadataProviderFactory

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def example_download_from_url():
    """Download content directly from a URL."""
    # Initialize configuration
    config = DownloaderConfig()
    session_manager = SessionManager()  # type: ignore[missing-argument]
    progress_tracker = ProgressTracker()

    # Create download service
    download_service = DownloadService(config, session_manager, progress_tracker)

    # Example Qobuz URL (replace with actual URL)
    url = "https://www.qobuz.com/album/example-album/123456"

    # Qobuz credentials (replace with actual credentials)
    credentials = {
        "email_or_userid": "your_email@example.com",
        "password_or_token": "your_password_or_token",
        "app_id": "your_app_id",
        "secrets": ["your_secret"],
        "use_auth_token": False,
    }

    try:
        # Download from URL
        result = await download_service.download_from_url(
            url=url,
            download_directory="./downloads",
            credentials=credentials,
            progress_callback=lambda bytes_downloaded: logger.info(
                "Downloaded: %s bytes", bytes_downloaded
            ),
        )

        if result.success:
            for _download_result in result.download_results:
                pass

    except Exception:
        logger.exception("Download from URL failed")
    finally:
        await download_service.cleanup()


async def example_download_with_metadata():
    """Download content using pre-fetched metadata."""
    # Initialize configuration
    config = DownloaderConfig()
    session_manager = SessionManager()  # type: ignore[missing-argument]
    progress_tracker = ProgressTracker()

    # Create download service
    download_service = DownloadService(config, session_manager, progress_tracker)

    # Create metadata provider
    metadata_provider = MetadataProviderFactory.create_provider(
        StreamingSource.QOBUZ,
        credentials={
            "email_or_userid": "your_email@example.com",
            "password_or_token": "your_password_or_token",
            "app_id": "your_app_id",
            "secrets": ["your_secret"],
            "use_auth_token": False,
        },
    )

    try:
        # Fetch metadata first
        artist_id = "123456"  # Replace with actual artist ID
        metadata_result = await metadata_provider.fetch_artist_metadata(artist_id)

        if metadata_result:
            # Download using the metadata
            result = await download_service.download_with_metadata(
                metadata_result=metadata_result,
                download_directory="./downloads",
                credentials={
                    "email_or_userid": "your_email@example.com",
                    "password_or_token": "your_password_or_token",
                    "app_id": "your_app_id",
                    "secrets": ["your_secret"],
                    "use_auth_token": False,
                },
            )

            if result.success:
                for _download_result in result.download_results:
                    pass

    except Exception:
        logger.exception("Download with metadata failed")
    finally:
        await download_service.cleanup()
        await metadata_provider.cleanup()


def example_url_parsing():
    """Parse URLs to determine service and content type."""
    url_parser = URLParser()

    # Example URLs for different services
    urls = [
        "https://www.qobuz.com/album/example-album/123456",
        "https://open.spotify.com/album/1234567890abcdef",
        "https://tidal.com/album/123456",
        "https://www.deezer.com/album/123456",
    ]

    for url in urls:
        url_parser.parse_url(url)


async def example_provider_factory():
    """Use the download provider factory directly."""
    from ripstream.downloader.providers.factory import DownloadProviderFactory

    # Check supported services
    supported_services = DownloadProviderFactory.get_supported_services()

    # Check if a service is supported
    is_qobuz_supported = DownloadProviderFactory.is_service_supported(
        StreamingSource.QOBUZ
    )

    # Create a provider directly
    config = DownloaderConfig()
    session_manager = SessionManager()  # type: ignore[missing-argument]
    progress_tracker = ProgressTracker()

    try:
        provider = DownloadProviderFactory.create_provider(
            StreamingSource.QOBUZ,
            config,
            session_manager,
            progress_tracker,
            credentials={
                "email_or_userid": "your_email@example.com",
                "password_or_token": "your_password_or_token",
                "app_id": "your_app_id",
                "secrets": ["your_secret"],
                "use_auth_token": False,
            },
        )

        # Authenticate
        authenticated = await provider.authenticate()

    except Exception:
        logger.exception("Provider factory example failed")
    finally:
        if "provider" in locals():
            await provider.cleanup()


async def main():
    """Run all examples."""
    # Create downloads directory
    Path("./downloads").mkdir(exist_ok=True)

    # Run examples
    example_url_parsing()
    await example_provider_factory()


if __name__ == "__main__":
    asyncio.run(main())
