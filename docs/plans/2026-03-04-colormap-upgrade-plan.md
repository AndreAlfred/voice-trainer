# Colormap Upgrade Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the 3-stop custom colormap with matplotlib's perceptually uniform colormaps sampled at 256 points, giving 6-8 perceptible color zones across the dynamic range.

**Architecture:** Remove `color_floor`/`color_mid`/`color_peak` from AppSettings, add `colormap_name: str`. Sample the named matplotlib colormap at 256 points and convert to a pyqtgraph `ColorMap`. Replace the 3-color-picker UI with 4 preset buttons (Inferno, Viridis, Magma, Terrain) with active-highlight.

**Tech Stack:** matplotlib.cm, numpy, pyqtgraph, PySide6

---

### Task 1: Update AppSettings — remove color tuples, add colormap_name

**Files:**
- Modify: `ui/settings.py`
- Test: `tests/test_settings.py`

**Step 1: Write the failing test**

Replace the body of `test_defaults_are_correct` in `tests/test_settings.py` and add a new test:

```python
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
```

**Step 2: Run test to verify it fails**

Run: `source venv/bin/activate && python -m pytest tests/test_settings.py::TestAppSettings::test_no_color_floor_field -v`
Expected: FAIL — `color_floor` still exists

**Step 3: Write minimal implementation**

In `ui/settings.py`, replace the AppSettings dataclass body. Remove these 3 fields:
```python
    color_floor: tuple = (13, 79, 82)
    color_mid:   tuple = (212, 80, 10)
    color_peak:  tuple = (255, 240, 160)
```

Add this field at the top of the dataclass (where the color fields were):
```python
    # Matplotlib colormap name (e.g. "inferno", "viridis", "magma", "gist_earth")
    colormap_name: str = "inferno"
```

Update the `load()` method — remove `"color_floor", "color_mid", "color_peak"` from the tuple-conversion loop. The loop should become:
```python
            for key in ("f1_color", "f2_color", "background_color"):
                if key in data:
                    data[key] = tuple(data[key])
```

Update the comment at the top of the dataclass to reflect the change.

**Step 4: Run tests to verify they pass**

Run: `source venv/bin/activate && python -m pytest tests/test_settings.py -v`
Expected: ALL PASS (the `test_blur_sigma_default` test stays unchanged)

**Step 5: Commit**

```bash
git add ui/settings.py tests/test_settings.py
git commit -m "feat: replace color_floor/mid/peak with colormap_name in AppSettings"
```

---

### Task 2: Update spectrogram to use matplotlib colormaps

**Files:**
- Modify: `ui/spectrogram.py`
- Modify: `requirements.txt`
- Test: `tests/test_spectrogram.py`

**Step 1: Write the failing tests**

Add a new test class to `tests/test_spectrogram.py`:

```python
class TestMatplotlibColormap:
    """Verify matplotlib colormap integration."""

    def test_build_colormap_returns_pg_colormap(self, qt_app):
        """_build_colormap should return a pyqtgraph ColorMap."""
        import pyqtgraph as pg
        from ui.spectrogram import SpectrogramWidget
        w = SpectrogramWidget()
        cmap = w._build_colormap("inferno")
        assert isinstance(cmap, pg.ColorMap)

    def test_build_colormap_has_256_stops(self, qt_app):
        """Colormap should be sampled at 256 points."""
        from ui.spectrogram import SpectrogramWidget
        w = SpectrogramWidget()
        cmap = w._build_colormap("inferno")
        # pg.ColorMap stores positions; 256 sample points
        assert len(cmap.pos) == 256

    def test_build_colormap_invalid_falls_back_to_inferno(self, qt_app):
        """Invalid colormap name should fall back to inferno without error."""
        from ui.spectrogram import SpectrogramWidget
        w = SpectrogramWidget()
        cmap = w._build_colormap("nonexistent_colormap_xyz")
        assert cmap is not None

    def test_apply_settings_with_colormap_name(self, qt_app):
        """apply_settings should accept colormap_name and not raise."""
        from ui.spectrogram import SpectrogramWidget
        from ui.settings import AppSettings
        w = SpectrogramWidget()
        w.apply_settings(AppSettings(colormap_name="viridis"))
        # Should not raise
```

**Step 2: Run tests to verify they fail**

Run: `source venv/bin/activate && python -m pytest tests/test_spectrogram.py::TestMatplotlibColormap -v`
Expected: FAIL — no `_build_colormap` method

**Step 3: Write minimal implementation**

**Add `matplotlib` to `requirements.txt`:**
```
PySide6
pyqtgraph
sounddevice
numpy
scipy
matplotlib
pytest
```

**Install it:**
Run: `source venv/bin/activate && pip install matplotlib`

**In `ui/spectrogram.py`, add import after the existing imports (after line 17):**
```python
import matplotlib.cm as mpl_cm
```

**Add a `_build_colormap` method to `SpectrogramWidget` (after `_build_frequency_ticks`, before `add_column`):**

```python
    def _build_colormap(self, name: str) -> pg.ColorMap:
        """Sample a matplotlib colormap at 256 points and return a pg.ColorMap.

        Falls back to 'inferno' if the name is not found.
        """
        try:
            mpl_cmap = mpl_cm.get_cmap(name)
        except ValueError:
            mpl_cmap = mpl_cm.get_cmap("inferno")
        positions = np.linspace(0.0, 1.0, 256)
        colors = (mpl_cmap(positions) * 255).astype(np.uint8)
        return pg.ColorMap(pos=positions, color=colors)
```

**In `_setup_ui`, replace the 3-stop colormap block (lines 120-132) with:**

```python
        # Perceptually uniform colormap sampled at 256 points from matplotlib.
        # Default is 'inferno': black → purple → red → orange → yellow.
        colormap = self._build_colormap("inferno")
        self._image_item.setColorMap(colormap)
        self._image_item.setLevels([DISPLAY_DB_MIN, DISPLAY_DB_MAX])
```

**In `apply_settings`, replace the colormap block (lines 286-296) with:**

```python
        # Colormap
        colormap_name = getattr(settings, 'colormap_name', 'inferno')
        colormap = self._build_colormap(colormap_name)
        self._image_item.setColorMap(colormap)
        self._image_item.setLevels([settings.db_floor, settings.db_ceiling])
```

**Fix existing tests:** The `TestApplySettings` tests all construct `AppSettings()` which no longer has `color_floor` etc. — they should still work since they don't reference those fields. But verify by running:

Run: `source venv/bin/activate && python -m pytest tests/test_spectrogram.py -v`
Expected: ALL PASS

**Step 4: Commit**

```bash
git add ui/spectrogram.py requirements.txt tests/test_spectrogram.py
git commit -m "feat: use matplotlib colormaps sampled at 256 points"
```

---

### Task 3: Update settings panel — replace color pickers with matplotlib presets

**Files:**
- Modify: `ui/settings_panel.py`
- Test: `tests/test_settings_panel.py`

**Step 1: Write the failing tests**

Replace the full contents of `tests/test_settings_panel.py`:

```python
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
        assert len(panel._preset_buttons) == 4

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
```

**Step 2: Run tests to verify they fail**

Run: `source venv/bin/activate && python -m pytest tests/test_settings_panel.py::TestSettingsPanel::test_preset_buttons_exist -v`
Expected: FAIL — no `_preset_buttons` attribute

**Step 3: Write minimal implementation**

Replace `ui/settings_panel.py` with the updated version. Key changes:

**Update module docstring** — replace "4 preset buttons + Floor / Mid / Peak colour pickers" with "4 matplotlib colormap preset buttons".

**Remove the `PRESETS` class attribute** (lines 128-133). Replace with:

```python
    COLORMAP_PRESETS: dict = {
        "Inferno":  "inferno",
        "Viridis":  "viridis",
        "Magma":    "magma",
        "Terrain":  "gist_earth",
    }
```

**Replace `_colormap_section` method entirely:**

```python
    def _colormap_section(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)
        lay.addWidget(self._header("Colormap"))

        row = QHBoxLayout()
        row.setSpacing(3)
        self._preset_buttons: dict[str, QPushButton] = {}
        for label, cmap_name in self.COLORMAP_PRESETS.items():
            btn = QPushButton(label)
            btn.setFixedHeight(22)
            btn.clicked.connect(
                lambda _, name=cmap_name: self._select_colormap(name)
            )
            self._preset_buttons[cmap_name] = btn
            row.addWidget(btn)
        lay.addLayout(row)

        self._update_preset_highlight()
        return w
```

**Replace `_apply_preset` with two new methods:**

```python
    def _select_colormap(self, name: str) -> None:
        self._settings.colormap_name = name
        self._update_preset_highlight()
        self._emit()

    def _update_preset_highlight(self) -> None:
        active = self._settings.colormap_name
        for cmap_name, btn in self._preset_buttons.items():
            if cmap_name == active:
                btn.setStyleSheet(
                    "font-size: 10px; border-radius: 3px; "
                    "border: 2px solid #c8c8d4; background-color: #2a2a4a;"
                )
            else:
                btn.setStyleSheet(
                    "font-size: 10px; border-radius: 3px;"
                )
```

**Remove the 3 `ColorButton` instances** — delete `self._c_floor`, `self._c_mid`, `self._c_peak` and the pickers HBoxLayout from `_colormap_section`.

**Keep `ColorButton` class** — it's still used by the Formant Dots section (`_f1_btn`, `_f2_btn`) and Background section (`_bg_btn`).

**Step 4: Run all tests**

Run: `source venv/bin/activate && python -m pytest tests/test_settings_panel.py -v`
Expected: ALL PASS (7 tests)

**Step 5: Commit**

```bash
git add ui/settings_panel.py tests/test_settings_panel.py
git commit -m "feat: replace color pickers with matplotlib colormap presets"
```

---

### Task 4: Run full test suite and verify

**Step 1: Run all tests**

Run: `source venv/bin/activate && python -m pytest tests/ -v`
Expected: ALL PASS (~53-55 tests)

If any tests fail due to references to the removed `color_floor`/`color_mid`/`color_peak` fields, fix them — these fields no longer exist.

**Step 2: Manual smoke test**

Run: `source venv/bin/activate && python main.py`

Verify:
1. Spectrogram displays with the inferno colormap (black → purple → red → orange → yellow)
2. Open Settings sidebar → Colormap section shows 4 buttons: Inferno, Viridis, Magma, Terrain
3. Inferno button has a highlight border (active)
4. Click Viridis — spectrogram changes to purple → teal → green → yellow, Viridis button highlights
5. Click Terrain — earth tones appear
6. Floor/Mid/Peak color picker buttons are gone
7. All other settings still work (dB range, scroll window, dots, overlays, background, blur)
8. Close and reopen — the selected colormap persists

**Step 3: Commit any fixes**

If smoke test revealed issues, fix and commit.
