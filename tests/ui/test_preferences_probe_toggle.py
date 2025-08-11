# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Tests for the 'Probe audio technicals' preference wiring."""

from __future__ import annotations

import pytest

from ripstream.config.user import UserConfig
from ripstream.ui.preferences import PreferencesDialog


@pytest.fixture
def dialog(qapp) -> PreferencesDialog:
    return PreferencesDialog(UserConfig())


def _get_downloads_tab(dialog: PreferencesDialog):
    # Tab order: General, Services, Downloads, Audio, Advanced
    return dialog.tab_widget.widget(2)


def test_loads_probe_toggle_from_config(dialog: PreferencesDialog) -> None:
    # Default is False; checkbox should reflect that
    tab = _get_downloads_tab(dialog)
    dialog.load_config()
    assert hasattr(tab, "probe_audio_technicals")
    assert tab.probe_audio_technicals.isChecked() is False

    # If config is True, it should reflect as checked
    dialog.config.downloads.probe_audio_technicals = True
    dialog.load_config()
    assert tab.probe_audio_technicals.isChecked() is True


def test_saves_probe_toggle_to_config(dialog: PreferencesDialog) -> None:
    tab = _get_downloads_tab(dialog)
    dialog.load_config()

    # Flip the UI and save
    tab.probe_audio_technicals.setChecked(True)
    dialog.save_config()
    assert dialog.config.downloads.probe_audio_technicals is True

    # Flip back and save again
    tab.probe_audio_technicals.setChecked(False)
    dialog.save_config()
    assert dialog.config.downloads.probe_audio_technicals is False
