# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Tests for downloader utility functions."""

import pytest

from ripstream.downloader.utils import raise_error


class TestRaiseError:
    """Test the raise_error utility function."""

    def test_raise_error_basic(self):
        """Test raising a basic error without base error."""
        with pytest.raises(ValueError, match="Test error message"):
            raise_error(ValueError, "Test error message")

    def test_raise_error_with_base_error(self):
        """Test raising an error chained from a base error."""
        base_error = RuntimeError("Base error")

        with pytest.raises(ValueError, match="Chained error") as exc_info:
            raise_error(ValueError, "Chained error", base_error=base_error)

        # Check that the error is properly chained
        assert exc_info.value.__cause__ is base_error

    def test_raise_error_with_kwargs(self):
        """Test raising an error with additional keyword arguments."""

        # Create a custom exception that accepts additional arguments
        class CustomError(Exception):
            def __init__(self, message, code=None):
                super().__init__(message)
                self.code = code

        with pytest.raises(CustomError, match="Custom error") as exc_info:
            raise_error(CustomError, "Custom error", code=404)

        # Type assertion to help the type checker understand the specific exception type
        assert isinstance(exc_info.value, CustomError)
        assert exc_info.value.code == 404

    def test_raise_error_with_base_error_and_kwargs(self):
        """Test raising an error with both base error and kwargs."""
        base_error = RuntimeError("Base error")

        class CustomError(Exception):
            def __init__(self, message, code=None):
                super().__init__(message)
                self.code = code

        with pytest.raises(CustomError, match="Complex error") as exc_info:
            raise_error(CustomError, "Complex error", base_error=base_error, code=500)

        # Type assertion to help the type checker understand the specific exception type
        assert isinstance(exc_info.value, CustomError)
        assert exc_info.value.__cause__ is base_error
        assert exc_info.value.code == 500

    @pytest.mark.parametrize(
        ("error_type", "message"),
        [
            (ValueError, "Value error message"),
            (TypeError, "Type error message"),
            (RuntimeError, "Runtime error message"),
            (FileNotFoundError, "File not found message"),
        ],
    )
    def test_raise_error_different_types(self, error_type, message):
        """Test raising different types of errors."""
        with pytest.raises(error_type, match=message):
            raise_error(error_type, message)
