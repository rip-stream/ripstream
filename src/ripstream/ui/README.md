# Ripstream UI Components

This directory contains the PyQt6-based user interface components for the Ripstream music downloader application.

## Components

### Main Window (`main_window.py`)
The main application window with menu bar and central content area.

**Features:**
- File menu with Exit option
- Edit menu with Preferences option (Ctrl+, / Cmd+,)
- Help menu with About dialog
- Status bar showing configuration path
- Window geometry persistence

**Usage:**
```python
from ripstream.ui.main_window import main
main()
```

### Preferences Dialog (`preferences.py`)
The main preferences dialog with tabbed interface for configuring all application settings.

**Features:**
- Modal dialog with OK, Cancel, Apply, and Restore Defaults buttons
- Tabbed interface for organized settings
- Configuration change signals
- Base64 encoding/decoding for passwords and secrets

### Preference Tabs (`preferences_tabs.py`)
Individual tabs for different categories of settings:

#### GeneralTab
- Default audio quality selection
- Download folder configuration with browse button
- Source-specific and disc subdirectories options
- Interface preferences (updates, progress bars, etc.)

#### ServicesTab
- **Qobuz**: Email/password, quality (1-4), booklet downloads
- **Tidal**: Access/refresh tokens, user ID, country, quality (0-3), videos
- **Deezer**: ARL cookie, quality (0-2), deezloader options
- **SoundCloud**: Client ID, app version
- **YouTube**: Video downloads, video folder path

**Security:** All passwords, tokens, and secrets are automatically encoded as base64 when saved.

#### DownloadsTab
- Connection settings (max concurrent downloads, API rate limits)
- SSL verification
- Concurrent vs sequential downloads
- Database settings for tracking downloads and failures

#### AudioTab
- Audio conversion settings (codec, sampling rate, bit depth, bitrate)
- Artwork embedding and saving options
- Size limits for embedded and saved artwork

#### FilesTab
- File and folder naming templates
- Character restrictions and filename truncation
- Metadata handling (playlist albums, track renumbering, excluded tags)

#### AdvancedTab
- Qobuz discography filters (extras, repeats, non-albums, etc.)
- Last.fm integration settings
- CLI-specific options

## Configuration Management

### Base64 Encoding
Sensitive data (passwords, tokens, secrets) are automatically encoded using base64:

```python
from ripstream.ui.preferences import encode_secret, decode_secret

# Encoding
encoded = encode_secret("my_password")  # Returns base64 string

# Decoding
decoded = decode_secret(encoded)  # Returns original string
```

### Configuration Persistence
Settings are saved to JSON format using the UserConfig model:

```python
# Load configuration
config = UserConfig.from_json_file("~/.config/ripstream/config.json")

# Save configuration
config.to_json_file("~/.config/ripstream/config.json")
```

## Testing

### Test Script (`test_preferences.py`)
A standalone test script for the preferences dialog:

```bash
cd src/ripstream/ui
python test_preferences.py
```

## Requirements

- PyQt6
- Python 3.8+
- Pydantic (for configuration models)

## Installation

Install PyQt6:
```bash
pip install PyQt6
```

## Architecture

The UI follows these design principles:

### Single Responsibility
Each tab handles one category of settings and has clear load/save methods.

### DRY (Don't Repeat Yourself)
- Common functionality in `BasePreferenceTab`
- Shared encoding/decoding functions
- Consistent widget patterns

### Configuration Separation
- UI components don't directly modify configuration files
- All changes go through the UserConfig model
- Type-safe configuration with Pydantic validation

### Signal-Based Communication
- Configuration changes emit signals
- Loose coupling between components
- Easy to extend with additional listeners

## Usage Examples

### Opening Preferences from Menu
```python
def show_preferences(self):
    dialog = PreferencesDialog(self.config, self)
    dialog.config_changed.connect(self.on_config_changed)
    dialog.exec()

def on_config_changed(self, new_config):
    self.config = new_config
    self.save_config()
```

### Programmatic Configuration
```python
# Create dialog
dialog = PreferencesDialog(config)

# Connect to changes
dialog.config_changed.connect(lambda cfg: print("Config changed!"))

# Show dialog
result = dialog.exec()
```

## File Structure

```
src/ripstream/ui/
├── __init__.py              # Package initialization
├── README.md               # This documentation
├── main_window.py          # Main application window
├── preferences.py          # Main preferences dialog
├── preferences_tabs.py     # Individual preference tabs
└── test_preferences.py     # Test script
```

## Future Enhancements

- Dark mode support
- Keyboard shortcuts for all tabs
- Import/export configuration
- Configuration validation with user feedback
- Undo/redo for preference changes
- Search functionality within preferences
