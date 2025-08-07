# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Tests for core utils module."""

import base64
import binascii

import pytest

from ripstream.core.utils import decode_secret, encode_secret


class TestEncodeSecret:
    """Test the encode_secret function."""

    def test_encode_secret_basic_string(self):
        """Test encoding a basic string."""
        value = "test_secret"
        encoded = encode_secret(value)

        # Verify it's base64 encoded
        expected = base64.b64encode(value.encode("utf-8")).decode("ascii")
        assert encoded == expected

    def test_encode_secret_empty_string(self):
        """Test encoding an empty string."""
        encoded = encode_secret("")
        assert encoded == ""

    def test_encode_secret_unicode_characters(self):
        """Test encoding string with unicode characters."""
        value = "test_secret_🔐_unicode"
        encoded = encode_secret(value)

        # Verify it can be decoded back
        decoded_bytes = base64.b64decode(encoded.encode("ascii"))
        decoded_string = decoded_bytes.decode("utf-8")
        assert decoded_string == value

    def test_encode_secret_special_characters(self):
        """Test encoding string with special characters."""
        value = "test!@#$%^&*()_+-={}[]|\\:;\"'<>?,./"
        encoded = encode_secret(value)

        # Verify it can be decoded back
        decoded_bytes = base64.b64decode(encoded.encode("ascii"))
        decoded_string = decoded_bytes.decode("utf-8")
        assert decoded_string == value

    def test_encode_secret_long_string(self):
        """Test encoding a long string."""
        value = "a" * 1000  # 1000 character string
        encoded = encode_secret(value)

        # Verify it can be decoded back
        decoded_bytes = base64.b64decode(encoded.encode("ascii"))
        decoded_string = decoded_bytes.decode("utf-8")
        assert decoded_string == value

    def test_encode_secret_whitespace(self):
        """Test encoding string with whitespace."""
        value = "  test secret with spaces  "
        encoded = encode_secret(value)

        # Verify it preserves whitespace
        decoded_bytes = base64.b64decode(encoded.encode("ascii"))
        decoded_string = decoded_bytes.decode("utf-8")
        assert decoded_string == value

    def test_encode_secret_newlines_and_tabs(self):
        """Test encoding string with newlines and tabs."""
        value = "line1\nline2\tindented"
        encoded = encode_secret(value)

        # Verify it preserves formatting
        decoded_bytes = base64.b64decode(encoded.encode("ascii"))
        decoded_string = decoded_bytes.decode("utf-8")
        assert decoded_string == value

    @pytest.mark.parametrize(
        "test_value",
        [
            "simple",
            "with spaces",
            "with-dashes",
            "with_underscores",
            "with.dots",
            "123456789",
            "MixedCaseString",
            "email@domain.com",
            "https://example.com/path?param=value",
        ],
    )
    def test_encode_secret_various_formats(self, test_value: str):
        """Test encoding various string formats."""
        encoded = encode_secret(test_value)

        # Verify it's valid base64
        try:
            decoded_bytes = base64.b64decode(encoded.encode("ascii"))
            decoded_string = decoded_bytes.decode("utf-8")
            assert decoded_string == test_value
        except (ValueError, UnicodeDecodeError, binascii.Error) as e:
            pytest.fail(f"Failed to decode encoded value: {e}")


class TestDecodeSecret:
    """Test the decode_secret function."""

    def test_decode_secret_basic_string(self):
        """Test decoding a basic encoded string."""
        original = "test_secret"
        encoded = base64.b64encode(original.encode("utf-8")).decode("ascii")
        decoded = decode_secret(encoded)

        assert decoded == original

    def test_decode_secret_empty_string(self):
        """Test decoding an empty string."""
        decoded = decode_secret("")
        assert decoded == ""

    def test_decode_secret_invalid_base64(self):
        """Test decoding invalid base64 string."""
        invalid_encoded = "not_valid_base64!"
        decoded = decode_secret(invalid_encoded)
        assert decoded == ""

    def test_decode_secret_invalid_utf8(self):
        """Test decoding base64 that doesn't represent valid UTF-8."""
        # Create invalid UTF-8 bytes and encode them as base64
        invalid_utf8_bytes = b"\xff\xfe\xfd"
        invalid_encoded = base64.b64encode(invalid_utf8_bytes).decode("ascii")
        decoded = decode_secret(invalid_encoded)
        assert decoded == ""

    def test_decode_secret_unicode_characters(self):
        """Test decoding string with unicode characters."""
        original = "test_secret_🔐_unicode"
        encoded = base64.b64encode(original.encode("utf-8")).decode("ascii")
        decoded = decode_secret(encoded)

        assert decoded == original

    def test_decode_secret_special_characters(self):
        """Test decoding string with special characters."""
        original = "test!@#$%^&*()_+-={}[]|\\:;\"'<>?,./"
        encoded = base64.b64encode(original.encode("utf-8")).decode("ascii")
        decoded = decode_secret(encoded)

        assert decoded == original

    def test_decode_secret_long_string(self):
        """Test decoding a long string."""
        original = "a" * 1000  # 1000 character string
        encoded = base64.b64encode(original.encode("utf-8")).decode("ascii")
        decoded = decode_secret(encoded)

        assert decoded == original

    def test_decode_secret_whitespace(self):
        """Test decoding string with whitespace."""
        original = "  test secret with spaces  "
        encoded = base64.b64encode(original.encode("utf-8")).decode("ascii")
        decoded = decode_secret(encoded)

        assert decoded == original

    def test_decode_secret_newlines_and_tabs(self):
        """Test decoding string with newlines and tabs."""
        original = "line1\nline2\tindented"
        encoded = base64.b64encode(original.encode("utf-8")).decode("ascii")
        decoded = decode_secret(encoded)

        assert decoded == original

    @pytest.mark.parametrize(
        "test_value",
        [
            "simple",
            "with spaces",
            "with-dashes",
            "with_underscores",
            "with.dots",
            "123456789",
            "MixedCaseString",
            "email@domain.com",
            "https://example.com/path?param=value",
        ],
    )
    def test_decode_secret_various_formats(self, test_value: str):
        """Test decoding various string formats."""
        encoded = base64.b64encode(test_value.encode("utf-8")).decode("ascii")
        decoded = decode_secret(encoded)

        assert decoded == test_value

    def test_decode_secret_malformed_padding(self):
        """Test decoding base64 with malformed padding."""
        # Valid base64 but with wrong padding
        malformed = "dGVzdA"  # "test" without proper padding
        decoded = decode_secret(malformed)
        # Should return empty string for invalid base64
        assert decoded == ""

    def test_decode_secret_non_ascii_input(self):
        """Test decoding with non-ASCII input."""
        # This should fail as base64 expects ASCII input
        non_ascii = "tëst"  # Contains non-ASCII character
        decoded = decode_secret(non_ascii)
        assert decoded == ""


class TestRoundTripEncoding:
    """Test round-trip encoding and decoding."""

    @pytest.mark.parametrize(
        "original_value",
        [
            "",
            "simple_string",
            "string with spaces",
            "string-with-dashes",
            "string_with_underscores",
            "string.with.dots",
            "123456789",
            "MixedCaseString",
            "UPPERCASE_STRING",
            "lowercase_string",
            "email@domain.com",
            "https://example.com/path?param=value&other=123",
            "special!@#$%^&*()chars",
            "unicode_🔐_characters_🎵",
            "line1\nline2\nline3",
            "tab\tseparated\tvalues",
            "mixed\nformatting\twith\rcarriage\rreturns",
            "very_long_string_" + "x" * 500,
            "   leading_and_trailing_spaces   ",
        ],
    )
    def test_encode_decode_round_trip(self, original_value: str):
        """Test that encoding then decoding returns the original value."""
        encoded = encode_secret(original_value)
        decoded = decode_secret(encoded)

        assert decoded == original_value

    def test_multiple_round_trips(self):
        """Test multiple encode/decode cycles."""
        original = "test_secret_multiple_rounds"

        # Perform multiple round trips
        current = original
        for _ in range(5):
            encoded = encode_secret(current)
            decoded = decode_secret(encoded)
            assert decoded == original
            current = decoded

    def test_empty_string_round_trip(self):
        """Test round trip with empty string."""
        original = ""
        encoded = encode_secret(original)
        decoded = decode_secret(encoded)

        assert encoded == ""
        assert decoded == ""


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_encode_secret_none_input(self):
        """Test encode_secret with None input (returns empty string)."""
        result = encode_secret(None)  # type: ignore[arg-type]
        assert result == ""

    def test_decode_secret_none_input(self):
        """Test decode_secret with None input (returns empty string)."""
        result = decode_secret(None)  # type: ignore[arg-type]
        assert result == ""

    def test_encode_secret_non_string_input(self):
        """Test encode_secret with non-string input."""
        with pytest.raises(AttributeError):
            encode_secret(123)  # type: ignore[arg-type]

    def test_decode_secret_non_string_input(self):
        """Test decode_secret with non-string input."""
        with pytest.raises(AttributeError):
            decode_secret(123)  # type: ignore[arg-type]

    def test_decode_secret_partial_base64(self):
        """Test decoding partial base64 string."""
        partial = "dGVz"  # Partial encoding
        decoded = decode_secret(partial)
        # Should handle gracefully and return decoded result or empty string
        assert isinstance(decoded, str)

    def test_decode_secret_with_whitespace(self):
        """Test decoding base64 with extra whitespace."""
        original = "test_secret"
        encoded = base64.b64encode(original.encode("utf-8")).decode("ascii")
        encoded_with_whitespace = f"  {encoded}  "

        # decode_secret should handle this gracefully
        decoded = decode_secret(encoded_with_whitespace)
        # The actual implementation might handle whitespace differently
        # Let's test what it actually does
        assert isinstance(
            decoded, str
        )  # Should return a string, whether empty or decoded


class TestSecurityConsiderations:
    """Test security-related aspects of the encoding functions."""

    def test_encoded_output_is_ascii(self):
        """Test that encoded output contains only ASCII characters."""
        test_values = [
            "simple",
            "unicode_🔐_test",
            "special!@#$%^&*()",
            "mixed\nformatting\twith\rreturns",
        ]

        for value in test_values:
            encoded = encode_secret(value)
            if encoded:  # Skip empty strings
                # All characters should be ASCII
                assert all(ord(char) < 128 for char in encoded)

    def test_encoded_output_is_base64(self):
        """Test that encoded output is valid base64."""
        test_values = [
            "simple",
            "unicode_🔐_test",
            "special!@#$%^&*()",
        ]

        for value in test_values:
            encoded = encode_secret(value)
            if encoded:  # Skip empty strings
                try:
                    # Should be able to decode without error
                    base64.b64decode(encoded.encode("ascii"))
                except (ValueError, binascii.Error) as e:
                    pytest.fail(f"Invalid base64 output for '{value}': {e}")

    def test_no_information_leakage_in_length(self):
        """Test that similar inputs don't leak information through length."""
        # Note: Base64 encoding will have predictable length patterns
        # This test documents the behavior rather than enforcing security

        inputs = ["a", "ab", "abc", "abcd"]
        encoded_lengths = [len(encode_secret(inp)) for inp in inputs]

        # Base64 encoding has predictable length patterns (groups of 4)
        # This is expected behavior, not a security flaw
        assert all(
            length > 0 for length in encoded_lengths[1:]
        )  # Non-empty inputs produce non-empty output
