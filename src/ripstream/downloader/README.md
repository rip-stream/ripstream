# RipStream Downloader Module

The RipStream downloader module provides a comprehensive, generic framework for implementing music downloaders. It follows DRY principles and single responsibility patterns, offering a solid foundation for building downloaders for various streaming services.

## Architecture Overview

The downloader module is built around several key components:

### Core Classes

- **`BaseDownloader`**: Abstract base class that all downloaders must inherit from
- **`DownloadableContent`**: Represents content that can be downloaded with metadata
- **`DownloadResult`**: Contains the result of a download operation
- **`DownloadSession`**: Manages HTTP sessions with retry logic and error handling

### Configuration

- **`DownloadConfig`**: Main configuration class for the downloader
- **`DownloadSettings`**: Settings for individual downloads (timeouts, retries, etc.)

### Progress Tracking

- **`ProgressTracker`**: Tracks progress for multiple downloads
- **`DownloadProgress`**: Represents the progress of a single download
- **`ProgressCallback`**: Protocol for progress callback functions

### Queue Management

- **`DownloadQueue`**: Manages a queue of download tasks
- **`DownloadTask`**: Represents a download task with metadata and dependencies

### Session Management

- **`SessionManager`**: Manages HTTP sessions for different sources
- **`DownloadSession`**: Provides HTTP operations with error handling

### Error Handling

Comprehensive exception hierarchy:
- **`DownloadError`**: Base exception for download-related errors
- **`NetworkError`**: Network-related errors
- **`AuthenticationError`**: Authentication failures
- **`RateLimitError`**: Rate limiting errors
- **`RetryExhaustedError`**: When all retry attempts are exhausted

## Usage Examples

### Basic Downloader Implementation

```python
from ripstream.downloader import (
    BaseDownloader,
    DownloadableContent,
    ContentType,
    DownloaderConfig,
    SessionManager,
    ProgressTracker,
)

class MyStreamingServiceDownloader(BaseDownloader):
    @property
    def source_name(self) -> str:
        return "my_service"

    @property
    def supported_content_types(self) -> list[ContentType]:
        return [ContentType.TRACK, ContentType.ALBUM]

    async def authenticate(self, credentials: dict[str, Any]) -> bool:
        # Implement authentication logic
        pass

    async def get_download_info(self, content_id: str) -> DownloadableContent:
        # Fetch metadata from service API
        pass

    async def _download_content(self, content, file_path, progress_callback):
        # Implement actual download logic
        pass
```

### Using the Downloader

```python
async def download_example():
    # Setup
    config = DownloadConfig()
    session_manager = SessionManager(config)
    progress_tracker = ProgressTracker()

    # Create downloader
    downloader = MyStreamingServiceDownloader(config, session_manager, progress_tracker)

    # Authenticate
    await downloader.authenticate({"api_key": "your_key"})

    # Get content info
    content = await downloader.get_download_info("track_123")

    # Download
    result = await downloader.download(content)

    if result.is_success:
        print(f"Downloaded: {result.file_path}")
    else:
        print(f"Failed: {result.error_message}")
```

### Progress Tracking

```python
def on_progress(download_id, progress):
    print(f"Download {download_id}: {progress.percentage:.1f}% - {progress.get_formatted_speed()}")

progress_tracker.add_callback(on_progress)
```

### Queue Management

```python
from ripstream.downloader import DownloadQueue, DownloadTask

queue = DownloadQueue(max_size=1000)

# Add tasks
task = DownloadTask(
    content_id="track_123",
    content_type=ContentType.TRACK,
    source="my_service",
    title="My Song",
    url="https://example.com/track_123",
    file_path="/downloads/my_song.mp3",
)

await queue.add_task(task)

# Process tasks
while not queue.is_empty:
    task = await queue.get_next_task()
    if task:
        # Process the task
        await queue.complete_task(task.task_id)
```

## Configuration

### Download Settings

```python
from ripstream.downloader import DownloaderConfig, DownloadSettings, RetryStrategy

config = DownloadConfig(
    download_directory=Path("./downloads"),
    max_concurrent_downloads=3,
    default_settings=DownloadBehaviorSettings(
        timeout_seconds=30.0,
        max_retries=3,
        retry_strategy=RetryStrategy.EXPONENTIAL,
        retry_delay=1.0,
        verify_checksums=True,
    )
)
```

### Source-Specific Settings

```python
# Add source-specific configuration
config.add_source_setting("spotify", "max_retries", 5)
config.add_source_setting("deezer", "timeout_seconds", 60.0)

# Get settings for a specific source
settings = config.get_behavior_for_source("spotify")
```

## Error Handling

The module provides comprehensive error handling with specific exception types:

```python
from ripstream.downloader.exceptions import (
    AuthenticationError,
    NetworkError,
    RateLimitError,
    RetryExhaustedError,
)

try:
    result = await downloader.download(content)
except AuthenticationError:
    print("Authentication failed - check credentials")
except RateLimitError as e:
    print(f"Rate limited - retry after {e.retry_after} seconds")
except NetworkError as e:
    print(f"Network error: {e.status_code}")
except RetryExhaustedError as e:
    print(f"Download failed after {e.retry_count} retries")
```

## Features

### Retry Logic
- Configurable retry strategies (linear, exponential, fixed delay)
- Automatic retry on transient failures
- Exponential backoff to avoid overwhelming servers

### Progress Tracking
- Real-time download progress
- Speed calculation and ETA estimation
- Multiple progress callbacks support

### Session Management
- HTTP session pooling and reuse
- SSL verification control
- Custom headers and user agents
- Rate limiting support

### File Management
- Safe filename generation
- Checksum verification
- Temporary file handling
- Directory creation

### Queue Management
- Priority-based task scheduling
- Task dependencies
- Concurrent download limiting
- Task state tracking

## Testing

The module includes comprehensive tests:

```bash
# Run downloader tests
pytest tests/downloader/

# Run specific test file
pytest tests/downloader/test_base_downloader.py
```

## Extension Points

The framework is designed to be easily extensible:

1. **Custom Downloaders**: Inherit from `BaseDownloader`
2. **Custom Progress Callbacks**: Implement `ProgressCallback` protocol
3. **Custom Retry Strategies**: Extend retry logic in downloaders
4. **Custom Session Handling**: Override session creation in `SessionManager`

## Best Practices

1. **Always use async context managers** for proper resource cleanup
2. **Implement proper authentication** with credential validation
3. **Handle rate limiting** gracefully with appropriate delays
4. **Validate downloaded content** using checksums when available
5. **Use progress callbacks** for user feedback
6. **Configure appropriate timeouts** for your use case
7. **Implement proper error handling** for different failure scenarios

## Dependencies

The downloader module requires:
- `aiohttp` for HTTP operations
- `pydantic` for data validation
- `asyncio` for asynchronous operations

Optional dependencies:
- `pytest` for running tests
- `pytest-asyncio` for async test support

## Future Enhancements

Potential areas for future development:
- Resume interrupted downloads
- Parallel chunk downloading
- Bandwidth throttling
- Download scheduling
- Plugin system for custom sources
- Metrics and monitoring integration
