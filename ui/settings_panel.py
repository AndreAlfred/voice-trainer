"""
ui/settings_panel.py — Visual customisation sidebar.

SettingsPanel emits settings_changed(AppSettings) on every control change.
MainWindow listens and applies updates live, then saves to disk.

Sections:
  Colormap      — 4 matplotlib colormap preset buttons
  Display Range — dB Floor and dB Ceiling sliders
  Scroll Window — display_seconds slider
  Formant Dots  — F1 colour, F2 colour, dot size slider
  Overlays      — Singer's Formant band toggle
  Background    — background colour picker
  Smoothing     — blur sigma slider
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider,
    QPushButton, QCheckBox, QScrollArea, QFrame,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import QColorDialog

from ui import theme
from ui.ornaments import attach_glow
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
        attach_glow(self)

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
            f"border: 2px ridge {theme.BRASS_DARK}; border-radius: 4px;"
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
        self._val_lbl.setStyleSheet(f"color: {theme.ULTRAMARINE};")
        top.addWidget(self._val_lbl)
        layout.addLayout(top)

        self._slider = QSlider(Qt.Orientation.Horizontal)
        self._slider.setMinimum(int(min_val * self._scale))
        self._slider.setMaximum(int(max_val * self._scale))
        self._slider.setValue(int(current_val * self._scale))
        self._slider.valueChanged.connect(self._on_change)
        layout.addWidget(self._slider)

        hint = QLabel(f"default: {self._fmt(default_val)}")
        hint.setStyleSheet(f"color: {theme.SEPIA_FAINT}; font-size: 10px;")
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

    COLORMAP_PRESETS: dict = {
        "Inferno":  "inferno",
        "Viridis":  "viridis",
        "Magma":    "magma",
        "Terrain":  "gist_earth",
    }

    def __init__(self, settings: AppSettings, parent=None):
        super().__init__(parent)
        self._settings = settings
        self.setMinimumWidth(230)
        # Parchment sheet backdrop (textured via the app stylesheet)
        self.setObjectName("settings_panel")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
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
            self._blur_section,
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
        f.setFixedHeight(2)
        f.setStyleSheet(
            "border: none; background: qlineargradient(x1:0, y1:0, x2:1, y2:0,"
            f" stop:0 transparent, stop:0.5 {theme.BRASS}, stop:1 transparent);"
        )
        return f

    def _header(self, text: str) -> QLabel:
        # Rubricated section header — red ink with a leaf fleuron, the way
        # scribes marked new sections
        lbl = QLabel(f"{theme.RUBRIC_LEAF} {text.upper()}")
        font = QFont(theme.SERIF_FAMILY)
        font.setBold(True)
        font.setPointSize(11)
        lbl.setFont(font)
        lbl.setStyleSheet(f"color: {theme.VERMILLION}; letter-spacing: 2px;")
        return lbl

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
            btn.setFixedHeight(24)
            attach_glow(btn)
            btn.clicked.connect(
                lambda _, name=cmap_name: self._select_colormap(name)
            )
            self._preset_buttons[cmap_name] = btn
            row.addWidget(btn)
        lay.addLayout(row)

        self._update_preset_highlight()
        return w

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
                    f"border: 2px solid {theme.ULTRAMARINE}; "
                    f"background-color: {theme.PARCHMENT_DARK}; "
                    f"color: {theme.ULTRAMARINE};"
                )
            else:
                btn.setStyleSheet(
                    "font-size: 10px; border-radius: 3px;"
                )

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

    def _blur_section(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0); lay.setSpacing(6)
        lay.addWidget(self._header("Smoothing"))
        self._blur_sl = LabeledSlider(
            "Blur Sigma", 0.0, 4.0, 1.5, self._settings.blur_sigma,
            decimals=1)
        self._blur_sl.value_changed.connect(
            lambda v: self._set("blur_sigma", v))
        lay.addWidget(self._blur_sl)
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
