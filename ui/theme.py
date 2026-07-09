"""
ui/theme.py — Renaissance visual theme for the window chrome.

Single source of truth for the look of everything AROUND the spectrogram:
toolbar, title, pitch readout, settings panel. The palette draws on
renaissance manuscript pigments: parchment grounds, sepia ink, ultramarine
(lapis), vermillion, and gold-leaf ochre.

The spectrogram plot itself (colormap, formant dots, overlays) is styled
independently in ui/spectrogram.py and via AppSettings — not here.
"""

# ---------------------------------------------------------------------------
# Palette — renaissance pigments
# ---------------------------------------------------------------------------

PARCHMENT       = "#f2e8d5"   # aged paper ground
PARCHMENT_LIGHT = "#f9f2e3"   # raised panels / readouts
PARCHMENT_DARK  = "#e4d5b7"   # recessed areas, hover states
UMBER           = "#8a6f47"   # raw umber — borders and frames
SEPIA           = "#3b2f1e"   # ink — primary text
SEPIA_FAINT     = "#9c8a6a"   # faded ink — secondary text, silence
ULTRAMARINE     = "#274690"   # lapis lazuli — headers, emphasis
VERMILLION      = "#c8371f"   # rubrication red — active highlights
GOLD            = "#c9a227"   # gold leaf — slider accents

# Palatino ships with macOS and is named for Giambattista Palatino,
# a 16th-century calligrapher — the most renaissance font a Mac has.
SERIF_FAMILY = "Palatino"

# ---------------------------------------------------------------------------
# Application stylesheet
# ---------------------------------------------------------------------------

APP_STYLESHEET = f"""
QMainWindow, QWidget {{
    background-color: {PARCHMENT};
    color: {SEPIA};
    font-family: "{SERIF_FAMILY}";
}}

QToolBar {{
    background-color: {PARCHMENT_DARK};
    border-bottom: 1px solid {UMBER};
    spacing: 6px;
    padding: 2px 6px;
}}

QToolBar QToolButton {{
    background-color: {PARCHMENT_LIGHT};
    color: {SEPIA};
    border: 1px solid {UMBER};
    border-radius: 3px;
    padding: 3px 10px;
}}
QToolBar QToolButton:hover {{
    border-color: {ULTRAMARINE};
    color: {ULTRAMARINE};
}}
QToolBar QToolButton:checked {{
    background-color: {ULTRAMARINE};
    color: {PARCHMENT_LIGHT};
    border-color: {ULTRAMARINE};
}}

QDockWidget {{
    color: {SEPIA};
    font-weight: bold;
}}
QDockWidget::title {{
    background-color: {PARCHMENT_DARK};
    border-bottom: 1px solid {UMBER};
    padding: 5px;
    text-align: center;
}}

QLabel {{
    background: transparent;
}}

QPushButton {{
    background-color: {PARCHMENT_LIGHT};
    color: {SEPIA};
    border: 1px solid {UMBER};
    border-radius: 3px;
    padding: 3px 8px;
}}
QPushButton:hover {{
    border-color: {ULTRAMARINE};
    color: {ULTRAMARINE};
}}
QPushButton:pressed {{
    background-color: {PARCHMENT_DARK};
}}

QCheckBox {{
    color: {SEPIA};
    spacing: 6px;
}}
QCheckBox::indicator {{
    width: 14px;
    height: 14px;
    border: 1px solid {UMBER};
    border-radius: 3px;
    background-color: {PARCHMENT_LIGHT};
}}
QCheckBox::indicator:checked {{
    background-color: {ULTRAMARINE};
    border-color: {ULTRAMARINE};
}}

QSlider::groove:horizontal {{
    height: 4px;
    background: {PARCHMENT_DARK};
    border: 1px solid {UMBER};
    border-radius: 2px;
}}
QSlider::handle:horizontal {{
    width: 12px;
    height: 12px;
    margin: -5px 0;
    border-radius: 7px;
    background: {ULTRAMARINE};
    border: 1px solid {SEPIA};
}}
QSlider::sub-page:horizontal {{
    background: {GOLD};
    border: 1px solid {UMBER};
    border-radius: 2px;
}}

QScrollArea {{
    border: none;
}}
QScrollBar:vertical {{
    background: {PARCHMENT};
    width: 10px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {UMBER};
    border-radius: 5px;
    min-height: 24px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
"""
