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

    def test_preset_buttons_exist(self, qt_app):
        from ui.settings import AppSettings
        from ui.settings_panel import SettingsPanel
        panel = SettingsPanel(AppSettings())
        assert hasattr(panel, '_preset_buttons')
        assert len(panel._preset_buttons) == 5
        assert "manuscript" in panel._preset_buttons

    def test_selecting_preset_emits_signal(self, qt_app):
        from ui.settings import AppSettings
        from ui.settings_panel import SettingsPanel
        received = []
        panel = SettingsPanel(AppSettings())
        panel.settings_changed.connect(lambda s: received.append(s))
        panel._select_colormap("viridis")
        assert len(received) == 1
        assert received[0].colormap_name == "viridis"

    def test_active_preset_highlighted(self, qt_app):
        from ui.settings import AppSettings
        from ui.settings_panel import SettingsPanel
        panel = SettingsPanel(AppSettings(colormap_name="viridis"))
        # The viridis button should have the active style
        viridis_btn = panel._preset_buttons["viridis"]
        assert "border: 2px solid" in viridis_btn.styleSheet()

    def test_blur_slider_exists(self, qt_app):
        from ui.settings import AppSettings
        from ui.settings_panel import SettingsPanel
        panel = SettingsPanel(AppSettings())
        assert hasattr(panel, '_blur_sl')

    def test_blur_slider_emits_signal(self, qt_app):
        from ui.settings import AppSettings
        from ui.settings_panel import SettingsPanel
        received = []
        panel = SettingsPanel(AppSettings())
        panel.settings_changed.connect(lambda s: received.append(s))
        panel._blur_sl.value_changed.emit(2.0)
        assert len(received) == 1
        assert received[0].blur_sigma == 2.0
