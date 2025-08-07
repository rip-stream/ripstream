# Download Provider Strategy Pattern

This module implements a strategy design pattern for download providers that is agnostic to streaming sources. It provides a clean abstraction layer on top of the existing downloader implementations.

## Architecture Overview

The download provider strategy pattern consists of several key components:

### 1. Base Classes (`base.py`)

- **`BaseDownloadProvider`**: Abstract base class that defines the interface for all download providers
- **`DownloadProviderResult`**: Result container for download operations

### 2. Concrete Implementations

- **`QobuzDownloadProvider`**: Adapter for the existing QobuzDownloader
- Future implementations for Tidal, Deezer, YouTube, etc.

### 3. Factory Pattern (`factory.py`)

- **`DownloadProviderFactory`**: Factory for creating service-specific download providers
- Supports dynamic registration of new providers

### 4. Service Orchestration (`service.py`)

- **`DownloadService`**: Main service that orchestrates the complete download workflow
- Handles URL parsing, metadata fetching, and downloading

## Key Features

### 🔄 **Agnostic to Streaming Sources**
The strategy pattern allows the frontend to work with any streaming service without knowing the implementation details.

### 🏭 **Factory Pattern**
Easy creation and management of download providers through the factory pattern.

### 🔗 **URL-to-Download Workflow**
Complete workflow from URL parsing to metadata fetching to downloading.

### 📊 **Progress Tracking**
Built-in support for progress callbacks and tracking.

### 🔐 **Authentication Management**
Handles authentication for each streaming service automatically.

## Usage Examples

### Basic Usage

```python
from ripstream.downloader.providers.service import DownloadService
from ripstream.downloader.config import DownloaderConfig
from ripstream.downloader.session import SessionManager
from ripstream.downloader.progress import ProgressTracker

# Initialize the service
config = DownloadConfig()
session_manager = SessionManager()
progress_tracker = ProgressTracker()
download_service = DownloadService(config, session_manager, progress_tracker)

# Download from URL
result = await download_service.download_from_url(
    url="https://www.qobuz.com/album/example/123456",
    download_directory="./downloads",
    credentials={"email": "user@example.com", "password": "pass"},
    progress_callback=lambda bytes_downloaded: print(f"Downloaded: {bytes_downloaded} bytes")
)

if result.success:
    print(f"Download successful! {len(result.download_results)} files downloaded.")
else:
    print(f"Download failed: {result.error_message}")
```

### Using Pre-fetched Metadata

```python
from ripstream.ui.metadata_providers.factory import MetadataProviderFactory
from ripstream.models.enums import StreamingSource

# Fetch metadata first
metadata_provider = MetadataProviderFactory.create_provider(StreamingSource.QOBUZ, credentials)
metadata_result = await metadata_provider.fetch_artist_metadata("artist_id")

# Download using metadata
result = await download_service.download_with_metadata(
    metadata_result=metadata_result,
    download_directory="./downloads",
    credentials=credentials
)
```

### Direct Provider Usage

```python
from ripstream.downloader.providers.factory import DownloadProviderFactory
from ripstream.models.enums import StreamingSource

# Create provider directly
provider = DownloadProviderFactory.create_provider(
    StreamingSource.QOBUZ,
    config, session_manager, progress_tracker,
    credentials
)

# Authenticate and download
await provider.authenticate()
result = await provider.download_album("album_id", "./downloads")
```

## Workflow

### 1. URL Parsing
The service uses the existing `URLParser` to extract:
- Streaming service (Qobuz, Tidal, etc.)
- Content type (album, track, playlist, artist)
- Content ID

### 2. Provider Selection
The factory creates the appropriate download provider based on the streaming service.

### 3. Authentication
Each provider handles authentication with its respective streaming service.

### 4. Download Execution
The provider downloads the content using the appropriate method for the content type.

### 5. Result Handling
Results are standardized across all providers using `DownloadProviderResult`.

## Adding New Providers

To add support for a new streaming service:

1. **Create the Provider Implementation** (or adapter for existing downloader):
```python
from ripstream.downloader.providers.base import BaseDownloadProvider

# If you have an existing downloader:
class TidalDownloadProvider(BaseDownloadProvider):
    def __init__(self, config, session_manager, progress_tracker, credentials=None):
        super().__init__(config, session_manager, progress_tracker, credentials)
        self._downloader = TidalDownloader(config, session_manager, progress_tracker)

    @property
    def service_name(self) -> str:
        return "tidal"

    @property
    def streaming_source(self) -> StreamingSource:
        return StreamingSource.TIDAL

    # Implement abstract methods by delegating to existing downloader...
```

2. **Register with Factory**:
```python
from ripstream.downloader.providers.factory import DownloadProviderFactory

DownloadProviderFactory.register_provider(
    StreamingSource.TIDAL,
    TidalDownloadProvider
)
```

3. **Update URL Parser** (if needed):
Add URL patterns for the new service in `ripstream.core.url_parser.URLParser`.

## Design Principles

### ✅ **DRY (Don't Repeat Yourself)**
- Common functionality is implemented in the base classes
- Providers only implement service-specific logic

### ✅ **Single Responsibility**
- Each class has a single, well-defined responsibility
- `BaseDownloadProvider`: Interface definition
- `DownloadProviderFactory`: Provider creation
- `DownloadService`: Workflow orchestration

### ✅ **Type Hints**
- All methods and properties are fully typed
- Uses modern Python typing (no `typing.Dict`, `typing.List`, etc.)

### ✅ **Agnostic Design**
- Frontend doesn't need to know about specific streaming services
- Easy to add new services without changing existing code

## Integration with Frontend

The download provider strategy integrates seamlessly with the PyQt6 frontend:

```python
# In your PyQt6 application
class DownloadManager:
    def __init__(self):
        self.download_service = DownloadService(config, session_manager, progress_tracker)

    async def handle_url_paste(self, url: str):
        """Handle when user pastes a URL."""
        result = await self.download_service.download_from_url(url)
        self.update_ui_with_result(result)

    async def handle_metadata_download(self, metadata_result: MetadataResult):
        """Handle download from pre-fetched metadata."""
        result = await self.download_service.download_with_metadata(metadata_result)
        self.update_ui_with_result(result)
```

## Error Handling

The strategy provides comprehensive error handling:

- **Authentication errors**: Handled by each provider
- **Network errors**: Retry logic built into base classes
- **Invalid URLs**: Validated by URL parser
- **Unsupported services**: Clear error messages with supported services list

## Testing

The strategy pattern makes testing easier:

```python
# Mock provider for testing
class MockDownloadProvider(BaseDownloadProvider):
    async def download_content(self, content_id, content_type, **kwargs):
        return self._create_download_result(True, [mock_result])

# Test the service with mock provider
DownloadProviderFactory.register_provider(StreamingSource.TEST, MockDownloadProvider)
```

This architecture provides a clean, maintainable, and extensible solution for downloading music from various streaming services while keeping the frontend agnostic to the underlying implementations.
