# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Tests for the embedded Qobuz browser login dialog."""

from __future__ import annotations

import json
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

PyQt6 = pytest.importorskip("PyQt6")
pytest.importorskip("PyQt6.QtWebEngineWidgets")

from PyQt6.QtWidgets import QDialog  # noqa: E402

from ripstream.ui.qobuz_login_dialog import QobuzLoginDialog  # noqa: E402


def test_dialog_captures_payload_from_intercept_marker(qapp):
    dialog = QobuzLoginDialog()
    payload = json.dumps({
        "user_id": "42",
        "user_auth_token": "jwt.token.value",
    })
    dialog._on_token_payload(payload)
    assert dialog.captured_user_id == "42"
    assert dialog.captured_token == "jwt.token.value"
    assert dialog.result() == QDialog.DialogCode.Accepted


def test_dialog_ignores_invalid_payload(qapp):
    dialog = QobuzLoginDialog()
    dialog._on_token_payload("not-json")
    assert dialog.captured_user_id is None
    assert dialog.captured_token is None


def test_dialog_ignores_payload_missing_fields(qapp):
    dialog = QobuzLoginDialog()
    dialog._on_token_payload(json.dumps({"user_id": "1"}))
    assert dialog.captured_user_id is None
    assert dialog.captured_token is None
