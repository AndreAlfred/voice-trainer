# Customization Sidebar Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a collapsible settings dock that lets the user tune all visual parameters live, with changes auto-saved to `~/.voicetrainer/settings.json`.

**Architecture:** `AppSettings` dataclass owns all values and handles JSON persistence. `SettingsPanel` emits `settings_changed(AppSettings)` on every control change. `MainWindow` listens, calls `SpectrogramWidget.apply_settings()`, and updates the window background. The dock is hidden by default; a ⚙ toolbar button toggles it.

**Tech Stack:** Python 3.14, PySide6 6.10.2, pyqtgraph 0.14.0, numpy 2.4.2, dataclasses, json

**Design doc:** `docs/plans/2026-02-23-customization-and-ipa-design.md`

---

## Before You Start

```bash
cd ~/voice-trainer && source venv/bin/activate
pytest tests/ -v
```
Expected: **28 passed**

---

## Task 1: AppSettings — Data Model and Persistence

**Files:**
- Create: `ui/settings.py`
- Create: `tests/test_settings.py`

### Step 1: Write the failing tests

Create `tests/test_settings.py`:

```python
"""tests/test_settings.py — Tests for AppSettings load/save/defaults."""

import pytest


class TestAppSettings:

    def test_defaults_are_correct(self):
        from ui.settings import AppSettings
        s = AppSettings()
        assert s.color_floor == (13, 79, 82)
        assert s.color_mid   == (212, 80, 10)
        assert s.color_peak  == (255, 240, 160)
        assert s.db_floor    == -60.0
        assert s.db_ceiling  ==   0.0
        assert s.display_seconds == 8.0
        assert s.f1_color    == (100, 180, 255)
        assert s.f2_color    == (80, 240, 120)
        assert s.dot_size    == 4
        assert s.singers_formant_visible is True
        assert s.background_color == (26, 26, 46)

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
```

### Step 2: Run — expect 5 failures

```bash
pytest tests/test_settings.py -v
```
Expected: `ModuleNotFoundError: No module named 'ui.settings'`

### Step 3: Create `ui/settings.py`

```python
"""
ui/settings.py — Application settings: data model and JSON persistence.

AppSettings is the single source of truth for all visual parameters.
Saved automatically to ~/.voicetrainer/settings.json on every change.
"""

from __future__ import annotations
import json
from dataclasses import dataclass, asdict
from pathlib import Path

SETTINGS_DIR  = Path.home() / ".voicetrainer"
SETTINGS_FILE = SETTINGS_DIR / "settings.json"


@dataclass
class AppSettings:
    # Colormap — three RGB tuples for the pyqtgraph ColorMap stops
    color_floor: tuple = (13, 79, 82)        # dark teal   #0d4f52
    color_mid:   tuple = (212, 80, 10)       # warm orange #d4500a
    color_peak:  tuple = (255, 240, 160)     # pale yellow #fff0a0

    # dB display range
    db_floor:   float = -60.0
    db_ceiling: float =   0.0

    # Scrolling window duration in seconds
    display_seconds: float = 8.0

    # Formant dot appearance
    f1_color: tuple = (100, 180, 255)   # light blue
    f2_color: tuple = (80,  240, 120)   # bright green
    dot_size:   int = 4

    # Overlay visibility
    singers_formant_visible: bool = True

    # Window / plot background
    background_color: tuple = (26, 26, 46)  # #1a1a2e

    @classmethod
    def load(cls) -> "AppSettings":
        """Load from SETTINGS_FILE. Returns defaults if file is missing or corrupt."""
        try:
            with open(SETTINGS_FILE) as f:
                data = json.load(f)
            for key in ("color_floor", "color_mid", "color_peak",
                        "f1_color", "f2_color", "background_color"):
                if key in data:
                    data[key] = tuple(data[key])
            valid = {k: v for k, v in data.items()
                     if k in cls.__dataclass_fields__}
            return cls(**valid)
        except Exception:
            return cls()

    def save(self) -> None:
        """Save to SETTINGS_FILE atomically. Creates directory if needed."""
        SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
        tmp = SETTINGS_FILE.with_suffix(".tmp")
        with open(tmp, "w") as f:
            json.dump(asdict(self), f, indent=2)
        tmp.replace(SETTINGS_FILE)
```

### Step 4: Run — expect 5 passed

```bash
pytest tests/test_settings.py -v && pytest tests/ -v
```
Expected: **5 passed** / **33 passed** total

### Step 5: Commit

```bash
git add ui/settings.py tests/test_settings.py
git commit -m "feat: add AppSettings with JSON persistence"
```

---

## Task 2: SettingsPanel Widget

**Files:**
- Create: `ui/settings_panel.py`
- Create: `tests/test_settings_panel.py`

### Step 1: Write the failing tests

Create `tests/test_settings_panel.py`:

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
```

### Step 2: Run — expect 4 failures

```bash
pytest tests/test_settings_panel.py -v
```
Expected: `ModuleNotFoundError: No module named 'ui.settings_panel'`

### Step 3: Create `ui/settings_panel.py`

```python
"""
ui/settings_panel.py — Visual customisation sidebar.

SettingsPanel emits settings_changed(AppSettings) on every control change.
MainWindow listens and applies updates live, then saves to disk.

Sections:
  Colormap      — 4 preset buttons + Floor / Mid / Peak colour pickers
  Display Range — dB Floor and dB Ceiling sliders
  Scroll Window — display_seconds slider
  Formant Dots  — F1 colour, F2 colour, dot size slider
  Overlays      — Singer's Formant band toggle
  Background    — background colour picker
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider,
    QPushButton, QCheckBox, QScrollArea, QFrame,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import QColorDialog

from ui.settings import AppSettings


# ---------------------------------------------------------------------------
# Reusable sub-widgets
# ---------------------------------------------------------------------------

class ColorButton(QPushButton):
    """Button showing a colour swatch; opens QColorDialog on click."""
    color_changed = Signal(tuple)   # emits (r, g, b)

    def __init__(self, color: tuple, label: str = "", parent=None):
        super().__init__(label, parent)
        self._color = color
        self._refresh_swatch()
        self.clicked.connect(self._pick)

    def set_color(self, color: tuple) -> None:
        self._color = color
        self._refresh_swatch()

    def color(self) -> tuple:
        return self._color

    def _refresh_swatch(self) -> None:
        r, g, b = self._color
        text = "black" if (r + g + b) > 380 else "white"
        self.setStyleSheet(
            f"background-color: rgb({r},{g},{b}); color: {text}; "
            f"border: 1px solid #444466; border-radius: 3px;"
        )

    def _pick(self) -> None:
        r, g, b = self._color
        chosen = QColorDialog.getColor(QColor(r, g, b), self, "Choose Colour")
        if chosen.isValid():
            self._color = (chosen.red(), chosen.green(), chosen.blue())
            self._refresh_swatch()
            self.color_changed.emit(self._color)


class LabeledSlider(QWidget):
    """Slider with a live value label and a permanent 'default: X' hint."""
    value_changed = Signal(float)

    def __init__(self, label, min_val, max_val, default_val,
                 current_val, unit="", decimals=0, parent=None):
        super().__init__(parent)
        self._decimals = decimals
        self._unit     = unit
        self._scale    = 10 ** decimals

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 2)
        layout.setSpacing(2)

        top = QHBoxLayout()
        top.addWidget(QLabel(label))
        top.addStretch()
        self._val_lbl = QLabel(self._fmt(current_val))
        self._val_lbl.setStyleSheet("color: #c8c8d4;")
        top.addWidget(self._val_lbl)
        layout.addLayout(top)

        self._slider = QSlider(Qt.Orientation.Horizontal)
        self._slider.setMinimum(int(min_val * self._scale))
        self._slider.setMaximum(int(max_val * self._scale))
        self._slider.setValue(int(current_val * self._scale))
        self._slider.valueChanged.connect(self._on_change)
        layout.addWidget(self._slider)

        hint = QLabel(f"default: {self._fmt(default_val)}")
        hint.setStyleSheet("color: #555577; font-size: 10px;")
        layout.addWidget(hint)

    def _fmt(self, val: float) -> str:
        if self._decimals == 0:
            return f"{int(round(val))}{self._unit}"
        return f"{val:.{self._decimals}f}{self._unit}"

    def _on_change(self, raw: int) -> None:
        val = raw / self._scale
        self._val_lbl.setText(self._fmt(val))
        self.value_changed.emit(val)

    def set_value(self, val: float) -> None:
        self._slider.blockSignals(True)
        self._slider.setValue(int(val * self._scale))
        self._slider.blockSignals(False)
        self._val_lbl.setText(self._fmt(val))


# ---------------------------------------------------------------------------
# Main panel
# ---------------------------------------------------------------------------

class SettingsPanel(QWidget):
    """All visual customisation controls in a scrollable panel."""

    settings_changed = Signal(object)   # carries updated AppSettings

    PRESETS: dict = {
        "Voice": ((13, 79, 82),   (212, 80, 10),  (255, 240, 160)),
        "Magma": ((13, 2, 33),    (166, 46, 0),   (253, 246, 178)),
        "Ocean": ((5, 10, 46),    (0, 102, 255),  (255, 255, 255)),
        "Ember": ((26, 5, 0),     (192, 57, 43),  (255, 179, 71)),
    }

    def __init__(self, settings: AppSettings, parent=None):
        super().__init__(parent)
        self._settings = settings
        self.setMinimumWidth(230)
        self._build()

    def _build(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        outer.addWidget(scroll)

        container = QWidget()
        scroll.setWidget(container)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(14)

        for section in [
            self._colormap_section,
            self._db_section,
            self._window_section,
            self._dots_section,
            self._overlays_section,
            self._background_section,
        ]:
            layout.addWidget(section())
            layout.addWidget(self._divider())

        layout.addStretch()

    # ------------------------------------------------------------------
    # Section builders
    # ------------------------------------------------------------------

    def _divider(self) -> QFrame:
        f = QFrame()
        f.setFrameShape(QFrame.Shape.HLine)
        f.setStyleSheet("color: #2a2a4a;")
        return f

    def _header(self, text: str) -> QLabel:
        lbl = QLabel(text.upper())
        font = QFont()
        font.setBold(True)
        font.setPointSize(9)
        lbl.setFont(font)
        lbl.setStyleSheet("color: #888aaa; letter-spacing: 1px;")
        return lbl

    def _colormap_section(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)
        lay.addWidget(self._header("Colormap"))

        row = QHBoxLayout()
        row.setSpacing(3)
        for name, (floor, mid, peak) in self.PRESETS.items():
            btn = QPushButton(name)
            btn.setFixedHeight(22)
            btn.setStyleSheet("font-size: 10px; border-radius: 3px;")
            btn.clicked.connect(
                lambda _, f=floor, m=mid, p=peak: self._apply_preset(f, m, p)
            )
            row.addWidget(btn)
        lay.addLayout(row)

        self._c_floor = ColorButton(self._settings.color_floor, "Floor")
        self._c_mid   = ColorButton(self._settings.color_mid,   "Mid")
        self._c_peak  = ColorButton(self._settings.color_peak,  "Peak")
        self._c_floor.color_changed.connect(lambda c: self._set("color_floor", c))
        self._c_mid.color_changed.connect(  lambda c: self._set("color_mid",   c))
        self._c_peak.color_changed.connect( lambda c: self._set("color_peak",  c))

        pickers = QHBoxLayout()
        pickers.setSpacing(4)
        for btn in (self._c_floor, self._c_mid, self._c_peak):
            pickers.addWidget(btn)
        lay.addLayout(pickers)
        return w

    def _apply_preset(self, floor: tuple, mid: tuple, peak: tuple) -> None:
        self._settings.color_floor = floor
        self._settings.color_mid   = mid
        self._settings.color_peak  = peak
        self._c_floor.set_color(floor)
        self._c_mid.set_color(mid)
        self._c_peak.set_color(peak)
        self._emit()

    def _db_section(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0); lay.setSpacing(6)
        lay.addWidget(self._header("Display Range"))
        self._db_floor_sl = LabeledSlider(
            "dB Floor", -80, -20, -60, self._settings.db_floor, unit=" dB")
        self._db_ceil_sl  = LabeledSlider(
            "dB Ceiling", -20, 0, 0, self._settings.db_ceiling, unit=" dB")
        self._db_floor_sl.value_changed.connect(lambda v: self._set("db_floor",   v))
        self._db_ceil_sl.value_changed.connect( lambda v: self._set("db_ceiling", v))
        lay.addWidget(self._db_floor_sl)
        lay.addWidget(self._db_ceil_sl)
        return w

    def _window_section(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0); lay.setSpacing(6)
        lay.addWidget(self._header("Scroll Window"))
        self._sec_sl = LabeledSlider(
            "Duration", 2, 30, 8, self._settings.display_seconds,
            unit=" s", decimals=1)
        self._sec_sl.value_changed.connect(lambda v: self._set("display_seconds", v))
        lay.addWidget(self._sec_sl)
        return w

    def _dots_section(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0); lay.setSpacing(6)
        lay.addWidget(self._header("Formant Dots"))
        self._f1_btn = ColorButton(self._settings.f1_color, "F1 Colour")
        self._f2_btn = ColorButton(self._settings.f2_color, "F2 Colour")
        self._f1_btn.color_changed.connect(lambda c: self._set("f1_color", c))
        self._f2_btn.color_changed.connect(lambda c: self._set("f2_color", c))
        row = QHBoxLayout(); row.setSpacing(4)
        row.addWidget(self._f1_btn); row.addWidget(self._f2_btn)
        lay.addLayout(row)
        self._dot_sl = LabeledSlider(
            "Dot Size", 2, 10, 4, self._settings.dot_size, unit=" px")
        self._dot_sl.value_changed.connect(lambda v: self._set("dot_size", int(v)))
        lay.addWidget(self._dot_sl)
        return w

    def _overlays_section(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0); lay.setSpacing(6)
        lay.addWidget(self._header("Overlays"))
        self._sf_cb = QCheckBox("Singer's Formant Band")
        self._sf_cb.setChecked(self._settings.singers_formant_visible)
        self._sf_cb.toggled.connect(
            lambda v: self._set("singers_formant_visible", v))
        lay.addWidget(self._sf_cb)
        return w

    def _background_section(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0); lay.setSpacing(6)
        lay.addWidget(self._header("Background"))
        self._bg_btn = ColorButton(
            self._settings.background_color, "Background Colour")
        self._bg_btn.color_changed.connect(
            lambda c: self._set("background_color", c))
        lay.addWidget(self._bg_btn)
        return w

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _set(self, attr: str, value) -> None:
        setattr(self._settings, attr, value)
        self._emit()

    def _emit(self) -> None:
        self._settings.save()
        self.settings_changed.emit(self._settings)
```

### Step 4: Run — expect 4 passed

```bash
pytest tests/test_settings_panel.py -v && pytest tests/ -v
```
Expected: **4 passed** / **37 passed** total

### Step 5: Commit

```bash
git add ui/settings_panel.py tests/test_settings_panel.py
git commit -m "feat: add SettingsPanel with presets, sliders, and colour pickers"
```

---

## Task 3: SpectrogramWidget.apply_settings()

**Files:**
- Modify: `ui/spectrogram.py`
- Modify: `tests/test_spectrogram.py` (add 4 tests)

### Step 1: Write failing tests

Append this class to the bottom of `tests/test_spectrogram.py`:

```python
class TestApplySettings:

    def test_apply_settings_does_not_raise(self, qt_app):
        from ui.spectrogram import SpectrogramWidget
        from ui.settings import AppSettings
        SpectrogramWidget().apply_settings(AppSettings())

    def test_apply_settings_hides_singers_formant(self, qt_app):
        from ui.spectrogram import SpectrogramWidget
        from ui.settings import AppSettings
        w = SpectrogramWidget()
        w.apply_settings(AppSettings(singers_formant_visible=False))
        assert not w._singers_formant_region.isVisible()

    def test_apply_settings_resizes_buffer(self, qt_app):
        from ui.spectrogram import SpectrogramWidget
        from ui.settings import AppSettings
        w = SpectrogramWidget(display_seconds=8.0)
        original = w._n_time_cols
        w.apply_settings(AppSettings(display_seconds=4.0))
        assert w._n_time_cols < original
        assert w._buffer.shape[0] == w._n_time_cols
        assert len(w._f1_bins) == w._n_time_cols

    def test_apply_settings_restores_singers_formant(self, qt_app):
        from ui.spectrogram import SpectrogramWidget
        from ui.settings import AppSettings
        w = SpectrogramWidget()
        w.apply_settings(AppSettings(singers_formant_visible=False))
        w.apply_settings(AppSettings(singers_formant_visible=True))
        assert w._singers_formant_region.isVisible()
```

### Step 2: Run — expect 4 failures

```bash
pytest tests/test_spectrogram.py::TestApplySettings -v
```
Expected: `AttributeError: 'SpectrogramWidget' has no attribute 'apply_settings'`

### Step 3: Add `apply_settings()` to `ui/spectrogram.py`

Add this method to `SpectrogramWidget` after `add_formants()`:

```python
    def apply_settings(self, settings: object) -> None:
        """Apply all visual settings live — no restart needed.

        Args:
            settings: AppSettings instance from ui.settings.
        """
        import numpy as np
        import pyqtgraph as pg

        # Colormap
        colormap = pg.ColorMap(
            pos=np.array([0.0, 0.5, 1.0]),
            color=np.array([
                list(settings.color_floor) + [255],
                list(settings.color_mid)   + [255],
                list(settings.color_peak)  + [255],
            ], dtype=np.uint8),
        )
        self._image_item.setColorMap(colormap)
        self._image_item.setLevels([settings.db_floor, settings.db_ceiling])

        # Formant dots
        self._f1_scatter.setBrush(pg.mkBrush(*settings.f1_color, 200))
        self._f2_scatter.setBrush(pg.mkBrush(*settings.f2_color, 200))
        self._f1_scatter.setSize(settings.dot_size)
        self._f2_scatter.setSize(settings.dot_size)

        # Singer's formant band
        self._singers_formant_region.setVisible(settings.singers_formant_visible)

        # Background
        r, g, b = settings.background_color
        self._plot.setBackground(f"#{r:02x}{g:02x}{b:02x}")

        # Scroll buffer resize when display_seconds changes
        hop = self.n_fft // 2
        new_cols = int(settings.display_seconds * (self.sample_rate / hop))
        if new_cols != self._n_time_cols:
            new_buf = np.full(
                (new_cols, self._n_freq_bins),
                fill_value=settings.db_floor,
                dtype=np.float32,
            )
            copy = min(new_cols, self._n_time_cols)
            new_buf[-copy:] = self._buffer[-copy:]
            self._buffer = new_buf

            new_f1 = np.full(new_cols, np.nan, dtype=np.float32)
            new_f2 = np.full(new_cols, np.nan, dtype=np.float32)
            cf = min(new_cols, len(self._f1_bins))
            new_f1[-cf:] = self._f1_bins[-cf:]
            new_f2[-cf:] = self._f2_bins[-cf:]
            self._f1_bins = new_f1
            self._f2_bins = new_f2

            self._n_time_cols = new_cols
            self._plot.setXRange(0, new_cols, padding=0)
```

### Step 4: Run — expect 11 passed

```bash
pytest tests/test_spectrogram.py -v && pytest tests/ -v
```
Expected: **11 passed** / **41 passed** total

### Step 5: Commit

```bash
git add ui/spectrogram.py tests/test_spectrogram.py
git commit -m "feat: add SpectrogramWidget.apply_settings() for live visual updates"
```

---

## Task 4: MainWindow — Dock, Toolbar, and Wiring

**Files:**
- Modify: `ui/app.py`

No new unit tests — the "test" is launching the app and verifying the dock opens.

### Step 1: Replace `ui/app.py` with this content

```python
"""
ui/app.py — Main application window.

Loads AppSettings on startup, creates the spectrogram and pitch widgets,
wraps a SettingsPanel in a QDockWidget on the right, and wires everything
together so every settings change applies live and auto-saves to disk.
"""

import numpy as np
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QLabel, QDockWidget, QToolBar,
)
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QFont, QAction

from audio.capture import AudioCapture
from audio.analysis import compute_spectrogram_column, estimate_pitch, estimate_formants
from ui.settings import AppSettings
from ui.settings_panel import SettingsPanel
from ui.spectrogram import SpectrogramWidget
from ui.pitch_display import PitchDisplayWidget

SAMPLE_RATE      = 44100
BLOCK_SIZE       = 1024
N_FFT            = 2048
HOP_SIZE         = N_FFT // 2
TIMER_INTERVAL_MS = 16


class MainWindow(QMainWindow):
    """Main application window for the voice trainer."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Voice Trainer — Classical Singing Analysis")
        self.resize(1100, 650)

        self._settings = AppSettings.load()
        r, g, b = self._settings.background_color
        self.setStyleSheet(f"background-color: rgb({r},{g},{b});")

        self._capture = AudioCapture(sample_rate=SAMPLE_RATE, block_size=BLOCK_SIZE)
        self._audio_buffer = np.zeros(0, dtype=np.float32)

        self._setup_ui()
        self._setup_settings_dock()
        self._spectrogram.apply_settings(self._settings)

        self._capture.start()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._process_audio)
        self._timer.start(TIMER_INTERVAL_MS)

    def _setup_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        title = QLabel("VOICE TRAINER")
        title.setFont(QFont("Courier", 11))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFixedHeight(30)
        title.setStyleSheet(
            "color: #666688; background-color: #0d0d1a; letter-spacing: 4px;"
        )
        layout.addWidget(title)

        self._spectrogram = SpectrogramWidget(
            sample_rate=SAMPLE_RATE,
            n_fft=N_FFT,
            display_seconds=self._settings.display_seconds,
        )
        layout.addWidget(self._spectrogram, stretch=1)

        self._pitch_display = PitchDisplayWidget()
        layout.addWidget(self._pitch_display)

    def _setup_settings_dock(self) -> None:
        self._settings_panel = SettingsPanel(self._settings)
        self._settings_panel.settings_changed.connect(self._on_settings_changed)

        dock = QDockWidget("Visual Settings", self)
        dock.setObjectName("settings_dock")
        dock.setWidget(self._settings_panel)
        dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetClosable |
            QDockWidget.DockWidgetFeature.DockWidgetMovable
        )
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)
        dock.hide()
        self._settings_dock = dock

        toolbar = QToolBar("Settings", self)
        toolbar.setMovable(False)
        toggle = QAction("⚙  Settings", self)
        toggle.setCheckable(True)
        toggle.toggled.connect(dock.setVisible)
        dock.visibilityChanged.connect(toggle.setChecked)
        toolbar.addAction(toggle)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, toolbar)

    def _on_settings_changed(self, settings: AppSettings) -> None:
        r, g, b = settings.background_color
        self.setStyleSheet(f"background-color: rgb({r},{g},{b});")
        self._spectrogram.apply_settings(settings)

    def _process_audio(self) -> None:
        new_chunks = []
        while True:
            chunk = self._capture.get_chunk()
            if chunk is None:
                break
            new_chunks.append(chunk)

        if not new_chunks:
            return

        self._audio_buffer = np.concatenate([self._audio_buffer] + new_chunks)
        latest_pitch = None

        while len(self._audio_buffer) >= N_FFT:
            window = self._audio_buffer[:N_FFT]
            spectrum_db  = compute_spectrogram_column(window, SAMPLE_RATE, N_FFT)
            pitch_hz     = estimate_pitch(window, SAMPLE_RATE)
            f1_hz, f2_hz = estimate_formants(window, SAMPLE_RATE)

            self._spectrogram.add_column(spectrum_db)
            self._spectrogram.add_formants(f1_hz, f2_hz)

            if pitch_hz is not None:
                latest_pitch = pitch_hz

            self._audio_buffer = self._audio_buffer[HOP_SIZE:]

        self._pitch_display.update_pitch(latest_pitch)

    def closeEvent(self, event) -> None:
        self._timer.stop()
        self._capture.stop()
        event.accept()
```

### Step 2: Verify clean import

```bash
cd ~/voice-trainer && source venv/bin/activate && python -c "from ui.app import MainWindow; print('OK')"
```
Expected: `OK`

### Step 3: Run the app and verify the dock works

```bash
python main.py
```

Verify:
- App opens normally
- A "⚙  Settings" button appears in the toolbar at the top
- Clicking it reveals the settings panel on the right
- Adjusting any slider or colour updates the spectrogram live
- Closing and reopening the app restores your last settings

### Step 4: Commit

```bash
git add ui/app.py
git commit -m "feat: wire settings dock and toolbar into MainWindow"
```

---

## Done

```bash
pytest tests/ -v
```
Expected: **41 passed**
