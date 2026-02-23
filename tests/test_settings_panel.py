"""tests/test_settings_panel.py — Smoke tests for SettingsPanel."""

import sys
import pytest
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="session")
def qt_app():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


class TestSettingsPanel:

    def test_panel_instantiates(self, qt_app):
        from ui.settings import AppSettings
        from ui.settings_panel import SettingsPanel
        assert SettingsPanel(AppSettings()) is not None

    def test_panel_has_settings_changed_signal(self, qt_app):
        from ui.settings import AppSettings
        from ui.settings_panel import SettingsPanel
        assert hasattr(SettingsPanel(AppSettings()), "settings_changed")

    def test_applying_preset_emits_signal(self, qt_app):
        from ui.settings import AppSettings
        from ui.settings_panel import SettingsPanel
        received = []
        panel = SettingsPanel(AppSettings())
        panel.settings_changed.connect(lambda s: received.append(s))
        floor, mid, peak = (13, 2, 33), (166, 46, 0), (253, 246, 178)
        panel._apply_preset(floor, mid, peak)
        assert len(received) == 1
        assert received[0].color_floor == floor
        assert received[0].color_peak  == peak

    def test_color_button_stores_color(self, qt_app):
        from ui.settings_panel import ColorButton
        btn = ColorButton((100, 100, 100), "Test")
        btn.set_color((200, 50, 30))
        assert btn.color() == (200, 50, 30)
