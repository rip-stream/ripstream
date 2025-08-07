# Ripstream Packaging Guide

This guide explains how to package the Ripstream application into a standalone executable for distribution to end users.

## Overview

The packaging process creates a single executable file (`Ripstream.exe`) that contains:
- The entire Python runtime
- All Python dependencies
- The application code
- Resources (icons, etc.)
- Everything needed to run the application

Users can simply download and run the executable without installing Python or any dependencies.

## Prerequisites

1. **Python Environment**: Ensure you have the development environment set up
2. **PyInstaller**: Already included in development dependencies
3. **All Dependencies**: Make sure all application dependencies are installed

```bash
# Install development dependencies (including PyInstaller)
uv add --group dev pyinstaller
```

## Quick Start

### Method 1: Using the Build Script (Recommended)

```bash
# Run the automated build script
python build.py
```

Or on Windows:
```bash
# Double-click or run from command line
build.bat
```

### Method 2: Manual Build

```bash
# Clean previous builds
pyinstaller ripstream.spec --clean
```

## Build Files

### `ripstream.spec`
The PyInstaller specification file that configures the build process:

- **Entry Point**: `main.py`
- **Icon**: `images/icon.png`
- **Hidden Imports**: Explicitly includes modules that PyInstaller might miss
- **Excludes**: Removes unnecessary modules to reduce file size
- **Data Files**: Includes resource files (icons, etc.)
- **Build Options**: Optimized for size and performance

### `build.py`
Automated build script that:

1. **Cleans** previous build artifacts
2. **Builds** the executable using PyInstaller
3. **Tests** the executable
4. **Creates** distribution documentation
5. **Reports** build statistics

### `build.bat`
Windows batch file for easy building on Windows systems.

## Build Process Details

### 1. Cleaning
- Removes `build/` and `dist/` directories
- Cleans Python cache files (`.pyc`)
- Ensures a fresh build environment

### 2. Analysis
PyInstaller analyzes the code to determine:
- Required Python modules
- Shared libraries and DLLs
- Data files and resources
- Entry points and dependencies

### 3. Building
Creates the executable with:
- **Single File**: Everything bundled into one `.exe`
- **No Console**: GUI application (no command prompt window)
- **Icon**: Application icon embedded
- **Compression**: UPX compression for smaller size
- **Optimization**: Excludes unnecessary modules

### 4. Testing
- Verifies the executable was created
- Checks file size and creation time
- Attempts basic functionality test

## Output

After building, you'll find in the `dist/` directory:

- **`Ripstream.exe`** (~55MB): The standalone executable
- **`README.txt`**: Distribution instructions for end users

## Distribution

### For End Users
1. Download `Ripstream.exe`
2. Run it directly - no installation required
3. Windows may show security warnings (normal for unsigned executables)

### For Developers
1. Share the `Ripstream.exe` file
2. Include `README.txt` for user instructions
3. Consider code signing for production releases

## Optimization Tips

### Reducing File Size
The current build excludes many unnecessary modules. To further reduce size:

1. **Review Dependencies**: Remove unused packages from `pyproject.toml`
2. **Exclude More Modules**: Add to the `excludes` list in `ripstream.spec`
3. **One-Directory Mode**: Use directory distribution instead of single file

### Improving Performance
1. **UPX Compression**: Already enabled (reduces size, may slightly increase startup time)
2. **Bytecode Optimization**: Consider setting `optimize=2` in the spec file
3. **Lazy Imports**: Use lazy imports in the application code

## Troubleshooting

### Common Issues

#### "Module not found" errors
- Add missing modules to `hiddenimports` in `ripstream.spec`
- Check if the module is being imported dynamically

#### Large file size
- Review and expand the `excludes` list
- Consider using one-directory distribution
- Remove unused dependencies

#### Slow startup
- This is normal for PyInstaller executables
- Consider splash screen for better user experience
- One-directory mode may start faster

#### Windows Defender warnings
- Normal for unsigned executables
- Consider code signing for production
- Users can add to exclusions

### Build Failures

#### PyInstaller not found
```bash
uv add --group dev pyinstaller
```

#### Missing dependencies
```bash
uv sync
```

#### Permission errors
- Run as administrator on Windows
- Check file permissions
- Close any running instances of the application

## Advanced Configuration

### Code Signing (Production)
For production releases, consider code signing:

1. Obtain a code signing certificate
2. Use `signtool.exe` on Windows
3. Update the spec file with signing parameters

### Custom Splash Screen
Add a splash screen while the app loads:

```python
# In ripstream.spec
splash = Splash('images/splash.png',
                binaries=a.binaries,
                datas=a.datas,
                text_pos=(10, 50),
                text_size=12,
                text_color='black')
```

### Version Information
Add version info to the executable:

```python
# Create version.rc file and reference in spec
version_file='version.rc'
```

## Continuous Integration

For automated builds in CI/CD:

```yaml
# Example GitHub Actions workflow
- name: Build executable
  run: |
    uv sync
    python build.py
    
- name: Upload artifact
  uses: actions/upload-artifact@v3
  with:
    name: ripstream-executable
    path: dist/Ripstream.exe
```

## Security Considerations

1. **Virus Scanners**: May flag PyInstaller executables as suspicious
2. **Code Signing**: Recommended for production releases
3. **Dependencies**: Keep all dependencies updated
4. **Source Protection**: PyInstaller doesn't obfuscate code

## Performance Metrics

Current build statistics:
- **File Size**: ~55MB (optimized)
- **Build Time**: ~60 seconds
- **Startup Time**: 2-5 seconds (typical for PyInstaller)
- **Memory Usage**: Similar to running with Python interpreter

## Support

For packaging issues:
1. Check the build logs in `build/ripstream/warn-ripstream.txt`
2. Review PyInstaller documentation
3. Test with a minimal example first
4. Consider using virtual environments for clean builds

---

**Note**: This packaging setup is optimized for Windows. For cross-platform distribution, you'll need to build on each target platform (Windows, macOS, Linux) as PyInstaller creates platform-specific executables.