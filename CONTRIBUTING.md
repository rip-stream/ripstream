# Contributing to Ripstream

Thank you for your interest in contributing to Ripstream! This document provides guidelines and instructions for setting up your development environment and contributing to the project.

## 🚀 Quick Start

### Prerequisites

- Python 3.12 or higher
- Git
- [uv](https://github.com/astral-sh/uv) - Fast Python package installer and resolver

### Installing uv

#### macOS/Linux
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

#### Windows (PowerShell)
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

After installation, restart your terminal or source your shell configuration to ensure `uv` is available in your PATH.

## 🛠️ Development Setup

### 1. Fork and Clone the Repository

```bash
# Fork the repository on GitHub, then clone your fork
git clone https://github.com/YOUR_USERNAME/ripstream.git
cd ripstream

# Add the upstream repository as a remote
git remote add upstream https://github.com/original-owner/ripstream.git
```

### 2. Create and Activate Virtual Environment

#### Linux/macOS
```bash
# Create virtual environment
uv venv

# Activate virtual environment
source .venv/bin/activate
```

#### Windows (PowerShell)
```powershell
# Create virtual environment
uv venv

# Activate virtual environment
.\.venv\Scripts\activate.ps1
```

#### Windows (Command Prompt)
```cmd
# Create virtual environment
uv venv

# Activate virtual environment
.\.venv\Scripts\activate.bat
```

### 3. Install Dependencies

```bash
# Sync all dependencies (including dev dependencies)
uv sync
```

This will install all project dependencies as defined in `pyproject.toml`, including development dependencies.

### 4. Install Pre-commit Hooks

```bash
# Install pre-commit hooks
pre-commit install
```

The pre-commit hooks will automatically run code formatting and linting checks before each commit.

### 5. Verify Installation

```bash
# Run the application to verify everything works
python main.py

# Run tests to ensure everything is working
pytest tests/
```

## 🧪 Testing

We maintain comprehensive test coverage across all components. Please ensure your contributions include appropriate tests.

### Running Tests

```bash
# Run all tests
pytest tests/

# Run tests with coverage report
pytest --cov=src tests/

# Run specific test categories
pytest tests/ui/          # UI component tests
pytest tests/downloader/  # Downloader framework tests
pytest tests/models/      # Data model tests
pytest tests/metadata/    # Metadata processing tests
pytest tests/core/        # Core utility tests
pytest tests/config/      # Configuration tests

# Run tests in parallel (faster)
pytest -n auto tests/

# Run tests with verbose output
pytest -v tests/

# Run specific test file
pytest tests/ui/test_main_window.py

# Run specific test function
pytest tests/ui/test_main_window.py::test_window_initialization
```

### Writing Tests

#### Test Structure
- Place tests in the `tests/` directory
- Mirror the source code structure in your test organization
- Use descriptive test names that explain what is being tested
- Follow the pattern: `test_<functionality>_<expected_behavior>`

#### Test Categories

1. **Unit Tests**: Test individual functions and methods
2. **Integration Tests**: Test component interactions
3. **UI Tests**: Test PyQt6 interface components (use `pytest-qt`)
4. **End-to-End Tests**: Test complete workflows

#### Example Test

```python
import pytest
from unittest.mock import Mock, patch
from ripstream.core.url_parser import URLParser, StreamingSource

class TestURLParser:
    def test_parse_qobuz_album_url_returns_correct_info(self):
        """Test that Qobuz album URLs are parsed correctly."""
        parser = URLParser()
        url = "https://open.qobuz.com/album/abc123"

        result = parser.parse_url(url)

        assert result.service == StreamingSource.QOBUZ
        assert result.content_type == ContentType.ALBUM
        assert result.content_id == "abc123"
        assert result.is_valid

    @pytest.mark.asyncio
    async def test_downloader_handles_network_error_gracefully(self):
        """Test that downloader properly handles network errors."""
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_get.side_effect = aiohttp.ClientError("Network error")

            downloader = QobuzDownloader(config, session_manager, progress_tracker)

            with pytest.raises(NetworkError):
                await downloader.get_download_info("track_123")
```

#### Testing Guidelines

- **Test both success and failure cases**
- **Mock external dependencies** (network calls, file system operations)
- **Use fixtures** for common test data and setup
- **Test edge cases** and boundary conditions
- **Ensure tests are deterministic** and don't depend on external state
- **Use descriptive assertions** with clear error messages

### Test Requirements for Contributions

All contributions must include:

1. **Unit tests** for new functions and methods
2. **Integration tests** for component interactions
3. **UI tests** for interface changes (using `pytest-qt`)
4. **Error handling tests** for failure scenarios
5. **Edge case tests** for boundary conditions

## 📝 Code Style and Standards

### Code Formatting

We use [Ruff](https://github.com/astral-sh/ruff) for code formatting and linting:

```bash
# Format code
ruff format src/ tests/

# Check for linting issues
ruff check src/ tests/

# Fix auto-fixable linting issues
ruff check --fix src/ tests/
```

### Code Style Guidelines

1. **Follow PEP 8** with Ruff's default configuration
2. **Use type hints** for all function parameters and return values
3. **Write comprehensive docstrings** using NumPy style
4. **Keep functions focused** and follow single responsibility principle
5. **Use descriptive variable names** that explain their purpose
6. **Limit line length** to 88 characters (Ruff default)

### Example Code Style

```python
from typing import Optional, List, Dict, Any
from pathlib import Path

class MusicDownloader:
    """Downloads music from streaming services with metadata.

    This class provides a unified interface for downloading music
    from various streaming services while maintaining consistent
    metadata and file organization.

    Parameters
    ----------
    config : DownloaderConfig
        Configuration object containing download settings
    session_manager : SessionManager
        HTTP session manager for network requests

    Attributes
    ----------
    download_count : int
        Number of successful downloads completed
    """

    def __init__(
        self,
        config: DownloaderConfig,
        session_manager: SessionManager
    ) -> None:
        self.config = config
        self.session_manager = session_manager
        self.download_count = 0

    async def download_track(
        self,
        track_id: str,
        output_path: Optional[Path] = None
    ) -> DownloadResult:
        """Download a single track with metadata.

        Parameters
        ----------
        track_id : str
            Unique identifier for the track
        output_path : Path, optional
            Custom output path for the downloaded file

        Returns
        -------
        DownloadResult
            Result object containing download status and file path

        Raises
        ------
        DownloadError
            If the download fails due to network or service issues
        ValidationError
            If the track_id is invalid or empty
        """
        if not track_id:
            raise ValidationError("Track ID cannot be empty")

        try:
            # Implementation here
            pass
        except NetworkError as e:
            logger.error(f"Network error downloading track {track_id}: {e}")
            raise DownloadError(f"Failed to download track: {e}") from e
```

## 🔄 Development Workflow

### 1. Create a Feature Branch

```bash
# Ensure you're on the main branch and up to date
git checkout main
git pull upstream main

# Create a new feature branch
git checkout -b feature/your-feature-name
```

### 2. Make Your Changes

- Write your code following the style guidelines
- Add comprehensive tests for your changes
- Update documentation as needed
- Ensure all tests pass

### 3. Test Your Changes

```bash
# Run the full test suite
pytest tests/

# Run linting and formatting checks
ruff check src/ tests/
ruff format src/ tests/

# Test the application manually
python main.py
```

### 4. Commit Your Changes

```bash
# Stage your changes
git add .

# Commit with a descriptive message
git commit -m "feat: add support for new streaming service

- Implement URL parsing for ServiceX
- Add downloader with authentication
- Include comprehensive tests
- Update documentation"
```

### 5. Push and Create Pull Request

```bash
# Push your branch to your fork
git push origin feature/your-feature-name

# Create a pull request on GitHub
# Include a detailed description of your changes
```

## 📋 Pull Request Guidelines

### Pull Request Checklist

Before submitting a pull request, ensure:

- [ ] **Code follows style guidelines** (Ruff formatting passes)
- [ ] **All tests pass** (`pytest tests/` succeeds)
- [ ] **New functionality includes tests** with good coverage
- [ ] **Documentation is updated** for new features
- [ ] **Commit messages are descriptive** and follow conventional commits
- [ ] **No merge conflicts** with the main branch
- [ ] **Pre-commit hooks pass** without issues

### Pull Request Description Template

```markdown
## Description
Brief description of the changes and their purpose.

## Type of Change
- [ ] Bug fix (non-breaking change that fixes an issue)
- [ ] New feature (non-breaking change that adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update
- [ ] Performance improvement
- [ ] Code refactoring

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing completed
- [ ] All tests pass

## Screenshots (if applicable)
Include screenshots for UI changes.

## Additional Notes
Any additional information or context about the changes.
```

## 🏗️ Architecture Guidelines

### Adding New Streaming Services

When adding support for a new streaming service:

1. **Create URL patterns** in `src/ripstream/core/url_parser.py`
2. **Implement downloader** in `src/ripstream/downloader/providers/`
3. **Add service configuration** in `src/ripstream/config/services.py`
4. **Create metadata provider** in `src/ripstream/ui/metadata_providers/`
5. **Add comprehensive tests** for all components
6. **Update documentation** with service-specific information

### Code Organization Principles

- **Single Responsibility**: Each class/function should have one clear purpose
- **Dependency Injection**: Use dependency injection for testability
- **Type Safety**: Use Pydantic models and type hints throughout
- **Error Handling**: Implement comprehensive error handling with specific exceptions
- **Logging**: Add appropriate logging for debugging and monitoring

## 🐛 Bug Reports and Feature Requests

### Reporting Bugs

When reporting bugs, please include:

1. **Clear description** of the issue
2. **Steps to reproduce** the problem
3. **Expected vs actual behavior**
4. **Environment information** (OS, Python version, etc.)
5. **Log files** or error messages
6. **Screenshots** if applicable

### Feature Requests

For feature requests, please provide:

1. **Clear description** of the desired feature
2. **Use case** and motivation
3. **Proposed implementation** (if you have ideas)
4. **Potential impact** on existing functionality

## 📚 Documentation

### Documentation Standards

- **Keep README.md updated** with new features
- **Document all public APIs** with comprehensive docstrings
- **Include code examples** in documentation
- **Update configuration documentation** for new settings
- **Maintain changelog** for version releases

### Docstring Format

Use NumPy-style docstrings:

```python
def process_metadata(
    track_data: Dict[str, Any],
    include_artwork: bool = True
) -> TrackMetadata:
    """Process raw track data into structured metadata.

    This function takes raw track data from a streaming service
    and converts it into a standardized TrackMetadata object
    with proper validation and type conversion.

    Parameters
    ----------
    track_data : Dict[str, Any]
        Raw track data from streaming service API
    include_artwork : bool, default True
        Whether to process and include artwork URLs

    Returns
    -------
    TrackMetadata
        Processed and validated track metadata

    Raises
    ------
    ValidationError
        If the track data is invalid or missing required fields
    ProcessingError
        If metadata processing fails

    Examples
    --------
    >>> raw_data = {"title": "Song Name", "artist": "Artist Name"}
    >>> metadata = process_metadata(raw_data)
    >>> print(metadata.title)
    'Song Name'
    """
```

## 🤝 Community Guidelines

### Code of Conduct

- **Be respectful** and inclusive in all interactions
- **Provide constructive feedback** in code reviews
- **Help newcomers** get started with the project
- **Focus on the code**, not the person
- **Assume good intentions** from contributors

### Getting Help

- **GitHub Discussions**: For general questions and discussions
- **GitHub Issues**: For bug reports and feature requests
- **Code Reviews**: For feedback on pull requests

## 🏷️ Release Process

### Version Numbering

We follow [Semantic Versioning](https://semver.org/):
- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes (backward compatible)

### Release Checklist

- [ ] All tests pass
- [ ] Documentation updated
- [ ] Changelog updated
- [ ] Version bumped in `pyproject.toml`
- [ ] Git tag created
- [ ] Release notes prepared

## 📄 License

By contributing to Ripstream, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing to Ripstream! Your efforts help make music downloading more accessible and reliable for everyone. 🎵
