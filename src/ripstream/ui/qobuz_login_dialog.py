# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Browser-based Qobuz login dialog.

Qobuz no longer accepts plain ``email`` + ``password`` against the
``user/login`` endpoint for third-party clients. Authentication now goes
through the official Qobuz web flow, which issues a ``user_auth_token``
that can be reused for subsequent API calls.

This dialog embeds a Qt WebEngine view pointed at
``https://play.qobuz.com/login`` and intercepts the JSON response of the
``/api.json/0.2/user/login`` request the web app makes. Once the response
is observed the dialog emits the captured ``user_id`` and
``user_auth_token`` and closes itself.
"""

from __future__ import annotations

import json
import logging
import re

from PyQt6.QtCore import QObject, QUrl, pyqtSignal, pyqtSlot
from PyQt6.QtWebEngineCore import (
    QWebEnginePage,
    QWebEngineProfile,
    QWebEngineScript,
)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QVBoxLayout,
)

logger = logging.getLogger(__name__)

QOBUZ_LOGIN_URL = "https://play.qobuz.com/login"
QOBUZ_LOGIN_API_PATTERN = re.compile(
    r"https?://(?:www\.)?qobuz\.com/api\.json/0\.2/user/login"
)

_INTERCEPT_MARKER = "__RIPSTREAM_QOBUZ_TOKEN__"

_INTERCEPT_SCRIPT = f"""
(function () {{
    if (window.__ripstreamQobuzInstalled) {{
        return;
    }}
    window.__ripstreamQobuzInstalled = true;

    const MARKER = "{_INTERCEPT_MARKER}";
    const ENDPOINT_RE = /\\/api\\.json\\/0\\.2\\/user\\/login/;

    const emit = (payload) => {{
        try {{
            const userId = payload && payload.user && payload.user.id;
            const token = payload && payload.user_auth_token;
            if (userId && token) {{
                console.log(MARKER + JSON.stringify({{
                    user_id: String(userId),
                    user_auth_token: String(token),
                }}));
            }}
        }} catch (err) {{
            // Swallow to avoid breaking the page.
        }}
    }};

    const originalFetch = window.fetch;
    if (typeof originalFetch === "function") {{
        window.fetch = async function (...args) {{
            const response = await originalFetch.apply(this, args);
            try {{
                const url = (typeof args[0] === "string")
                    ? args[0]
                    : (args[0] && args[0].url) || "";
                if (ENDPOINT_RE.test(url)) {{
                    response.clone().json().then(emit).catch(() => {{}});
                }}
            }} catch (err) {{
                // ignore
            }}
            return response;
        }};
    }}

    const OriginalXhr = window.XMLHttpRequest;
    if (OriginalXhr) {{
        const open = OriginalXhr.prototype.open;
        OriginalXhr.prototype.open = function (method, url) {{
            this.__ripstream_url = url || "";
            return open.apply(this, arguments);
        }};

        const send = OriginalXhr.prototype.send;
        OriginalXhr.prototype.send = function (...args) {{
            this.addEventListener("load", () => {{
                try {{
                    if (
                        this.__ripstream_url
                        && ENDPOINT_RE.test(this.__ripstream_url)
                    ) {{
                        emit(JSON.parse(this.responseText));
                    }}
                }} catch (err) {{
                    // ignore
                }}
            }});
            return send.apply(this, args);
        }};
    }}
}})();
"""


class _TokenCapturePage(QWebEnginePage):
    """Custom page that surfaces injected ``console.log`` messages."""

    token_payload_received = pyqtSignal(str)

    def javaScriptConsoleMessage(  # noqa: N802 (Qt signature)
        self,
        level: QWebEnginePage.JavaScriptConsoleMessageLevel,
        message: str,
        line_number: int,
        source_id: str,
    ) -> None:
        """Forward marker-prefixed messages to listeners."""
        if message.startswith(_INTERCEPT_MARKER):
            payload = message[len(_INTERCEPT_MARKER) :]
            self.token_payload_received.emit(payload)
            return
        super().javaScriptConsoleMessage(level, message, line_number, source_id)


class QobuzLoginDialog(QDialog):
    """Modal dialog that captures a Qobuz user_auth_token via the web flow.

    Parameters
    ----------
    parent : QObject | None
        Parent widget passed through to :class:`QDialog`.

    Notes
    -----
    On successful capture, ``user_id`` and ``user_auth_token`` are stored
    on the instance and the dialog accepts itself. Callers should read
    :pyattr:`captured_user_id` and :pyattr:`captured_token` after
    :py:meth:`exec` returns ``QDialog.DialogCode.Accepted``.
    """

    captured = pyqtSignal(str, str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)  # type: ignore[arg-type]
        self.setWindowTitle("Sign in to Qobuz")
        self.resize(900, 700)
        self.captured_user_id: str | None = None
        self.captured_token: str | None = None
        self._build_ui()
        self._install_intercept_script()
        self._view.setUrl(QUrl(QOBUZ_LOGIN_URL))

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        instructions = QLabel(
            "Sign in to your Qobuz account in the window below. Once "
            "Qobuz accepts your credentials, ripstream will automatically "
            "capture the session token and close this dialog."
        )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)

        self._profile = QWebEngineProfile(self)
        self._page = _TokenCapturePage(self._profile, self._profile)
        self._page.token_payload_received.connect(self._on_token_payload)

        self._view = QWebEngineView(self)
        self._view.setPage(self._page)
        layout.addWidget(self._view, stretch=1)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel, self)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _install_intercept_script(self) -> None:
        script = QWebEngineScript()
        script.setName("ripstream-qobuz-token-capture")
        script.setSourceCode(_INTERCEPT_SCRIPT)
        script.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentCreation)
        script.setRunsOnSubFrames(True)
        script.setWorldId(QWebEngineScript.ScriptWorldId.MainWorld)
        self._page.scripts().insert(script)

    @pyqtSlot(str)
    def _on_token_payload(self, payload: str) -> None:
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            logger.warning("Failed to parse Qobuz token payload")
            return

        user_id = data.get("user_id")
        token = data.get("user_auth_token")
        if not user_id or not token:
            return

        self.captured_user_id = str(user_id)
        self.captured_token = str(token)
        self.captured.emit(self.captured_user_id, self.captured_token)
        self.accept()
