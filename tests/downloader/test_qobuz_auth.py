# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Tests for the new browser-token Qobuz authentication path."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from ripstream.downloader.config import DownloaderConfig
from ripstream.downloader.exceptions import AuthenticationError
from ripstream.downloader.qobuz.client import QobuzClient
from ripstream.downloader.qobuz.models import QobuzCredentials
from ripstream.downloader.session import SessionManager


@pytest.fixture
def client():
    config = DownloaderConfig()
    return QobuzClient(SessionManager(config))


def _credentials(**overrides) -> QobuzCredentials:
    base = {
        "email_or_userid": "12345",
        "password_or_token": "tok",
        "app_id": "798273057",
        "secrets": ["s1"],
        "use_auth_token": True,
    }
    base.update(overrides)
    return QobuzCredentials(**base)


class TestRedaction:
    def test_redacts_password(self):
        out = QobuzClient._redact_auth_payload({
            "email": "a@b",
            "password": "secret",
            "app_id": "1",
        })
        assert out["password"] == "***REDACTED***"
        assert out["email"] == "a@b"

    def test_redacts_user_auth_token(self):
        out = QobuzClient._redact_auth_payload({
            "user_id": "1",
            "user_auth_token": "jwt.payload.sig",
            "app_id": "1",
        })
        assert out["user_auth_token"] == "***REDACTED***"

    def test_handles_non_dict(self):
        assert QobuzClient._redact_auth_payload("nope") == "nope"

    def test_keeps_empty_values_unchanged(self):
        out = QobuzClient._redact_auth_payload({"password": ""})
        assert out == {"password": ""}


class TestBuildLoginParams:
    def test_token_mode(self):
        params = QobuzClient._build_login_params(_credentials())
        assert params == {
            "user_id": "12345",
            "user_auth_token": "tok",
            "app_id": "798273057",
        }

    def test_email_mode(self):
        params = QobuzClient._build_login_params(
            _credentials(
                use_auth_token=False, email_or_userid="u@x", password_or_token="p"
            )
        )
        assert params == {
            "email": "u@x",
            "password": "p",
            "app_id": "798273057",
        }


class TestValidateCredentials:
    def test_passes_with_complete_token_creds(self):
        QobuzClient._validate_credentials(_credentials())

    def test_token_mode_missing_token_raises(self):
        with pytest.raises(AuthenticationError, match="user id"):
            QobuzClient._validate_credentials(_credentials(password_or_token=""))

    def test_email_mode_missing_password_raises(self):
        with pytest.raises(AuthenticationError, match="no longer accepted"):
            QobuzClient._validate_credentials(
                _credentials(
                    use_auth_token=False,
                    email_or_userid="u",
                    password_or_token="",
                )
            )


class TestRaiseForLoginStatus:
    def test_200_is_noop(self):
        QobuzClient._raise_for_login_status(200, {}, _credentials())

    def test_401_token_mode_mentions_expiry(self):
        with pytest.raises(AuthenticationError, match="expired"):
            QobuzClient._raise_for_login_status(401, {}, _credentials())

    def test_401_email_mode_recommends_browser(self):
        with pytest.raises(AuthenticationError, match="Login with browser"):
            QobuzClient._raise_for_login_status(
                401, {}, _credentials(use_auth_token=False)
            )

    def test_400_mentions_app_id(self):
        with pytest.raises(AuthenticationError, match="app id"):
            QobuzClient._raise_for_login_status(400, {}, _credentials())

    def test_other_status_includes_message(self):
        with pytest.raises(AuthenticationError, match="status 500"):
            QobuzClient._raise_for_login_status(
                500, {"message": "boom"}, _credentials()
            )


class TestAuthenticateIntegration:
    @pytest.mark.asyncio
    async def test_token_mode_success(self, client):
        creds = _credentials()
        with (
            patch.object(
                client,
                "_api_request",
                new=AsyncMock(
                    return_value=(
                        200,
                        {
                            "user": {
                                "id": 12345,
                                "credential": {"parameters": {"x": 1}},
                            },
                            "user_auth_token": "tok",
                        },
                    )
                ),
            ),
            patch.object(client, "_get_valid_secret", new=AsyncMock(return_value="s1")),
        ):
            assert await client.authenticate(creds) is True
        assert client.logged_in is True
        assert client.user_auth_token == "tok"

    @pytest.mark.asyncio
    async def test_token_mode_401_surfaces_helpful_error(self, client):
        creds = _credentials()
        with (
            patch.object(
                client,
                "_api_request",
                new=AsyncMock(
                    return_value=(
                        401,
                        {"message": "User authentication is required."},
                    )
                ),
            ),
            pytest.raises(AuthenticationError, match="expired"),
        ):
            await client.authenticate(creds)
        assert client.logged_in is False
