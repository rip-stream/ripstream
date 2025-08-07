#!/usr/bin/env python3
"""
Copyright (c) 2025 Ripstream Project.

Build script for packaging Ripstream into a standalone executable.

This script handles the complete build process including:
- Cleaning previous builds
- Building the executable with PyInstaller
- Creating distribution packages
- Providing build information
"""

import os
import shutil
import subprocess  # noqa: S404
import sys
import time
from pathlib import Path


def print_banner(text: str) -> None:
    """Print a formatted banner."""
    print("\n" + "=" * 60)
    print(f" {text}")
    print("=" * 60)


def clean_build() -> None:
    """Clean previous build artifacts."""
    print_banner("Cleaning Previous Build")

    directories_to_clean = ["build", "dist", "__pycache__"]

    for directory in directories_to_clean:
        if Path(directory).exists():
            print(f"Removing {directory}/")
            shutil.rmtree(directory)

    # Clean .pyc files
    for root, _dirs, files in os.walk("."):
        for file in files:
            if file.endswith(".pyc"):
                Path(Path(root) / file).unlink()

    print("✓ Build artifacts cleaned")


def build_executable() -> bool:
    """Build the executable using PyInstaller."""
    print_banner("Building Executable")

    try:
        # Run PyInstaller with the spec file
        subprocess.run(
            ["pyinstaller", "ripstream.spec", "--clean"],  # noqa: S607
            check=True,
            capture_output=True,
            text=True,
        )

    except subprocess.CalledProcessError as e:
        print(f"✗ Build failed with error code {e.returncode}")
        print("STDOUT:", e.stdout)
        print("STDERR:", e.stderr)
        return False
    except FileNotFoundError:
        print(
            "✗ PyInstaller not found. Please install it with: uv add --group dev pyinstaller"
        )
        return False
    else:
        print("✓ Build completed successfully")
        return True


def get_file_size(file_path: Path) -> str:
    """Get human-readable file size."""
    size = file_path.stat().st_size
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} TB"


def show_build_info() -> None:
    """Show information about the built executable."""
    print_banner("Build Information")

    exe_path = Path("dist/Ripstream.exe")

    if exe_path.exists():
        file_size = get_file_size(exe_path)
        print(f"Executable: {exe_path}")
        print(f"Size: {file_size}")
        print(f"Created: {time.ctime(exe_path.stat().st_mtime)}")

        # # Test if the executable can be run
        # Uncomment the following lines to test the executable
        # print("\nTesting executable...")
        # try:
        #     result = subprocess.run(
        #         [str(exe_path), "--version"],
        #         capture_output=True,
        #         text=True,
        #         timeout=10,
        #     )
        #     if result.returncode == 0:
        #         print("✓ Executable test passed")
        #     else:
        #         print("⚠ Executable test returned non-zero exit code")
        # except (subprocess.TimeoutExpired, FileNotFoundError):
        #     print("⚠ Could not test executable (this is normal for GUI apps)")

        print(f"\n✓ Executable ready for distribution: {exe_path.absolute()}")
    else:
        print("✗ Executable not found in dist/ directory")


def create_distribution_info() -> None:
    """Create distribution information file."""
    print_banner("Creating Distribution Info")

    # Get PyInstaller version safely
    pyinstaller_version = subprocess.run(
        ["pyinstaller", "--version"],  # noqa: S607
        capture_output=True,
        text=True,
    ).stdout.strip()

    info_content = f"""# Ripstream Distribution

## Installation
1. Download Ripstream.exe
2. Run the executable - no installation required!

## System Requirements
- Windows 10 or later (64-bit)
- No additional software required (all dependencies included)

## File Information
- Built on: {time.strftime("%Y-%m-%d %H:%M:%S")}
- Python version: {sys.version.split()[0]}
- PyInstaller version: {pyinstaller_version}

## Usage
Simply double-click Ripstream.exe to launch the application.

## Troubleshooting
- If Windows Defender flags the executable, add it to exclusions
- If the app doesn't start, try running from command line to see error messages
- Make sure you have the latest Windows updates installed

## Support
For issues and support, please visit the project repository.
"""

    Path("dist/README.txt").write_text(info_content, encoding="utf-8")

    print("✓ Distribution info created: dist/README.txt")


def main() -> None:
    """Execute the main build process."""
    print_banner("Ripstream Build Script")
    print("Building standalone executable for distribution...")

    start_time = time.time()

    # Step 1: Clean previous builds
    clean_build()

    # Step 2: Build executable
    if not build_executable():
        print("\n✗ Build failed!")
        sys.exit(1)

    # Step 3: Show build information
    show_build_info()

    # Step 4: Create distribution info
    create_distribution_info()

    # Final summary
    build_time = time.time() - start_time
    print_banner("Build Complete")
    print(f"Total build time: {build_time:.1f} seconds")
    print("\nYour executable is ready for distribution!")
    print("Location: dist/Ripstream.exe")
    print("\nTo distribute:")
    print("1. Share the Ripstream.exe file")
    print("2. Include the README.txt for user instructions")
    print("3. Users can run it directly - no installation needed!")


if __name__ == "__main__":
    main()
