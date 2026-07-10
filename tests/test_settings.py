"""tests/test_settings.py — Tests for AppSettings load/save/defaults."""

import pytest


class TestAppSettings:

    def test_defaults_are_correct(self):
        from ui.settings import AppSettings
        s = AppSettings()
        assert s.colormap_name == "inferno"
        assert s.db_floor    == -60.0
        assert s.db_ceiling  ==   0.0
        assert s.display_seconds == 8.0
        assert s.f1_color    == (100, 180, 255)
        assert s.f2_color    == (80, 240, 120)
        assert s.dot_size    == 4
        assert s.singers_formant_visible is True
        assert s.background_color == (26, 26, 46)

    def test_colormap_name_default(self):
        from ui.settings import AppSettings
        s = AppSettings()
        assert s.colormap_name == "inferno"

    def test_no_color_floor_field(self):
        from ui.settings import AppSettings
        assert not hasattr(AppSettings(), 'color_floor')

    def test_blur_sigma_default(self):
        from ui.settings import AppSettings
        s = AppSettings()
        assert s.blur_sigma == 1.5

    def test_save_creates_file(self, tmp_path, monkeypatch):
        from ui import settings as m
        monkeypatch.setattr(m, "SETTINGS_DIR",  tmp_path)
        monkeypatch.setattr(m, "SETTINGS_FILE", tmp_path / "settings.json")
        from ui.settings import AppSettings
        AppSettings().save()
        assert (tmp_path / "settings.json").exists()

    def test_load_returns_saved_values(self, tmp_path, monkeypatch):
        from ui import settings as m
        monkeypatch.setattr(m, "SETTINGS_DIR",  tmp_path)
        monkeypatch.setattr(m, "SETTINGS_FILE", tmp_path / "settings.json")
        from ui.settings import AppSettings
        AppSettings(db_floor=-45.0, dot_size=7).save()
        loaded = AppSettings.load()
        assert loaded.db_floor == -45.0
        assert loaded.dot_size == 7

    def test_load_returns_defaults_when_file_missing(self, tmp_path, monkeypatch):
        from ui import settings as m
        monkeypatch.setattr(m, "SETTINGS_DIR",  tmp_path)
        monkeypatch.setattr(m, "SETTINGS_FILE", tmp_path / "missing.json")
        from ui.settings import AppSettings
        assert AppSettings.load().db_floor == -60.0

    def test_load_returns_defaults_on_corrupt_json(self, tmp_path, monkeypatch):
        from ui import settings as m
        bad = tmp_path / "settings.json"
        bad.write_text("not valid json {{{{")
        monkeypatch.setattr(m, "SETTINGS_DIR",  tmp_path)
        monkeypatch.setattr(m, "SETTINGS_FILE", bad)
        from ui.settings import AppSettings
        assert AppSettings.load().db_floor == -60.0
