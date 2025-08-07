# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Global pytest configuration for ripstream tests."""

# Configure pytest-asyncio for all async tests
pytest_plugins = ["pytest_asyncio"]


# Mark all async test functions with asyncio marker
def pytest_configure(config):
    """Configure pytest with asyncio markers."""
    config.addinivalue_line("markers", "asyncio: mark test as async")


# Note: Async tests should be manually marked with @pytest.mark.asyncio
# This function was causing issues with incorrect async detection
