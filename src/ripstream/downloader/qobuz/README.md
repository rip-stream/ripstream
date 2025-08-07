# Qobuz Downloader

This module provides a complete implementation of a Qobuz music downloader that integrates with the ripstream framework.

## Features

- **Authentication**: Supports both email/password and auth token authentication
- **Automatic App ID/Secret Discovery**: Automatically extracts app credentials from Qobuz web player
- **High-Quality Downloads**: Supports all Qobuz quality levels (MP3 320, FLAC 16/44.1, FLAC 24/96, FLAC 24/192)
- **Bulk Downloads**: Download entire albums, playlists, and artist discographies
- **Metadata Integration**: Converts Qobuz metadata to ripstream's unified model system
- **Search Functionality**: Search for tracks, albums, and playlists
- **Download Management**: Full integration with ripstream's download queue and progress tracking

## Architecture

The Qobuz downloader follows ripstream's plugin architecture and consists of:

### Core Components

1. **QobuzDownloader** (`downloader.py`): Main downloader class extending `BaseDownloader`
2. **QobuzClient** (`client.py`): Handles Qobuz API interactions and authentication
3. **Models** (`models.py`): Qobuz-specific data structures and API response models

### Key Classes

- `QobuzDownloader`: Main interface implementing the BaseDownloader contract
- `QobuzClient`: Low-level API client for Qobuz services
- `QobuzCredentials`: Authentication credentials model
- `QobuzTrackResponse`, `QobuzAlbumResponse`, `QobuzPlaylistResponse`: API response models
- `QobuzDownloadInfo`: Download URL and metadata container

## Usage

### Basic Setup

```python
from ripstream.downloader.config import DownloaderConfig
from ripstream.downloader.progress import ProgressTracker
from ripstream.downloader.qobuz import QobuzDownloader
from ripstream.downloader.session import SessionManager

# Configure downloader
config = DownloadConfig(download_directory=Path("./downloads"))
session_manager = SessionManager(config)
progress_tracker = ProgressTracker()

# Create downloader
downloader = QobuzDownloader(config, session_manager, progress_tracker)
```

### Authentication

```python
# Using email/password
credentials = {
    "email_or_userid": "your_email@example.com",
    "password_or_token": "your_password",
    "use_auth_token": False,
}

# Using auth token
credentials = {
    "email_or_userid": "your_user_id",
    "password_or_token": "your_auth_token",
    "use_auth_token": True,
}

# Authenticate
authenticated = await downloader.authenticate(credentials)
```

### Searching and Downloading

```python
from ripstream.downloader.enums import ContentType

# Search for tracks
tracks = await downloader.search("Daft Punk", ContentType.TRACK, limit=10)

# Get download info
download_info = await downloader.get_download_info(tracks[0].info.id)

# Download track
result = await downloader.download(download_info)
```

### Working with Albums

```python
# Search for albums
albums = await downloader.search("Random Access Memories", ContentType.ALBUM)

# Get full album metadata
album = await downloader.get_album_metadata(albums[0].info.id)

# Download entire album at once
results = await downloader.download_album(albums[0].info.id)

# Check results
successful = [r for r in results if r.is_success]
failed = [r for r in results if not r.is_success]
print(f"Downloaded {len(successful)} tracks, {len(failed)} failed")
```

### Working with Playlists

```python
# Search for playlists
playlists = await downloader.search("Electronic", ContentType.PLAYLIST)

# Download entire playlist
results = await downloader.download_playlist(playlists[0].info.id)

# Playlist tracks are downloaded to a dedicated folder
print(f"Playlist downloaded to: {results[0].file_path}")
```

### Artist Discography Downloads

```python
# Download an artist's complete discography
results = await downloader.download_artist_discography("artist_id")

# This downloads all albums by the artist
print(f"Downloaded {len(results)} tracks from discography")
```

## Quality Levels

Qobuz supports multiple quality levels:

| Quality | Format | Bitrate | Description |
|---------|--------|---------|-------------|
| 1 | MP3 | 320 kbps | High quality lossy |
| 2 | FLAC | 1411 kbps | CD quality lossless (16-bit/44.1kHz) |
| 3 | FLAC | ~2304 kbps | Hi-Res lossless (24-bit/96kHz) |
| 4 | FLAC | ~4608 kbps | Hi-Res lossless (24-bit/192kHz) |

The downloader automatically selects the highest available quality by default.

## Authentication Details

### App ID and Secrets

The Qobuz downloader uses a sophisticated method to obtain valid app credentials:

1. **Automatic Discovery**: Fetches the Qobuz web player and extracts app ID and secrets
2. **Secret Validation**: Tests multiple secrets to find working ones
3. **Caching**: Stores valid credentials for reuse

### Credential Types

- **Email/Password**: Standard user credentials
- **Auth Token**: Pre-obtained authentication token for API access

## Error Handling

The downloader handles various error conditions:

- **Authentication Errors**: Invalid credentials, expired tokens
- **Content Restrictions**: Geo-blocked or unavailable content
- **Network Errors**: Connection issues, rate limiting
- **Download Errors**: Corrupted downloads, insufficient storage

## Integration with ripstream Models

The Qobuz downloader seamlessly integrates with ripstream's unified model system:

- **Track**: Qobuz tracks are converted to ripstream `Track` objects
- **Album**: Qobuz albums become ripstream `Album` objects with track relationships
- **Playlist**: Qobuz playlists are mapped to ripstream `Playlist` objects
- **Metadata**: All Qobuz-specific metadata is preserved in the model's raw data

## Testing

The module includes comprehensive tests covering:

- Authentication flows
- Metadata extraction and conversion
- Search functionality
- Download operations
- Error handling scenarios

Run tests with:
```bash
pytest tests/downloader/test_qobuz_downloader.py
```

## Dependencies

- `aiohttp`: Async HTTP client for API requests
- `pydantic`: Data validation and serialization
- `aiofiles`: Async file operations

## Limitations

- Requires valid Qobuz subscription for high-quality downloads
- Subject to Qobuz's rate limiting and terms of service
- App ID/secret discovery may break if Qobuz changes their web player structure

## Contributing

When contributing to the Qobuz downloader:

1. Follow ripstream's coding standards
2. Maintain compatibility with the BaseDownloader interface
3. Add tests for new functionality
4. Update documentation for API changes

## Legal Notice

This downloader is for educational and personal use only. Users must comply with Qobuz's terms of service and applicable copyright laws. The developers are not responsible for any misuse of this software.
